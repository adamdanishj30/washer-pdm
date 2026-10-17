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
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH") or os.getenv("FIREBASE_SECRET")
SMARTTHINGS_PAT = os.getenv("SMARTTHINGS_PAT")
SMARTTHINGS_DEVICE_ID = os.getenv("SMARTTHINGS_DEVICE_ID")

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from firmware.smartthings_client import (
    get_valid_smartthings_token,
    query_smartthings,
    get_smartthings_status,
    push_phase_to_firebase,
    fetch_session_phase_timeline,
    estimate_point_phase_fallback,
    compute_weight_and_class
)

def query_firebase(path: str):
    url = f"{FIREBASE_HOST}/{path.lstrip('/')}"
    delimiter = "&" if "?" in url else "?"
    if FIREBASE_AUTH:
        url = f"{url}{delimiter}auth={FIREBASE_AUTH}"
    req = urllib.request.Request(url, headers={"User-Agent": "PdM-CloudSync/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None

def format_session_filename(session_id: str, first_timestamp_ms=None) -> str:
    """Generate clean, standardized filename: wash_cycle_YYYY-MM-DD_HHMM.csv"""
    if session_id.startswith("wash_202"):
        clean_id = session_id.replace("wash_", "")
        for fmt in ("%Y-%m-%d_%H%M%S", "%Y-%m-%d_%H%M", "%Y%m%d_%H%M%S", "%Y%m%d_%H%M"):
            try:
                sample_len = len(datetime.now().strftime(fmt))
                dt = datetime.strptime(clean_id[:sample_len], fmt)
                return f"wash_cycle_{dt.strftime('%Y-%m-%d_%H%M')}.csv"
            except Exception:
                pass
        return f"wash_cycle_{clean_id}.csv"

    if first_timestamp_ms and first_timestamp_ms > 1700000000000:
        dt = datetime.fromtimestamp(first_timestamp_ms / 1000.0)
        return f"wash_cycle_{dt.strftime('%Y-%m-%d_%H%M')}.csv"

    now = datetime.now()
    clean_id = session_id.replace("wash_", "")
    return f"wash_cycle_{now.strftime('%Y-%m-%d')}_{clean_id}.csv"

def sync_completed_session(session_id: str, raw_batches: list, st_info: dict = None):
    """Compiles a validated unified CSV dataset into data/ and triggers dashboard rebuild."""
    if not raw_batches:
        return None

    real_dir = DATA_DIR / "real_sessions"
    test_dir = DATA_DIR / "testing_data"
    real_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    load_class, est_kg = compute_weight_and_class(raw_batches, st_info)

    first_ts = None
    for b in raw_batches:
        ts_val = b.get("ts")
        if isinstance(ts_val, (int, float)) and ts_val > 1700000000000:
            first_ts = ts_val
            break

    # Clean filename & route
    filename = format_session_filename(session_id, first_ts)
    is_test = len(raw_batches) < 150 or "test" in filename.lower() or session_id == "wash_1009" or filename == "wash_cycle_2026-10-12_0800.csv"
    target_dir = test_dir if is_test else real_dir
    target_csv = target_dir / filename

    print(f"\n>>> Compiling session '{session_id}' -> {target_csv.relative_to(BASE_DIR)}")
    print(f"    Load Classification: {load_class} (~{est_kg} kg)")

    # Acoustic scale rectification
    rms_vals = [float(b.get("rms", 0.0)) for b in raw_batches if b.get("rms") is not None]
    median_rms = sorted(rms_vals)[len(rms_vals)//2] if rms_vals else 0.0
    scale_factor = (256000.0 / 16384.0) if median_rms > 1200.0 else 1.0

    # Retrieve recorded phase timeline from Firebase
    phase_timeline = fetch_session_phase_timeline(session_id)

    total_duration_ms = (raw_batches[-1].get("t", 0) - raw_batches[0].get("t", 0)) if raw_batches else 0
    last_phase = "weightSensing"

    with open(target_csv, "w", encoding="utf-8") as f:
        # Standard 8-column schema
        f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms,power_w,phase,load_class\n")
        for b in raw_batches:
            t = b.get("t", 0)
            ax = float(b.get("ax", 0.0))
            ay = float(b.get("ay", 0.0))
            az = float(b.get("az", 0.0))
            raw_rms = float(b.get("rms", 0.0))
            clean_rms = round(raw_rms / scale_factor, 1)
            pwr = float(b.get("pwr") if b.get("pwr") is not None else b.get("power", 0.0))
            vibe_mag = math.sqrt(ax * ax + ay * ay + az * az)
            
            row_epoch = b.get("ts")
            if not row_epoch and first_ts and first_ts > 1700000000000:
                row_epoch = first_ts + t

            matched_phase = None
            if phase_timeline and row_epoch:
                valid_checks = [c for c in phase_timeline if c["ts"] <= (row_epoch + 15000)]
                if valid_checks:
                    matched_phase = valid_checks[-1]["phase"]

            if not matched_phase or matched_phase == "none":
                matched_phase = estimate_point_phase_fallback(
                    pwr, vibe_mag, clean_rms, t,
                    total_duration_ms=total_duration_ms,
                    last_phase=last_phase
                )

            if matched_phase and matched_phase != "none":
                last_phase = matched_phase

            f.write(f"{t},{ax:.2f},{ay:.2f},{az:.2f},{clean_rms:.1f},{pwr:.1f},{matched_phase},{load_class}\n")

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

    # Rebuild dashboards and standardizer
    try:
        import subprocess
        subprocess.run([sys.executable, str(BASE_DIR / "build_clean_dashboard.py")], check=True)
        print("[DASHBOARD] Clean dashboards updated with new session!")
        subprocess.run([sys.executable, str(BASE_DIR / "firmware" / "pdm_ml_standardizer.py")], check=True)
        print("[ML] Acoustic baselines & standardized training dataset updated!")
    except Exception as e:
        print(f"[WARN] Post-sync rebuild/ML error: {e}")

    return target_csv

def run_sync_iteration():
    """Performs one complete cloud sync step."""
    live = query_firebase("live.json")
    st = get_smartthings_status(min_interval_s=30.0)

    session_id = live.get("session") if live else None
    if st:
        push_phase_to_firebase(st, session_id=session_id)

    if not live:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Firebase /live.json is empty or offline.")
        return

    session_id = live.get("session")
    state = live.get("state", "IDLE")
    uptime = live.get("uptime", 0)
    live_power = live.get("power", 0.0)

    st_phase = str(st.get("job_state") or "none") if isinstance(st, dict) else "none"
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
