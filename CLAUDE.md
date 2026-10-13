# Washer PdM - Autonomous Multimodal Anomaly Detection Rig

Predictive Maintenance (PdM) & vibration/acoustic anomaly detection for a Samsung WW10TP44DSX front-load washing machine using an ESP32 edge microcontroller, MPU-6050 accelerometer, INMP441 MEMS microphone, Tapo P110 power monitor, and Samsung SmartThings API.

## Tech Stack
- **Firmware / Edge:** C++ / Arduino ESP32 (`esp32:esp32@3.3.12`), FreeRTOS dual-core multitasking, I2C, I2S DMA.
- **Backend & Cloud:** Python 3.12+ (`urllib`, `json`, `subprocess`), Google Firebase RTDB, Google Apps Script (Cloud-to-Drive auto sync).
- **Frontend / Visuals:** HTML5, CSS3 Custom Properties (Dark luxury theme), Vanilla JS, CanvasJS / Chart.js for real-time telemetry waveforms.
- **Data & ML:** CSV time series (`timestamp_ms`, `accel_x`, `accel_y`, `accel_z`, `audio_rms`), FFT spectral analysis, unsupervised anomaly detection (Isolation Forest / Autoencoder).

## Common Tasks & Commands
- **Run Auto-Sync Daemon:** `py firmware/auto_drive_sync_daemon.py` (or execute `run_auto_sync_daemon.bat`)
- **Download Firebase Session:** `py firmware/cloud_downloader.py`
- **Recompile HTML Dashboards:** `py build_clean_dashboard.py`
- **Run Wi-Fi UDP Logger:** `py firmware/wifi_logger.py`
- **Flash Firmware via Serial:** Open `firmware/05_firebase_multimodal_streamer/05_firebase_multimodal_streamer.ino` in Arduino IDE 2.3.10 (Board: ESP32 Dev Module, Port: COM3).
- **Verify Python Syntax:** `py -m py_compile build_clean_dashboard.py firmware/auto_drive_sync_daemon.py firmware/cloud_downloader.py`

## Project Structure
```
PdM SideProject/
├── firmware/                        # Arduino sketches & Python daemons
│   ├── 01_i2c_bus_scanner/          # Benchtop I2C address detection (0x68)
│   ├── 01b_live_vibration_plotter/  # Serial plotter for 3-axis vibration
│   ├── 02_multimodal_telemetry_test/# Synchronous MPU-6050 + INMP441 test
│   ├── 04_wifi_multimodal_streamer/ # Local UDP 50Hz broadcaster & web server
│   ├── 05_firebase_multimodal_streamer/ # Production FreeRTOS + Firebase RTDB
│   ├── auto_drive_sync_daemon.py    # Offline auto-archiver to data/
│   └── cloud_downloader.py          # Session downloader CLI
├── data/                            # Raw and testing wash cycle CSVs
├── *.html                           # Telemetry dashboards (cloud, live, historical)
├── build_clean_dashboard.py         # Static HTML dashboard generator
└── google_apps_script_drive_sync.js # 24/7 cloud auto-sync script
```

## Hardware Pinout
- **MPU-6050 (I2C):** `SDA` -> GPIO 21, `SCL` -> GPIO 22, `VCC` -> 3.3V, `GND`/`AD0` -> GND (`0x68`)
- **INMP441 (I2S DMA):** `WS` -> GPIO 25, `SCK` -> GPIO 33, `SD` -> GPIO 32, `VDD` -> 3.3V, `GND`/`L/R` -> GND (Left Channel)
- **FreeRTOS Affinity:** Core 1 = 50 Hz sensor sampling & UDP broadcast. Core 0 = HTTPS Firebase, Web server, ArduinoOTA.

## Conventions & Rules
- **Data Schema:** All telemetry CSVs must strictly follow `timestamp_ms,accel_x,accel_y,accel_z,audio_rms`.
- **Git Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **Security:** Do not commit production Wi-Fi passwords, Firebase database secrets, or SmartThings PATs.
