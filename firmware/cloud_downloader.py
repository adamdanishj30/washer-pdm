import urllib.request
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(base_dir, ".env")
if os.path.exists(env_file):
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip().strip("\"'")
    except Exception:
        pass

FIREBASE_HOST = os.environ.get("FIREBASE_HOST", "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app")
FIREBASE_SECRET = os.environ.get("FIREBASE_SECRET", "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V")
TZ_GMT8 = timezone(timedelta(hours=8))

def format_ts_filename(prefix, epoch_ms=None):
    if epoch_ms and isinstance(epoch_ms, (int, float)) and epoch_ms > 1700000000000:
        dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=TZ_GMT8)
        return f"{prefix}_{dt.strftime('%Y-%m-%d_%H%M')}.csv"
    return None

def write_rows_to_csv(filepath, rows):
    has_pwr = any("pwr" in r or "power" in r for r in rows)
    with open(filepath, "w", encoding="utf-8") as f:
        if has_pwr:
            f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms,power_w\n")
            for r in rows:
                p = r.get("pwr") if "pwr" in r else r.get("power", 0.0)
                f.write(f"{r.get('t', 0)},{r.get('ax', 0.0)},{r.get('ay', 0.0)},{r.get('az', 0.0)},{r.get('rms', 0.0)},{p:.1f}\n")
        else:
            f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms\n")
            for r in rows:
                f.write(f"{r.get('t', 0)},{r.get('ax', 0.0)},{r.get('ay', 0.0)},{r.get('az', 0.0)},{r.get('rms', 0.0)}\n")

def download_sessions():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    print("=" * 60)
    print("   FIREBASE CLOUD TELEMETRY DOWNLOADER (PDM RIG)   ")
    print("=" * 60)
    print(f"Connecting to: {FIREBASE_HOST}")
    print("Querying cloud database for recorded wash sessions...\n")

    try:
        url = f"{FIREBASE_HOST}/sessions.json"
        if FIREBASE_SECRET:
            url += f"?auth={FIREBASE_SECRET}"
            
        req = urllib.request.Request(url, headers={"User-Agent": "PdM-Cloud-Client"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            sessions = json.loads(resp.read().decode())

        if not sessions:
            print("[INFO] No wash sessions found in cloud database yet.")
            return

        print(f"Found {len(sessions)} wash session(s) in cloud!\n")

        for session_id, batches in sessions.items():
            if not batches:
                continue

            print(f"--> Processing session: {session_id}")
            
            # Extract and sort batches
            raw_batches = []
            if isinstance(batches, dict):
                for b_id, b_data in sorted(batches.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else str(x[0])):
                    if isinstance(b_data, dict) and "t" in b_data:
                        raw_batches.append((b_id, b_data))
            elif isinstance(batches, list):
                for idx, b_data in enumerate(batches):
                    if isinstance(b_data, dict) and "t" in b_data:
                        raw_batches.append((idx, b_data))

            if not raw_batches:
                print(f"    No valid telemetry records in {session_id}.")
                continue

            # Detect discontinuities where 't' drops backward significantly (> 5s jump backwards)
            # or where 'ts' jumps to a different date
            segments = []
            current_seg = [raw_batches[0][1]]
            
            for i in range(1, len(raw_batches)):
                prev_row = raw_batches[i-1][1]
                curr_row = raw_batches[i][1]
                
                t_dropped = (curr_row.get("t", 0) < prev_row.get("t", 0) - 5000)
                
                prev_ts = prev_row.get("ts")
                curr_ts = curr_row.get("ts")
                ts_jumped = False
                if prev_ts and curr_ts and isinstance(prev_ts, (int, float)) and isinstance(curr_ts, (int, float)):
                    if abs(curr_ts - prev_ts) > 3600000:  # > 1 hour gap
                        ts_jumped = True
                
                if t_dropped or ts_jumped:
                    print(f"    [DISCONTINUITY DETECTED] at index {i}: batch {raw_batches[i][0]} (t={curr_row.get('t')}) vs prev (t={prev_row.get('t')})")
                    segments.append(current_seg)
                    current_seg = [curr_row]
                else:
                    current_seg.append(curr_row)
                    
            if current_seg:
                segments.append(current_seg)

            # Save each segment
            for seg_idx, seg_rows in enumerate(segments):
                first_row = seg_rows[0]
                first_ts = first_row.get("ts") if isinstance(first_row.get("ts"), (int, float)) and first_row.get("ts") > 1700000000000 else None
                
                if len(segments) > 1:
                    # Overwritten prefix / suffix detected
                    if seg_idx == 0:
                        fname = f"wash_cycle_{session_id}_prefix_recovered.csv"
                    else:
                        fname = f"wash_cycle_{session_id}_older_batches_recovered.csv"
                else:
                    # Single contiguous session
                    formatted_name = format_ts_filename("wash_cycle", first_ts)
                    if formatted_name:
                        fname = formatted_name
                    elif session_id == "wash_1019":
                        count = len(seg_rows)
                        if count > 500:
                            fname = "wash_cycle_2026-10-12_0800.csv"
                        else:
                            fname = "wash_cycle_2026-10-11_1019.csv"
                    elif session_id == "wash_1020":
                        fname = "wash_cycle_2026-10-15_1020.csv"
                    elif session_id.startswith("wash_202"):
                        clean_id = session_id.replace("wash_", "")
                        fname = f"wash_cycle_{clean_id}.csv"
                    elif session_id.startswith("wash_offline_"):
                        fname = f"{session_id}.csv"
                    elif session_id.startswith("wash_"):
                        suffix = session_id.replace("wash_", "")
                        fname = f"wash_cycle_{suffix}.csv"
                    else:
                        fname = f"{session_id}.csv"

                csv_file = os.path.join(data_dir, fname)
                write_rows_to_csv(csv_file, seg_rows)
                print(f"    Saved segment {seg_idx + 1}/{len(segments)} ({len(seg_rows)} records) -> {fname}")

        print("\n[COMPLETE] All cloud sessions successfully downloaded and synced to CSV!")

        # Automatically rebuild dashboards so the newly downloaded sessions appear in UI
        try:
            import subprocess
            subprocess.run([sys.executable, os.path.join(base_dir, "build_clean_dashboard.py")], check=True)
            print("[DASHBOARD] Clean dashboards updated with newly downloaded sessions!")
        except Exception as e:
            print(f"[WARN] Could not rebuild dashboard: {e}")

    except Exception as e:
        print(f"[ERROR] Could not fetch sessions from Firebase: {e}")

if __name__ == "__main__":
    download_sessions()

