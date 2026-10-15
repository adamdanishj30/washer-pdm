"""
Tapo P110 Real-Time Firebase Streamer
Predictive Maintenance (PdM) SideProject

Queries Tapo P110 local telemetry (Watts, Volts, Amps, Wh) over LAN
and streams live power data to Google Firebase Realtime Database (/tapo_live.json).

Usage:
  py -3.12 firmware/tapo_firebase_streamer.py
  py -3.12 firmware/tapo_firebase_streamer.py --ip 192.168.0.45 --user admin --password secret
  py -3.12 firmware/tapo_firebase_streamer.py --mock
"""

import asyncio
import argparse
import datetime
import math
import os
import sys
import time
import urllib.request
import urllib.error
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

FIREBASE_HOST = os.getenv("FIREBASE_HOST", "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app")
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH", "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V")

def push_to_firebase(payload: dict) -> bool:
    """Push real-time Tapo power telemetry to Firebase RTDB node /tapo_live.json."""
    url = f"{FIREBASE_HOST}/tapo_live.json?auth={FIREBASE_AUTH}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[FIREBASE ERROR] Could not push to {url}: {e}")
        return False

def get_parser():
    parser = argparse.ArgumentParser(description="Tapo P110 to Firebase Realtime Streamer")
    parser.add_argument("--ip", type=str, default=os.getenv("TAPO_IP"), help="Tapo P110 IP address")
    parser.add_argument("--user", type=str, default=os.getenv("TAPO_DEVICE_USER") or os.getenv("TAPO_EMAIL"), help="Device Account username")
    parser.add_argument("--password", type=str, default=os.getenv("TAPO_DEVICE_PASS") or os.getenv("TAPO_PASSWORD"), help="Device Account password")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds (default: 1.0)")
    parser.add_argument("--mock", action="store_true", help="Simulate Tapo power readings without real hardware")
    return parser

async def run_mock_streamer(interval: float):
    print("\n" + "=" * 65)
    print("      TAPO P110 FIREBASE STREAMER (MOCK / SIMULATION MODE)         ")
    print("=" * 65)
    print(f"Target Firebase : {FIREBASE_HOST}/tapo_live.json")
    print(f"Poll Interval   : {interval}s")
    print("Press Ctrl+C to stop.\n")

    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        # Simulate realistic washer power profile
        if elapsed < 20:
            phase = "WEIGHT_SENSING"
            power = 110.0 + 35.0 * math.sin(elapsed * 2.0)
        elif elapsed < 60:
            phase = "HEATING_WASH"
            power = 2050.0 + 20.0 * math.sin(elapsed)
        elif elapsed < 100:
            phase = "RINSE_TUMBLE"
            power = 180.0 + 60.0 * math.sin(elapsed * 1.5)
        else:
            phase = "HIGH_SPIN_1400"
            power = 520.0 + 80.0 * math.sin(elapsed * 0.8)

        voltage = 239.5 + 1.2 * math.sin(elapsed * 0.5)
        current_ma = (power / max(voltage, 1.0)) * 1000.0
        today_wh = 120.0 + (elapsed * power / 3600.0)

        payload = {
            "ts": {".sv": "timestamp"},
            "power_w": round(power, 2),
            "voltage_v": round(voltage, 1),
            "current_ma": round(current_ma, 1),
            "today_energy_wh": round(today_wh, 1),
            "is_on": True,
            "mock": True,
            "phase_hint": phase,
            "updated_at": datetime.datetime.now().strftime("%H:%M:%S")
        }

        ok = push_to_firebase(payload)
        status_tag = "[FIREBASE OK]" if ok else "[FIREBASE ERR]"
        print(f"{status_tag} {datetime.datetime.now().strftime('%H:%M:%S')} | {power:7.2f} W | {voltage:5.1f} V | {current_ma:7.1f} mA | {phase}")
        await asyncio.sleep(interval)

async def run_live_streamer(ip: str, user: str, password: str, interval: float):
    import kasa
    from kasa import Device, Credentials
    from kasa.interfaces.energy import Energy

    print("\n" + "=" * 65)
    print("      TAPO P110 REAL-TIME FIREBASE STREAMER                        ")
    print("=" * 65)
    print(f"Plug IP Address : {ip}")
    print(f"Device Account  : {'Configured (' + user + ')' if user else 'None (Anonymous)'}")
    print(f"Target Firebase : {FIREBASE_HOST}/tapo_live.json")
    print(f"Poll Interval   : {interval}s")
    print("=" * 65)

    credentials = Credentials(user, password) if user and password else None

    print(f"\nConnecting to Tapo P110 at {ip}...")
    try:
        device = await Device.connect(host=ip, credentials=credentials)
        await device.update()
        print(f"[CONNECTED] {device.alias} ({device.model}) | Power: {'ON' if device.is_on else 'OFF'}")
    except Exception as e:
        print(f"[ERROR] Could not connect to Tapo P110 at {ip}: {e}")
        print("\nChecklist:")
        print("1. Is the IP address correct in .env (TAPO_IP)?")
        print("2. Is the Device Account created in Tapo App (Me -> Third-Party Services -> Device Account)?")
        return

    energy = device.modules.get(Energy)
    if not energy:
        print("[ERROR] Energy metering module not found on this device!")
        return

    print("\nStreaming live to Firebase! Press Ctrl+C to stop.\n")
    print(f"{'TIME':<10} | {'POWER (W)':<10} | {'VOLTAGE (V)':<11} | {'CURRENT (mA)':<12} | {'FIREBASE STATUS'}")
    print("-" * 65)

    while True:
        try:
            await device.update()
            power_w = energy.current_consumption or 0.0
            voltage_v = energy.voltage or 0.0
            current_a = energy.current or 0.0
            current_ma = current_a * 1000.0
            today_wh = (energy.consumption_today or 0.0) * 1000.0

            payload = {
                "ts": {".sv": "timestamp"},
                "power_w": round(power_w, 2),
                "voltage_v": round(voltage_v, 1),
                "current_ma": round(current_ma, 1),
                "today_energy_wh": round(today_wh, 1),
                "is_on": device.is_on,
                "alias": device.alias,
                "model": device.model,
                "updated_at": datetime.datetime.now().strftime("%H:%M:%S")
            }

            ok = push_to_firebase(payload)
            fb_status = "PUSHED OK" if ok else "FAILED"
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"{now_str:<10} | {power_w:8.2f} W | {voltage_v:9.1f} V | {current_ma:10.1f} mA | {fb_status}", flush=True)

        except Exception as e:
            print(f"[WARN] Read error: {e}, reconnecting in 2s...")
            await asyncio.sleep(2.0)
            try:
                device = await Device.connect(host=ip, credentials=credentials)
            except Exception:
                pass

        await asyncio.sleep(interval)

def main():
    parser = get_parser()
    args = parser.parse_args()

    if args.mock:
        asyncio.run(run_mock_streamer(args.interval))
        return

    if not args.ip:
        print("\n[ERROR] No Tapo IP address provided!")
        print("Options to run:")
        print("  1. Add TAPO_IP=192.168.x.x to your .env file.")
        print("  2. Pass as argument: py -3.12 firmware/tapo_firebase_streamer.py --ip <IP> --user <USER> --password <PASS>")
        print("  3. Run in mock mode to test Firebase: py -3.12 firmware/tapo_firebase_streamer.py --mock\n")
        sys.exit(1)

    asyncio.run(run_live_streamer(args.ip, args.user, args.password, args.interval))

if __name__ == "__main__":
    main()
