# Antigravity Agent Guidelines: Washer PdM SideProject

This project contains the complete multimodal IoT edge rig, cloud streaming pipelines, real-time dashboards, and predictive maintenance analysis for the Samsung WW10TP44DSX washing machine.

## Active Tooling & Subagents
- **Architect / Planner:** For Phase 4 multimodal integration (Tapo P110 power + SmartThings API) and ML pipeline design.
- **Code Reviewer:** Review firmware FreeRTOS task affinities, memory allocations in `audio_buffer`, and Python daemon retry logic.
- **Security Reviewer:** Guard Wi-Fi credentials, Firebase database rules/secrets, and SmartThings PAT tokens.

## Architecture Guidelines
1. **FreeRTOS Dual-Core Discipline:**
   - Always run high-frequency sensor acquisition (MPU-6050 I2C & INMP441 I2S DMA) on **Core 1** to prevent loop starvation or audio buffer under-runs.
   - Run network protocols (Wi-Fi, HTTP, Firebase SSL, OTA) exclusively on **Core 0**.
   - Use `portMUX_TYPE` spinlocks or mutexes when modifying shared global telemetry variables (`g_ax`, `g_ay`, `g_az`, `g_rms`).

2. **Data Pipeline Conventions:**
   - Raw logs must adhere to `timestamp_ms,accel_x,accel_y,accel_z,audio_rms`.
   - Multimodal prediction datasets adhere to the 22-column schema in `data/pdm_feature_dictionary.json` (capturing kinematics, acoustics, electrical power, and SmartThings ground truth).
   - Wash sessions use ISO date timestamps (`wash_cycle_YYYY-MM-DD_HHMM.csv`).
   - Ground truth labels (`washerJobState`) should condition anomaly thresholds rather than triggering raw magnitude alerts during spin cycles.

3. **Dashboard Standards:**
   - Keep responsive dark UI tokens consistent (`--bg-body: #1e2229`, `--teal-accent: #00f0d2`, `--coral-accent: #fb923c`).
   - Use Web Audio API and CanvasJS/Chart.js efficiently without locking main UI threads during live playback.

4. **Security & Secrets:**
   - Never expose live Firebase database write secrets or Wi-Fi keys in public repositories.
   - Isolate device tokens into external configuration files or environment variables.

5. **Prognostics & Predictive AI (RUL & Energy Optimization):**
   - The ML roadmap targets continuous **Machine Health Index (0%–100%)** and **Remaining Useful Life (RUL)** forecasting rather than binary fault alarms.
   - Correlate vibration harmonics and acoustic RMS with Tapo P110 active power ($W$) to quantify **parasitic energy waste** caused by mechanical friction (worn bearings/dampers).
   - Frame solutions around the **P-F Interval**: early component-level replacement (RM 25–50) prevents catastrophic motor/tub failures (RM 800–1,800+) and unnecessary e-waste.
