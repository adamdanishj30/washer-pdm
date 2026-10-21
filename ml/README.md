# ML subsystem: feature fusion + unsupervised anomaly detection (v3)

Everything in this file describes code that exists in this folder. If you change the code, change this file.

## 1. What the supervisor asked for, and how it maps

> *"From acoustic signal input, perform feature extraction, combine with kinematics and power in feature fusion, and apply an ML model to output anomaly detection as either normal or abnormal/faulty."*

| Requirement | Where it happens |
|---|---|
| Acoustic feature extraction | On the ESP32 (firmware 07, `firmware/07_feature_streamer/pdm_dsp.h`) for new data; `feature_fusion.py` for legacy snapshots |
| Fusion with kinematics + power | `feature_fusion.py`: one early-fused vector per 5 s window (acoustic + vibration + power when available) |
| ML model | `detectors.py`: Mahalanobis (Ledoit-Wolf), Isolation Forest, One-Class SVM; optionally one sub-model per washer phase |
| Output normal / abnormal | `pipeline.py`: `window_decision` per 5 s window and `cycle_decision` per wash cycle (NORMAL / ABNORMAL) |

There are no fault labels (the machine is a working household appliance), so the model is **one-class**: trained only on healthy cycles, it flags departures from them.

## 2. Files

| File | Role |
|---|---|
| `feature_fusion.py` | Load cycles, detect schema (legacy vs windowed), resolve phases, compute features. **No fitting, no files written** (v2's `fit()` leaked test data into its normalisation). |
| `detectors.py` | The three one-class models + `PhaseConditioned` wrapper. All return "larger = more unusual". |
| `calibration.py` | Out-of-fold percentiles, traffic-light bands, the persistence statistic (slow EWMA), thresholds. |
| `pipeline.py` | `PdmPipeline`: fit (with inner leave-one-cycle-out calibration), score, cycle summary, indicators. |
| `fault_injection.py` | Severity-swept, physically parameterised faults injected into **measurements** of a **held-out** cycle. |
| `loco_eval.py` | Nested leave-one-cycle-out evaluation + markdown report. |
| `train_unsupervised_pdm.py` | Data audit, evaluation of all models, deployment model -> `models/`. |
| `predict_pdm.py` | Score a cycle (or all), print the report, write per-window CSV to `outputs/`. |
| `dsp_features.py` | Python twin of the firmware DSP (bit-for-bit within float precision). |
| `waveform_fault_study.py` | Adds modelled spall impacts to **recorded audio clips** and measures how each firmware feature moves. |
| `tests/` | `test_dsp_parity.py` (C++ firmware DSP vs Python), `test_pipeline_synthetic.py` (windowed path mechanics). |

## 3. Data: two schemas

| | Legacy (firmware 05/06) | Windowed (firmware 07) |
|---|---|---|
| Per 5 s row | one instantaneous accel sample + one 8 ms audio RMS + power | statistics of the **whole** window: 80,384 audio samples, ~1,000 accel samples, ~5 power samples |
| Audio features | log RMS + 1-min rolling mean/std | log RMS, crest, kurtosis, 2 kHz high-pass RMS + kurtosis, burst ratio, centroid, 6 band shapes |
| Vibration features | deviation from the cycle's median gravity vector + 1-min rolling mean/std | horizontal and vertical std, magnitude std, dominant frequency (≈ drum speed) and its RMS, 4 band RMS values |
| Power features | log power + rolling std (only if every training cycle has power) | log mean power, log power std (same rule) |

`train_unsupervised_pdm.py` switches to the windowed schema automatically once at least 3 firmware-07 cycles exist in `data/real_sessions/`. The two schemas are never mixed in one model.

**Raw accelerometer axes are deliberately not features.** The sensor was re-mounted between 16 and 17 Oct 2026 (median `accel_y` 1.42 → 2.14 m/s²); raw axes would make every later cycle look anomalous. Vibration features are taken relative to each cycle's own static gravity vector, or are orientation-free statistics.

## 4. Model

1. **Phase conditioning.** If at least 50% of training windows carry a SmartThings phase label, one sub-model is fitted per phase (with at least 150 windows) plus a pooled model. Otherwise one pooled model is used. Phases are **never guessed from audio loudness** (v2 did that, which made "audio is unusual for this phase" circular).
2. **Detector.** Default `mahalanobis`: robust scaling (10–90% range) + Ledoit-Wolf shrinkage covariance, squared Mahalanobis distance. It is transparent: per-feature contributions sum exactly to the score (`top_features` in the output). `iforest` and `ocsvm` are available and evaluated side by side.
3. **Calibration (no leakage).** Inside the training set each cycle is scored by a model fitted on the other cycles. Those out-of-fold healthy scores define:
   * the **baseline percentile** of a window (99 = more unusual than 99% of held-out healthy windows), and its band: green < 95, amber 95–99.5, red ≥ 99.5;
   * the **persistence threshold** `h` (see below).
4. **Indicators.** Separate Mahalanobis models on the acoustic, vibration and power feature subsets, calibrated the same way. They say *where* a deviation is. They replace v2's "Tub Bearing Health %" and "Damper Health %", which could not be learned without fault data.
5. **Cycle decision.** For the overall model and for each indicator: z = Φ⁻¹(percentile), smoothed with a slow EWMA (λ = 2/121, about 10 minutes of memory). The cycle is **ABNORMAL** if any of these stays above its own threshold `h = worst healthy out-of-fold value + 0.25`. CUSUM was tried first and rejected: healthy cycles differ by a persistent offset, which CUSUM integrates over the whole cycle, so its threshold grew with cycle length and nothing but huge faults crossed it.

**No remaining-useful-life, P-F stage or ringgit cost is output.** Those need real degradation data. They can return once a real degradation trajectory has been recorded.

## 5. Validation (nested leave-one-cycle-out)

`loco_eval.py`: for each cycle c, fit the whole pipeline (including its calibration and threshold) on the other cycles. Then:

* **Healthy test:** score c as recorded. Any cycle alarm is a false alarm.
* **Fault test:** inject each fault kind × 4 severities into c's measurements from mid-cycle (3-minute ramp). Measure clean detection (alarm after onset, none before) and delay.
* **Report:** false-alarm cycles k/n with a one-sided 95% Clopper-Pearson upper bound, plus detection rate vs severity and minimum detectable severity. Written to `models/loco_report.md` and `.json`.

### Current result on the 8 legacy cycles (Mahalanobis, deployed)

| | Result |
|---|---|
| Healthy cycles flagged | **0 / 8** (95% upper bound on the false-alarm rate: 31%) |
| Healthy windows red / amber | 0.3% / 4.9% |
| Sustained +100% sound pressure | caught in 7/8 cycles, median about 16 min after onset |
| +50% / +25% / +10% sound pressure | 2/8, 1/8, 1/8 |
| Added random vibration up to 0.2 m/s² RMS | **not detected** |

**How to read this.** On snapshot data with no phase labels, power in only 3 of 8 cycles, and unknown load and program variation, the pipeline can reliably notice only a *large, sustained* change in sound, and no plausible vibration change. That is a limitation of the data, not of the model choice: Isolation Forest and OC-SVM do no better (`models/loco_report.md`).

The same code on synthetic firmware-07 cycles with phase labels (`tests/test_pipeline_synthetic.py`) detects modelled impulsive bearing energy and suspension rocking within minutes. Synthetic results only show that the code works, not how the real washer behaves.

### Fault models and their limits
* Legacy faults are broadband level changes. Snapshot data cannot represent impact physics.
* Windowed faults use moment algebra for an independent added component (energy adds; kurtosis mixes; impact-train kurtosis 20).
* `waveform_fault_study.py` is the stronger test. It adds a spall impact train (BPFO = 4.3 × drum speed, 3 kHz resonance, 0.6 ms decay, load-zone modulation) to **recorded clips** and runs the exact firmware DSP. On synthetic stand-in noise the 2 kHz high-pass kurtosis moves by about 18 healthy standard deviations at impact RMS = 0.5 × healthy high-band RMS, while full-band kurtosis barely moves. Run it again once real clips exist.

## 6. How to run

```powershell
py ml/train_unsupervised_pdm.py                 # audit + nested LOCO of all 3 models + deploy Mahalanobis (~30 s)
py ml/train_unsupervised_pdm.py --skip-eval     # just refit + save
py ml/predict_pdm.py --file data/real_sessions/wash_cycle_2026-10-18_0516.csv
py ml/predict_pdm.py --benchmark                # training cycles: optimistic, for dashboards only
py ml/predict_pdm.py --file <csv> --test-fault acoustic_rise --severity 1.0
py ml/waveform_fault_study.py                   # after collecting clips with firmware/collect_audio_clips.py
py ml/tests/test_dsp_parity.py                  # needs g++ / clang++ on PATH
py ml/tests/test_pipeline_synthetic.py
```

`predict_pdm.py` writes `ml/outputs/<cycle>_scored.csv` with one row per window: `baseline_pct`, `band`, `z`, `persistence`, `acoustic/vibration/power_indicator_pct` and `_persistence`, `window_decision` and `top_features`. Dashboards should read this file.

## 7. When to consider a neural network

Not yet. With 8 cycles a deep or LSTM autoencoder would memorise the baseline. Revisit when **all** of these hold:
* 50–100+ firmware-07 cycles across varied loads and programs, with SmartThings phases;
* raw audio clips are being collected routinely (spectrogram inputs are where learned features help);
* the Mahalanobis baseline demonstrably misses something important in the nested LOCO report.

A cheaper intermediate step is to compute a pretrained audio embedding (PANNs, BEATs, OpenL3) on the clips and feed it to the same Mahalanobis + calibration pipeline.

## 8. Legacy v2 files

`synthetic_fault_generator.py` and the v2 artifacts (`pdm_isolation_forest.joblib`, `pdm_one_class_svm.joblib`, `pdm_feature_scaler.joblib`, `pdm_phase_baselines.json`, `pdm_model_metadata.json`) are in `archive/ml_v2/`. They are superseded and not used by any v3 code.
