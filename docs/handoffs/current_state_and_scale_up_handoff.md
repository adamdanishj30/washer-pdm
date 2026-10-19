# Apex PdM: current-state handoff and scale-up plan

Last updated: 2026-10-19. This is the file to read first when starting a new session.
Status labels: **[DONE]** built and tested here, **[UNVERIFIED]** written but not run on hardware, **[PROPOSAL]** idea, not built.

## 1. What this project is
A non-destructive, in-situ predictive-maintenance (PdM) proof of concept on a household Samsung WW10TP44DSX washer, intended as the seed for a township asset-health platform. Supervisor directive: acoustic feature extraction, fusion with kinematics and power, an ML model giving normal vs abnormal/faulty.

Rig: ESP32, MPU-6050 (vibration), INMP441 mic (16 kHz I2S), Tapo P110 (power, 1 Hz), SmartThings (phase labels), Firebase RTDB. Wiring and commands: `CLAUDE.md`.

## 2. State of the work (2026-10-19)
| Area | Status | Where |
|---|---|---|
| Firmware 07 (on-device DSP, one feature vector per 5.024 s window, 200 Hz vibration FIFO, quota-aware Firebase) | [DONE] Compiled with `esp32:esp32@3.3.12`. DRAM overflow solved (outbox capacity 48 windows, batch body 4096, dynamic allocation for diagnostic snapshot). Flashed to ESP32 over COM6. Rig is actively running on external power, connected to Wi-Fi (`leo`), streaming Schema 3 telemetry to Firebase RTDB (`heap: ~52 kB` steady, `drops: 0`, `outbox: 0`). Dynamic vibration confirmed (`vib_std` spikes from 0.03 to 1.72 m/s² on physical motion/tapping). | `firmware/07_feature_streamer/` |
| Quota-aware PC side (shared Firebase client, archiver daemon, incremental downloader, local-first SmartThings phases) | [DONE] Incremental downloader (`cloud_downloader.py`) and archive daemon (`auto_drive_sync_daemon.py`) verified against live Firebase; test session `wash_cycle_2026-10-19_0107.csv` (127 windows) successfully archived to Drive. | `firmware/*.py`, `firmware/tests/` |
| Web Dashboard (`build_clean_dashboard.py` & HTML pages) | [DONE] Built and verified with `node --check` across all 4 pages (`https://washer-pdm.pages.dev`). Restored cadence invariants (10s active / 25s idle / 30s offline, no delay < 5000ms); unified time base to epoch ms (`d.ts` and `w.e`); single buffer source per state; key-cursor backfill (`startAt`); centralized `mergeRecords()`; manual pause stops traffic via `stopLivePolling()`; live gap breaks; AFK 5-min zero-request freeze; Card 1 plots `vib_mag_std` (σ) on honest 0 to 0.5+ m/s² scale with 0.03 sensor noise floor marker; Card 2 plots per-axis dynamic vibration (σx, σy, σz) hiding mean gravity lanes; State pill evaluates dynamic vibration across live and historic sessions; Card 2 header displays dominant vibration frequency in Hz (gated on running threshold > 0.08 m/s²; no rpm shown); legacy files preserve byte-identical |a| magnitude display. | `build_clean_dashboard.py`, `*.html` |
| ML pipeline v3 | [DONE] runs on the 8 real legacy cycles | `ml/` |
| Credentials | Hard-coded secrets removed from source. **Firebase secret and Wi-Fi password still need rotating** (they remain in Drive history and old `build/*.bin`) | `.env` only |
| Archive | Superseded v1/v2 material moved, nothing deleted | `archive/ARCHIVE_LOG_2026-10-18.md` |

## 3. ML structure (`ml/`, details in `ml/README.md`)
`feature_fusion.py` (features, no fitting) -> `detectors.py` (Mahalanobis with Ledoit-Wolf shrinkage; Isolation Forest; OC-SVM; optional per-phase sub-models) -> `calibration.py` (out-of-fold baseline percentiles, green/amber/red bands, slow-EWMA persistence, thresholds) -> `pipeline.py` (fit, score, per-cycle decision, acoustic/vibration/power indicators) -> `loco_eval.py` (nested leave-one-cycle-out + fault injection) -> `train_unsupervised_pdm.py` / `predict_pdm.py`. `dsp_features.py` is the Python twin of the firmware DSP; `waveform_fault_study.py` tests bearing-spall injection on recorded clips.

Key decisions and why:
* **One-class, not clustering and not a neural net.** No fault labels exist; effective N is 8 cycles, not 6,461 rows. Neural nets only after 50-100+ firmware-07 cycles.
* **Cycle verdict = slow EWMA (~10 min) persistence**, not CUSUM (CUSUM's threshold grew with cycle length; tried and rejected).
* **Honest outputs only.** No RUL, P-F stage or ringgit figures until real degradation data exists.
* **Orientation-free vibration features** (sensor was re-mounted between 16 and 17 Oct).
* **Phases are never guessed from audio.**

Current real-data result (legacy snapshot schema, Mahalanobis, nested LOCO): 0/8 healthy cycles falsely flagged (95% upper bound 31%); +100% sound pressure detected in 7/8 cycles (median ~16 min); +50%/+25%/+10% in 2/8, 1/8, 1/8; added vibration not detected. Limits come from the data (no phase labels, power in 3/8 cycles, 5 s snapshots), not the model choice. Full report: `ml/models/loco_report.md`. Synthetic firmware-07 tests only show the code works.

## 4. Next steps (in order)
1. Rotate Firebase secret + Wi-Fi password; add `OTA_PASS` to `.env`.
2. **[COMPLETED]** Flash firmware 07, work through the hardware checklist, fix compile or heap problems (DRAM overflow resolved, flashed and streaming stably).
3. **[READY]** Profile acoustic background noise and verify pump fill-phase correlation ([`docs/handoffs/TODO_BACKGROUND_NOISE_AND_DATA_COLLECTION.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/TODO_BACKGROUND_NOISE_AND_DATA_COLLECTION.md)):
   - Lock INMP441 mounting position facing cabinet with directional acoustic baffle.
   - Record 2–3 min baselines with washer off (compressor on/off, water pump on/off) via `firmware/collect_audio_clips.py`.
   - Verify whether water pressure pump activates exclusively during water fill phases.
   - Update `ml/feature_fusion.py` & `ml/detectors.py` to down-weight `ab0` / RMS, prioritize high bands (`ab1`–`ab5`, `ahr`, `ahk`), and enforce multimodal gating (acoustic alarm requires $P > 15\text{ W}$ or $\sigma_v > 0.1\text{ m/s}^2$).
4. Record 20+ cycles with the daemon running (verify SmartThings phases are saved), varied loads and programs, sensor fixed.
5. `py ml/train_unsupervised_pdm.py` (auto-switches to the windowed schema at 3+ firmware-07 cycles).
6. Collect audio clips (`firmware/collect_audio_clips.py`), run `ml/waveform_fault_study.py`.
7. Safe, reversible perturbation runs tagged via `/tag` (unbalanced load, soft mat) as real test cases.
8. Optional: pretrained audio embedding (PANNs/BEATs/OpenL3) fed into the same pipeline.

## 5. Hackathon story [PROPOSAL]
Pitch what is true: a low-cost, non-destructive multimodal edge sensor that learns each machine's own healthy baseline and flags sustained departures, with every claim backed by a leave-one-cycle-out report. Do not claim remaining-life or cost savings yet; frame them as what the platform enables once degradation data is collected. Strong, defensible points: on-device DSP (raw audio never leaves the device), tiny Firebase footprint, per-asset baselines (no labelled faults needed), transparent per-feature explanations.

## 6. From rig to mass-producible prototype [PROPOSAL]
Nothing here is built or priced; costs and part choices must be verified.
* **Hardware:** custom ESP32 board replacing the breadboard rig; a better MEMS accelerometer (wider bandwidth than the MPU-6050's 44 Hz filter setting, e.g. an industrial vibration part) for bearing-range content; MEMS mic in a protected port; a current-transformer energy-metering front end instead of a plug-in smart plug for fixed-wired equipment; magnet/adhesive/stud mount so placement is repeatable; enclosure sealed for dust and humidity.
* **Manufacturing/ops:** per-device credentials (replace the shared database secret with per-device auth and write-only rules), OTA updates, factory provisioning (QR code -> asset ID), pinned TLS certificate, fleet dashboard with per-asset status.
* **Data/ML:** baseline learned per asset on-site (commissioning period); **peer comparison across identical units** (e.g. 20 fan-coil units of the same model) is a strong unsupervised signal; ingest maintenance records (work orders) to get the first real fault labels.

## 7. Target assets [PROPOSAL]
Mosques, temples (kuil), malls: air-conditioning plant and related rotating equipment.
| Asset | Why it fits | What differs from the washer |
|---|---|---|
| Fan-coil / AHU fans, exhaust fans | Steady rotating load, belt and bearing faults, many identical units (good for peer comparison) | Constant speed, so no wash phases; baseline per operating mode (fan speed, damper position) |
| Chillers, compressors, pumps (chilled/condenser water) | High consequence of failure, high energy use | Larger machines, noisy plant rooms, three-phase power (CT clamps), needs a higher-bandwidth accelerometer |
| Cooling-tower fans | Gearbox/bearing wear, outdoor | Weather-proofing, low-speed content |
| Prayer-hall / worship-space AC | Noise and comfort sensitive; usage follows prayer and event times | Duty cycle follows schedule; use schedule as context like washer phases |

Honest caveats: none of this is validated outside the washer. Plant rooms have more background noise than a laundry room; per-asset baselines and peer comparison must be proven on real units; for mosques and temples, get building-management consent and avoid recording any intelligible speech (prefer on-device features only, no raw audio retention).

## 8. Open questions for the supervisor
* Acceptable evidence for the hackathon: is the nested-LOCO report plus a staged-perturbation demo enough, or is a partner site with real maintenance logs expected?
* Priority asset for the pilot (fan-coil units are the easiest first step beyond the washer).
