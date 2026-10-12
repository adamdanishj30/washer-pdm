# Multimodal IoT PdM Handoff: Tapo P110 Smart Plug & Samsung SmartThings Integration Plan

**Project:** Autonomous Multimodal Predictive Maintenance (PdM) & Anomaly Detection  
**Target Appliance:** Samsung WW10TP44DSX/FQ (10kg AI Control Front-Load Washing Machine)  
**Document Purpose:** Detailed technical handoff and architecture plan for the next AI agent / developer to implement real-time **Electrical Power (Watts)** from **TP-Link Tapo P110** and **Appliance Cycle Phase** from **Samsung SmartThings**.  
**Date Created:** October 12, 2026 (+08:00)  

---

## 1. Executive Summary & Vision

The current PdM system successfully streams and archives physical telemetry:
- **Kinematic Vibration:** 3-Axis Accelerometer ($A_x, A_y, A_z$ in $\text{m/s}^2$) via MPU-6050 ($\pm 16\text{g}$).
- **Acoustic Pressure:** Digital Microphone sound energy ($RMS$) via INMP441 (I2S DMA, 16 kHz).
- **Autonomous Cloud Logging:** Real-time stream to Firebase RTDB $\rightarrow$ Auto-export to Google Drive on session completion.

### The Missing Telemetry Layers (Phase & Power)
To achieve industrial-grade anomaly detection and eliminate false alarms, the system must integrate two additional modalities:
1. **Electrical Power & Energy (Watt Usage):** Provided by a **TP-Link Tapo P110 / P110P** smart energy monitoring plug.
2. **Ground-Truth Operational Phase:** Provided by the **Samsung SmartThings API** directly from the washing machine's onboard controller.

```
+---------------------------------------------------------------------------------------------------------+
|                                UNIFIED MULTIMODAL PDM TELEMETRY MATRIX                                  |
+--------------------------+-----------------------+-----------------------+------------------------------+
| Modality                 | Physical Sensor/Source| Primary Metrics       | Diagnostic Role              |
+--------------------------+-----------------------+-----------------------+------------------------------+
| 1. Kinematic Vibration   | ESP32 + MPU-6050      | Ax, Ay, Az, |a|       | Mechanical imbalance & wear  |
| 2. Acoustic Sound        | ESP32 + INMP441       | Audio RMS             | Cavitation, friction, squeal |
| 3. Electrical Power      | Tapo P110 Smart Plug  | Watts, Volts, Amps    | Motor load & heater health   |
| 4. Operational Phase     | Samsung SmartThings   | washerJobState        | Contextual baseline & ground |
|                          | Cloud REST API        | (Wash, Rinse, Spin)   | truth supervisory labels     |
+--------------------------+-----------------------+-----------------------+------------------------------+
```

---

## 2. Why Phase & Watt Usage are Vital for Machine Learning

### A. The "Normal Spin vs Anomaly" Problem
In an unsupervised machine learning model (e.g., Isolation Forest, Autoencoder, or One-Class SVM):
- Vibration magnitude $|a|$ during **Wash Agitation** is naturally low ($\approx 9.5 - 10.5\text{ m/s}^2$).
- Vibration magnitude $|a|$ during **High-Speed Spin Extraction (1400 RPM)** naturally peaks at $\approx 11.5 - 14.0\text{ m/s}^2$.
- Sound RMS during wash is $\approx 60 - 150\text{ RMS}$, while during spin it peaks at $\approx 800 - 1100\text{ RMS}$.

**The Problem:** Without knowing the **Phase**, a general anomaly detector will falsely classify every high-speed spin extraction as a catastrophic mechanical failure!  
**The Solution:** By capturing the ground-truth **Phase** (`washerJobState`) from SmartThings, the model performs **Phase-Conditioned Anomaly Detection**:
$$\text{Anomaly Score} = \mathcal{P}(\text{Vibe}, \text{Acoustic}, \text{Watts} \mid \text{Phase})$$

### B. Electrical Power (Watts) as an Independent Mechanical Diagnostic
The Tapo P110 reveals electrical symptoms that vibration sensors cannot directly identify:
- **Water Heating Element (1800W - 2000W):** Confirms if internal water heating cycles activate as scheduled. Burnout or scale build-up causes abnormal wattage or prolonged heating.
- **Inverter Motor Load Curves:** 
  - Gentle wash tumbling: $60\text{ W} - 220\text{ W}$ cyclical pulses.
  - Drain pump activation: $30\text{ W} - 55\text{ W}$ steady baseline.
  - High-speed spin ramp-up: $350\text{ W} - 650\text{ W}$ dynamic load.
  - Motor stall or drum jam: Sudden surge in active current ($I > 10\text{ A}$) without corresponding rotational vibration frequency.

---

## 3. Telemetry Stream Specifications

### Stream A: TP-Link Tapo P110 (Power & Watt Usage)

| Parameter | Specification | Details |
| :--- | :--- | :--- |
| **Device Model** | TP-Link Tapo P110 / P110P (or P110M Matter) | Smart Wi-Fi Energy Monitoring Plug |
| **Rated Load** | 16A / 230V (Max 3680W UK/MY 3-pin standard) | Plugs directly between wall socket & washer plug |
| **Sampling Rate** | $0.5\text{ Hz}$ to $1.0\text{ Hz}$ (Every 1–2 seconds) | Fast enough to capture heater cycles & motor pulses |
| **Metrics Captured** | `power_watts`: Active real-time power (W)<br>`voltage_v`: Grid voltage (V)<br>`current_ma`: Load current (mA)<br>`today_energy_wh`: Cumulative energy (Wh) | All retrieved via JSON |

#### How to Query Tapo P110:
Tapo P110 plugs run an authenticated local HTTP/KLAP server on the local Wi-Fi network. This allows local polling without cloud delays.
- **Recommended Python Library:** `python-kasa` or `plugp100` (`pip install plugp100` or `pip install python-kasa`).
- **Required Credentials:**
  - Plug Local IP Address (e.g. `192.168.0.x` on the home Wi-Fi `leo`).
  - TP-Link Tapo Account Email & Password (used for local device token exchange).
- **Sample Query Output:**
  ```json
  {
    "current_power": 482.6,
    "voltage": 239.1,
    "current": 2040,
    "today_runtime": 86,
    "today_energy": 642
  }
  ```

---

### Stream B: Samsung SmartThings (Appliance Cycle Phase)

| Parameter | Specification | Details |
| :--- | :--- | :--- |
| **Integration Method** | SmartThings Cloud REST API v1 | `https://api.smartthings.com/v1` |
| **Authentication** | Personal Access Token (PAT) | Free token generated from [SmartThings Tokens](https://account.smartthings.com/tokens) |
| **Sampling Rate** | $0.1\text{ Hz}$ to $0.2\text{ Hz}$ (Every 5–10 seconds) | Phases change over minutes, so 5s polling is plenty |
| **Device ID** | Unique UUID assigned to Samsung WW10TP44DSX | Discovered via `GET /v1/devices` |

#### Exact SmartThings Capability Mapping:
Querying `GET https://api.smartthings.com/v1/devices/{deviceId}/status` returns:

```json
{
  "components": {
    "main": {
      "washerOperatingState": {
        "washerJobState": {
          "value": "wash" 
        },
        "machineState": {
          "value": "run"
        },
        "completionTime": {
          "value": "2026-10-12T09:42:00Z"
        }
      },
      "samsungce.washerCycle": {
        "washerCycle": {
          "value": "cotton"
        }
      }
    }
  }
}
```

#### Valid Phase States (`washerJobState`):
1. `weightSensing` — Drum rotates back and forth to weigh laundry load.
2. `wash` — Water fill, detergent mixing, heating, and tumble agitation.
3. `drain` — Drain pump empties soapy water.
4. `rinse` — Fresh water filling and spray rinse tumbling.
5. `spin` — High-speed centrifugal spin extraction (ramping up to 1400 RPM).
6. `finished` / `none` — Cycle ended, gentle unwrinkling, power off.

---

## 4. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Laundry_Room ["Laundry Hardware & Environment"]
        Washer["Samsung WW10TP44DSX Washer"]
        Plug["Tapo P110 Smart Plug (Wall Socket)"]
        ESP["ESP32 PdM Rig (Chassis Box)"]
        
        Washer -->|"Power Drawn Through"| Plug
        Washer -->|"Vibrates Chassis & Emits Sound"| ESP
    end

    subgraph Data_Acquisition ["Acquisition Streams"]
        Plug -->|"Local Wi-Fi (KLAP / 1 Hz)\nWatts, Volts, Amps"| Poller["Central PdM Collector Script / Daemon"]
        Washer -->|"SmartThings Cloud API (5s)\nwasherJobState (Phase)"| Poller
        ESP -->|"HTTPS PUT (2s)\nAx, Ay, Az, RMS"| Firebase[("Google Firebase RTDB")]
        Firebase --> Poller
    end

    subgraph Storage_Dashboard ["Storage & Analytics"]
        Poller -->|"Synchronized 12-Column CSV"| GDrive[("Google Drive Storage")]
        Poller -->|"Live / Historic Telemetry"| Dashboard["PdM Web Dashboard\n(Cards 1, 2, 3 + Power/Phase)"]
    end
```

---

## 5. Unified Dataset Schema (Target Format)

The final merged CSV output stored in Google Drive (`G:\My Drive\PdM SideProject\data\wash_cycle_YYYY-MM-DD_HHMM.csv`) will feature the following unified format:

```csv
timestamp_iso,timestamp_ms,phase,machine_state,power_w,voltage_v,current_ma,accel_x,accel_y,accel_z,vibe_mag,audio_rms
2026-10-12T08:00:10Z,1791794410000,weightSensing,running,85.4,240.1,380,-0.42,1.15,-9.50,9.58,110.2
2026-10-12T08:03:00Z,1791794580000,wash,running,2010.5,238.4,8450,-0.65,1.38,-9.42,9.54,82.4
2026-10-12T08:45:15Z,1791797115000,drain,running,42.1,239.8,190,-0.12,0.85,-9.65,9.69,215.8
2026-10-12T08:52:00Z,1791797520000,rinse,running,145.2,239.0,620,-1.10,1.80,-9.35,9.58,125.0
2026-10-12T09:26:30Z,1791799590000,spin,running,542.8,236.8,2290,-3.45,4.12,-11.20,12.42,1036.5
2026-10-12T09:42:50Z,1791800570000,finished,idle,2.1,241.0,20,-0.38,1.16,-9.43,9.51,68.0
```

---

## 6. Dashboard Visualization Plan

Once Phase and Watt usage are ingested, the Dashboard will reflect them as follows:

1. **Card 1 (Dual-Modality Telemetry):**
   - Add a 3rd curve or secondary toggle: **Electrical Power ($W$)** alongside Vibration Resultant ($|a|$) and Acoustic Sound ($RMS$).
   - Clearly visualizes the 2000W heating spike during `wash`, dropping to ~40W during `drain`, and rising to 550W during high-speed `spin`.

2. **Card 2 (Tri-Axial Vibration):**
   - Retain isolated $A_x, A_y, A_z$ waveforms with 1g gravity baselines.

3. **Card 3 (Timeline, Controls & Phase Band):**
   - Add a colored horizontal **Phase Progression Ribbon** above the time slider:
     - 🟣 `Weight Sensing` (0 – 2m)
     - 🔵 `Wash / Heat` (2 – 45m)
     - 🟠 `Drain & Rinse` (45 – 75m)
     - 🔴 `Final High-Speed Spin` (75 – 102m)
     - 🟢 `Finished`
   - Hovering or scrubbing the playhead immediately shows the exact phase label and Watt consumption at that point in time.

---

## 7. Step-by-Step Implementation Instructions for Next AI

When the user is ready to connect the hardware, the next AI assistant should follow this sequence:

### Step 1: Tapo P110 Setup
1. Instruct user to plug the Tapo P110 into the wall and connect the washer to it via the Tapo Mobile App on 2.4 GHz Wi-Fi `leo`.
2. Find the local IP address of the plug (e.g. `192.168.0.x`).
3. Install the Tapo library:
   ```powershell
   py -m pip install plugp100
   ```
4. Create `firmware/tapo_p110_poller.py` to authenticate locally and verify live power readings ($W, V, mA$).

### Step 2: SmartThings API Setup
1. Instruct user to go to [SmartThings Personal Access Tokens](https://account.smartthings.com/tokens) and generate a token with `r:devices:*` permissions.
2. Create `firmware/smartthings_poller.py` using `urllib.request` or `requests`:
   ```python
   headers = {"Authorization": f"Bearer {SMARTTHINGS_PAT}"}
   # Discover devices:
   # GET https://api.smartthings.com/v1/devices
   # Query status:
   # GET https://api.smartthings.com/v1/devices/{device_id}/status
   ```
3. Extract `washerJobState` (`wash`, `rinse`, `spin`, etc.).

### Step 3: Central Collector Daemon (`firmware/unified_multimodal_collector.py`)
1. Create a background service that:
   - Polls Tapo P110 locally every 2.0s for Watt usage.
   - Polls SmartThings API every 5.0s for cycle phase.
   - Writes/merges these values into Firebase under `/live.json` and `/sessions/<session_id>/...` or into the local sync daemon [auto_drive_sync_daemon.py](file:///g:/My%20Drive/PdM%20SideProject/firmware/auto_drive_sync_daemon.py).
2. When the washer cycle completes (`washerJobState == 'finished'` or ESP goes offline):
   - Compiles the full 12-column CSV dataset and saves to `G:\My Drive\PdM SideProject\data\`.
   - Triggers dashboard re-generation via [build_clean_dashboard.py](file:///g:/My%20Drive/PdM%20SideProject/build_clean_dashboard.py).

---

## 8. Summary of Credentials & Config Keys Needed from User

| Item | Description | Where to Get |
| :--- | :--- | :--- |
| `TAPO_IP` | Local IP address of Tapo P110 plug | Router DHCP list or Tapo App Device Settings |
| `TAPO_EMAIL` | TP-Link / Tapo account email | Tapo App profile |
| `TAPO_PASSWORD` | TP-Link / Tapo account password | Tapo App profile |
| `SMARTTHINGS_PAT` | Samsung SmartThings Personal Access Token | [https://account.smartthings.com/tokens](https://account.smartthings.com/tokens) |
| `SMARTTHINGS_DEVICE_ID` | UUID of Samsung WW10TP44DSX Washer | Auto-discovered via API using PAT |

---
*This handoff document is fully preserved in `g:\My Drive\PdM SideProject\tapo_and_smartthings_pdm_handoff.md` and ready for immediate reference by the next AI assistant.*
