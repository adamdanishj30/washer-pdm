"""
live_data_detector.py
Real-time Firebase Cloud Telemetry Detector for Samsung Washer PdM Rig.

Monitors Google Firebase RTDB remotely from anywhere.
Continuously checks for live data packets streamed by the ESP32 edge microcontroller
(MPU-6050 vibration + INMP441 acoustic RMS).

Usage:
  py firmware/live_data_detector.py [--interval 2.0]
"""

import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_FILE):
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip().strip("\"'")
    except Exception:
        pass

FIREBASE_HOST = os.environ.get("FIREBASE_HOST", "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app")
FIREBASE_AUTH = os.environ.get("FIREBASE_AUTH", "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V")


def query_firebase(path):
    url = f"{FIREBASE_HOST}/{path.lstrip('/')}"
    if "?" in url:
        url += f"&auth={FIREBASE_AUTH}"
    else:
        url += f"?auth={FIREBASE_AUTH}"
    req = urllib.request.Request(url, headers={"User-Agent": "PdM-LiveDetector/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def run_detector(poll_interval=2.0):
    print("=" * 70)
    print("       REMOTE CLOUD TELEMETRY DETECTOR (FIREBASE LIVE MONITOR)        ")
    print("=" * 70)
    print(f" Target Cloud Host : {FIREBASE_HOST}")
    print(f" Polling Frequency : Every {poll_interval:.1f}s")
    print("=" * 70)

    # 1. Fetch initial baseline state
    print("\n[INIT] Fetching current baseline from Firebase...")
    baseline = query_firebase("live.json")
    base_cnt = baseline.get("cnt") if baseline else None
    base_uptime = baseline.get("uptime") if baseline else None
    base_session = baseline.get("session") if baseline else None

    print(f"  Current DB State: Session='{base_session}', Uptime={base_uptime}s, PacketCount={base_cnt}")
    print("\n[LISTENING] Waiting for ESP32 to power on and transmit live packets...")
    print("  (Ask your mom to plug in the 5V USB power to the ESP32 now)\n")

    last_cnt = base_cnt
    last_uptime = base_uptime
    last_session = base_session
    last_change_time = time.time()
    rig_online = False
    packet_rate_samples = []

    heartbeat_ticks = 0

    while True:
        try:
            live = query_firebase("live.json")
            now = time.time()

            if live:
                cur_cnt = live.get("cnt", 0)
                cur_uptime = live.get("uptime", 0)
                cur_session = live.get("session", "unknown")
                ax = live.get("ax", 0.0)
                ay = live.get("ay", 0.0)
                az = live.get("az", 0.0)
                vibe = live.get("vibe", 0.0)
                rms = live.get("rms", 0.0)
                state = live.get("state", "UNKNOWN")

                # Detect if new data has arrived
                is_advancing = (cur_cnt != last_cnt) or (cur_uptime != last_uptime) or (cur_session != last_session)

                if is_advancing:
                    time_delta = now - last_change_time
                    cnt_delta = cur_cnt - last_cnt if last_cnt is not None else 0
                    hz = (cnt_delta / time_delta) if time_delta > 0 and cnt_delta > 0 else 0.0

                    last_cnt = cur_cnt
                    last_uptime = cur_uptime
                    last_session = cur_session
                    last_change_time = now

                    if not rig_online:
                        rig_online = True
                        print("\n" + "#" * 70)
                        print(f" >>> [LIVE RIG DETECTED ONLINE!] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] <<<")
                        print(f" Session ID    : {cur_session}")
                        print(f" Rig Uptime    : {cur_uptime} seconds")
                        print(f" Initial State : {state}")
                        print("#" * 70 + "\n")
                        print(f"{'TIME':<8} | {'STATE':<10} | {'ACCEL X':<8} {'ACCEL Y':<8} {'ACCEL Z':<8} | {'VIBE |a|':<9} | {'AUDIO RMS':<10} | {'SAMPLES':<8}")
                        print("-" * 75)

                    time_str = datetime.now().strftime("%H:%M:%S")
                    print(f"{time_str:<8} | {state:<10} | {ax:7.2f}  {ay:7.2f}  {az:7.2f}  | {vibe:7.2f} m/s² | {rms:7.1f} RMS | #{cur_cnt}", flush=True)

                else:
                    # No increment yet
                    if rig_online:
                        inactive = now - last_change_time
                        if inactive > 15:
                            print(f"\n[WARN] Rig telemetry paused for {inactive:.1f}s...")
                            if inactive > 30:
                                rig_online = False
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] [OFFLINE] Rig stopped transmitting.")
                    else:
                        heartbeat_ticks += 1
                        if heartbeat_ticks % 5 == 0:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Still waiting... (No new packets yet from ESP32)", flush=True)

            else:
                if heartbeat_ticks % 5 == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling Firebase... (live node empty or unreachable)", flush=True)

        except Exception as e:
            # print(f"[DEBUG] Fetch error: {e}")
            pass

        time.sleep(poll_interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Telemetry Detector")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds (default: 2.0)")
    args = parser.parse_args()
    try:
        run_detector(poll_interval=args.interval)
    except KeyboardInterrupt:
        print("\n[STOPPED] Monitor terminated by user.")
