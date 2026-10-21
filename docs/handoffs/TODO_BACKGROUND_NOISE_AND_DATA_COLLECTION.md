# To-Do Handoff: Acoustic Background Profiling, Multimodal Gating & 20-Cycle Data Collection

**Date:** 2026-10-19  
**Status:** READY FOR EXECUTION  
**Primary Files Involved:**
- [`firmware/collect_audio_clips.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/collect_audio_clips.py) (Raw audio LAN capture)
- [`data/real_sessions/wash_cycle_2026-10-19_0911.csv`](file:///g:/My%20Drive/PdM%20SideProject/data/real_sessions/wash_cycle_2026-10-19_0911.csv) (Empirical Schema 3 reference)
- [`ml/feature_fusion.py`](file:///g:/My%20Drive/PdM%20SideProject/ml/feature_fusion.py) (Feature extraction & band weighting)
- [`ml/detectors.py`](file:///g:/My%20Drive/PdM%20SideProject/ml/detectors.py) (Multimodal concurrence gating & anomaly detection)
- [`firmware/auto_drive_sync_daemon.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/auto_drive_sync_daemon.py) (Background sync & SmartThings phase recording)

---

## 1. Executive Summary & Problem Context

Empirical analysis of the newly recorded Schema 3 wash cycle ([`wash_cycle_2026-10-19_0911.csv`](file:///g:/My%20Drive/PdM%20SideProject/data/real_sessions/wash_cycle_2026-10-19_0911.csv)) reveals the exact spectral boundaries between ambient room noise and active washer physics:

1. **Immunity of Kinematic & Electrical Channels:**
   - **Tapo P110 Power:** Measures active power ($W$) drawn directly through the plug; 100% immune to airborne acoustic noise.
   - **MPU-6050 Vibration:** Clamped rigidly to the washer chassis. When the washer is in standby (~4.8 W), standard deviation `vib_std_x` sits at $\approx 0.020\text{ m/s}^2$ (the MPU-6050 internal ADC noise floor). Airborne room noise does not perturb kinematic vibration.
2. **Microphone Susceptibility & Spectral Distribution:**
   - **Low-Frequency Dominance (< 250 Hz):** The ambient background (refrigerator/freezer compressor hum and water pressure pump) has a low spectral centroid ($\text{acn} \approx 40\text{ Hz}$) with nearly all energy concentrated in `ab0` ($0–250\text{ Hz}$).
   - **High SNR at High Frequencies ($\ge 250\text{ Hz}$):** During high-speed spin, the washer's internal mechanics are **$36\times\text{ to }90\times$ louder** than ambient in the high-frequency bands (`ab1`–`ab5`, `ahr` > 2 kHz RMS).
   - **Transient Click Concurrence Risk:** With the washer off, sharp transient clicks (e.g. laundry door slam, tub unloading) generated high-pass kurtosis spikes (`ahk` = 465). Because bearing spall micro-impacts also generate impulsive kurtosis, relying on microphone audio alone causes false alarms.

```
                          SPECTRAL SEPARATION PROFILE
      Acoustic Band            Ambient Room Hum         Washer Final Spin       SNR Margin
  -----------------------------------------------------------------------------------------
   0 - 250 Hz (ab0)            ~45 - 52 RMS                ~555 RMS                ~12x
   250 - 500 Hz (ab1)          ~3 RMS                      ~277 RMS                ~90x (Max SNR)
   1 - 4 kHz (ab3, ab4)        ~0.6 - 0.8 RMS              ~30 - 46 RMS            ~45x - 55x
   > 2 kHz HP RMS (ahr)        ~0.95 RMS                   ~34.5 RMS               ~36x
   Centroid (acn)              ~40 Hz (Compressor hum)     ~183 Hz (Motor / Drum)
```

---

## 2. Sequenced Action Plan (Cheapest & Zero-Code First)

### Phase 1: Physical Rig Stabilization (Prevent Future Dataset Shifts)
> [!IMPORTANT]
> **Lock microphone mounting now.** Re-mounting the sensor midway through data collection changes mechanical coupling and acoustic transfer functions, repeating the dataset split that occurred on 16–17 Oct.

- [ ] **Task 1.1: Rigid Cabinet-Facing Orientation:**
  - Fasten the INMP441 MEMS microphone rigidly to the rig bracket, facing directly toward the washing machine side panel at close range ($< 5\text{ cm}$).
- [ ] **Task 1.2: Directional Acoustic Baffle:**
  - Attach a small piece of open-cell acoustic foam or rubber shield to the outer/rear side of the mic (facing away from the washer and toward the water pump/room) to attenuate ambient room reverberation without muffling the washer's direct acoustic emissions.

---

### Phase 2: Empirical Baseline Characterization (Zero Rig Code Changes)
- [ ] **Task 2.1: Multi-Condition Standby Noise Floor Recording:**
  - With the washer in standby (powered on, drum stationary, $P \approx 4.8\text{ W}$), record 2–3 minutes of steady-state telemetry for each environmental condition:
    1. **Condition A (Quiet Baseline):** Washer idle, compressor OFF, water pump OFF.
    2. **Condition B (Compressor Hum):** Washer idle, refrigerator compressor actively running, water pump OFF.
    3. **Condition C (Water Pump Active):** Washer idle, household water pressure pump actively running (e.g. running a distant domestic tap), compressor OFF.
    4. **Condition D (Dual Interference):** Washer idle, both compressor and water pump running simultaneously.
  - Script: Run [`firmware/collect_audio_clips.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/collect_audio_clips.py) to save raw WAV clips and compute baseline feature vectors (`ab0`–`ab5`, `ahr`, `ahk`, `acn`).
  - Output: Persist benchmark noise profiles in `data/pdm_acoustic_baselines.json`.

- [ ] **Task 2.2: Water Pump vs. Washer Fill-Phase Correlation Test:**
  - Check whether the household water pump automatically kicks in whenever the washer solenoids open during water intake.
  - Verification: Start a wash cycle; log exact timestamps when the water solenoid valves open. Check if the acoustic signature matches Condition C.
  - Resolution: If the pump correlates strictly with fill phases, tag `phase == "fill"` to automatically mask low-frequency acoustic spikes from anomaly scoring.

---

### Phase 3: ML Pipeline & Feature Fusion Updates (`ml/`)
- [ ] **Task 3.1: High-Frequency & Impulsive Acoustic Band Weighting (`ml/feature_fusion.py`):**
  - Down-weight or exclude low-frequency acoustic bands (`ab0` 0–250 Hz and bulk unweighted RMS) from bearing degradation indices.
  - Prioritize high-frequency and impulsive metrics where washer mechanical SNR is $36\times–90\times$ above background:
    - High-Pass RMS: `ahr` (> 2 kHz)
    - High-Pass Kurtosis: `ahk` (micro-impact detection)
    - Acoustic Crest Factor: `acr` (peak-to-RMS ratio)
    - Mid/High Bands: `ab1` (250–500 Hz), `ab3` (1–2 kHz), `ab4` (2–4 kHz).

- [ ] **Task 3.2: Multimodal Concurrence Gating (`ml/detectors.py`):**
  - Implement a logical gating rule in the detector:
    $$\text{Machine Fault Alarm} = \text{Acoustic Departure} \land \left(\text{Active Power } P > 15\text{ W} \;\lor\; \text{Kinematic Vibration } \sigma_v > 0.10\text{ m/s}^2\right)$$
  - Any isolated acoustic spike that occurs while power is in standby ($P < 10\text{ W}$) and vibration is at the noise floor ($\sigma_v \le 0.03\text{ m/s}^2$) must be classified as an **"Environmental / Room Noise Event"**, suppressing false positives from door slams, footsteps, or room handling.

- [ ] **Task 3.3: Slow-EWMA Cycle Persistence Smoothing:**
  - Maintain the $\sim 10\text{ min}$ slow-EWMA score persistence. Verify that isolated non-stationary clicks (e.g. `ahk` = 465 from door closing or tub unloading) do not trigger a persistent cycle alarm.

---

### Phase 4: 20-Cycle Dataset Collection Campaign
- [ ] **Task 4.1: Continuous Daemon Execution:**
  - Keep [`firmware/auto_drive_sync_daemon.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/auto_drive_sync_daemon.py) running in the background on the PC to capture wash cycles automatically and query SmartThings for ground-truth phase labels (`wash`, `rinse`, `spin`).
- [ ] **Task 4.2: Operational Cycle Diversity:**
  - Record 20+ cycles across varied wash programs (Cotton, Quick Wash, Delicates, Heavy Eco) and varying laundry payloads (empty drum, light load ~2.5 kg, medium load ~5.0 kg, heavy load ~8.0 kg).
- [ ] **Task 4.3: Automated Retraining Trigger:**
  - Once 20+ Firmware 07 Schema 3 cycles are accumulated, execute `py ml/train_unsupervised_pdm.py` to compute nested Leave-One-Cycle-Out (LOCO) baseline percentiles on pure windowed data.

---

### Phase 5: Future Hardware Upgrade (Post-Hackathon Roadmap)
- [ ] **Task 5.1: Dual-Microphone Differential Ambient Cancellation (Reference Channel):**
  - Exploit the unused Right Channel of the INMP441 I2S bus.
  - Add a 2nd identical INMP441 MEMS microphone (~RM 10) connected to the same I2S clock (`BCLK`, `WS`) with `L/R` tied to $3.3\text{ V}$.
  - Place Mic 2 facing outward into the room as an ambient reference.
  - On-device DSP can compute real-time spectral subtraction:
    $$\text{Signal}_{\text{washer}} = \text{Mic}_{\text{contact}} - \alpha \cdot \text{Mic}_{\text{ambient}}$$

---

## 3. Hackathon & Township Value Narrative

> [!TIP]
> **Key Pitch Alignment (Sime Darby "Township of Tomorrow"):**
> Real-world commercial plant rooms (chillers, pumps, AHUs in shopping malls, mosques, and community clubhouses) are never quiet laboratory environments. They are flooded with continuous compressor hum and adjacent pump noise.
> 
> By demonstrating that our multimodal edge fusion:
> 1. Ignores ambient low-frequency hum via high-band acoustic filtering (`ab1`–`ab5`, `ahr`),
> 2. Rejects loud room transient noises (doors, footsteps, voices) via kinematic/electrical concurrence gating, and
> 3. Captures early bearing friction without false alarms,
> 
> we prove that this IoT edge architecture scales directly from residential appliances to township-scale municipal infrastructure.

---

## 4. Verification Checklist

| Item | Verification Step | Expected Outcome |
|---|---|---|
| **Noise Baselines** | Record washer off with compressor/pump on/off | Discrete baseline entries in `data/pdm_acoustic_baselines.json` |
| **Fill Phase Correlation** | Monitor next wash intake phase | Clarify if water pump noise lines up with `phase == "fill"` |
| **Multimodal Gating** | Inject simulated door-slam acoustic click into standby row | Gating suppresses alarm; classifies as Environmental Noise |
| **20-Cycle Dataset** | Continuous collection via `auto_drive_sync_daemon.py` | 20+ Schema 3 files in `data/real_sessions/` |
| **LOCO Evaluation** | Run `py ml/loco_eval.py` on Schema 3 dataset | 0 false alarms on healthy cycles; clean fault detection margin |
