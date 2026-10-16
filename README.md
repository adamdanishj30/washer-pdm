# AcuVibe PdM: Multimodal Predictive Maintenance for Sustainable Townships

> **From Home Appliances to Township Infrastructure**  
> An autonomous IoT edge rig, cloud streaming pipeline, and predictive AI platform designed for the **Sime Darby Property Hackathon ("Township of Tomorrow")**.
>
> 🌐 **Live Deployed Dashboard:** [https://washer-pdm.pages.dev](https://washer-pdm.pages.dev)

---

## 1. Executive Summary & Vision

In modern residential townships and commercial developments, mechanical equipment (from household washing machines to massive rooftop air-conditioning chillers) is traditionally managed through **reactive "run-to-failure" maintenance**. 

When a bearing wears down or a suspension damper fatigues:
1. **Parasitic Energy Waste:** Mechanical friction silently leeches **15% to 35% excess electrical power** for months without being noticed.
2. **Catastrophic Failure:** Unaddressed friction leads to total motor burnout or structural damage, forcing full equipment replacement (RM 800–1,800+ for appliances, RM 15,000–50,000+ for commercial HVAC).
3. **Massive E-Waste:** Perfectly salvageable 70 kg machines and heavy industrial hardware are dumped into landfills simply because a **RM 25 consumable component** failed unnoticed.

### The Solution: Option 2 Positioning
**AcuVibe PdM** solves this by uniting a **proven physical testbed** with a **scalable township infrastructure architecture**:
* **Micro (The Proven Hardware Rig):** A fully functioning edge-AI rig deployed on a front-load Samsung washing machine, capturing 3-axis vibration kinematics, 16 kHz acoustic sound pressure, active electrical wattage, and cycle ground truth in real time.
* **Macro (Township-Scale Expansion):** Scaling the exact same multimodal sensor pods across commercial township assets—monitoring **20 to 30 air conditioning compressors in mosques, suraus, commercial malls, clubhouses, and water pump stations** from a single centralized facility dashboard.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   THE TOWNSHIP PDM PLATFORM                            │
│                                                                        │
│   [ MICRO: The Proven Testbed ]         [ MACRO: The Township Vision ] │
│   • Home Appliance (Samsung Washer)     • Mosques, Suraus & Clubhouses │
│   • Dual-core ESP32 Edge Processing     • Commercial Malls & Offices   │
│   • Kinematics + Acoustics + Tapo P110  • Township Water Pump Stations │
│   • Real Data & Live Web Dashboard      • 20–30+ Centralized HVACs     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Alignment with Sime Darby "Township of Tomorrow"

| Challenge Pillar | Specific Criterion | Township Impact |
| :--- | :--- | :--- |
| **Planet** | **02 Circular Economy (reuse, don't waste)** | Extends appliance and commercial HVAC lifespan by **5 to 10 years** by catching faults early on the **P-F Interval** (replacing RM 25 dampers/bearings before drum or compressor seizure), preventing tons of bulky landfill e-waste. |
| **Planet** | **03 Energy Efficiency** | Quantifies and eliminates **parasitic friction drag** (+15% to +35% excess wattage), reducing residential and commercial grid load across the township. |
| **People** | **05 Digital Living** | Replaces stressful emergency breakdowns with proactive mobile asset health transparency (**0%–100% Machine Health Index**) for residents and automated triage for facility managers. |
| **Business** | **Facility OpEx Reduction** | Replaces manual 1-by-1 physical inspections of 30+ township AC compressors with centralized, AI-driven dispatching. |

---

## 3. Multimodal Telemetry Matrix

Rotating electromechanical machinery shares universal degradation physics:
$$\text{Micro-Vibration Harmonics} \longrightarrow \text{Acoustic Friction} \longrightarrow \text{Parasitic Electrical Drag} \longrightarrow \text{Catastrophic Breakdown}$$

Our platform captures all 4 diagnostic dimensions simultaneously:

| Modality | Hardware / Source | Sampling / Specs | Diagnostic Function |
| :--- | :--- | :--- | :--- |
| **1. Kinematics** | MPU-6050 Accelerometer | 50 Hz, $\pm 16\text{g}$, I2C | Detects drum unbalance, violent chassis rocking, and damper fatigue. |
| **2. Acoustics** | INMP441 MEMS Microphone | 16 kHz I2S DMA $\rightarrow$ RMS | Identifies high-frequency bearing squeal, rubbing, and cavitation. |
| **3. Electrical** | TP-Link Tapo P110 Smart Plug | 1 Hz local KLAP ($W, V, mA$) | Measures active motor load, parasitic friction drag, and cycle kWh. |
| **4. Ground Truth** | Samsung SmartThings API | REST OAuth2 (`washerJobState`) | Contextual phase supervisory labels (`wash`, `rinse`, `spin`). |

---

## 4. Hardware Architecture & Dual-Core Discipline

To ensure rock-solid data integrity without thread starvation or dropped audio packets, the ESP32 firmware enforces a strict **FreeRTOS dual-core separation**:

```
             ┌──────────────────────────────────────────────┐
             │            ESP32 NodeMCU DevKit              │
             ├──────────────────────┬───────────────────────┤
             │       CORE 1         │        CORE 0         │
             │ (High-Speed Sensors) │   (Network & Cloud)   │
             ├──────────────────────┼───────────────────────┤
             │ • MPU-6050 (I2C)     │ • Wi-Fi 802.11 b/g/n  │
             │ • INMP441 (I2S DMA)  │ • SSL / HTTPS Client  │
             │ • Real-time RMS Calc │ • Firebase RTDB Sync  │
             │ • Mutex Spinlocks    │ • Watchdog Keep-Alive │
             └──────────────────────┴───────────────────────┘
```

* **Chassis Enclosure:** IP65 weatherproof junction box with PG7 cable glands and 3M VHB vibration-coupling mounting.
* **Screw Terminal Shield:** High-vibration-resistant screw terminals preventing jumper wire disconnects during 1,400 RPM spin cycles.

---

## 5. Live Interactive Dashboard

The dashboard provides a real-time, responsive dark UI built with pure web technologies (zero heavy frameworks, instant loading on mobile and desktop):

* **Card 1 (Kinematic Waveform):** Real-time tri-axial acceleration ($a_x, a_y, a_z$) in $\text{m/s}^2$ with baseline gravity reference.
* **Card 2 (Acoustic Pressure):** Standardized $[0, 1200]\text{ RMS}$ audio energy waveform with dynamic anomaly threshold and peak spike badges.
* **Card 3 (Vibration Magnitude):** Combined Euclidean acceleration $|a| = \sqrt{a_x^2 + a_y^2 + a_z^2}$ tracking centrifugal spin dynamics.
* **Card 4 (Electrical Power & Energy Diagnostics):** Active wattage curve ($W$), centrifugal spin threshold ($400\text{ W}$), automatic load mass classification (`LIGHT`, `MEDIUM`, `HEAVY`), parasitic motor drag detection, and cumulative cycle energy cost ($\text{kWh}$ and $\text{RM}$).

🔗 **Access the live site:** [https://washer-pdm.pages.dev](https://washer-pdm.pages.dev)

---

## 6. Repository Structure

```
├── firmware/
│   ├── 06_standalone_tapo_streamer/   # ESP32 FreeRTOS Dual-Core C++ Firmware
│   ├── capture_pdm_dataset.py         # Real-time multimodal session recorder
│   ├── cloud_downloader.py            # Automated Firebase session sync engine
│   ├── standardize_datasets.py        # Acoustic RMS normalization engine
│   ├── pdm_ml_standardizer.py         # ML feature transformer (canonical scale, log, dB)
│   └── audit_all_datasets.py          # Integrity audit across all historical CSVs
├── data/
│   ├── real_sessions/                 # Full multi-minute wash cycles (6-column standardized)
│   ├── testing_data/                  # Diagnostic bench logs and buffer dump traces
│   ├── pdm_multimodal_prediction_dataset.csv  # 22-column ML master dataset
│   ├── pdm_ml_standardized_training_dataset.csv # 5,530-point ML training dataset
│   └── pdm_feature_dictionary.json   # Formal ML schema & physical unit contract
├── build_clean_dashboard.py           # Dashboard generator & preset compiler
├── index.html                         # Live Rig default dashboard view
├── historical.html                    # Historical Archive default view
├── dashboard.html / cloud_dashboard.html # Synchronized distribution builds
├── AGENTS.md                          # Engineering & architecture guidelines
└── washing_machine_fault_project_blueprint.md # Full project technical blueprint
```

---

## 7. How to Run Locally

### Prerequisites
* Python 3.12+ (standard library only; no compiled C-extension requirements)
* Web browser (Chrome, Edge, Brave, Safari)

### 1. Launch the Dashboard
Simply double-click `index.html` or run a local HTTP server:
```powershell
py -3.12 -m http.server 8080
```
Open `http://localhost:8080` in your browser.

### 2. Download Latest Cloud Sessions
To pull new wash sessions from Firebase RTDB and update dashboard presets:
```powershell
py -3.12 firmware/cloud_downloader.py
py -3.12 build_clean_dashboard.py
```

### 3. Run ML Dataset Standardizer & Audit
```powershell
py -3.12 firmware/standardize_datasets.py
py -3.12 firmware/pdm_ml_standardizer.py
py -3.12 firmware/audit_all_datasets.py
```

---

## 8. Sustainability & Financial Impact Equation

$$\text{Early Detection (Point P)} \longrightarrow \text{RM 25–50 Component Fix} \ll \text{RM 1,500+ Replacement} + \text{15–35% Energy Saved}$$

By transforming reactive appliance breakdown into **Township Asset Intelligence**, AcuVibe PdM proves that sustainable townships start with smart, friction-free engineering.
