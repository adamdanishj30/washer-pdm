import sys
import time
import os
import subprocess
import serial
import serial.tools.list_ports

PYTHON_EXE = sys.executable
FIRMWARE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_BIN = os.path.join(
    FIRMWARE_DIR, 
    "04_wifi_multimodal_streamer", 
    "build", 
    "04_wifi_multimodal_streamer.ino.merged.bin"
)
PORT = "COM3"

def kill_serial_monitors():
    try:
        subprocess.run(
            ["powershell", "-Command", "Stop-Process -Name 'serial-monitor' -Force -ErrorAction SilentlyContinue"],
            capture_output=True
        )
    except Exception:
        pass

def flash_esp32(max_loops=30):
    print("=" * 60, flush=True)
    print("   FLASHING MULTIMODAL WI-FI TELEMETRY FIRMWARE (ESP32)   ", flush=True)
    print("=" * 60, flush=True)
    print(f"Target Binary: {TARGET_BIN}", flush=True)
    print(f"Target Port:   {PORT}", flush=True)
    
    if not os.path.exists(TARGET_BIN):
        print(f"[ERROR] Binary not found at: {TARGET_BIN}", flush=True)
        return False

    kill_serial_monitors()
    time.sleep(0.5)

    print("\n[PROBING] Attempting automated flash...", flush=True)
    print("Tip: If connection fails, HOLD the 'BOOT' button on the ESP32.\n", flush=True)

    for attempt in range(1, max_loops + 1):
        kill_serial_monitors()
        
        # Check if COM3 exists
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if PORT not in ports:
            print(f"[{time.strftime('%H:%M:%S')}] Waiting for {PORT} to appear...", flush=True)
            time.sleep(1)
            continue
            
        baud = "115200" if attempt % 2 != 0 else "921600"
        print(f"[{time.strftime('%H:%M:%S')}] Attempt {attempt}/{max_loops} at {baud} baud...", flush=True)
        
        cmd = [
            PYTHON_EXE, "-m", "esptool",
            "--port", PORT,
            "--chip", "esp32",
            "--baud", baud,
            "--before", "default-reset",
            "--after", "hard-reset",
            "--connect-attempts", "5",
            "write-flash",
            "--flash-mode", "dio",
            "--flash-freq", "80m",
            "--flash-size", "4MB",
            "0x0",
            TARGET_BIN
        ]
        
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            connected = False
            for line in iter(p.stdout.readline, ''):
                sys.stdout.write(line)
                sys.stdout.flush()
                if "Chip is ESP32" in line or "Uploading stub..." in line:
                    if not connected:
                        connected = True
                        print("\n>>> [HANDSHAKE SUCCESSFUL] Uploading firmware to ESP32...\n", flush=True)
            p.wait()
            if p.returncode == 0:
                print("\n[FLASH SUCCESS] Firmware written successfully 100%!", flush=True)
                return True
        except Exception as e:
            print(f"Attempt error: {e}", flush=True)
            
        time.sleep(1)
    return False

def monitor_boot_log(duration_sec=12):
    print("\n" + "=" * 60, flush=True)
    print("   MONITORING ESP32 WI-FI BOOT & IP ALLOCATION   ", flush=True)
    print("=" * 60, flush=True)
    time.sleep(1.5) # Allow ESP32 reboot
    
    try:
        s = serial.Serial(PORT, 115200, timeout=1)
        s.dtr = False
        s.rts = False
        start = time.time()
        ip_found = None
        
        while time.time() - start < duration_sec:
            if s.in_waiting:
                line = s.readline().decode('utf-8', errors='replace').strip()
                if line:
                    print(f"  [ESP32] {line}", flush=True)
                    if "IP Address:" in line:
                        ip_found = line.split(":")[-1].strip()
            time.sleep(0.01)
        s.close()
        
        if ip_found:
            print(f"\n[CONFIRMED] ESP32 IP is: {ip_found}", flush=True)
            print(f"Open your browser to: http://{ip_found} or http://washer-pdm.local")
        return True
    except Exception as e:
        print(f"[MONITOR ERROR] {e}", flush=True)
        return False

if __name__ == "__main__":
    if flash_esp32():
        monitor_boot_log(15)
    else:
        print("[FAILED] Flash timed out.", flush=True)
