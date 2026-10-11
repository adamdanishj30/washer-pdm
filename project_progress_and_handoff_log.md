# Multimodal IoT PdM Project — Comprehensive AI Handoff & Progress Log

**Project:** Anomaly Vibration & Acoustic Detection for Samsung WW10TP44DSX/FQ (10kg Washer)  
**Academic Alignment:** Multimodal Machine Learning for Rotating Machinery Fault & Misalignment Detection  
**Hardware Core:** ESP32 DevKit V1 (30-Pin) + MPU-6050 (I2C) + INMP441 (I2S DMA)  
**Date Logged:** 2026-10-10 23:20 (+08:00)  
**Status:** **Phase 1 Benchtop Verification (MPU-6050 + INMP441 Multimodal Rig) 100% COMPLETED!**

---

## 1. Verified Hardware Configuration & Inventory

| Hardware Item | Specific Model / Variant Received | Physical State & Details |
| :--- | :--- | :--- |
| **Microcontroller** | NodeMCU ESP32 DEVKIT V1 (30-pin, Black PCB) | Seated firmly into expansion shield. Verified working on COM3. |
| **Expansion Board** | ESP32 30P G-V-S Sensor Shield | Yellow jumper set to **`3.3V`**. Both MPU-6050 and INMP441 powered at 3.3V. |
| **Vibration Sensor** | MPU-6050 6-DOF IMU (Blue PCB) | Spliced to dedicated I2C header (`D21`, `D22`, `VCC`, `GND`). **Tested & verified streaming live ±16g acceleration**. |
| **Acoustic Sensor** | INMP441 MEMS Digital Microphone (Yellow round PCB) | Spliced to Rows 8, 9, 10 (`WS` $\rightarrow$ GPIO 25, `SCK` $\rightarrow$ GPIO 33, `SD` $\rightarrow$ GPIO 32, `VDD` $\rightarrow$ 3.3V, `GND`/`L/R` $\rightarrow$ GND). **Tested & verified streaming 16 kHz I2S DMA audio RMS**. |
| **Wiring** | Custom DIY Spliced Female-to-Female Jumper Wires | 11 spliced lines (5 for MPU-6050 + 6 for INMP441) verified stable. |
| **Enclosure** | ABS IP65 Weather-sealed box ($158 \times 90 \times 60\text{ mm}$) | Ready for Phase 2 mounting. |
| **Coupling Tape** | 3M Original VHB Acrylic Foam Tape ($2.5\text{cm} \times 3\text{m}$) | Ready for mounting enclosure rigidly to washing machine chassis. |
| **PC Connection** | Micro-USB Data Cable $\rightarrow$ Laptop | Connected directly to ESP32 board's own Micro-USB port (`COM3`). |

---

## 2. Software & Toolchain Status

* **OS:** Windows 10 / 11
* **Host Driver:** Silicon Labs CP210x Universal Windows Driver active on **`COM3`** (`USB\VID_10C4&PID_EA60`).
* **Arduino IDE Version:** 2.3.10
* **ESP32 Core Package:** `esp32:esp32@3.3.12` installed.
* **Firmware:** [`firmware/02_multimodal_telemetry_test/02_multimodal_telemetry_test.ino`](file:///G:/My%20Drive/PdM%20SideProject/firmware/02_multimodal_telemetry_test/02_multimodal_telemetry_test.ino) flashed and verified.
* **Automation Tool:** [`firmware/auto_flash_and_stream.py`](file:///G:/My%20Drive/PdM%20SideProject/firmware/auto_flash_and_stream.py) operational.

---

## 3. Current Pinout & Wiring Mapping (Live Benchtop)

### MPU-6050 (Vibration) $\rightarrow$ Expansion Board Left Cluster:
```
[ MPU-6050 ]                                 [ Expansion Board Left Cluster ]
   VCC        ----------------------------->    VCC  (Row 3, 3.3V)
   GND        ----------------------------->    GND  (Row 4, Left Pin)
   SCL        ----------------------------->    D22  (Row 1, SCL)
   SDA        ----------------------------->    D21  (Row 2, SDA)
   AD0        ----------------------------->    GND  (Row 4, Right Pin - address 0x68)
```

### INMP441 (Microphone) $\rightarrow$ Expansion Board Right Rail:
```
[ INMP441 ]                                  [ Expansion Board Right Rail ]
   VDD        ----------------------------->    Middle Row (V) [3.3V]
   GND        ----------------------------->    Inner Row  (G) [GND at D34]
   L/R        ----------------------------->    Inner Row  (G) [GND at VN] (Left Channel)
   SCK        ----------------------------->    Outer Row  (S) at GPIO 33
   WS         ----------------------------->    Outer Row  (S) at GPIO 25
   SD         ----------------------------->    Outer Row  (S) at GPIO 32
```

---

## 4. Test Verification History

1. **Test 1: I2C Bus Scanner (`01_i2c_bus_scanner.ino`)**
   * **Result:** **PASSED.** MPU-6050 detected at `0x68`.

2. **Test 2: Live 3-Axis Vibration Streamer (`01b_live_vibration_plotter.ino`)**
   * **Result:** **PASSED.** Verified $X, Y, Z$ motion acceleration with 1.0g gravity vector.

3. **Test 3: Multimodal Synchronous Vibration + Acoustic Stream (`02_multimodal_telemetry_test.ino`)**
   * **Result:** **PASSED & VERIFIED 100% LIVE.**
   * **Telemetry Sample:**
     ```text
     Accel_X:4.63,Accel_Y:-5.21,Accel_Z:7.19,Audio_RMS:473.72
     Accel_X:4.66,Accel_Y:-5.16,Accel_Z:7.09,Audio_RMS:719.11
     ... (202 synchronized dual-modality frames captured @ ~50 Hz)
     ```
   * **Acoustic Validation:** I2S DMA buffer capturing 16 kHz 24-bit sound pressure waveforms and calculating real-time RMS energy.
   * **Vibration Validation:** Direct I2C register burst-reading at ±16g full-scale range.

4. **Test 4: Wireless Wi-Fi Multimodal Telemetry & Web Dashboard (`04_wifi_multimodal_streamer.ino`)**
   * **Result:** **PASSED & OPERATIONAL (100% VERIFIED OVER WI-FI).**
   * **Network Assigned:** `leo` (2.4 GHz) -> ESP32 IP: `192.168.0.171`.
   * **Live Web Dashboard:** Reachable at `http://192.168.0.171` or `http://washer-pdm.local` on port 80.
   * **High-Speed UDP Stream:** Broadcasts synchronized packets (`timestamp_ms,accel_x,accel_y,accel_z,audio_rms`) to port 5005 at ~50 Hz.
   * **Wireless CSV Logger:** [`firmware/wifi_logger.py`](file:///G:/My%20Drive/PdM%20SideProject/firmware/wifi_logger.py) verified capturing clean CSV logs over Wi-Fi.

5. **Test 5: Pre-Deployment Enclosure Verification Test (POST-ASSEMBLY)**
   * **Result:** **ALL SYSTEMS GO (100% PASS).**
   * **Telemetry Sample (Enclosure Sealed):**
     * Streaming Rate: `45.5 Hz`
     * Gravity Vector: `X=-0.38, Y=1.16, Z=-9.43 m/s^2` (Total resultant: `9.51 m/s^2` ~ 1.0g gravity confirmed).
     * Acoustic RMS: `102.7` (INMP441 active, sensitive, unobstructed).

6. **Test 6: Autonomous Google Firebase Cloud Telemetry (`05_firebase_multimodal_streamer.ino`)**
   * **Result:** **FULLY OPERATIONAL & LIVE IN THE CLOUD.**
   * **Firebase Endpoint:** `https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app`
   * **Dual-Core FreeRTOS Architecture:**
     * **Core 1:** 100% dedicated to uninterrupted 50 Hz sensor sampling & local UDP stream (zero SSL latency jitter).
     * **Core 0:** Runs background HTTPS cloud uploads to Firebase, Web Server, and ArduinoOTA.
   * **Live Cloud State (`/live.json`):** Updates every 2 seconds with machine state (`IDLE` / `RUNNING` / `SPIN_CYCLE`), vibration magnitude, and acoustic RMS.
   * **Wash Session Chunks (`/sessions/<session_id>/...`):** Automatically logs wash cycles to Firebase in batches every 5 seconds.
   * **Cloud Downloader Tool:** [`firmware/cloud_downloader.py`](file:///G:/My%20Drive/PdM%20SideProject/firmware/cloud_downloader.py) downloads any wash session from the cloud directly into a local CSV with one click.
   * **Cloud Live Web Monitor:** [`cloud_dashboard.html`](file:///G:/My%20Drive/PdM%20SideProject/cloud_dashboard.html) opens in any mobile/desktop browser anywhere in the world to view real-time washer status.
   * **Wireless OTA:** `ArduinoOTA` active (`washer-pdm-rig`), allowing future firmware updates over Wi-Fi without USB cables.

---

## 5. Next Immediate Action Items (Roadmap)

1. **Phase 3: Machine Deployment & Data Logging (100% Autonomous!)**
   * Unplug micro-USB and plug the Type-C cable back into the expansion board.
   * Mount the enclosure to the Samsung WW10TP44DSX washing machine using 3M VHB tape.
   * Plug Type-C into any 5V USB wall plug outside.
   * Whenever your father runs laundry, data automatically records to Google Firebase!
   * Monitor from anywhere via [`cloud_dashboard.html`](file:///G:/My%20Drive/PdM%20SideProject/cloud_dashboard.html) or run [`firmware/cloud_downloader.py`](file:///G:/My%20Drive/PdM%20SideProject/firmware/cloud_downloader.py) whenever you want the full CSV!
