# Washer PdM - Autonomous Multimodal Anomaly Detection Rig

Predictive Maintenance (PdM) & vibration/acoustic anomaly detection for a Samsung WW10TP44DSX front-load washing machine using an ESP32 edge microcontroller, MPU-6050 accelerometer, INMP441 MEMS microphone, Tapo P110 power monitor, and Samsung SmartThings API.

## Strategic Scope & Hackathon Alignment (Prognostics & Energy AI)
- **High-Level Vision:** Low-cost multimodal edge IoT (pilot kit about RM 170 net paid, sensor node about RM 131; a sub-RM 50 volume BOM is an unvalidated target) & Predictive AI Platform for home appliances and smart township facilities (aligned with Sime Darby Property "Township of Tomorrow" People & Planet tracks and rotating machinery PdM).
- **Prognostics & Remaining Useful Life (RUL), FUTURE (not built; needs real degradation data):** Aims to move beyond reactive "fix-when-broken" to proactive degradation forecasting. Would estimate remaining machine cycles before critical component failure (e.g., drum suspension dampers, tub bearings, pump impellers).
- **Parasitic Energy Waste Reduction:** Mechanical friction and misalignment may force inverter motors to draw extra electrical power ($W$) to maintain target RPM (hypothesis: the "15%–35%" figure is unverified and not measured on this rig; do not quote it). Cross-correlating Tapo P110 power telemetry with MPU-6050 vibration harmonics and INMP441 acoustics quantifies and flags parasitic energy drain.
- **Economic Value (P-F Interval, illustrative scenario, not measured):** Intervening at Point P (micro-vibration/acoustic harmonics) allows minor RM 25–50 preventative component replacements before reaching Point F (motor burnout, tub cracking, flooding/fire hazard costing RM 800–1,800+ or total machine scrapping).
- **Smart Township & Facility Management (FM):** Scalable fleet monitoring across high-density residential towers, shared laundry hubs, clubhouse equipment, and water booster pumps to eliminate resident noise complaints and prevent catastrophic equipment failures.

## Tech Stack
- **Firmware / Edge:** C++ / Arduino ESP32 (`esp32:esp32@3.3.12`), FreeRTOS dual-core multitasking, I2C, I2S DMA.
- **Backend & Cloud:** Python 3.12+ (`urllib`, `json`, `subprocess`), Google Firebase RTDB, `firmware/auto_drive_sync_daemon.py` (current quota-aware archiver; Google Apps Script is legacy).
- **Auxiliary Telemetry (Phase 4):** TP-Link Tapo P110 (UK/MY Type G 3-Pin, BS 1363 13A/2,990W max, local KLAP protocol via `python-kasa`), Samsung SmartThings Cloud REST API v1 (`washerOperatingState.washerJobState`, CLI/OAuth token refresh).
- **Frontend / Visuals:** HTML5, CSS3 Custom Properties (Dark luxury theme), Vanilla JS, CanvasJS / Chart.js for real-time telemetry waveforms. Includes **Card 4: Electrical Power & Energy Consumption Diagnostics**.
- **Data & ML:** Multimodal early feature fusion combining kinematics, acoustics, and active power into unsupervised anomaly detection (Robust Mahalanobis baseline, Isolation Forest, OC-SVM). Strictly follow PHM engineering standards:
  - **Sample Size & LOCO:** Validated exclusively via Leave-One-Cycle-Out (LOCO) across independent wash sessions ($N \approx 8$) with zero leakage in phase normalization statistics.
  - **Sensor Physics:** Firmware 07 samples the MPU-6050 at $200\text{ Hz}$ via FIFO with a $44\text{ Hz}$ anti-alias DLPF (drum imbalance 1x/2x orders, suspension rocking); bearing-type evidence comes from the $16\text{ kHz}$ INMP441 (2 kHz high-pass RMS/kurtosis computed on-device). Firmware 05/06 data are 5 s snapshots (no impulsive/spectral features possible).
  - **Feature Pruning & Impulsive Metrics:** Prune monotonic loudness duplicates; prioritize impulsive time-domain audio metrics (**Kurtosis, Crest Factor**) and phase-conditioned Z-scores.
  - **Cycle-Level Smoothing & Honest Reporting:** 5-second scores -> out-of-fold baseline percentiles -> slow EWMA (~10 min) persistence statistic; cycle ABNORMAL if the overall model or an acoustic/vibration/power indicator exceeds its calibrated threshold (CUSUM was tried and rejected, see `ml/calibration.py`). No RUL / P-F stage / RM cost outputs until real degradation data exists. Results: `ml/models/loco_report.md`.
  - Current state, ML structure, next steps and scale-up plan: [`docs/handoffs/current_state_and_scale_up_handoff.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/current_state_and_scale_up_handoff.md) (read first in a new session).
  - **BEFORE EDITING ANYTHING (firmware, dashboard, scripts, ML) read [`docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md): it lists what MUST STAY, what CAN CHANGE, and the change checklist. If the two disagree, the invariants file wins.**
  - Follow the supervisor guidelines in [`docs/handoffs/supervisor_ml_guidance_and_fusion.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/supervisor_ml_guidance_and_fusion.md) and [`ml/README.md`](file:///g:/My%20Drive/PdM%20SideProject/ml/README.md). Legacy 31-field dataset contract in [`pdm_feature_dictionary.json`](file:///g:/My%20Drive/PdM%20SideProject/data/pdm_feature_dictionary.json).

## Document Map (source of truth)
If two files disagree: `INVARIANTS_DO_NOT_CHANGE.md` wins, then the source of truth below; fix the other file.

| Need | Source of truth |
|---|---|
| Rules: what must not change | `docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md` |
| Current state, next steps, scale-up plan | `docs/handoffs/current_state_and_scale_up_handoff.md` |
| Numbers allowed in any pitch, proposal or video | `docs/proposals/PROPOSAL_WRITING_GUIDE.md` §4 |
| ML design and results | `ml/README.md`, `ml/models/loco_report.md` (generated) |
| Supervisor directive (why one-class) | `docs/handoffs/supervisor_ml_guidance_and_fusion.md` |
| Prices actually paid (receipts) | `Hackathon/HARDWARE_BOM_AND_COST_BREAKDOWN.md` |
| Wiring, assembly, drilling guide | `docs/hardware_guides/hardware_bom_and_setup_guide.md` (its price column is the original plan) |
| Firmware 07, Firebase quota, endpoints | `firmware/07_feature_streamer/README.md` |
| Hackathon rules, dates, rubric | `Hackathon/SDP_HACKATHON_BRIEFING_SUMMARY.md` |
| Video script and 10-slide deck outline | `Hackathon/VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md` |
| Submission Q&A pack | `docs/proposals/HACKATHON_INFO_AND_AI_EXECUTIVE_SUMMARY.md` |
| Task plan and executor handoff | `docs/handoffs/PLAN.md`, `docs/handoffs/HANDOFF.md` |
| Agent rules | `AGENTS.md`, `.agents/rules/architect-handoff-workflow.md` |
| Superseded material (do not read unless given an exact path) | `archive/` (logs: `archive/ARCHIVE_LOG_*.md`) |

## Common Tasks & Commands
- **Flash Rig Firmware (07, current):** `py -3.12 firmware/07_feature_streamer/flash_firmware.py --compile --port COM3` (credentials from `.env` only)
- **Flash Legacy Firmware (06):** `py -3.12 firmware/06_standalone_tapo_streamer/flash_firmware.py --port COM3`
- **Archive Daemon (quota-aware):** `py firmware/auto_drive_sync_daemon.py` (`--once`, `--prune-archived`)
- **Collect Raw Audio Clips (LAN only):** `py firmware/collect_audio_clips.py`
- **Train + Nested LOCO Evaluation:** `py ml/train_unsupervised_pdm.py` -> `ml/models/loco_report.md`
- **Score a Cycle:** `py ml/predict_pdm.py --file data/real_sessions/<cycle>.csv`
- **Tests:** `py ml/tests/test_dsp_parity.py`, `py ml/tests/test_pipeline_synthetic.py`, `py firmware/tests/test_session_export.py`, `py firmware/tests/test_daemon_offline.py`
- **Run Live Tapo Streamer (firmware 05 only; 07 reads Tapo itself):** `py -3.12 firmware/tapo_firebase_streamer.py` (default 5 s)
- **Capture Multimodal Prediction Snapshot:** `py -3.12 firmware/capture_pdm_dataset.py --snapshot`
- **Continuous Multimodal Dataset Recording:** `py -3.12 firmware/capture_pdm_dataset.py --record --interval 2 --duration 300`
- **Run Cloud Multimodal Sync (Once):** `py -3.12 firmware/cloud_multimodal_sync.py --once`
- **Run Continuous Cloud Sync Daemon:** `py -3.12 firmware/cloud_multimodal_sync.py --interval 30` (wrapper around the archive daemon; min 30 s)
- **Download Firebase Sessions (incremental):** `py firmware/cloud_downloader.py` (`--force` re-downloads everything: costly)
- **Recompile HTML Dashboards:** `py build_clean_dashboard.py`
- **Run Wi-Fi UDP Logger:** `py firmware/wifi_logger.py`
- **Verify Python Syntax:** `py -m py_compile build_clean_dashboard.py firmware/cloud_multimodal_sync.py firmware/capture_pdm_dataset.py firmware/tapo_firebase_streamer.py`

## Project Structure
```
PdM SideProject/
├── firmware/                        # Arduino sketches & Python daemons
│   │   (01, 01b, 02, 04 sketches and one-off flashers/tests are in archive/firmware/, see archive/ARCHIVE_LOG_2026-10-18.md)
│   ├── 05_firebase_multimodal_streamer/ # Dual-Core FreeRTOS + Firebase RTDB
│   ├── 06_standalone_tapo_streamer/ # Autonomous ESP32 + Tapo P110 (KLAP) + Firebase
│   │   ├── 06_standalone_tapo_streamer.ino # Main FreeRTOS firmware (Core 0/1)
│   │   ├── tapo_device.h            # C++ Tapo P110 energy client
│   │   ├── tapo_protocol.h & cipher.h # Local KLAP encryption implementation
│   │   ├── secrets.h / secrets.h.example # Network & hardware credentials
│   │   └── flash_firmware.py        # Automated flasher & compiler
│   ├── capture_pdm_dataset.py       # Synchronous 3-API capture engine (SmartThings + Tapo + ESP32)
│   ├── tapo_firebase_streamer.py    # Real-time LAN Tapo P110 to Firebase bridge (with Force-ON Guard)
│   ├── cloud_multimodal_sync.py     # Autonomous Cloud-to-Cloud Bridge (Firebase + SmartThings)
│   ├── auto_drive_sync_daemon.py    # Offline auto-archiver to data/
│   └── cloud_downloader.py          # Session downloader CLI
├── data/                            # Datasets, snapshots, and schemas
│   ├── pdm_multimodal_prediction_dataset.csv # 22-column unified ML training table
│   ├── pdm_feature_dictionary.json  # Data contract & feature engineering schema
│   ├── live_multimodal_pdm_snapshot.json # Full hierarchical live telemetry snapshot
│   └── wash_cycle_*.csv             # Archived physical wash cycle logs
├── *.html                           # Telemetry dashboards (cloud, live, historical, index)
├── build_clean_dashboard.py         # Static HTML dashboard generator (includes Card 4 Energy)
└── .github/workflows/               # Serverless GitHub Actions cron & mobile sync
```

## Hardware Pinout
- **MPU-6050 (I2C):** `SDA` -> GPIO 21, `SCL` -> GPIO 22, `VCC` -> 3.3V, `GND`/`AD0` -> GND (`0x68`)
- **INMP441 (I2S DMA):** `WS` -> GPIO 25, `SCK` -> GPIO 33, `SD` -> GPIO 32, `VDD` -> 3.3V, `GND`/`L/R` -> GND (Left Channel)
- **FreeRTOS Affinity (07):** Core 1 = continuous I2S audio + 200 Hz MPU FIFO + window DSP. Core 0 = Tapo KLAP, session gating, batched Firebase (keep-alive, print=silent), web server, OTA.

## Conventions & Rules
- **Data Schemas:** Legacy (firmware 05/06) session CSVs start with `timestamp_ms,accel_x,accel_y,accel_z,audio_rms` (older files stop at `power_w`; newer ones add `phase,load_class`). Firmware-07 windows are 45-column rows (32 signal features) defined by `V3_KEY_MAP` in `firmware/session_export.py`. `data/pdm_feature_dictionary.json` is the legacy 31-field dataset contract; its health-index and parasitic-drag fields are not model outputs.
- **Git Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **Security:** Do not commit production Wi-Fi passwords, Firebase database secrets, or SmartThings PATs. No hard-coded fallback credentials anywhere: sketches `#error` without `secrets.h`; Python reads `.env` via `firmware/firebase_rest.py`.
- **Firebase Quota (Spark: 10 GB/month download, 1 GB stored):** All PC access goes through `firmware/firebase_rest.py` (keep-alive, `print=silent`, shallow listings). PC-side scripts never poll faster than 30 s or re-download archived sessions (dashboard viewers: cadence per INVARIANTS §3, via the cached `/api/live`). Budget in `firmware/07_feature_streamer/README.md`.
- **Smart Plug Safety:** Keep Tapo P110 relay ON permanently; operate as a passive inline meter with automated Force-ON Guard enabled.
- **AI Token Conservation & Archive Quarantine:** Never read or scan files inside `archive/`. Those are preserved historical drafts/intermediates. Refer strictly to active files in `docs/`, `ml/`, and `firmware/`.
