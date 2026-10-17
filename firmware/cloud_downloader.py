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
FIREBASE_SECRET = os.environ.get("FIREBASE_SECRET") or os.environ.get("FIREBASE_AUTH")
TZ_GMT8 = timezone(timedelta(hours=8))

def format_ts_filename(prefix, epoch_ms=None):
    if epoch_ms and isinstance(epoch_ms, (int, float)) and epoch_ms > 1700000000000:
        dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=TZ_GMT8)
        return f"{prefix}_{dt.strftime('%Y-%m-%d_%H%M')}.csv"
    return None

from pathlib import Path
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from firmware.smartthings_client import (
    fetch_session_phase_timeline,
    estimate_point_phase_fallback,
    compute_weight_and_class
)

def write_rows_to_csv(filepath, rows, session_id=None):
    """Writes standardized 8-column session CSV (including phase & load_class) with acoustic scale rectification."""
    rms_vals = [float(r.get("rms", 0.0)) for r in rows if "rms" in r and r.get("rms") is not None]
    median_rms = sorted(rms_vals)[len(rms_vals)//2] if rms_vals else 0.0
    scale_factor = (256000.0 / 16384.0) if median_rms > 1200.0 else 1.0

    load_class, _ = compute_weight_and_class(rows)
    phase_timeline = fetch_session_phase_timeline(session_id) if session_id else []

    first_ts = None
    for r in rows:
        ts_val = r.get("ts")
        if isinstance(ts_val, (int, float)) and ts_val > 1700000000000:
            first_ts = ts_val
            break

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms,power_w,phase,load_class\n")
        for r in rows:
            t = r.get("t", 0)
            ax = float(r.get("ax", 0.0))
            ay = float(r.get("ay", 0.0))
            az = float(r.get("az", 0.0))
            raw_rms = float(r.get("rms", 0.0))
            clean_rms = round(raw_rms / scale_factor, 1)
            p = float(r.get("pwr") if "pwr" in r else r.get("power", 0.0))
            vibe_mag = (ax * ax + ay * ay + az * az) ** 0.5

            row_epoch = r.get("ts")
            if not row_epoch and first_ts and first_ts > 1700000000000:
                row_epoch = first_ts + t

            matched_phase = None
            if phase_timeline and row_epoch:
                valid_checks = [c for c in phase_timeline if c["ts"] <= (row_epoch + 15000)]
                if valid_checks:
                    matched_phase = valid_checks[-1]["phase"]

            if not matched_phase or matched_phase == "none":
                matched_phase = estimate_point_phase_fallback(p, vibe_mag, clean_rms, t)

            f.write(f"{t},{ax:.2f},{ay:.2f},{az:.2f},{clean_rms:.1f},{p:.1f},{matched_phase},{load_class}\n")

def download_sessions():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    real_dir = os.path.join(data_dir, "real_sessions")
    test_dir = os.path.join(data_dir, "testing_data")
    os.makedirs(real_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

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

                # Classify session: test vs real wash (< 150 points = bench/pre-wash test, or known bench test)
                is_test = session_id.startswith("wash_offline_") or len(seg_rows) < 150 or "test" in fname.lower() or session_id == "wash_1009" or fname == "wash_cycle_2026-10-12_0800.csv"
                target_folder = test_dir if is_test else real_dir
                csv_file = os.path.join(target_folder, fname)
                write_rows_to_csv(csv_file, seg_rows, session_id=session_id)
                rel_folder = "testing_data" if is_test else "real_sessions"
                print(f"    Saved segment {seg_idx + 1}/{len(segments)} ({len(seg_rows)} records) -> data/{rel_folder}/{fname}")

        print("\n[COMPLETE] All cloud sessions successfully downloaded and synced to CSV!")

        # Automatically rebuild dashboards and refit ML baselines
        try:
            import subprocess
            subprocess.run([sys.executable, os.path.join(base_dir, "build_clean_dashboard.py")], check=True)
            print("[DASHBOARD] Clean dashboards updated with newly downloaded sessions!")
            subprocess.run([sys.executable, os.path.join(base_dir, "firmware", "pdm_ml_standardizer.py")], check=True)
            print("[ML] Acoustic baselines & standardized training dataset updated!")
        except Exception as e:
            print(f"[WARN] Post-download build/ML update error: {e}")

    except Exception as e:
        print(f"[ERROR] Could not fetch sessions from Firebase: {e}")

if __name__ == "__main__":
    download_sessions()

