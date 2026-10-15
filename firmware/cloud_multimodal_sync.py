"""
Cloud Multimodal PdM Auto-Sync Engine
Predictive Maintenance (PdM) SideProject

Autonomous Cloud-to-Cloud Bridge:
1. Queries Google Firebase Realtime Database for live ESP32 telemetry (Vibration, Sound, Tapo Power).
2. Queries Samsung SmartThings REST API for washer cycle phase (washerJobState), RPM, water level, and timing.
3. Automatically computes load class and estimated laundry weight (kg) from initial dry-tumble power.
4. Generates unified 13-column CSV datasets directly in data/ and updates the web dashboard.

Can run locally, as a background daemon, or inside GitHub Actions / Cloud Cron.

Usage:
  py -3.12 firmware/cloud_multimodal_sync.py [--once] [--interval 10]
"""

import os
import sys
import time
import json
import math
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SYNC_HISTORY_FILE = DATA_DIR / ".sync_history.json"

# Load .env
load_dotenv(dotenv_path=BASE_DIR / ".env")

FIREBASE_HOST = os.getenv("FIREBASE_HOST", "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app")
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH", "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V")
SMARTTHINGS_PAT = os.getenv("SMARTTHINGS_PAT")
SMARTTHINGS_DEVICE_ID = os.getenv("SMARTTHINGS_DEVICE_ID")
SMARTTHINGS_CLIENT_ID = "d18cf96e-c626-4433-bf51-ddbb10c5d1ed"
SMARTTHINGS_REFRESH_URL = "https://auth-global.api.smartthings.com/oauth/token"

def get_valid_smartthings_token() -> str:
    """
    Retrieves or automatically refreshes the SmartThings OAuth2 access token.
    Prioritizes persistent CLI credentials with automated token exchange.
    """
    cred_path = Path(os.path.expandvars(r"%LOCALAPPDATA%\@smartthings\cli\Data\credentials.json"))
    
    # 1. Try reading from CLI credentials file
    if cred_path.is_file():
        try:
            with open(cred_path, "r", encoding="utf-8") as f:
                creds = json.load(f)
            prof = creds.get("default:api.smartthings.com", {})
            acc = prof.get("accessToken")
            ref = prof.get("refreshToken")
            exp_str = prof.get("expires")
            
            # Check expiry
            needs_refresh = False
            if exp_str:
                try:
                    exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                    now_dt = datetime.now(exp_dt.tzinfo)
                    if (exp_dt - now_dt).total_seconds() < 300:
                        needs_refresh = True
                except Exception:
                    needs_refresh = True
            
            if not needs_refresh and acc:
                return acc
            
            # Refresh using refresh token
            if ref:
                body = urllib.parse.urlencode({
                    "grant_type": "refresh_token",
                    "client_id": SMARTTHINGS_CLIENT_ID,
                    "refresh_token": ref
                }).encode("utf-8")
                req = urllib.request.Request(
                    SMARTTHINGS_REFRESH_URL,
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    new_acc = data.get("access_token")
                    new_ref = data.get("refresh_token")
                    expires_in = data.get("expires_in", 86400)
                    
                    if new_acc and new_ref:
                        prof["accessToken"] = new_acc
                        prof["refreshToken"] = new_ref
                        import datetime as dt_mod
                        prof["expires"] = (dt_mod.datetime.now(dt_mod.timezone.utc) + dt_mod.timedelta(seconds=expires_in)).isoformat().replace("+00:00", "Z")
                        creds["default:api.smartthings.com"] = prof
                        with open(cred_path, "w", encoding="utf-8") as out_f:
                            json.dump(creds, out_f, indent=4)
                        return new_acc
        except Exception as e:
            print(f"[AUTH REFRESH NOTICE] CLI token refresh attempt: {e}")

    # 2. Check environment variable refresh token (e.g. for GitHub Actions)
    env_ref = os.getenv("SMARTTHINGS_REFRESH_TOKEN")
    if env_ref:
        try:
            body = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "client_id": SMARTTHINGS_CLIENT_ID,
                "refresh_token": env_ref
            }).encode("utf-8")
            req = urllib.request.Request(
                SMARTTHINGS_REFRESH_URL,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                new_acc = data.get("access_token")
                if new_acc:
                    return new_acc
        except Exception as e:
            print(f"[ENV REFRESH NOTICE] Token refresh from env: {e}")

    # 3. Fallback to access token or PAT
    return os.getenv("SMARTTHINGS_ACCESS_TOKEN") or SMARTTHINGS_PAT

def query_firebase(path: str):
    url = f"{FIREBASE_HOST}/{path.lstrip('/')}"
    delimiter = "&" if "?" in url else "?"
    url = f"{url}{delimiter}auth={FIREBASE_AUTH}"
    req = urllib.request.Request(url, headers={"User-Agent": "PdM-CloudSync/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None

def put_firebase(path: str, payload: dict) -> bool:
    url = f"{FIREBASE_HOST}/{path.lstrip('/')}"
    delimiter = "&" if "?" in url else "?"
    url = f"{url}{delimiter}auth={FIREBASE_AUTH}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[FIREBASE ERR] Could not write to {path}: {e}")
        return False

def query_smartthings():
    if not SMARTTHINGS_DEVICE_ID:
        return None
    token = get_valid_smartthings_token()
    if not token:
        return None
    url = f"https://api.smartthings.com/v1/devices/{SMARTTHINGS_DEVICE_ID}/status"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.smartthings+json;v=1"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            main = data.get("components", {}).get("main", {})
            
            # Standard operating state
            op = main.get("washerOperatingState", {})
            job_state = op.get("washerJobState", {}).get("value", "none")
            mach_state = op.get("machineState", {}).get("value", "stop")
            comp_time = op.get("completionTime", {}).get("value")

            # Samsung CE custom capabilities
            s_op = main.get("samsungce.washerOperatingState", {})
            remaining_mins = s_op.get("remainingTime", {}).get("value")
            progress_pct = s_op.get("progress", {}).get("value")
            
            cycle = main.get("samsungce.washerCycle", {}).get("washerCycle", {}).get("value", "unknown")
            spin_speed = (main.get("custom.washerSpinLevel", {}).get("washerSpinLevel", {}).get("value") or
                          main.get("samsungce.washerSpinLevel", {}).get("spinLevel", {}).get("value", "unknown"))
            water_level = main.get("samsungce.washerWaterLevel", {}).get("waterLevel", {}).get("value", "Auto")
            water_temp = main.get("custom.washerWaterTemperature", {}).get("washerWaterTemperature", {}).get("value", "cold")
            rinse_cycles = main.get("custom.washerRinseCycles", {}).get("washerRinseCycles", {}).get("value", "0")
            detergent = main.get("samsungce.autoDispenseDetergent", {}).get("remainingAmount", {}).get("value", "unknown")
            softener = main.get("samsungce.autoDispenseSoftener", {}).get("remainingAmount", {}).get("value", "unknown")
            kids_lock = main.get("samsungce.kidsLock", {}).get("lockState", {}).get("value", "unlocked")
            cum_water = main.get("samsungce.waterConsumptionReport", {}).get("waterConsumption", {}).get("value", {}).get("cumulativeAmount", 0)

            return {
                "job_state": job_state,
                "machine_state": mach_state,
                "completion_time": comp_time,
                "remaining_mins": remaining_mins,
                "progress_pct": progress_pct,
                "cycle": cycle,
                "spin_speed": spin_speed,
                "water_level": water_level,
                "water_temp": water_temp,
                "rinse_cycles": rinse_cycles,
                "detergent_remaining": detergent,
                "softener_remaining": softener,
                "kids_lock": kids_lock,
                "cumulative_water_l": round(cum_water / 1000.0, 1) if cum_water else 0.0,
                "updated_at": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"[SMARTTHINGS ERR] Could not fetch washer status: {e}")
        return None

_last_st_call = 0.0
_cached_st_data = None

def get_smartthings_status(min_interval_s: float = 60.0):
    """Fetches SmartThings status with a 60-second minimum interval throttle to protect API quotas."""
    global _last_st_call, _cached_st_data
    now = time.time()
    if _cached_st_data is not None and (now - _last_st_call) < min_interval_s:
        return _cached_st_data
    
    data = query_smartthings()
    if data:
        _cached_st_data = data
        _last_st_call = now
    return _cached_st_data or data

def compute_weight_and_class(batches: list, st_info: dict = None) -> tuple:
    """
    Computes load class (LIGHT, MEDIUM, HEAVY) and estimated weight (kg)
    using dry-tumble motor power inertia during early cycle phase.
    """
    # Look for early dry-tumble readings (first 10-20 batches, t < 120s)
    sensing_powers = []
    for b in batches[:25]:
        pwr = b.get("pwr") or b.get("power")
        if pwr is not None and 60.0 <= pwr <= 350.0:
            sensing_powers.append(pwr)

    if sensing_powers:
        avg_sensing_w = sum(sensing_powers) / len(sensing_powers)
        # Weight formula: m = (P - 70) / 15.0 kg
        est_kg = max(0.5, min(10.0, (avg_sensing_w - 70.0) / 15.0))
    else:
        # Fallback estimation from SmartThings water level if power absent
        wl = str(st_info.get("water_level") if st_info else "").lower()
        if wl in ("low", "1"):
            avg_sensing_w, est_kg = 100.0, 2.0
        elif wl in ("high", "3"):
            avg_sensing_w, est_kg = 240.0, 8.0
        else:
            avg_sensing_w, est_kg = 160.0, 5.0

    if est_kg < 3.0 or avg_sensing_w < 120.0:
        load_class = "LIGHT"
    elif est_kg <= 6.0 or avg_sensing_w <= 220.0:
        load_class = "MEDIUM"
    else:
        load_class = "HEAVY"

    return load_class, round(est_kg, 1), round(avg_sensing_w, 1)

def sync_completed_session(session_id: str, raw_batches: list, st_info: dict = None):
    """Compiles a validated unified CSV dataset into data/ and triggers dashboard rebuild."""
    if not raw_batches:
        return None

    real_dir = DATA_DIR / "real_sessions"
    test_dir = DATA_DIR / "testing_data"
    real_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    load_class, est_kg, avg_pwr = compute_weight_and_class(raw_batches, st_info)

    # Clean filename & route
    clean_id = session_id.replace("wash_", "")
    is_test = session_id.startswith("wash_offline_") or len(raw_batches) < 40
    target_dir = test_dir if is_test else real_dir
    target_csv = target_dir / f"wash_cycle_{clean_id}.csv"

    print(f"\n>>> Compiling session '{session_id}' -> {target_csv.relative_to(BASE_DIR)}")
    print(f"    Load Classification: {load_class} (~{est_kg} kg | Sensing Pwr: {avg_pwr} W)")

    with open(target_csv, "w", encoding="utf-8") as f:
        # Standard schema
        f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms,power_w,phase,load_class\n")
        for b in raw_batches:
            t = b.get("t", 0)
            ax = b.get("ax", 0.0)
            ay = b.get("ay", 0.0)
            az = b.get("az", 0.0)
            rms = b.get("rms", 0.0)
            pwr = b.get("pwr") if b.get("pwr") is not None else b.get("power", 0.0)
            
            # Simple phase estimator if ground truth not logged per point
            vibe_mag = math.sqrt(ax * ax + ay * ay + az * az)
            if pwr > 1500.0:
                point_phase = "wash_heating"
            elif vibe_mag > 11.0 or rms > 400.0:
                point_phase = "spin"
            elif pwr > 35.0 and rms < 100.0 and abs(vibe_mag - 9.81) < 0.5:
                point_phase = "drain"
            elif t < 120000:
                point_phase = "weightSensing"
            else:
                point_phase = "wash"

            f.write(f"{t},{ax:.2f},{ay:.2f},{az:.2f},{rms:.1f},{pwr:.1f},{point_phase},{load_class}\n")

    # Update sync history
    sync_hist = {}
    if SYNC_HISTORY_FILE.exists():
        try:
            with open(SYNC_HISTORY_FILE, "r", encoding="utf-8") as f:
                sync_hist = json.load(f)
        except Exception:
            pass

    sync_hist[session_id] = {
        "completed": True,
        "file": target_csv.name,
        "points": len(raw_batches),
        "load_class": load_class,
        "estimated_weight_kg": est_kg,
        "synced_at": datetime.now().isoformat()
    }
    with open(SYNC_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sync_hist, f, indent=2)

    # Rebuild dashboards
    try:
        import subprocess
        subprocess.run([sys.executable, str(BASE_DIR / "build_clean_dashboard.py")], check=True)
        print("[DASHBOARD] Clean dashboards updated with new session!")
    except Exception as e:
        print(f"[WARN] Could not rebuild dashboard: {e}")

    return target_csv

def run_sync_iteration():
    """Performs one complete cloud sync step."""
    live = query_firebase("live.json")
    st = get_smartthings_status(min_interval_s=60.0)

    if st:
        # Mirror live SmartThings state to Firebase /live_phase.json
        put_firebase("live_phase.json", st)

    if not live:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Firebase /live.json is empty or offline.")
        return

    session_id = live.get("session")
    state = live.get("state", "IDLE")
    uptime = live.get("uptime", 0)
    live_power = live.get("power", 0.0)

    st_phase = st.get("job_state", "none") if st else "none"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Session: {session_id} | State: {state} | Phase: {st_phase.upper()} | Power: {live_power:.1f} W")

    # Check sync history
    sync_hist = {}
    if SYNC_HISTORY_FILE.exists():
        try:
            with open(SYNC_HISTORY_FILE, "r", encoding="utf-8") as f:
                sync_hist = json.load(f)
        except Exception:
            pass

    # If session is active and recorded batches exist
    if session_id and (session_id not in sync_hist or not sync_hist[session_id].get("completed")):
        # Check if cycle ended (either state is IDLE or SmartThings reports finish/stop)
        if state == "IDLE" and (st_phase in ("finish", "none") or uptime > 600):
            batches_raw = query_firebase(f"sessions/{session_id}.json")
            if batches_raw:
                if isinstance(batches_raw, list):
                    batches = [b for b in batches_raw if b is not None]
                else:
                    batches = [b for k, b in sorted(batches_raw.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0) if b is not None]

                if len(batches) > 10:
                    sync_completed_session(session_id, batches, st)

def main():
    parser = argparse.ArgumentParser(description="Cloud Multimodal PdM Auto-Sync Engine")
    parser.add_argument("--once", action="store_true", help="Run a single sync check and exit")
    parser.add_argument("--interval", type=float, default=60.0, help="Poll interval in seconds (default: 60s / 1 min)")
    args = parser.parse_args()

    print("=" * 65)
    print("      CLOUD MULTIMODAL PDM AUTO-SYNC ENGINE (ZERO-TOUCH)        ")
    print("=" * 65)
    print(f"Target Firebase : {FIREBASE_HOST}")
    print(f"SmartThings PAT : {'Configured' if SMARTTHINGS_PAT else 'NOT SET'}")
    print(f"Device UUID     : {SMARTTHINGS_DEVICE_ID or 'NOT SET'}")
    print(f"Mode            : {'Single Run (--once)' if args.once else f'Continuous Loop ({args.interval}s)'}")
    print("=" * 65 + "\n")

    if args.once:
        run_sync_iteration()
        return

    while True:
        try:
            run_sync_iteration()
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
