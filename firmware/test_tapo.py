"""
TP-Link Tapo P110 / P110P Local Telemetry Test Script
Predictive Maintenance (PdM) SideProject
Queries real-time active power (Watts), voltage (V), current (mA), and energy (Wh)
via local KLAP protocol using python-kasa.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

import kasa
from kasa import Device, Credentials
from kasa.interfaces.energy import Energy

async def test_tapo_telemetry(ip: str, username: str = None, password: str = None):
    print(f"\n[TAPO P110] Connecting to {ip} via local LAN...")
    
    credentials = None
    if username and password:
        credentials = Credentials(username, password)
        print(f"[TAPO P110] Using local Device Account authentication (User: {username})")
    else:
        print("[TAPO P110] No credentials provided, attempting connection...")

    try:
        device = await Device.connect(host=ip, credentials=credentials)
        await device.update()
        
        print("\n" + "=" * 50)
        print(f"Device Name      : {device.alias}")
        print(f"Model            : {device.model}")
        print(f"Hardware Version : {device.hw_info}")
        print(f"Power State      : {'ON [Active]' if device.is_on else 'OFF'}")
        print(f"Has Energy Meter : {device.has_emeter}")
        print("=" * 50)
        
        if not device.has_emeter:
            print("[ERROR] Connected device does not report energy metering support!")
            return

        energy = device.modules.get(Energy)
        if not energy:
            print("[ERROR] Energy module not found on device!")
            return

        # Fetch real-time metrics
        power_w = energy.current_consumption or 0.0
        voltage_v = energy.voltage or 0.0
        current_a = energy.current or 0.0
        current_ma = current_a * 1000.0
        today_wh = (energy.consumption_today or 0.0) * 1000.0
        total_kwh = energy.consumption_total or 0.0

        print(f"Active Power     : {power_w:8.2f} W")
        print(f"Grid Voltage     : {voltage_v:8.1f} V")
        print(f"Load Current     : {current_ma:8.1f} mA ({current_a:.2f} A)")
        print(f"Energy Today     : {today_wh:8.2f} Wh")
        print(f"Total Cumulative : {total_kwh:8.3f} kWh")
        print("=" * 50)
        print("[SUCCESS] Local Tapo P110 telemetry communication verified!\n")

    except Exception as e:
        print(f"\n[FAILED] Could not connect to Tapo P110 at {ip}")
        print(f"Error details: {e}")
        print("\nTroubleshooting tips:")
        print("1. Confirm the IP address matches your Tapo app device info.")
        print("2. Ensure PC and Tapo P110 are on the same Wi-Fi / subnet.")
        print("3. Verify Device Account username and password in Tapo App: Me -> Third-Party Services -> Device Account.")

def main():
    ip = os.getenv("TAPO_IP") or (sys.argv[1] if len(sys.argv) > 1 else None)
    username = os.getenv("TAPO_DEVICE_USER") or os.getenv("TAPO_EMAIL") or (sys.argv[2] if len(sys.argv) > 2 else None)
    password = os.getenv("TAPO_DEVICE_PASS") or os.getenv("TAPO_PASSWORD") or (sys.argv[3] if len(sys.argv) > 3 else None)

    if not ip:
        print("\nUsage:")
        print("  py firmware/test_tapo.py <IP_ADDRESS> [USERNAME] [PASSWORD]")
        print("Or set TAPO_IP, TAPO_DEVICE_USER, TAPO_DEVICE_PASS in your .env file.\n")
        sys.exit(1)

    asyncio.run(test_tapo_telemetry(ip, username, password))

if __name__ == "__main__":
    main()
