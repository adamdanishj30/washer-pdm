"""
auto_drive_sync_daemon.py
Autonomous Cloud-to-Drive Telemetry Sync Daemon for Samsung Washer PdM Rig.

Monitors Google Firebase Realtime Database and SmartThings REST API in real-time.
1. Actively tracks washer operational phase from Samsung SmartThings (job_state: wash, rinse, spin, etc.).
2. Logs phase checkpoints to Firebase (/session_phases/{session_id}/{timestamp_ms}) and updates /live_phase.json.
3. Automatically computes load class (LIGHT, MEDIUM, HEAVY) from Tapo P110 initial dry-tumble power.
4. Immediately upon detecting that the ESP32 is offline (after cycle completion or power-down):
   - Compiles standardized 8-column CSV (timestamp_ms, accel_x, accel_y, accel_z, audio_rms, power_w, phase, load_class).
   - Routes real cycles to 'data/real_sessions/' and tests to 'data/testing_data/'.
   - Rectifies acoustic RMS to canonical scale.
   - Re-runs 'build_clean_dashboard.py' and 'pdm_ml_standardizer.py'.

Usage:
  py firmware/auto_drive_sync_daemon.py [--timeout 20] [--interval 5] [--once]
"""

import os
import sys
import time
import json
import math
import argparse
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REAL_DIR = DATA_DIR / "real_sessions"
TEST_DIR = DATA_DIR / "testing_data"
SYNC_HISTORY_FILE = DATA_DIR / ".sync_history.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from firmware.smartthings_client import (
    get_smartthings_status,
    push_phase_to_firebase,
    fetch_session_phase_timeline,
    estimate_point_phase_fallback,
    compute_weight_and_class
)

def _load_env_file(env_path):
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file(BASE_DIR / ".env")

FIREBASE_HOST = os.environ.get("FIREBASE_HOST", "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app")
FIREBASE_AUTH = os.environ.get("FIREBASE_AUTH") or os.environ.get("FIREBASE_SECRET")

def load_sync_history():
    if os.path.exists(SYNC_HISTORY_FILE):
        try:
            with open(SYNC_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sync_history(history):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(SYNC_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[WARN] Could not save sync history: {e}")

def get_firebase_json(path):
    url = f"{FIREBASE_HOST}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "PdM-AutoSync-Daemon/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except Exception:
        raise

def mark_session_archived_in_firebase(session_id):
    try:
        url = f"{FIREBASE_HOST}/archived_sessions/{session_id}.json?auth={FIREBASE_AUTH}"
        payload = json.dumps({
            "archived_at": datetime.now().isoformat(),
            "status": "SAVED_TO_GOOGLE_DRIVE"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="PUT", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception as e:
        print(f"  [WARN] Could not mark session in Firebase: {e}")

def format_session_filename(session_id, first_timestamp_ms=None):
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

def trigger_dashboard_and_ml_refit():
    """Triggers clean dashboard rebuild and ML standardizer pipeline."""
    try:
        subprocess.run([sys.executable, str(BASE_DIR / "build_clean_dashboard.py")], cwd=str(BASE_DIR), check=True)
        print("  [BUILD] Dashboards recompiled successfully!")
    except Exception as e:
        print(f"  [WARN] Dashboard rebuild error: {e}")

    try:
        subprocess.run([sys.executable, str(BASE_DIR / "firmware" / "pdm_ml_standardizer.py")], cwd=str(BASE_DIR), check=True)
        print("  [ML] Acoustic baselines and ML training dataset re-fitted!")
    except Exception as e:
        print(f"  [WARN] Standardizer fit error: {e}")

def export_session_to_csv(session_id, batches, st_info=None):
    """
    Convert Firebase batch data to standardized 8-column CSV with SmartThings phase ground truth.
    Columns: timestamp_ms,accel_x,accel_y,accel_z,audio_rms,power_w,phase,load_class
    """
    rows = []
    if isinstance(batches, dict):
        for b_id, b_data in sorted(batches.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else str(x[0])):
            if isinstance(b_data, dict) and "ax" in b_data:
                rows.append(b_data)
    elif isinstance(batches, list):
        for b_data in batches:
            if isinstance(b_data, dict) and "ax" in b_data:
                rows.append(b_data)

    if not rows or len(rows) < 3:
        print(f"  [SKIP] Session '{session_id}' has insufficient data ({len(rows)} points).")
        return None

    # Check for real epoch timestamp (ts > 1700000000000)
    first_ts = None
    for r in rows:
        ts_val = r.get("ts")
        if isinstance(ts_val, (int, float)) and ts_val > 1700000000000:
            first_ts = ts_val
            break
    if first_ts is None:
        first_ts = rows[0].get("t", 0)

    # Route destination folder
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    filename = format_session_filename(session_id, first_ts)
    is_test = len(rows) < 150 or "test" in filename.lower() or session_id == "wash_1009" or filename == "wash_cycle_2026-10-12_0800.csv"
    target_dir = TEST_DIR if is_test else REAL_DIR
    csv_path = target_dir / filename

    # Acoustic scale rectification
    rms_vals = [float(r.get("rms", 0.0)) for r in rows if r.get("rms") is not None]
    median_rms = sorted(rms_vals)[len(rms_vals)//2] if rms_vals else 0.0
    scale_factor = (256000.0 / 16384.0) if median_rms > 1200.0 else 1.0

    # Load class calculation
    load_class, est_kg = compute_weight_and_class(rows, st_info)

    # Fetch recorded SmartThings phase timeline from Firebase
    phase_timeline = fetch_session_phase_timeline(session_id)

    total_duration_ms = (rows[-1].get("t", 0) - rows[0].get("t", 0)) if rows else 0
    last_phase = "weightSensing"

    print(f"\n>>> Compiling session '{session_id}' -> {csv_path.name}")
    print(f"    Load Classification: {load_class} (~{est_kg} kg)")
    print(f"    Recorded Phase Checkpoints: {len(phase_timeline)}")

    # Write standardized 8-column CSV
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms,power_w,phase,load_class\n")
        
        for r in rows:
            t = r.get("t", 0)
            ax = float(r.get("ax", 0.0))
            ay = float(r.get("ay", 0.0))
            az = float(r.get("az", 0.0))
            raw_rms = float(r.get("rms", 0.0))
            clean_rms = round(raw_rms / scale_factor, 1)
            pwr = float(r.get("pwr") if "pwr" in r else r.get("power", 0.0))
            vibe_mag = math.sqrt(ax * ax + ay * ay + az * az)

            # Determine point phase
            row_epoch = r.get("ts")
            if not row_epoch and first_ts and first_ts > 1700000000000:
                row_epoch = first_ts + t

            matched_phase = None
            if phase_timeline and row_epoch:
                # Match latest checkpoint with checkpoint_ts <= row_epoch (LOCF)
                valid_checks = [c for c in phase_timeline if c["ts"] <= (row_epoch + 15000)]
                if valid_checks:
                    matched_phase = valid_checks[-1]["phase"]

            # Fallback if unrecorded
            if not matched_phase or matched_phase == "none":
                matched_phase = estimate_point_phase_fallback(
                    pwr, vibe_mag, clean_rms, t,
                    total_duration_ms=total_duration_ms,
                    last_phase=last_phase
                )

            if matched_phase and matched_phase != "none":
                last_phase = matched_phase

            f.write(f"{t},{ax:.2f},{ay:.2f},{az:.2f},{clean_rms:.1f},{pwr:.1f},{matched_phase},{load_class}\n")

    print(f"  [SUCCESS] Created: {csv_path.name} ({len(rows)} records)")
    return str(csv_path)

def check_and_sync_all_unarchived():
    """Check Firebase for any completed sessions that are not yet recorded in sync history."""
    history = load_sync_history()
    try:
        shallow_sessions = get_firebase_json("sessions.json?shallow=true")
        if not shallow_sessions:
            return 0

        synced_count = 0
        for s_id in shallow_sessions.keys():
            batches = get_firebase_json(f"sessions/{s_id}.json")
            if not batches:
                continue

            items = []
            if isinstance(batches, dict):
                items = [v for k, v in sorted(batches.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else str(x[0])) if isinstance(v, dict) and "ax" in v]
            elif isinstance(batches, list):
                items = [v for v in batches if isinstance(v, dict) and "ax" in v]

            if len(items) < 3:
                continue

            cur_first_ts = None
            for r in items:
                ts_val = r.get("ts")
                if isinstance(ts_val, (int, float)) and ts_val > 1700000000000:
                    cur_first_ts = ts_val
                    break
            if cur_first_ts is None:
                cur_first_ts = items[0].get("t", 0)

            cur_last_t = items[-1].get("t", 0)

            sess_hist = history.get(s_id, {})
            prev_synced = sess_hist.get("completed", False)
            prev_first_ts = sess_hist.get("first_ts")
            prev_last_t = sess_hist.get("last_t", 0)
            prev_points = sess_hist.get("points", 0)

            is_identical = prev_synced and (prev_points >= len(items)) and (prev_last_t == cur_last_t) and (prev_first_ts == cur_first_ts)
            if is_identical:
                continue

            print(f"\n[SYNC] Fetching session '{s_id}' from Firebase ({len(items)} points)...")
            st_info = get_smartthings_status(min_interval_s=60.0)
            csv_path = export_session_to_csv(s_id, batches, st_info=st_info)
            if csv_path:
                history[s_id] = {
                    "completed": True,
                    "file": os.path.basename(csv_path),
                    "synced_at": datetime.now().isoformat(),
                    "points": len(items),
                    "first_ts": cur_first_ts,
                    "last_t": cur_last_t
                }
                save_sync_history(history)
                mark_session_archived_in_firebase(s_id)
                synced_count += 1

        if synced_count > 0:
            trigger_dashboard_and_ml_refit()
        return synced_count
    except Exception as e:
        print(f"[WARN] Error during batch sync: {e}")
        return 0

def run_daemon(poll_interval=5, offline_timeout=20, run_once=False):
    print("=" * 70)
    print("   MULTIMODAL AUTONOMOUS CLOUD-TO-DRIVE PDM TELEMETRY SYNC DAEMON   ")
    print("=" * 70)
    print(f" Firebase Host    : {FIREBASE_HOST}")
    print(f" Real Sessions    : {REAL_DIR}")
    print(f" Offline Timeout  : {offline_timeout} seconds")
    print(f" Polling Interval : {poll_interval} seconds")
    print("=" * 70)

    # Initial check
    print("\n[INIT] Checking for existing unarchived sessions in Firebase...")
    initial_synced = check_and_sync_all_unarchived()
    if initial_synced > 0:
        print(f"[INIT] Synced {initial_synced} session(s)!\n")
    else:
        print("[INIT] All existing sessions already up to date.\n")

    if run_once:
        print("[DONE] Single-run execution completed.")
        return

    history = load_sync_history()
    last_cnt = None
    last_uptime = None
    last_seen_time = 0
    is_rig_online = False
    active_session_id = None
    last_st_poll = 0.0

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Daemon active. Listening for SmartThings and ESP32...\n")

    while True:
        try:
            now = time.time()
            live = get_firebase_json("live.json")

            # Check SmartThings every 30-45s and mirror to Firebase
            if (now - last_st_poll) >= 30.0:
                st = get_smartthings_status(min_interval_s=30.0)
                if st:
                    push_phase_to_firebase(st, session_id=active_session_id)
                last_st_poll = now

            if live and ("cnt" in live or "uptime" in live):
                cur_cnt = live.get("cnt")
                cur_uptime = live.get("uptime")
                cur_session = live.get("session")

                has_advanced = (last_cnt is not None and cur_cnt != last_cnt) or \
                               (last_uptime is not None and cur_uptime != last_uptime)

                if last_seen_time == 0:
                    last_seen_time = now
                    last_cnt = cur_cnt
                    last_uptime = cur_uptime
                    continue

                if has_advanced:
                    last_seen_time = now
                    last_cnt = cur_cnt
                    last_uptime = cur_uptime

                    if not is_rig_online:
                        is_rig_online = True
                        active_session_id = cur_session
                        st_info = get_smartthings_status(min_interval_s=5.0)
                        st_phase = str(st_info.get("job_state") or "none") if isinstance(st_info, dict) else "none"
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> ESP32 ONLINE! Session: '{cur_session}' | SmartThings Phase: {st_phase.upper()}")
                    else:
                        active_session_id = cur_session
                else:
                    inactive_seconds = now - last_seen_time

                    if is_rig_online and inactive_seconds >= offline_timeout:
                        is_rig_online = False
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] !!! ESP32 OFFLINE DETECTED! (No packets for {inactive_seconds:.1f}s)")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Triggering automatic session archive to Google Drive...")

                        if active_session_id:
                            batches = get_firebase_json(f"sessions/{active_session_id}.json")
                            if batches:
                                st_final = get_smartthings_status(min_interval_s=5.0)
                                csv_path = export_session_to_csv(active_session_id, batches, st_info=st_final)
                                if csv_path:
                                    b_list = list(batches.values()) if isinstance(batches, dict) else (batches or [])
                                    valid_b = [b for b in b_list if isinstance(b, dict) and "ax" in b]
                                    b_first_ts = None
                                    for b in valid_b:
                                        ts_val = b.get("ts")
                                        if isinstance(ts_val, (int, float)) and ts_val > 1700000000000:
                                            b_first_ts = ts_val
                                            break
                                    if b_first_ts is None and valid_b:
                                        b_first_ts = valid_b[0].get("t", 0)
                                    b_last_t = valid_b[-1].get("t", 0) if valid_b else 0

                                    history[active_session_id] = {
                                        "completed": True,
                                        "file": os.path.basename(csv_path),
                                        "synced_at": datetime.now().isoformat(),
                                        "points": len(valid_b),
                                        "first_ts": b_first_ts,
                                        "last_t": b_last_t
                                    }
                                    save_sync_history(history)
                                    mark_session_archived_in_firebase(active_session_id)
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> Session '{active_session_id}' archived!\n")
                                    trigger_dashboard_and_ml_refit()

                        check_and_sync_all_unarchived()
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Daemon listening for next wash cycle...\n")

            else:
                if is_rig_online:
                    is_rig_online = False
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] !!! ESP32 unreachable. Offline mode.")

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [DAEMON LOOP NOTICE] {e}")

        time.sleep(poll_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32 Multimodal Cloud-to-Drive Sync Daemon")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    parser.add_argument("--timeout", type=int, default=20, help="Offline inactivity threshold in seconds (default: 20)")
    parser.add_argument("--once", action="store_true", help="Sync once and exit")
    args = parser.parse_args()

    run_daemon(poll_interval=args.interval, offline_timeout=args.timeout, run_once=args.once)
