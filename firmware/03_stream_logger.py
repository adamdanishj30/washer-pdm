"""
03_stream_logger.py
Multimodal PdM Project: Python Data Logger & Live CSV Recorder
Receives real-time telemetry from ESP32 via Serial (USB) and saves to timestamped CSV files.

Usage:
    python 03_stream_logger.py --port COM3 --baud 115200
"""

import sys
import os
import time
import argparse
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("[ERROR] 'pyserial' not installed. Run: pip install pyserial")
    sys.exit(1)

def auto_detect_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "CP210" in p.description or "CH340" in p.description or "USB" in p.description:
            return p.device
    if len(ports) > 0:
        return ports[0].device
    return None

def main():
    parser = argparse.ArgumentParser(description="Multimodal Vibration & Audio Logger")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (e.g., COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--output_dir", type=str, default="data_recordings", help="Output directory")
    args = parser.parse_args()

    port = args.port or auto_detect_port()
    if not port:
        print("[ERROR] No active serial COM port detected. Please plug in your ESP32.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(args.output_dir, f"pdm_recording_{timestamp}.csv")

    print(f"==================================================")
    print(f" Multimodal Telemetry Logger (Vibration + Audio)")
    print(f" Connecting to: {port} @ {args.baud} baud")
    print(f" Saving to:     {filename}")
    print(f" Press Ctrl+C to stop recording")
    print(f"==================================================")

    try:
        ser = serial.Serial(port, args.baud, timeout=1.0)
        time.sleep(2.0)  # Wait for ESP32 reboot upon DTR toggle
        ser.reset_input_buffer()

        with open(filename, "w", buffering=1) as f:
            f.write("timestamp_iso,elapsed_sec,accel_x,accel_y,accel_z,audio_rms\n")
            start_time = time.time()
            sample_count = 0

            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line or line.startswith("[") or line.startswith("-") or "Format:" in line:
                    continue

                parts = line.split(",")
                if len(parts) == 4:
                    try:
                        ax, ay, az, audio = [float(x) for x in parts]
                        now_iso = datetime.now().isoformat()
                        elapsed = time.time() - start_time
                        
                        f.write(f"{now_iso},{elapsed:.4f},{ax:.3f},{ay:.3f},{az:.3f},{audio:.2f}\n")
                        sample_count += 1

                        if sample_count % 100 == 0:
                            print(f"[{elapsed:6.1f}s] Samples: {sample_count:5d} | Ax: {ax:+6.2f} | Ay: {ay:+6.2f} | Az: {az:+6.2f} | Audio RMS: {audio:5.1f}")
                    except ValueError:
                        continue

    except KeyboardInterrupt:
        print(f"\n[STOP] Recording stopped. Total samples recorded: {sample_count}")
        print(f"[SAVED] File: {os.path.abspath(filename)}")
    except Exception as e:
        print(f"\n[ERROR] Serial communication failed: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
