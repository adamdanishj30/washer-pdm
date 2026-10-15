"""
Multimodal Predictive Maintenance (PdM) Data Capture Engine
Predictive Maintenance SideProject - Samsung WW10TP44DSX Washing Machine

Simultaneously queries and harmonizes:
1. Samsung SmartThings API (Cycle Phase, RPM, Water Temp, Water Level, Progress, Timing)
2. TP-Link Tapo P110 Local API (Active Power W, Voltage V, Current mA, Energy Wh)
3. ESP32 Multimodal Edge Rig (MPU-6050 3-Axis Kinematics + INMP441 Acoustic RMS)

Saves prediction-ready datasets into data/:
- data/live_multimodal_pdm_snapshot.json (Full JSON state snapshot)
- data/pdm_multimodal_prediction_dataset.csv (18-column ML training/inference table)
- data/pdm_feature_dictionary.json (Data contract and feature engineering schema)

Usage:
  py -3.12 firmware/capture_pdm_dataset.py --snapshot
  py -3.12 firmware/capture_pdm_dataset.py --record --interval 2 --duration 60
"""

import asyncio
import argparse
import datetime
import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Configurations
FIREBASE_HOST = os.getenv("FIREBASE_HOST", "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app")
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH", "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V")
TAPO_IP = os.getenv("TAPO_IP", "192.168.0.142")
TAPO_USER = os.getenv("TAPO_DEVICE_USER") or os.getenv("TAPO_EMAIL")
TAPO_PASS = os.getenv("TAPO_DEVICE_PASS") or os.getenv("TAPO_PASSWORD")
SMARTTHINGS_DEVICE_ID = os.getenv("SMARTTHINGS_DEVICE_ID")

sys.path.insert(0, str(BASE_DIR))
from firmware.cloud_multimodal_sync import get_valid_smartthings_token
from kasa import Discover, Credentials
from kasa.interfaces.energy import Energy

def fetch_smartthings_state() -> dict:
    """Fetch complete live machine state from Samsung SmartThings REST API."""
    if not SMARTTHINGS_DEVICE_ID:
        return {}
    token = get_valid_smartthings_token()
    if not token:
        return {}
    
    url = f"https://api.smartthings.com/v1/devices/{SMARTTHINGS_DEVICE_ID}/status"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.smartthings+json;v=1",
        "User-Agent": "PdM-DataCapture/1.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            main = data.get("components", {}).get("main", {})
            
            # Extract high-value predictive fields
            op = main.get("washerOperatingState", {})
            s_op = main.get("samsungce.washerOperatingState", {})
            spin = main.get("custom.washerSpinLevel", {})
            temp = main.get("custom.washerWaterTemperature", {})
            rinse = main.get("custom.washerRinseCycles", {})
            water = main.get("samsungce.washerWaterLevel", {})
            water_rep = main.get("samsungce.waterConsumptionReport", {})
            detergent = main.get("samsungce.autoDispenseDetergent", {})
            softener = main.get("samsungce.autoDispenseSoftener", {})
            lock = main.get("samsungce.kidsLock", {})

            spin_val = spin.get("washerSpinLevel", {}).get("value")
            try:
                target_rpm = int(spin_val) if spin_val and spin_val.isdigit() else 0
            except Exception:
                target_rpm = 0

            rinse_val = rinse.get("washerRinseCycles", {}).get("value")
            try:
                rinse_cycles = int(rinse_val) if rinse_val is not None and str(rinse_val).isdigit() else 0
            except Exception:
                rinse_cycles = 0

            cum_water_ml = water_rep.get("waterConsumption", {}).get("value", {}).get("cumulativeAmount", 0)

            return {
                "washer_job_state": op.get("washerJobState", {}).get("value", "none"),
                "machine_state": op.get("machineState", {}).get("value", "stop"),
                "progress_pct": s_op.get("progress", {}).get("value", 0),
                "operation_time_min": s_op.get("operationTime", {}).get("value", 0),
                "remaining_time_min": s_op.get("remainingTime", {}).get("value", 0),
                "scheduled_phases": s_op.get("scheduledPhases", {}).get("value", []),
                "target_rpm": target_rpm,
                "spin_level_str": spin_val or "none",
                "water_temperature": temp.get("washerWaterTemperature", {}).get("value", "cold"),
                "rinse_cycles": rinse_cycles,
                "water_level": water.get("waterLevel", {}).get("value") or "normal",
                "detergent_remaining": detergent.get("remainingAmount", {}).get("value", "unknown"),
                "detergent_density": detergent.get("density", {}).get("value", "high"),
                "detergent_amount": detergent.get("amount", {}).get("value", "standard"),
                "softener_remaining": softener.get("remainingAmount", {}).get("value", "unknown"),
                "softener_density": softener.get("density", {}).get("value", "normal"),
                "softener_amount": softener.get("amount", {}).get("value", "standard"),
                "cumulative_water_ml": cum_water_ml,
                "cumulative_water_l": round(cum_water_ml / 1000.0, 1),
                "kids_lock": lock.get("lockState", {}).get("value", "unlocked"),
                "smartthings_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
    except Exception as e:
        print(f"[WARN] SmartThings fetch error: {e}")
        return {}

async def fetch_tapo_telemetry() -> dict:
    """Fetch live electrical metrics directly from Tapo P110 via local KLAP."""
    try:
        creds = Credentials(TAPO_USER, TAPO_PASS) if TAPO_USER and TAPO_PASS else None
        devs = await Discover.discover(target=TAPO_IP, credentials=creds)
        if not devs or TAPO_IP not in devs:
            return {}
        dev = devs[TAPO_IP]
        await dev.update()
        em = dev.modules.get('Energy') or dev.modules.get(Energy)
        if not em:
            return {}
        
        power_w = float(em.current_consumption or 0.0)
        voltage_v = float(em.voltage or 240.0)
        current_a = float(em.current or 0.0)
        today_wh = float((em.consumption_today or 0.0) * 1000.0)
        month_kwh = float(em.consumption_this_month or 0.0)

        return {
            "power_w": round(power_w, 2),
            "voltage_v": round(voltage_v, 1),
            "current_ma": round(current_a * 1000.0, 1),
            "today_energy_wh": round(today_wh, 1),
            "month_energy_kwh": round(month_kwh, 3),
            "is_on": dev.is_on,
            "device_name": dev.alias,
            "model": dev.model,
            "tapo_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        print(f"[WARN] Tapo P110 fetch error: {e}")
        return {}

def fetch_esp32_telemetry() -> dict:
    """Fetch real-time vibration & acoustic RMS from Firebase RTDB (/live.json)."""
    url = f"{FIREBASE_HOST}/live.json?auth={FIREBASE_AUTH}"
    req = urllib.request.Request(url, headers={"User-Agent": "PdM-DataCapture/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data:
                return {}
            ax = float(data.get("ax", 0.0))
            ay = float(data.get("ay", 0.0))
            az = float(data.get("az", 0.0))
            rms = float(data.get("rms", 0.0))
            vibe = float(data.get("vibe", math.sqrt(ax*ax + ay*ay + az*az)))
            return {
                "accel_x": round(ax, 2),
                "accel_y": round(ay, 2),
                "accel_z": round(az, 2),
                "vibration_magnitude": round(vibe, 2),
                "audio_rms": round(rms, 1),
                "esp32_session": data.get("session", "unknown"),
                "esp32_uptime_s": data.get("uptime", 0),
                "esp32_sample_cnt": data.get("cnt", 0),
                "esp32_state": data.get("state", "IDLE"),
                "esp32_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
    except Exception as e:
        print(f"[WARN] ESP32 Firebase fetch error: {e}")
        return {}

def compute_pdm_features(st: dict, tapo: dict, esp: dict) -> dict:
    """
    Computes higher-order engineering and prognostics features:
    - Parasitic mechanical drag
    - Estimated laundry weight
    - Machine Health Index (0-100%)
    - Subsystem health indicators (Bearing, Damper)
    """
    pwr = tapo.get("power_w", 0.0)
    rms = esp.get("audio_rms", 120.0)
    vibe = esp.get("vibration_magnitude", 9.81)
    ay = esp.get("accel_y", 1.4)
    phase = st.get("washer_job_state", "none")
    rpm = st.get("target_rpm", 0)

    # 1. Load estimation (m = (P - 70) / 15.0 kg during sensing)
    if phase == "weightSensing" or (phase == "wash" and pwr > 75.0):
        est_kg = max(1.0, min(10.5, (pwr - 70.0) / 15.0))
    else:
        est_kg = 5.0 # Nominal default
    
    if est_kg < 3.2:
        load_class = "LIGHT"
    elif est_kg <= 6.8:
        load_class = "MEDIUM"
    else:
        load_class = "HEAVY"

    # 2. Expected power vs parasitic drag
    expected_w = 4.5
    if phase == "wash": expected_w = 140.0 + (est_kg * 12.0)
    elif phase == "rinse": expected_w = 160.0 + (est_kg * 14.0)
    elif phase == "spin": expected_w = 380.0 + ((rpm / 1400.0) * 180.0)

    parasitic_drag_w = max(0.0, pwr - expected_w) if pwr > expected_w and pwr < 1200.0 else 0.0
    parasitic_drag_pct = round((parasitic_drag_w / max(1.0, expected_w)) * 100.0, 1)

    # 3. Subsystem Health Indices (100% = Factory Fresh, <60% = Warning, <40% = Critical P-F Point)
    # Bearing Health: Sensitive to High-Frequency Acoustic RMS & Lateral Vibration Drag
    bearing_penalty = 0.0
    if rms > 220.0: bearing_penalty += (rms - 220.0) * 0.12
    if parasitic_drag_pct > 15.0: bearing_penalty += parasitic_drag_pct * 0.4
    bearing_health = round(max(15.0, min(100.0, 100.0 - bearing_penalty)), 1)

    # Damper Health: Sensitive to Vertical Bounce (ay) during High Spin
    damper_penalty = 0.0
    if abs(ay) > 18.0: damper_penalty += (abs(ay) - 18.0) * 2.5
    if vibe > 25.0 and rpm >= 1000: damper_penalty += (vibe - 25.0) * 1.5
    damper_health = round(max(20.0, min(100.0, 100.0 - damper_penalty)), 1)

    # Overall Composite Machine Health Index
    machine_health = round((bearing_health * 0.6) + (damper_health * 0.4), 1)

    return {
        "estimated_load_kg": round(est_kg, 1),
        "load_class": load_class,
        "expected_power_w": round(expected_w, 1),
        "parasitic_drag_w": round(parasitic_drag_w, 1),
        "parasitic_drag_pct": parasitic_drag_pct,
        "bearing_health_index": bearing_health,
        "damper_health_index": damper_health,
        "machine_health_index": machine_health
    }

def save_feature_dictionary():
    """Generates a formal data contract / feature dictionary in data/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dict_file = DATA_DIR / "pdm_feature_dictionary.json"
    schema = {
        "dataset_name": "Samsung WW10TP44DSX Multimodal Predictive Maintenance Dataset",
        "description": "Unified 31-feature prognostic dataset combining kinematics, acoustics, electrical power, and ground-truth machine states.",
        "pdm_framework": "P-F Interval Prognostics & Remaining Useful Life (RUL) Modeling",
        "features": {
            "timestamp_ms": {"type": "integer", "unit": "ms", "desc": "Unix epoch millisecond timestamp"},
            "iso_time": {"type": "string", "desc": "UTC ISO 8601 formatted datetime"},
            "phase": {"type": "categorical", "desc": "Ground truth cycle phase from SmartThings (none, weightSensing, wash, rinse, spin, finish)"},
            "machine_state": {"type": "categorical", "desc": "Machine running state (stop, run, pause)"},
            "progress_pct": {"type": "integer", "unit": "%", "desc": "Current cycle completion progress (0% - 100%)"},
            "remaining_time_min": {"type": "integer", "unit": "min", "desc": "Estimated remaining cycle time in minutes"},
            "target_rpm": {"type": "integer", "unit": "RPM", "desc": "Target centrifugal drum speed (0, 400, 800, 1000, 1200, 1400)"},
            "water_temperature": {"type": "categorical", "desc": "Selected water temp (cold, 20, 30, 40, 60, 90)"},
            "rinse_cycles": {"type": "integer", "unit": "count", "desc": "Configured wash rinse cycles (0 to 5)"},
            "accel_x": {"type": "float", "unit": "m/s^2", "desc": "Transverse lateral drum acceleration"},
            "accel_y": {"type": "float", "unit": "m/s^2", "desc": "Vertical acceleration (direct damper shock indicator)"},
            "accel_z": {"type": "float", "unit": "m/s^2", "desc": "Axial fore/aft acceleration (spider arm stability)"},
            "vibe_magnitude": {"type": "float", "unit": "m/s^2", "desc": "Euclidean resultant 3-axis vibration magnitude"},
            "audio_rms": {"type": "float", "unit": "RMS", "desc": "INMP441 MEMS microphone acoustic sound pressure (bearing friction)"},
            "power_w": {"type": "float", "unit": "W", "desc": "Tapo P110 active electrical motor & heater power"},
            "voltage_v": {"type": "float", "unit": "V", "desc": "Tapo P110 mains electrical supply voltage"},
            "current_ma": {"type": "float", "unit": "mA", "desc": "Tapo P110 electrical load current"},
            "today_energy_wh": {"type": "float", "unit": "Wh", "desc": "Cumulative electrical energy consumed today"},
            "month_energy_kwh": {"type": "float", "unit": "kWh", "desc": "Cumulative electrical energy consumed this month"},
            "is_on": {"type": "boolean", "desc": "Smart plug power relay state (true/false)"},
            "detergent_remaining": {"type": "categorical", "desc": "Auto-dispenser detergent reservoir level (unknown, normal, low)"},
            "softener_remaining": {"type": "categorical", "desc": "Auto-dispenser softener reservoir level (unknown, normal, low)"},
            "cumulative_water_l": {"type": "float", "unit": "L", "desc": "Cumulative water consumption report in Liters"},
            "kids_lock": {"type": "categorical", "desc": "Child safety lock status (locked, unlocked)"},
            "estimated_load_kg": {"type": "float", "unit": "kg", "desc": "AI estimated dry laundry mass from motor tumble inertia"},
            "load_class": {"type": "categorical", "desc": "Laundry classification (LIGHT, MEDIUM, HEAVY)"},
            "parasitic_drag_w": {"type": "float", "unit": "W", "desc": "Mechanical friction energy waste above baseline"},
            "parasitic_drag_pct": {"type": "float", "unit": "%", "desc": "Percentage excess energy waste caused by friction"},
            "bearing_health_index": {"type": "float", "unit": "%", "desc": "Continuous tub bearing health (100 = new, <40 = fail)"},
            "damper_health_index": {"type": "float", "unit": "%", "desc": "Continuous suspension damper health"},
            "machine_health_index": {"type": "float", "unit": "%", "desc": "Composite overall Machine Health Index (0-100%)"}
        }
    }
    with open(dict_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"[DATA DICTIONARY] Saved schema contract to: {dict_file.relative_to(BASE_DIR)}")

def append_to_prediction_csv(row: dict):
    """Appends unified multimodal sample to data/pdm_multimodal_prediction_dataset.csv."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_file = DATA_DIR / "pdm_multimodal_prediction_dataset.csv"
    headers = [
        "timestamp_ms", "iso_time", "phase", "machine_state", "progress_pct", "remaining_time_min",
        "target_rpm", "water_temperature", "rinse_cycles",
        "accel_x", "accel_y", "accel_z", "vibe_magnitude", "audio_rms",
        "power_w", "voltage_v", "current_ma", "today_energy_wh", "month_energy_kwh", "is_on",
        "detergent_remaining", "softener_remaining", "cumulative_water_l", "kids_lock",
        "estimated_load_kg", "load_class", "parasitic_drag_w", "parasitic_drag_pct",
        "bearing_health_index", "damper_health_index", "machine_health_index"
    ]
    file_exists = csv_file.is_file()
    with open(csv_file, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write(",".join(headers) + "\n")
        vals = [str(row.get(h, "")) for h in headers]
        f.write(",".join(vals) + "\n")

async def capture_snapshot() -> dict:
    """Executes a simultaneous single-shot pull from all 3 APIs and returns the compiled payload."""
    print("\n" + "=" * 65)
    print("      MULTIMODAL PREDICITVE MAINTENANCE DATA CAPTURE ENGINE       ")
    print("=" * 65)
    print("1. Querying Samsung SmartThings Cloud REST API...")
    st = fetch_smartthings_state()

    print("2. Querying TP-Link Tapo P110 Local LAN (192.168.0.142)...")
    tapo = await fetch_tapo_telemetry()

    print("3. Querying ESP32 Edge Sensor Rig via Google Firebase RTDB...")
    esp = fetch_esp32_telemetry()

    print("4. Computing Predictive Maintenance Features & Prognostics...")
    pdm = compute_pdm_features(st, tapo, esp)

    now_ts = int(time.time() * 1000)
    iso_now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    full_payload = {
        "timestamp_ms": now_ts,
        "iso_time": iso_now,
        "smartthings": st,
        "tapo": tapo,
        "esp32": esp,
        "pdm_prognostics": pdm
    }

    # Flattened row for CSV
    row = {
        "timestamp_ms": now_ts,
        "iso_time": iso_now,
        "phase": st.get("washer_job_state", "none"),
        "machine_state": st.get("machine_state", "stop"),
        "progress_pct": st.get("progress_pct", 0),
        "remaining_time_min": st.get("remaining_time_min", 0),
        "target_rpm": st.get("target_rpm", 0),
        "water_temperature": st.get("water_temperature", "cold"),
        "rinse_cycles": st.get("rinse_cycles", 0),
        "accel_x": esp.get("accel_x", 0.0),
        "accel_y": esp.get("accel_y", 0.0),
        "accel_z": esp.get("accel_z", 0.0),
        "vibe_magnitude": esp.get("vibration_magnitude", 0.0),
        "audio_rms": esp.get("audio_rms", 0.0),
        "power_w": tapo.get("power_w", 0.0),
        "voltage_v": tapo.get("voltage_v", 240.0),
        "current_ma": tapo.get("current_ma", 0.0),
        "today_energy_wh": tapo.get("today_energy_wh", 0.0),
        "month_energy_kwh": tapo.get("month_energy_kwh", 0.0),
        "is_on": tapo.get("is_on", True),
        "detergent_remaining": st.get("detergent_remaining", "unknown"),
        "softener_remaining": st.get("softener_remaining", "unknown"),
        "cumulative_water_l": st.get("cumulative_water_l", 0.0),
        "kids_lock": st.get("kids_lock", "unlocked"),
        "estimated_load_kg": pdm["estimated_load_kg"],
        "load_class": pdm["load_class"],
        "parasitic_drag_w": pdm["parasitic_drag_w"],
        "parasitic_drag_pct": pdm["parasitic_drag_pct"],
        "bearing_health_index": pdm["bearing_health_index"],
        "damper_health_index": pdm["damper_health_index"],
        "machine_health_index": pdm["machine_health_index"]
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Save live JSON snapshot
    json_path = DATA_DIR / "live_multimodal_pdm_snapshot.json"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(full_payload, jf, indent=2)
    print(f"\n[OK] Saved Live State Snapshot -> {json_path.relative_to(BASE_DIR)}")

    # 2. Append to Master CSV dataset
    append_to_prediction_csv(row)
    csv_path = DATA_DIR / "pdm_multimodal_prediction_dataset.csv"
    print(f"[OK] Appended Sample to Master Dataset -> {csv_path.relative_to(BASE_DIR)}")

    # 3. Save / Update Feature Dictionary
    save_feature_dictionary()

    print("\n" + "-" * 65)
    print("      LIVE MULTIMODAL TELEMETRY SUMMARY")
    print("-" * 65)
    print(f"Machine Phase        : {st.get('washer_job_state', 'N/A').upper()} ({st.get('machine_state', 'N/A')})")
    print(f"Target Centrifugal   : {st.get('target_rpm', 0)} RPM | Water Temp: {st.get('water_temperature', 'cold')}")
    print(f"Active Power Load    : {tapo.get('power_w', 0.0):.2f} W ({tapo.get('voltage_v', 0.0):.1f} V | {tapo.get('current_ma', 0.0):.1f} mA)")
    print(f"Kinematic Vibration  : {esp.get('vibration_magnitude', 0.0):.2f} m/s^2 (X:{esp.get('accel_x',0.0)}, Y:{esp.get('accel_y',0.0)}, Z:{esp.get('accel_z',0.0)})")
    print(f"Acoustic Sound RMS   : {esp.get('audio_rms', 0.0):.1f}")
    print(f"Estimated Load Mass  : {pdm['estimated_load_kg']} kg ({pdm['load_class']})")
    print(f"Parasitic Energy Drag: {pdm['parasitic_drag_pct']}% ({pdm['parasitic_drag_w']} W excess friction)")
    print(f"Bearing Health Index : {pdm['bearing_health_index']}%")
    print(f"Damper Health Index  : {pdm['damper_health_index']}%")
    print(f"Machine Health Index : {pdm['machine_health_index']}% (OVERALL)")
    print("=" * 65 + "\n")

    return full_payload

async def continuous_recorder(interval: float, duration: float):
    """Continuously records multimodal telemetry at regular intervals."""
    start = time.time()
    count = 0
    print(f"[RECORDER] Starting continuous recording every {interval}s for {duration}s...")
    while time.time() - start < duration:
        await capture_snapshot()
        count += 1
        await asyncio.sleep(interval)
    print(f"[RECORDER COMPLETED] Captured {count} multimodal frames into data/pdm_multimodal_prediction_dataset.csv\n")

def main():
    parser = argparse.ArgumentParser(description="Multimodal Predictive Maintenance Data Capture Engine")
    parser.add_argument("--snapshot", action="store_true", default=True, help="Capture one-shot snapshot")
    parser.add_argument("--record", action="store_true", help="Continuously record frames")
    parser.add_argument("--interval", type=float, default=2.0, help="Recording interval in seconds (default: 2.0s)")
    parser.add_argument("--duration", type=float, default=60.0, help="Recording duration in seconds (default: 60.0s)")
    args = parser.parse_args()

    if args.record:
        asyncio.run(continuous_recorder(args.interval, args.duration))
    else:
        asyncio.run(capture_snapshot())

if __name__ == "__main__":
    main()
