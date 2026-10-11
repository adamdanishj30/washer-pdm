import urllib.request
import json
import os
import sys
import time

FIREBASE_HOST = "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app"

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

            csv_file = os.path.join(data_dir, f"{session_id}.csv")
            print(f"--> Processing session: {session_id}")
            
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
