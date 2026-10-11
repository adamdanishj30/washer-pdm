# Project Blueprint: IoT Anomaly Vibration Detection for Household Washing Machine

This document serves as a complete project handover blueprint for an AI/LLM assistant or an Intelligent Systems student to generate code, design architecture, and implement a predictive maintenance pipeline.

---

## 1. Project Overview & Objective
* **Target System:** Outdoor household washing machine (subject to environmental moisture/wind-driven rain).
* **Objective:** Build an end-to-end unsupervised/semi-supervised anomaly detection system to identify mechanical faults (unbalanced loads, loose structural components, bearing wear) using physical vibration data.
* **Context:** Final Year Project / Advanced Intelligent Systems Side Project.

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

### Machine Learning Modeling (Unsupervised Anomaly Detection)
Because actual mechanical failure data is heavily imbalanced (rare), the model must learn what is *normal* and flag anomalies by exclusion.
* **Baseline Models:** Isolation Forest, One-Class Support Vector Machine (One-Class SVM).
* **Deep Learning Options:** Convolutional Neural Networks (CNN) trained on spectrogram charts, or LSTM-based Autoencoders where a high reconstruction error denotes an anomaly.

---

## 6. Prompt Engineering Hand-off Context
*When giving this to an AI to generate code, use this baseline system layout:*
* **MPU-6050 Connection:** I2C Communication (`SDA` to ESP32 Pin 21, `SCL` to ESP32 Pin 22 by default).
* **Target ML Library:** Python (`scikit-learn`, `pandas`, `numpy`, `scipy`) for server-side processing, or `EloquentTinyML` / `TensorFlow Lite for Microcontrollers` if attempting on-chip edge AI inference.
