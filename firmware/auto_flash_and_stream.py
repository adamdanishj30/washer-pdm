import sys
import time
import os
import subprocess
import serial
import serial.tools.list_ports

PYTHON_EXE = sys.executable

# Allow passing sketch name as command-line arg, default to 02_multimodal_telemetry_test
sketch_target = sys.argv[1] if len(sys.argv) > 1 else "02_multimodal_telemetry_test"

MERGED_BIN = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    sketch_target,
    "build",
    f"{sketch_target}.ino.merged.bin"
)
PORT = "COM3"

def kill_serial_monitors():
    try:
        subprocess.run(["powershell", "-Command", "Stop-Process -Name 'serial-monitor' -Force -ErrorAction SilentlyContinue"], capture_output=True)
    except Exception:
        pass

def is_port_present(port_name):
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return port_name in ports

def attempt_flash(max_loops=60):
    print(f"\n=======================================================", flush=True)
    print(f"   AUTOMATED PdM ESP32 FLASH & LIVE STREAM TOOL        ", flush=True)
    print(f"=======================================================", flush=True)
    print(f"Target Binary: {MERGED_BIN}", flush=True)
    print(f"Target Port:   {PORT}", flush=True)
    
    if not os.path.exists(MERGED_BIN):
        print(f"ERROR: Merged binary not found at {MERGED_BIN}", flush=True)
        return False
        
    kill_serial_monitors()
    time.sleep(0.5)

    print("\n[MONITORING ACTIVE] Waiting for board handshake...", flush=True)
    print("-------------------------------------------------------", flush=True)
    print(">>> 1. UNPLUG the USB cable for 3 seconds.", flush=True)
    print(">>> 2. PLUG IT BACK IN while holding the 'BOOT' button!", flush=True)
    print("-------------------------------------------------------", flush=True)
    
    was_disconnected = False
    
    for attempt in range(1, max_loops + 1):
        kill_serial_monitors()
        
        # Check if port is plugged in
        if not is_port_present(PORT):
            if not was_disconnected:
                print(f"\n[USB UNPLUGGED] Port {PORT} disconnected. Waiting for re-insertion...", flush=True)
                was_disconnected = True
            time.sleep(0.5)
            continue
        else:
            if was_disconnected:
                print(f"\n[USB RE-PLUGGED!] Port {PORT} detected! Initiating instant flash...", flush=True)
                was_disconnected = False
                time.sleep(0.5)
        
        # Alternate baud rates
        baud = "115200" if attempt % 2 != 0 else "921600"
        print(f"\n[{time.strftime('%H:%M:%S')}] Attempt {attempt}/{max_loops}: Probing {PORT} at {baud} baud...", flush=True)
        
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
            MERGED_BIN
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            connected = False
            for line in iter(process.stdout.readline, ''):
                sys.stdout.write(line)
                sys.stdout.flush()
                if "Chip is ESP32" in line or "Uploading stub..." in line:
                    if not connected:
                        connected = True
                        print("\n" + "="*55, flush=True)
                        print(">>> [SUCCESS!] ESP32 CHIP DETECTED! RELEASE THE BOOT BUTTON NOW!", flush=True)
                        print("="*55 + "\n", flush=True)
                        
            process.wait()
            if process.returncode == 0:
                print("\n[FLASH COMPLETE] Flashing succeeded 100%!", flush=True)
                return True
        except Exception as e:
            print(f"Attempt error: {e}", flush=True)
            
        time.sleep(0.8)
        
    return False

def stream_live_data(duration_sec=15):
    print(f"\n[STREAM] Opening {PORT} at 115200 baud to verify live motion stream...", flush=True)
    time.sleep(1.2) # Allow ESP32 reboot
    try:
        s = serial.Serial(PORT, 115200, timeout=1)
        s.dtr = False
        s.rts = False
        start = time.time()
        sample_count = 0
        print("\n--- LIVE VIBRATION TELEMETRY (Real-time MPU-6050) ---", flush=True)
        while time.time() - start < duration_sec:
            if s.in_waiting:
                line = s.readline().decode('utf-8', errors='replace').strip()
                if line:
                    print(f"  telemetry: {line}", flush=True)
                    if "Accel_X" in line:
                        sample_count += 1
            time.sleep(0.01)
        s.close()
        print(f"\n[VERIFIED] Successfully received {sample_count} live 3-axis vibration samples!", flush=True)
        return sample_count > 0
    except Exception as e:
        print(f"[STREAM ERROR] {e}", flush=True)
        return False

if __name__ == "__main__":
    success = attempt_flash()
    if success:
        print("\n[FLASH COMPLETE] Flashing succeeded 100%!", flush=True)
        stream_live_data(15)
    else:
        print("\n[FAILED] Flash timed out. Please check cable connection and try again.", flush=True)
