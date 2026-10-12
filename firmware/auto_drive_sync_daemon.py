"""
auto_drive_sync_daemon.py
Autonomous Cloud-to-Drive Telemetry Sync Daemon for Samsung Washer PdM Rig.

Monitors Google Firebase Realtime Database in real-time.
Immediately upon detecting that the ESP32 is offline and no longer transmitting data
(e.g., after 15-30 seconds of packet inactivity following wash completion or power-down),
this daemon automatically:
  1. Fetches all recorded session batches from Firebase.
  2. Compiles a clean, validated CSV dataset (timestamp_ms, accel_x, accel_y, accel_z, audio_rms).
  3. Saves the CSV directly into 'G:\\My Drive\\PdM SideProject\\data\\'.
  4. Triggers Google Drive for Desktop automatic cloud sync.
  5. Re-runs 'build_clean_dashboard.py' so the new session is instantly available on the web dashboard!

Usage:
  py firmware/auto_drive_sync_daemon.py [--timeout 20] [--interval 5] [--once]
"""

import os
import sys
import time
import json
import argparse
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

FIREBASE_HOST = "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app"
FIREBASE_AUTH = "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SYNC_HISTORY_FILE = os.path.join(DATA_DIR, ".sync_history.json")


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
    """
    Generate clean, standardized filename: wash_cycle_YYYY-MM-DD_HHMM.csv
    """
    if session_id.startswith("wash_202") and len(session_id) >= 18:
        # e.g., wash_20261012_080000 -> wash_cycle_2026-10-12_0800.csv
        try:
            raw_ts = session_id.replace("wash_", "")
            dt = datetime.strptime(raw_ts[:15], "%Y%m%d_%H%M%S")
            return f"wash_cycle_{dt.strftime('%Y-%m-%d_%H%M')}.csv"
        except Exception:
            pass

    if first_timestamp_ms and first_timestamp_ms > 1700000000000:
        dt = datetime.fromtimestamp(first_timestamp_ms / 1000.0)
        return f"wash_cycle_{dt.strftime('%Y-%m-%d_%H%M')}.csv"

    # Default to current date/time if not parseable
    now = datetime.now()
    clean_id = session_id.replace("wash_", "")
    return f"wash_cycle_{now.strftime('%Y-%m-%d')}_{clean_id}.csv"


def export_session_to_csv(session_id, batches):
    """
    Convert Firebase batch data to standardized CSV and save to data directory.
    """
    rows = []
    if isinstance(batches, dict):
        for b_id, b_data in sorted(batches.items(), key=lambda x: str(x[0])):
            if isinstance(b_data, dict) and "ax" in b_data:
                rows.append(b_data)
    elif isinstance(batches, list):
        for b_data in batches:
            if isinstance(b_data, dict) and "ax" in b_data:
                rows.append(b_data)

    if not rows or len(rows) < 3:
        print(f"  [SKIP] Session '{session_id}' has insufficient data ({len(rows)} points).")
        return None

    first_t = rows[0].get("t", 0)
    filename = format_session_filename(session_id, first_t)
    csv_path = os.path.join(DATA_DIR, filename)

    # Avoid overwriting existing distinct session file
    if os.path.exists(csv_path):
        existing_size = os.path.getsize(csv_path)
        # If the file already exists and is complete, don't overwrite unless current has more data
        with open(csv_path, "r", encoding="utf-8") as f:
            existing_lines = sum(1 for _ in f) - 1
        if existing_lines >= len(rows):
            print(f"  [INFO] Session '{session_id}' already synced to '{filename}' ({existing_lines} records).")
            return csv_path

    # Write clean CSV
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms\n")
        for r in rows:
            t = r.get("t", 0)
            ax = r.get("ax", 0.0)
            ay = r.get("ay", 0.0)
            az = r.get("az", 0.0)
            rms = r.get("rms", 0.0)
            f.write(f"{t},{ax:.2f},{ay:.2f},{az:.2f},{rms:.1f}\n")

    print(f"  [SUCCESS] Created: {csv_path}")
    print(f"            Records: {len(rows)} data points")
    print(f"            Cloud Status: Syncing to Google Drive...")

    # Rebuild dashboard so the session appears immediately
    builder_script = os.path.join(BASE_DIR, "build_clean_dashboard.py")
    if os.path.exists(builder_script):
        try:
            print("  [BUILD] Updating dashboard HTML files with new session...")
            subprocess.run([sys.executable, builder_script], cwd=BASE_DIR, check=True, capture_output=True)
            print("  [BUILD] Dashboards recompiled successfully!")
        except Exception as e:
            print(f"  [WARN] Dashboard rebuild error: {e}")

    return csv_path


def check_and_sync_all_unarchived():
    """
    Check Firebase for any completed sessions that are not yet recorded in sync history.
    """
    history = load_sync_history()
    try:
        shallow_sessions = get_firebase_json("sessions.json?shallow=true")
        if not shallow_sessions:
            return 0

        synced_count = 0
        for s_id in shallow_sessions.keys():
            if s_id in history and history[s_id].get("completed", False):
                continue

            print(f"\n[SYNC] Fetching session '{s_id}' from Firebase...")
            batches = get_firebase_json(f"sessions/{s_id}.json")
            if batches:
                csv_path = export_session_to_csv(s_id, batches)
                if csv_path:
                    history[s_id] = {
                        "completed": True,
                        "file": os.path.basename(csv_path),
                        "synced_at": datetime.now().isoformat(),
                        "points": len(batches) if isinstance(batches, (list, dict)) else 0
                    }
                    save_sync_history(history)
                    mark_session_archived_in_firebase(s_id)
                    synced_count += 1

        return synced_count
    except Exception as e:
        print(f"[WARN] Error during batch sync: {e}")
        return 0


def run_daemon(poll_interval=5, offline_timeout=20, run_once=False):
    print("=" * 70)
    print("   ESP32 AUTONOMOUS CLOUD-TO-DRIVE PDM TELEMETRY SYNC DAEMON   ")
    print("=" * 70)
    print(f" Firebase Host    : {FIREBASE_HOST}")
    print(f" Google Drive Dir : {DATA_DIR}")
    print(f" Offline Timeout  : {offline_timeout} seconds of packet inactivity")
    print(f" Polling Interval : {poll_interval} seconds")
    print("=" * 70)

    # Initial check for any existing unsynced sessions
    print("\n[INIT] Checking for existing unarchived sessions in Firebase...")
    initial_synced = check_and_sync_all_unarchived()
    if initial_synced > 0:
        print(f"[INIT] Synced {initial_synced} session(s) to Google Drive!\n")
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
    session_start_time = None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Daemon active. Waiting for ESP32 transmission...\n")

    while True:
        try:
            live = get_firebase_json("live.json")
            now = time.time()

            if live and ("cnt" in live or "uptime" in live):
                cur_cnt = live.get("cnt")
                cur_uptime = live.get("uptime")
                cur_session = live.get("session")

                # Check if telemetry is actively advancing
                has_advanced = (last_cnt is not None and cur_cnt != last_cnt) or \
                               (last_uptime is not None and cur_uptime != last_uptime)

                if has_advanced or last_seen_time == 0:
                    last_seen_time = now
                    last_cnt = cur_cnt
                    last_uptime = cur_uptime

                    if not is_rig_online:
                        is_rig_online = True
                        active_session_id = cur_session
                        session_start_time = now
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> ESP32 DETECTED ONLINE! Streaming session: '{cur_session}' (State: {live.get('state', 'RUNNING')})")
                    else:
                        active_session_id = cur_session
                else:
                    # No increment detected
                    inactive_seconds = now - last_seen_time

                    if is_rig_online and inactive_seconds >= offline_timeout:
                        is_rig_online = False
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] !!! ESP32 OFFLINE DETECTED! (No packets for {inactive_seconds:.1f}s)")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Triggering automatic session archive to Google Drive...")

                        if active_session_id:
                            batches = get_firebase_json(f"sessions/{active_session_id}.json")
                            if batches:
                                csv_path = export_session_to_csv(active_session_id, batches)
                                if csv_path:
                                    history[active_session_id] = {
                                        "completed": True,
                                        "file": os.path.basename(csv_path),
                                        "synced_at": datetime.now().isoformat(),
                                        "points": len(batches) if isinstance(batches, (list, dict)) else 0
                                    }
                                    save_sync_history(history)
                                    mark_session_archived_in_firebase(active_session_id)
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> Session '{active_session_id}' safely stored and synced to Google Drive!\n")

                        # Also sweep any other unarchived sessions
                        check_and_sync_all_unarchived()
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Daemon listening for next wash cycle...\n")

            else:
                if is_rig_online:
                    is_rig_online = False
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] !!! ESP32 unreachable. Offline mode.")

        except Exception as e:
            # Network blip or temporary connection issue - keep running
            pass

        time.sleep(poll_interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32 Cloud-to-Drive Sync Daemon")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    parser.add_argument("--timeout", type=int, default=20, help="Offline inactivity threshold in seconds (default: 20)")
    parser.add_argument("--once", action="store_true", help="Sync once and exit")
    args = parser.parse_args()

    run_daemon(poll_interval=args.interval, offline_timeout=args.timeout, run_once=args.once)
