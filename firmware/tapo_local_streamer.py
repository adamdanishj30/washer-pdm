"""
Standalone Local Tapo P110 Power Monitor & Logger (Zero Firebase)
Predictive Maintenance (PdM) SideProject

Features:
- Polls Tapo P110 at 1 Hz directly over local Wi-Fi (KLAP protocol).
- Completely isolated from Firebase (no cloud writes).
- Real-time terminal dashboard (Watts, Volts, Amps, Energy).
- Optional local CSV logging to data/test_tapo_power.csv.
- Includes a --mock flag to test the entire pipeline even when not near the hardware!
"""

import asyncio
import argparse
import datetime
import math
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

import kasa
from kasa import Device, Credentials
from kasa.interfaces.energy import Energy

def get_parser():
    parser = argparse.ArgumentParser(description="Tapo P110 Local Power Monitor (No Firebase)")
    parser.add_argument("--ip", type=str, default=os.getenv("TAPO_IP"), help="Tapo P110 IP address")
    parser.add_argument("--user", type=str, default=os.getenv("TAPO_DEVICE_USER") or os.getenv("TAPO_EMAIL"), help="Device Account username")
    parser.add_argument("--password", type=str, default=os.getenv("TAPO_DEVICE_PASS") or os.getenv("TAPO_PASSWORD"), help="Device Account password")
    parser.add_argument("--log-csv", action="store_true", help="Log readings to local CSV file")
    parser.add_argument("--mock", action="store_true", help="Simulate a Tapo P110 wash cycle without hardware")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds (default: 1.0)")
    return parser

async def run_live_monitor(ip: str, user: str, password: str, log_csv: bool, interval: float):
    print("\n" + "=" * 65)
    print("      TAPO P110 LOCAL POWER MONITOR (STANDALONE - NO FIREBASE)     ")
    print("=" * 65)
    print(f"Target IP       : {ip}")
    print(f"Authentication  : {'Local Device Account (' + user + ')' if user else 'None (Anonymous)'}")
    print(f"Sampling Rate   : {1.0 / interval:.1f} Hz (Every {interval}s)")
    print(f"Firebase Status : [COMPLETELY DISABLED - LOCAL ONLY]")
    
    csv_file = None
    if log_csv:
        log_dir = Path(__file__).resolve().parent.parent / "data"
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = log_dir / f"tapo_local_test_{timestamp_str}.csv"
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("timestamp_iso,timestamp_ms,power_w,voltage_v,current_ma,today_energy_wh\n")
        print(f"Local CSV Log   : {csv_file}")
    print("=" * 65)

    credentials = Credentials(user, password) if user and password else None
    
    print("\nConnecting to Tapo P110...")
    try:
        device = await Device.connect(host=ip, credentials=credentials)
        await device.update()
        print(f"[CONNECTED] {device.alias} ({device.model}) | State: {'ON' if device.is_on else 'OFF'}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Tapo P110 at {ip}: {e}")
        return

    energy = device.modules.get(Energy)
    if not energy:
        print("[ERROR] Energy metering module not found on this device!")
        return

    print("\nPress Ctrl+C to stop monitoring.\n")
    print(f"{'TIMESTAMP':<12} | {'POWER (W)':<10} | {'VOLTS (V)':<9} | {'CURRENT (mA)':<12} | {'TODAY (Wh)':<10}")
    print("-" * 65)

    try:
        while True:
            await device.update()
            power_w = energy.current_consumption or 0.0
            voltage_v = energy.voltage or 0.0
            current_a = energy.current or 0.0
            current_ma = current_a * 1000.0
            today_wh = (energy.consumption_today or 0.0) * 1000.0
            
            now = datetime.datetime.now()
            time_str = now.strftime("%H:%M:%S")
            iso_str = now.isoformat()
            now_ms = int(time.time() * 1000)

            # Terminal row
            print(f"{time_str:<12} | {power_w:8.2f} W  | {voltage_v:7.1f} V | {current_ma:10.1f} mA | {today_wh:8.1f} Wh", flush=True)

            if csv_file:
                with open(csv_file, "a", encoding="utf-8") as f:
                    f.write(f"{iso_str},{now_ms},{power_w:.2f},{voltage_v:.1f},{current_ma:.1f},{today_wh:.1f}\n")

            await asyncio.sleep(interval)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[STOPPED] Local monitoring halted by user.")
        if csv_file:
            print(f"[SAVED] Local data saved to: {csv_file}")

async def run_mock_monitor(log_csv: bool, interval: float):
    print("\n" + "=" * 65)
    print("      TAPO P110 MOCK SIMULATOR (STANDALONE - NO FIREBASE)         ")
    print("=" * 65)
    print("Mode            : SIMULATION (Mocking Washer Electrical Profile)")
    print("Firebase Status : [COMPLETELY DISABLED - LOCAL ONLY]")
    
    csv_file = None
    if log_csv:
        log_dir = Path(__file__).resolve().parent.parent / "data"
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = log_dir / f"tapo_mock_test_{timestamp_str}.csv"
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("timestamp_iso,timestamp_ms,phase,power_w,voltage_v,current_ma,today_energy_wh\n")
        print(f"Local CSV Log   : {csv_file}")
    print("=" * 65)

    print("\nPress Ctrl+C to stop simulation.\n")
    print(f"{'TIME':<8} | {'PHASE':<14} | {'POWER (W)':<10} | {'VOLTS (V)':<9} | {'CURRENT (mA)':<12}")
    print("-" * 65)

    phases = [
        ("weightSensing", 85.0, 30),
        ("waterHeating", 1980.0, 45),
        ("washAgitation", 140.0, 60),
        ("drainPump", 45.0, 20),
        ("spinRampUp", 480.0, 35),
        ("spinExtraction", 590.0, 40),
        ("standbyIdle", 2.2, 20),
    ]

    phase_idx = 0
    phase_time = 0
    total_energy_wh = 120.0

    try:
        while True:
            curr_phase, base_power, duration = phases[phase_idx]
            
            # Add dynamic natural fluctuations
            jitter = (math.sin(time.time() * 2) * 0.05 + 0.02 * math.cos(time.time() * 5)) * base_power
            power_w = max(1.0, base_power + jitter)
            voltage_v = 239.5 + math.sin(time.time()) * 1.5
            current_a = power_w / voltage_v
            current_ma = current_a * 1000.0
            
            total_energy_wh += (power_w * interval) / 3600.0
            
            now = datetime.datetime.now()
            time_str = now.strftime("%H:%M:%S")
            iso_str = now.isoformat()
            now_ms = int(time.time() * 1000)

            print(f"{time_str:<8} | {curr_phase:<14} | {power_w:8.2f} W  | {voltage_v:7.1f} V | {current_ma:10.1f} mA", flush=True)

            if csv_file:
                with open(csv_file, "a", encoding="utf-8") as f:
                    f.write(f"{iso_str},{now_ms},{curr_phase},{power_w:.2f},{voltage_v:.1f},{current_ma:.1f},{total_energy_wh:.2f}\n")

            phase_time += 1
            if phase_time >= duration:
                phase_time = 0
                phase_idx = (phase_idx + 1) % len(phases)

            await asyncio.sleep(interval)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[STOPPED] Mock simulation halted.")
        if csv_file:
            print(f"[SAVED] Mock data saved to: {csv_file}")

def main():
    parser = get_parser()
    args = parser.parse_args()

    if args.mock:
        asyncio.run(run_mock_monitor(log_csv=args.log_csv, interval=args.interval))
    else:
        if not args.ip:
            print("\n[!] No Tapo IP provided.")
            print("Run with: py firmware/tapo_local_streamer.py --ip <IP> [--user <USER>] [--password <PASS>] [--log-csv]")
            print("Or test with simulated washer power profiles right now using:")
            print("  py firmware/tapo_local_streamer.py --mock --log-csv\n")
            sys.exit(1)
        asyncio.run(run_live_monitor(args.ip, args.user, args.password, args.log_csv, args.interval))

if __name__ == "__main__":
    main()
