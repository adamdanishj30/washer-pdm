import socket
import time
import os
import sys

UDP_PORT = 5005
BUFFER_SIZE = 1024

def start_logger():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    csv_file = os.path.join(data_dir, f"wash_telemetry_{timestamp_str}.csv")
    
    print("=" * 60)
    print("    WIRELESS MULTIMODAL PDM TELEMETRY LOGGER (WIFI)    ")
    print("=" * 60)
    print(f"Listening on UDP port: {UDP_PORT}")
    print(f"Logging data to:       {csv_file}")
    print("Press Ctrl+C at any time to finish recording.\n")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.settimeout(2.0)
    
    sample_count = 0
    start_time = time.time()
    
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("timestamp_ms,accel_x,accel_y,accel_z,audio_rms\n")
        f.flush()
        
        print("Waiting for wireless packets from ESP32...")
        try:
            while True:
                try:
                    data, addr = sock.recvfrom(BUFFER_SIZE)
                    line = data.decode("utf-8", errors="replace").strip()
                    if line:
                        f.write(line + "\n")
                        sample_count += 1
                        
                        # Print status every 25 samples (~0.5s)
                        if sample_count % 25 == 0:
                            elapsed = time.time() - start_time
                            rate = sample_count / (elapsed if elapsed > 0 else 1)
                            print(f"[{elapsed:.1f}s | {rate:.1f} Hz] From {addr[0]}: {line}")
                            f.flush()
                except socket.timeout:
                    print("... waiting for packets (is the ESP32 powered on?) ...")
        except KeyboardInterrupt:
            print(f"\n\n[RECORDING FINISHED] Captured {sample_count} samples!")
            print(f"Saved to: {csv_file}")
            sock.close()

if __name__ == "__main__":
    start_logger()
