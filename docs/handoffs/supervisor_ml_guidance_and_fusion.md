# Supervisor Directive: Multimodal Feature Fusion & Anomaly Detection

**Purpose:** the supervisor's requirements and the reasoning behind the one-class approach. For *how it is built and how it performs*, the source of truth is [`ml/README.md`](file:///g:/My%20Drive/PdM%20SideProject/ml/README.md) and `ml/models/loco_report.md`. (The previous, longer version of this file is in `archive/docs_superseded_2026-10-20/`; its implementation sections were out of date.)

---

## 1. Supervisor directive

> *"From acoustic signal input, then you akan buat feature extraction, then apply ML model. Output is the anomaly detection as either normal or abnormal/faulty. So you kena combine both features, to develop feature fusion, then baru embark dalam ML model for fault classification."*

Requirements:
1. **Feature extraction** from the acoustic signal (and the other sensors).
2. **Feature fusion:** combine acoustic features with vibration (and power) features.
3. **ML model** applied to the fused features.
4. **Output:** a clear decision, **Normal** or **Abnormal / Faulty**.

How the code meets each one: `ml/README.md` section 1.

---

## 2. Why one-class instead of supervised classification

* The reference project had labelled healthy and fault data. Ours runs on an active, healthy household appliance, so we cannot deliberately destroy bearings or dampers to create fault labels.
* A two-class classifier cannot be trained without fault examples. So the model is **one-class**: trained only on healthy cycles, it flags departures from them. It still delivers the mandated chain: feature extraction → feature fusion → Normal / Abnormal.

### Sample size and validation (mandatory)
> Rows inside one wash cycle are strongly autocorrelated, so the effective sample size is the number of independent cycles (**N = 8** healthy legacy cycles today), not the 6,461 windows.
> * Validate with **leave-one-cycle-out (LOCO)**, never random row-level splits.
> * In every fold, fit scalers, normalisation statistics, baseline percentiles and thresholds **only on the training cycles**.

---

## 3. Sensor physics (what each sensor can and cannot see)

| Sensor | Rate / filter (firmware 07, current) | Can capture | Cannot capture |
|---|---|---|---|
| **MPU-6050** | 200 Hz hardware FIFO, 44 Hz anti-alias filter (Nyquist 100 Hz, usable content below about 44 Hz) | Drum unbalance (1x / 2x order; spin about 20 Hz at 1,200 rpm), suspension rocking, tilt | Bearing defect frequencies at several times shaft speed beyond the filter |
| **INMP441** | 16 kHz I2S (Nyquist 8 kHz), features computed on the ESP32 | Impulsive micro-impacts (kurtosis, crest, 2 kHz high-pass), friction and squeal bands | Purely structural low-frequency sway (use the accelerometer) |
| **Tapo P110** | 1 Hz, local KLAP | Motor load, session start and stop, mean/min/max/std power | Torque oscillations faster than 0.5 Hz |

Legacy firmware 05/06 sampled one instantaneous 50 Hz-class snapshot every 5 s; the old "25 Hz Nyquist" figures belong to that data only.

---

## 4. What the pipeline outputs (and does not)

* **Outputs:** window anomaly score and baseline percentile, traffic-light band (green / amber / red), acoustic / vibration / power indicator subsets (they say *where* a deviation is), and a cycle verdict **NORMAL / ABNORMAL** with per-feature contributions.
* **Does not output:** remaining useful life, health-index percentages (machine, bearing or damper), P-F stage, or ringgit and energy-saving figures. They cannot be learned without real degradation data (see `INVARIANTS_DO_NOT_CHANGE.md` §3).
* **Phase conditioning:** implemented in `ml/detectors.py` (one sub-model per SmartThings phase when at least 50% of training windows are labelled). The currently evaluated model is **pooled** because 0% of the 8 legacy cycles carry phase labels. Phases are never guessed from audio.
* **Model choice:** Mahalanobis with Ledoit-Wolf shrinkage is the deployed default (interpretable); Isolation Forest and OC-SVM are evaluated beside it. An autoencoder is deferred until there are 50–100+ firmware-07 cycles (`ml/README.md` section 7).
* **Decision smoothing:** slow EWMA persistence (about 10 minutes). CUSUM was tried and rejected (`ml/calibration.py`).

---

## 5. Rules for agents continuing this work
1. Do **not** build a two-class supervised classifier; train on healthy cycles only (`data/real_sessions/`).
2. Always fuse modalities; never rely on a single sensor, especially audio alone (door slams create kurtosis spikes; see `TODO_BACKGROUND_NOISE_AND_DATA_COLLECTION.md` for the planned multimodal gating).
3. Validate with nested LOCO and report the false-alarm upper bound honestly.
4. Keep this file about the directive and rationale; put implementation detail in `ml/README.md`.
