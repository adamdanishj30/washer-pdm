"""
Samsung SmartThings Washing Machine Telemetry & Weight Classifier
Predictive Maintenance (PdM) SideProject

Queries the official Samsung SmartThings REST API for WW10TP44DSX washer status:
- Ground-truth operational cycle phase (washerJobState)
- Water level and spin speed
- Completion time and duration delta
- Computes automated load class and estimated laundry weight in kg

Usage:
  py -3.12 firmware/test_smartthings.py [--token <PAT_TOKEN>] [--device-id <DEVICE_UUID>]
"""

import os
import sys
import json
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SMARTTHINGS_API_URL = "https://api.smartthings.com/v1"

def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.smartthings+json;v=1"
    }

def list_devices(token: str):
    """List all devices in the user's SmartThings account to find the washer UUID."""
    url = f"{SMARTTHINGS_API_URL}/devices"
    req = urllib.request.Request(url, headers=get_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", [])
            print(f"\n[FOUND {len(items)} DEVICES IN SMARTTHINGS]")
            print("-" * 65)
            washer_id = None
            for d in items:
                name = d.get("label") or d.get("name")
                dev_id = d.get("deviceId")
                dev_type = d.get("deviceTypeName") or d.get("type")
                is_washer = "washer" in str(name).lower() or "washer" in str(dev_type).lower()
                tag = ">>> [DETECTED WASHER]" if is_washer else "   "
                print(f"{tag} Name: {name:<25} | ID: {dev_id}")
                if is_washer and not washer_id:
                    washer_id = dev_id
            print("-" * 65)
            return washer_id
    except urllib.error.HTTPError as e:
        print(f"[AUTH ERROR] SmartThings API request failed (HTTP {e.code}): {e.reason}")
        if e.code == 401:
            print("Tip: Check that your Personal Access Token (PAT) has not expired.")
        return None
    except Exception as e:
        print(f"[ERROR] Could not connect to SmartThings API: {e}")
        return None

def get_washer_status(token: str, device_id: str):
    """Fetch live washer status and calculate load class / weight."""
    url = f"{SMARTTHINGS_API_URL}/devices/{device_id}/status"
    req = urllib.request.Request(url, headers=get_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            main = data.get("components", {}).get("main", {})
            
            # Extract capabilities
            op_state = main.get("washerOperatingState", {})
            job_state = op_state.get("washerJobState", {}).get("value", "none")
            mach_state = op_state.get("machineState", {}).get("value", "stop")
            comp_time = op_state.get("completionTime", {}).get("value")
            
            samsung_op = main.get("samsungce.washerOperatingState", {})
            remaining_min = samsung_op.get("remainingTime", {}).get("value")
            progress_pct = samsung_op.get("progress", {}).get("value")

            cycle = main.get("samsungce.washerCycle", {}).get("washerCycle", {}).get("value", "unknown")
            spin_speed = (main.get("custom.washerSpinLevel", {}).get("washerSpinLevel", {}).get("value") or
                          main.get("samsungce.washerSpinLevel", {}).get("spinLevel", {}).get("value", "unknown"))
            water_temp = (main.get("custom.washerWaterTemperature", {}).get("washerWaterTemperature", {}).get("value") or
                          main.get("samsungce.washerWaterTemperature", {}).get("waterTemperature", {}).get("value", "unknown"))
            water_level = main.get("samsungce.washerWaterLevel", {}).get("waterLevel", {}).get("value", "Auto")
            detergent_density = main.get("samsungce.autoDispenseDetergent", {}).get("density", {}).get("value", "Normal")

            print("\n" + "=" * 65)
            print("        SAMSUNG WW10TP44DSX LIVE OPERATIONAL TELEMETRY        ")
            print("=" * 65)
            print(f"Operational Phase (Job State) : {job_state.upper()}")
            print(f"Machine State                 : {mach_state.upper()}")
            print(f"Cycle Selected                : {cycle}")
            print(f"Remaining Time                : {remaining_min or 0} mins ({progress_pct or 0}% progress)")
            print(f"Spin RPM Target               : {spin_speed} RPM")
            print(f"Water Temperature             : {water_temp}")
            print(f"Water Level Setting           : {water_level}")
            print(f"Auto Detergent Density        : {detergent_density}")
            print(f"Expected Completion Time      : {comp_time or 'N/A'}")
            print("-" * 65)

            # Weight & Load Class Inference
            print("[WEIGHT & LOAD CLASS ESTIMATION]")
            if job_state.lower() in ("weightsensing", "sensing"):
                print("  Status: MACHINE IS CURRENTLY WEIGHING LAUNDRY (weightSensing phase)")
                print("  >> Tapo P110 power consumption during this phase directly dictates exact kg!")
            else:
                wl = str(water_level or "").lower()
                if wl in ("low", "1"):
                    inferred_class = "LIGHT"
                    est_kg = "1.5 – 3.0 kg"
                elif wl in ("medium", "2", "auto"):
                    inferred_class = "MEDIUM"
                    est_kg = "3.5 – 6.0 kg"
                elif wl in ("high", "3"):
                    inferred_class = "HEAVY"
                    est_kg = "6.5 – 10.0 kg"
                else:
                    inferred_class = "MEDIUM (Default)"
                    est_kg = "Approx ~4.0 – 5.0 kg"

                print(f"  Inferred Load Class : {inferred_class}")
                print(f"  Estimated Laundry Wt: {est_kg}")
            print("=" * 65 + "\n")
            return {
                "job_state": job_state,
                "machine_state": mach_state,
                "water_level": water_level,
                "cycle": cycle,
                "spin_speed": spin_speed,
                "completion_time": comp_time
            }
    except Exception as e:
        print(f"[ERROR] Failed to query device {device_id}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Samsung SmartThings Washer Status & Weight Estimator")
    parser.add_argument("--token", type=str, default=os.getenv("SMARTTHINGS_PAT"), help="SmartThings Personal Access Token")
    parser.add_argument("--device-id", type=str, default=os.getenv("SMARTTHINGS_DEVICE_ID"), help="Washer Device UUID")
    args = parser.parse_args()

    token = args.token
    if not token:
        print("\n[ERROR] No SmartThings token found!")
        print("How to get your SmartThings Token:")
        print("  1. Visit: https://account.smartthings.com/tokens")
        print("  2. Log in with your Samsung account (same as SmartThings phone app).")
        print("  3. Click 'Generate new token', select 'Devices' (Read/List), and copy it.")
        print("  4. Add SMARTTHINGS_PAT=<your_token> to your .env file or pass via --token.\n")
        sys.exit(1)

    device_id = args.device_id
    if not device_id:
        print("\nSearching for your Samsung washing machine in SmartThings...")
        device_id = list_devices(token)
        if device_id:
            print(f"Tip: Add SMARTTHINGS_DEVICE_ID={device_id} to your .env file for instant querying!")

    if device_id:
        get_washer_status(token, device_id)
    else:
        print("[ERROR] No washing machine found in this SmartThings account.")

if __name__ == "__main__":
    main()
