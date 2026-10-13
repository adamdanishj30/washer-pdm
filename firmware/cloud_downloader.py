import urllib.request
import json
import os
import sys
import time

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
        req = urllib.request.Request(url, headers={"User-Agent": "PdM-Cloud-Client"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            sessions = json.loads(resp.read().decode())

        if not sessions:
            print("[INFO] No wash sessions found in cloud database yet.")
            return

        print(f"Found {len(sessions)} wash session(s) in cloud!\n")

        for session_id, batches in sessions.items():
            if not batches:
                continue

            # Determine appropriate filename
            if session_id == "wash_1019":
                # Check batch count to distinguish between 11 Oct (422 batches) and 12 Oct morning run (1216 batches)
                count = len(batches) if isinstance(batches, (dict, list)) else 0
                if count > 500:
                    fname = "wash_cycle_2026-10-12_0800.csv"
                else:
                    fname = "wash_cycle_2026-10-11_1019.csv"
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
            print(f"--> Processing session: {session_id} -> {fname}")
            
            # Extract and sort batches
            rows = []
            if isinstance(batches, dict):
                for b_id, b_data in sorted(batches.items(), key=lambda x: str(x[0])):
                    if isinstance(b_data, dict) and "t" in b_data:
                        rows.append(b_data)
            elif isinstance(batches, list):
                for b_data in batches:
                    if isinstance(b_data, dict) and "t" in b_data:
                        rows.append(b_data)

            if rows:
                with open(csv_file, "w", encoding="utf-8") as f:
                    f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms\n")
                    for r in rows:
                        f.write(f"{r.get('t', 0)},{r.get('ax', 0.0)},{r.get('ay', 0.0)},{r.get('az', 0.0)},{r.get('rms', 0.0)}\n")

                print(f"    Saved {len(rows)} records to: {csv_file}")
            else:
                print(f"    No valid telemetry records in this session.")

        print("\n[COMPLETE] All cloud sessions successfully downloaded and synced to CSV!")

    except Exception as e:
        print(f"[ERROR] Could not fetch sessions from Firebase: {e}")

if __name__ == "__main__":
    download_sessions()
