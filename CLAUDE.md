# Washer PdM - Autonomous Multimodal Anomaly Detection Rig

Predictive Maintenance (PdM) & vibration/acoustic anomaly detection for a Samsung WW10TP44DSX front-load washing machine using an ESP32 edge microcontroller, MPU-6050 accelerometer, INMP441 MEMS microphone, Tapo P110 power monitor, and Samsung SmartThings API.

## Strategic Scope & Hackathon Alignment (Prognostics & Energy AI)
- **High-Level Vision:** Low-cost (< RM 50) Multimodal Edge IoT & Predictive AI Platform for home appliances and smart township facilities (aligned with Sime Darby Property "Township of Tomorrow" People & Planet tracks and rotating machinery PdM).
- **Prognostics & Remaining Useful Life (RUL):** Moves beyond reactive "fix-when-broken" to proactive degradation forecasting. Estimates remaining machine cycles before critical component failure (e.g., drum suspension dampers, tub bearings, pump impellers).
- **Parasitic Energy Waste Reduction:** Mechanical friction and misalignment force inverter motors to draw 15%–35% excess electrical power ($W$) to maintain target RPM. Cross-correlating Tapo P110 power telemetry with MPU-6050 vibration harmonics and INMP441 acoustics quantifies and flags parasitic energy drain.
- **Economic Value (P-F Interval):** Intervening at Point P (micro-vibration/acoustic harmonics) allows minor RM 25–50 preventative component replacements before reaching Point F (motor burnout, tub cracking, flooding/fire hazard costing RM 800–1,800+ or total machine scrapping).
- **Smart Township & Facility Management (FM):** Scalable fleet monitoring across high-density residential towers, shared laundry hubs, clubhouse equipment, and water booster pumps to eliminate resident noise complaints and prevent catastrophic equipment failures.

## Tech Stack
- **Firmware / Edge:** C++ / Arduino ESP32 (`esp32:esp32@3.3.12`), FreeRTOS dual-core multitasking, I2C, I2S DMA.
- **Backend & Cloud:** Python 3.12+ (`urllib`, `json`, `subprocess`), Google Firebase RTDB, Google Apps Script (Cloud-to-Drive auto sync).
- **Auxiliary Telemetry (Phase 4):** TP-Link Tapo P110 (UK/MY Type G 3-Pin, BS 1363 13A/2,990W max, local KLAP protocol via `python-kasa`), Samsung SmartThings Cloud REST API v1 (`washerOperatingState.washerJobState`, CLI/OAuth token refresh).
- **Frontend / Visuals:** HTML5, CSS3 Custom Properties (Dark luxury theme), Vanilla JS, CanvasJS / Chart.js for real-time telemetry waveforms.
- **Data & ML:** CSV time series (`timestamp_ms`, `accel_x`, `accel_y`, `accel_z`, `audio_rms`), FFT spectral analysis, unsupervised anomaly detection (Isolation Forest / Autoencoder).

## Common Tasks & Commands
- **Flash Standalone ESP32 Firmware:** `py -3.12 firmware/06_standalone_tapo_streamer/flash_firmware.py --port COM3` (add `--compile` to recompile)
- **Run Cloud Multimodal Sync (Once):** `py -3.12 firmware/cloud_multimodal_sync.py --once`
- **Run Continuous Cloud Sync Daemon:** `py -3.12 firmware/cloud_multimodal_sync.py --interval 10`
- **Download Firebase Session:** `py firmware/cloud_downloader.py`
- **Recompile HTML Dashboards:** `py build_clean_dashboard.py`
- **Run Wi-Fi UDP Logger:** `py firmware/wifi_logger.py`
- **Verify Python Syntax:** `py -m py_compile build_clean_dashboard.py firmware/cloud_multimodal_sync.py firmware/06_standalone_tapo_streamer/flash_firmware.py`

## Project Structure
```
PdM SideProject/
├── firmware/                        # Arduino sketches & Python daemons
│   ├── 01_i2c_bus_scanner/          # Benchtop I2C address detection (0x68)
│   ├── 01b_live_vibration_plotter/  # Serial plotter for 3-axis vibration
│   ├── 02_multimodal_telemetry_test/# Synchronous MPU-6050 + INMP441 test
│   ├── 04_wifi_multimodal_streamer/ # Local UDP 50Hz broadcaster & web server
│   ├── 05_firebase_multimodal_streamer/ # Dual-Core FreeRTOS + Firebase RTDB
│   ├── 06_standalone_tapo_streamer/ # Autonomous ESP32 + Tapo P110 (KLAP) + Firebase
│   │   ├── 06_standalone_tapo_streamer.ino # Main FreeRTOS firmware (Core 0/1)
│   │   ├── tapo_device.h            # C++ Tapo P110 energy client
│   │   ├── tapo_protocol.h & cipher.h # Local KLAP encryption implementation
│   │   ├── secrets.h / secrets.h.example # Network & hardware credentials
│   │   └── flash_firmware.py        # Automated flasher & compiler
│   ├── cloud_multimodal_sync.py     # Autonomous Cloud-to-Cloud Bridge (Firebase + SmartThings)
│   ├── auto_drive_sync_daemon.py    # Offline auto-archiver to data/
│   └── cloud_downloader.py          # Session downloader CLI
├── data/                            # Raw and testing wash cycle CSVs
├── *.html                           # Telemetry dashboards (cloud, live, historical)
├── build_clean_dashboard.py         # Static HTML dashboard generator
└── .github/workflows/               # Serverless GitHub Actions cron & mobile sync
```

## Hardware Pinout
- **MPU-6050 (I2C):** `SDA` -> GPIO 21, `SCL` -> GPIO 22, `VCC` -> 3.3V, `GND`/`AD0` -> GND (`0x68`)
- **INMP441 (I2S DMA):** `WS` -> GPIO 25, `SCK` -> GPIO 33, `SD` -> GPIO 32, `VDD` -> 3.3V, `GND`/`L/R` -> GND (Left Channel)
- **FreeRTOS Affinity:** Core 1 = 50 Hz sensor sampling & UDP broadcast. Core 0 = HTTPS Firebase, Web server, ArduinoOTA.

## Conventions & Rules
- **Data Schema:** All telemetry CSVs must strictly follow `timestamp_ms,accel_x,accel_y,accel_z,audio_rms`.
- **Git Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **Security:** Do not commit production Wi-Fi passwords, Firebase database secrets, or SmartThings PATs.
