# Project Blueprint: IoT Anomaly Vibration Detection for Household Washing Machine

This document serves as a complete project handover blueprint for an AI/LLM assistant or an Intelligent Systems student to generate code, design architecture, and implement a predictive maintenance pipeline.

---

## 1. Project Overview & Objective
* **Target System:** Front-load washing machine (Samsung WW10TP44DSX/FQ 10kg) and rotating electromechanical machinery.
* **Core Objective:** Build an end-to-end multimodal predictive maintenance (PdM) & prognostics system:
  1. **Physical Anomaly Detection:** Real-time identification of mechanical faults (unbalanced loads, suspension damper fatigue, tub bearing wear, drain pump cavitation) using vibration kinematics (MPU-6050) and acoustic sound pressure (INMP441).
  2. **Prognostic Machine Health & Remaining Useful Life (RUL):** Track machine degradation over operational cycles to forecast *when* components will fail, transitioning from reactive "run-to-failure" to proactive maintenance.
  3. **Parasitic Energy Waste Prevention:** Correlate mechanical friction and misalignment with active power draw (Tapo P110 smart plug). Degraded machinery draws 15%–35% excess electrical power to maintain target RPM; this system measures and flags the resulting energy leeching.
  4. **Cost & E-Waste Reduction:** Intervene at Point P on the P-F interval (early harmonic indicators) to enable cheap preventative component replacement (RM 25–50) instead of catastrophic motor/tub replacement (RM 800–1,800+) or appliance scrapping.
* **Context:** University FYP / Advanced Intelligent Systems Project / Sime Darby Property Hackathon ("Township of Tomorrow" Sustainability & Smart Facility Management).

---

## 2. Hardware Architecture & BOM (Bill of Materials)

| Component | Specification / Variant | Role | Estimated Cost (MYR) |
| :--- | :--- | :--- | :--- |
| **Microcontroller** | NodeMCU ESP32 DevKit (30/38 pin) | High-speed data processing, Wi-Fi streaming, or Edge AI execution (TinyML). | RM 12.00 |
| **Expansion Board** | Screw Terminal Block Shield for ESP32 | Houses ESP32; screw terminals provide complete vibration-resistance. | RM 8.00 |
| **Sensor** | MPU-6050 Accelerometer Module | Measures 3-axis digital acceleration (X, Y, Z) and rotation. | RM 5.00 |
| **Wiring** | Male-to-Female (M-F) Dupont Jumper Wires | Female end connects to MPU-6050; stripped male end locks into screw terminal. | RM 3.00 |
| **Weatherproofing**| IP65 Waterproof Plastic Junction Box | Encloses electronics; rigidly mounted to chassis to transfer vibration safely. | RM 10.00 |
| **Cable Entry** | PG7 Cable Glands | Creates a watertight rubber seal for any external power wires entering the box. | RM 2.00 |
| **Mounting** | 3M VHB Heavy Duty Outdoor Tape | Rigidly bonds the enclosure to the washing machine frame without dampening signals. | RM 15.00 |
| **Power** | USB Type-C or Micro-USB Cable | Delivers 5V power from an outdoor-rated adapter or weather-sealed power bank. | (Existing) |

---

## 3. Physical & Environmental Constraints
* **Moisture Mitigation:** System is outdoors under a roof but exposed to wind-driven rain. Hardware must be completely enclosed in the IP65 box. Exposed PCB components inside the enclosure should be coated with clear nail polish or electronic conformal coating to combat humidity.
* **Rigid Coupling:** The MPU-6050 must not rattle inside the enclosure. It should be taped down flat or hot-glued securely to the bottom base of the IP65 box, which is itself bonded flat against the washing machine chassis (ideally under the top lip console or inside the rear panel near the drum suspension).

---

## 4. Software & Data Infrastructure (Architectural Choices)

### Option A: Edge Data Logging (Local Storage)
* **Pipeline:** `MPU-6050` -> `ESP32` -> `SPI MicroSD Card Shield` -> `.CSV file`.
* **Pros:** 100% data preservation; unaffected by outdoor Wi-Fi drops caused by heavy spinning interference.
* **Cons:** Requires manual file retrieval via SD card extraction.

### Option B: Industrial Real-Time Stream (Recommended for Presentation)
* **Pipeline:** `MPU-6050` -> `ESP32` -> `Wi-Fi (MQTT Broker)` -> `Time-Series Database (InfluxDB on Laptop/Server)`.
* **Pros:** Enables live streaming visualizations, real-time dashboard tracking, and wireless dataset creation.
* **Cons:** Network packet loss if outdoor Wi-Fi signal is weak or blocked by the spinning metal drum.

---

## 5. Intelligent Systems & Machine Learning Workflow

### Data Collection & Baseline
* Log raw 3-axis acceleration continuously at a high sampling frequency (minimum **100 Hz to 200 Hz**).
* Establish a "Healthy Baseline" across multiple full wash cycles to capture distinct operational phases (Agitation, Rinsing, Slow Spin, High-Speed Spin).

### Feature Engineering
1. **Time-Domain Features:** Root Mean Square (RMS), Peak-to-Peak Amplitude, Kurtosis, and Variance calculated over rolling time windows.
2. **Frequency-Domain Features:** Execute a **Fast Fourier Transform (FFT)** on the ESP32 or the server to extract dominant frequencies and spectral energy bins. This shifts the focus from time-amplitude to vibration harmonics.

### Machine Learning Modeling (Unsupervised Anomaly Detection & Prognostics)
Because actual mechanical failure data is heavily imbalanced (rare), the model must learn what is *normal* and flag anomalies and gradual degradation:
* **Baseline Detection Models:** Isolation Forest, One-Class Support Vector Machine (One-Class SVM), Mahalanobis Distance on rolling multi-feature vectors.
* **Deep Learning Options:** Convolutional Neural Networks (CNN) trained on mel-spectrograms of combined acoustic+vibration audio, or LSTM-based Autoencoders where reconstruction error acts as an anomaly score.
* **Prognostic Health Degradation & Remaining Useful Life (RUL):**
  * **Health Index (HI) Mapping:** Normalize composite anomaly score into an intuitive 0%–100% Machine Health Index.
  * **Degradation Trendline / RUL Forecasting:** Exponential smoothing or Weibull survival regression on the multi-week degradation trajectory to predict cycles/days remaining before hitting critical fault threshold.
* **Parasitic Energy & Friction Loss Tracking:**
  * Cross-reference active wattage ($W$) from Tapo P110 against rotational spin speed and vibration harmonic amplitude.
  * Baseline energy envelope calculated per wash cycle phase (`washerJobState`). Any wattage deviation above baseline with elevated vibration indicates mechanical drag (unlubricated bearings, worn dampener drag, or impeller friction), quantifying excess kWh and carbon waste.

---

## 6. Prompt Engineering Hand-off Context
*When giving this to an AI to generate code, use this baseline system layout:*
* **Sensors & Hardware:**
  * MPU-6050 (I2C: `SDA` -> Pin 21, `SCL` -> Pin 22) @ 50 Hz.
  * INMP441 (I2S DMA: `WS` -> Pin 25, `SCK` -> Pin 33, `SD` -> Pin 32) @ 16 kHz sampling $\rightarrow$ RMS.
  * Tapo P110 Smart Plug: Polled at 1 Hz via local KLAP Wi-Fi protocol (`python-kasa`) for $W, V, mA$.
  * Samsung SmartThings REST API: Ingests ground-truth `washerJobState` (`wash`, `rinse`, `spin`).
* **Target ML / Data Libraries:** Python (`scikit-learn`, `pandas`, `numpy`, `scipy`, `lifelines` for survival/RUL modeling), or `EloquentTinyML` / `TensorFlow Lite for Microcontrollers` for on-chip edge inference.
* **Core Value Equation for Presentations:**
  $$\text{Early Detection (Point P)} \rightarrow \text{Preventative Fix (RM 25–50)} \ll \text{Catastrophic Failure (Point F: RM 1,500+)} + \text{15–35% Energy Saved}$$
