# Predictive Maintenance (PdM) System Handoff Log

**Project:** Samsung WW10TP44DSX Washing Machine PdM & Multimodal Rig  
**Date:** 2026-10-19  
**Branch:** `main`  
**Deployment Target:** Cloudflare Pages (`https://washer-pdm.pages.dev`)  

---

## 1. Session: Firmware-07 Vibration Std (σ) & Dominant Frequency

### 1.1 Objective & Context
For firmware-07 data (historical CSVs and live wash windows), display true dynamic vibration instead of gravity tilt means per [`docs/handoffs/PLAN.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/PLAN.md) and [`docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md):
- **Card 1 (`drawSpline`):** Plot `vib_mag_std` (σ) on an honest 0 to 0.5+ m/s² scale with a dashed sensor noise floor marker at `~0.03 m/s²`. Remove the legacy `9.81 + σ × 1.5` baseline offset and 1g guidelines in σ mode. Line breaks on missing σ or live stream gaps.
- **Card 2 (`drawXyz`):** In σ mode, plot per-axis dynamic vibration `σx`, `σy`, `σz` (`vib_std_x/y/z`) on a single shared 0 to max axis, hiding the static 1g / zero baseline tilt lanes and badges. Title updates to `Per-Axis Vibration (std per 5 s window)` and pills update to `σx / σy / σz / σ|a|`.
- **Card 2 Dominant Frequency (`pill-dom-freq`):** Readout displays dominant frequency in Hz (`vib_dom_hz`) gated on `vibStd > VIB_RUNNING_THRESHOLD` (0.08 m/s²), otherwise `—`. Tooltip notes drum speed tracks Hz × 60 ≈ rpm, but RPM is strictly not displayed as a measured value.
- **Card 1 Subtitles & Legend:** Historic σ mode displays `<dur>-min run • Vibration σ (window std) & sound RMS`; legacy mode displays `<dur>-min run • Legacy 5 s snapshots: |a| magnitude (not vibration std) & sound`. Legend shows `Vib (σ)` to 3 decimals whenever σ is available.
- **State Pill in Historical Mode:** Uses `vibStd = getVibStd(rec)` so historical firmware-07 sessions display `Running` vs `Idle` dynamically.
- **Legacy Parity:** Firmware 05/06 sessions preserve byte-identical ingestion and their existing |a| snapshot visualization.

### 1.2 Acceptance Criteria Verification Matrix

| # | Acceptance Criterion | Status | Verification Evidence / Testing Boundary |
|---|----------------------|--------|------------------------------------------|
| 1 | `py build_clean_dashboard.py` succeeds; `node --check` passes on all 4 pages | **PASS** | `py build_clean_dashboard.py` completed with exit code 0. Node syntax validation (`node --check`) executed on extracted inline `<script>` blocks from `index.html`, `dashboard.html`, `cloud_dashboard.html`, and `historical.html`; all 4 passed with 0 errors. |
| 2 | Python check: `load_csv('data/real_sessions/wash_cycle_2026-10-19_0911.csv')` returns length-12 rows. Row `t == 3741072` has `[6] == 0.7185`, `[8] == 1.1455`, `[11] == 19.938` (after 4-decimal rounding), and `[7] == 'w'` | **PASS** | Verified via Python:<br>`Total rows: 786`<br>`Row 0 length: 12`<br>`Row content: [3741072, -0.666, 2.8844, -8.9999, 689.02, 341.38, 0.7185, 'w', 1.1455, 0.6823, 0.7124, 19.938]`<br>`r[0] == 3741072: True`<br>`r[6] == 0.7185: True`<br>`r[7] == 'w': True`<br>`r[8] == 1.1455: True`<br>`r[11] == 19.938: True` |
| 3 | Python check: legacy file (`wash_cycle_2026-10-17_0835.csv`) `load_csv` output is identical to previous commit | **PASS** | Executed git baseline comparison against `495eaea`:<br>`Old row count: 792`<br>`New row count: 792`<br>`Byte-identical: True` |
| 4 | Page sizes before and after reported; all stay under 800 KB | **PASS** | Before: `index.html` (542,999 B), `dashboard.html` (542,999 B), `cloud_dashboard.html` (542,999 B), `historical.html` (543,011 B).<br>After: `index.html` (599,978 B / 586 KB), `dashboard.html` (599,978 B / 586 KB), `cloud_dashboard.html` (599,978 B / 586 KB), `historical.html` (599,990 B / 586 KB). All well under 800 KB ceiling. |
| 5 | Code inspection: in σ mode, no `9.81 +` mapping of σ remains in `drawSpline`; axis title reads `σ m/s²`; 0.03 floor marker present | **PASS** | Regex scan confirmed 0 occurrences of `9.81 +` or `9.81+` in `drawSpline`. Verified `splineCtx.fillText('\u03c3 m/s\u00b2', ...)` and `splineCtx.fillText('sensor floor ~0.03', ...)`. |
| 6 | Code inspection: no rpm value is displayed; dominant-frequency pill gated on `VIB_RUNNING_THRESHOLD` | **PASS** | Inspected Card 2 header and `applyRecord`: displays `${vdf.toFixed(1)} Hz` or `—` exclusively when `vibStd > VIB_RUNNING_THRESHOLD && vdf !== null`. No rpm value rendered in text or canvas. |
| 7 | Code inspection: poll-controller functions and `maxAgeMs` line unchanged (only `windowToRecord` gained indices 8–11) | **PASS** | Diff check confirmed 0 changes to `pollOnce`, `fetchWindowsSince`, `mergeRecords`, `confirmAndResume`, `resumeFromTabVisibility`, `stopLivePolling`, and `maxAgeMs`. Only `windowToRecord(w)` was extended with `[e, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf]`. |
| 8 | Browser check on `historical.html` → session `wash_cycle_2026-10-19_0911` | **UNVERIFIED (Pending manual browser check)** | Headless CLI testing environment cannot launch an interactive desktop browser to visually inspect canvas rendering. Marked UNVERIFIED per invariant rule. |
| 9 | Diff contains no secrets; no file under `data/` modified | **PASS** | Verified diff: zero credentials or private tokens. Raw CSV files in `data/real_sessions/` untouched. |
| 10 | New commit (not amended) pushed to `origin/main` | **PASS** | Committed as `03495d3`, pushed to `origin/main` (forward commit; see commit hash in Section 1.3). |

### 1.3 Deviations & Clarifications
- None. All 9 implementation steps executed strictly according to [`docs/handoffs/PLAN.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/PLAN.md). Forward commit hash: `03495d3`.

---

## 2. Session: Live Poll Controller & Invariant Restoration

### 2.1 Acceptance Criteria Verification Matrix

| # | Acceptance Criterion | Status | Verification Evidence / Testing Boundary |
|---|----------------------|--------|------------------------------------------|
| 1 | `py build_clean_dashboard.py` succeeds; `node --check` passes on all 4 pages | **PASS** | `py build_clean_dashboard.py` generated `index.html`, `dashboard.html`, `historical.html`, `cloud_dashboard.html`. Script extracted `<script>` blocks from all 4 and verified `node --check` exit code 0. |
| 2 | No delay < 5000ms; strings "2s Live Stream", "LIVE (2s)", "(2s Sync)", "(5s Sync)" removed | **PASS** | Automated AST/regex check: `Found forbidden: []`. Reschedule delays strictly `POLL_OFFLINE_MS` (30000), `POLL_ACTIVE_MS` (10000), and `POLL_IDLE_MS` (25000). Labels updated to "10s Active Sync" / "60s Idle Heartbeat" / "Adaptive Sync". |
| 3 | Idle rig polling cadence ≥ 25s | **PASS (Node/Static)**<br>*PENDING (Live DevTools)* | Controller reschedule evaluates `delay = isRigActive ? POLL_ACTIVE_MS : POLL_IDLE_MS` (25000 ms). Verified via Node test harness. Browser DevTools Network tab confirmation pending operator desktop run. |
| 4 | Active wash polling: `/api/live` ≥ 10s, `/sessions/...` ≥ 30s | **UNVERIFIED** | Rig is currently idle (standby). Code inspection confirms `POLL_ACTIVE_MS = 10000` and `WINDOW_FETCH_MS = 30000`. Marking UNVERIFIED per invariant rule since no active wash occurred during test. |
| 5 | `historical.html` makes 0 live network requests | **PASS (Node/Static)**<br>*PENDING (Live DevTools)* | Hard page-level guard `PAGE_DEFAULT_VIEW !== 'live'` at top of `pollOnce`, `resumeFromTabVisibility`, `recordUserActivity`, and `freezeForAfk` halts live polling. 5-min network quiet pending DevTools confirmation. |
| 6 | Manual "Pause Live Stream" halts traffic for 2+ min; Resume restarts within 1 cycle | **PASS (Node/Static)**<br>*PENDING (Live DevTools)* | `onPrimaryAction` calls `stopLivePolling()` (increments `generation`, clears `pollTimer`, aborts `inflight`). `isLivePaused` guards `pollOnce`, `resumeFromTabVisibility`, and `visibilitychange`. Resuming calls `resumeFromTabVisibility()`. |
| 7 | `?afk_test_ms=20000` triggers modal at 20s; 0 requests while away; Resume guarded against double-click | **PASS (Node/Static)**<br>*PENDING (Live DevTools)* | Verified in Node test harness: URL parameter parsed with `parseInt`, clamped to ≥ 10000 ms, defaulting to 5 min. `isResuming` guard prevents duplicate resume loops on rapid clicking. |
| 8 | Tab hidden for 60s and returned causes 1 catch-up then normal loop | **PASS (Node/Static)**<br>*PENDING (Live DevTools)* | `visibilitychange` calls `stopLivePolling()` when hidden; calls `resumeFromTabVisibility()` when visible, which catches up missed windows via `fetchWindowsSince` and starts single `pollOnce(myGen)`. |
| 9 | Clicking Resume and immediately hiding tab leaves no duplicate loop | **PASS (Node/Static)**<br>*PENDING (Live DevTools)* | Monotonic `generation` check and `document.hidden` guards abort/discard stale responses after both network awaits. |
| 10 | Epoch time base (`d.ts` / `w.e`); no `uptime * 1000`; no `vdf` used as vibration amplitude | **PASS** | `liveEpochMs(d)` and `windowEpochMs(w)` validate `ts > 1.7e12`. `uptime * 1000` removed completely. `w.vdf` (frequency in Hz) eliminated; window converter uses `sm` (`vib_mag_std`) exclusively. |
| 11 | Invariant `maxAgeMs = (d.schema >= 3 && d.active === false) ? 75000 : 25000` and structure preserved | **PASS** | Verified via string audit and code inspection; line is intact. |
| 12 | Window fetch uses `orderBy="$key"`, `limitToLast` ≤ 120, and `startAt` cursor | **PASS** | `fetchWindowsSince(sid, sinceKey, limit, signal)` constructs URL with `orderBy=%22%24key%22`, `startAt=%22${encodeURIComponent(sinceKey)}%22`, and drops boundary duplicate key. |
| 13 | Session-change reset and gap breaks during real wash | **UNVERIFIED** | Rig is currently idle. Unit tests verified `isGapBefore` logic, but live wash session transition was not observed on hardware. Marking UNVERIFIED per invariant rule. |
| 14 | Diff contains no secrets | **PASS** | Inspected diff: only public Firebase RTDB endpoint (`pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app`) and dashboard UI/logic. No Wi-Fi, PAT, or private keys. |
| 15 | Committed and pushed to `origin main` | **PASS** | Committed as `5086684` (amended `8a21fbe`). Pushed to `origin/main` (SHA: `5086684e2e1a95481a94a4d93b068e26c2b7258a`). Cloudflare Pages build triggered via GitHub webhook. |

---

## 3. Session: SmartThings Auth Diagnosis & Cloud Downloader Sync

### 3.1 Problem & Root Cause
During execution of `firmware/cloud_downloader.py`, the archiver reported:
```
[AUTH ENV NOTICE] Env token refresh notice: HTTP Error 401: Unauthorized
[SMARTTHINGS CLIENT ERR] HTTP Error 401: Unauthorized
```
and saved session `wash_cycle_2026-10-19_0911.csv` with heuristic fallback labels (`SmartThings phase on 0/786 rows`).

**Root Cause Findings:**
1. **Samsung 24-Hour PAT Expiration:** All SmartThings Personal Access Tokens created after Dec 30, 2024 strictly expire in 24 hours. The PAT in `.env` had expired.
2. **Single-Use OAuth Refresh Token Rotation (RTR):** SmartThings refresh tokens are single-use. When used, SmartThings issues a rotated `refresh_token` and `access_token`. The old script did not persist rotated tokens, invalidating the refresh chain.
3. **Secret Isolation Fix:** To avoid syncing OAuth refresh tokens to Google Drive cloud history, the token cache was directed to `%LOCALAPPDATA%\PdM_Washer\smartthings_token_cache.json` rather than the Drive project workspace.

### 3.2 Synchronized Datasets on Drive
- **Firebase Status:** 21 sessions total in Firebase, 0 pending download.
- **Drive Archive:**
  - 10 real wash cycles archived to [`data/real_sessions/`](file:///g:/My%20Drive/PdM%20SideProject/data/real_sessions), including `wash_cycle_2026-10-19_0911.csv` (786 windows, 253 KB).
  - 19 test datasets archived to [`data/testing_data/`](file:///g:/My%20Drive/PdM%20SideProject/data/testing_data).
  - 3 abandoned short test bursts ($< 3$ rows) recorded in [`data/.sync_history.json`](file:///g:/My%20Drive/PdM%20SideProject/data/.sync_history.json) as discarded to prevent unnecessary download quota burn.
- **Machine Learning Training Dataset:** Rebuilt [`data/pdm_ml_standardized_training_dataset.csv`](file:///g:/My%20Drive/PdM%20SideProject/data/pdm_ml_standardized_training_dataset.csv) (7,414 rows across all 10 real sessions).

---

## 4. Canonical Architecture & File Map

| Category | Canonical Path | Description |
|---|---|---|
| **Firmware Streamer** | [`firmware/07_feature_streamer/07_feature_streamer.ino`](file:///g:/My%20Drive/PdM%20SideProject/firmware/07_feature_streamer/07_feature_streamer.ino) | Active ESP32 firmware (5s windows, 16 kHz I2S DMA INMP441, **200 Hz MPU-6050 FIFO**, 1 Hz Tapo power). |
| **Sync Daemon** | [`firmware/auto_drive_sync_daemon.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/auto_drive_sync_daemon.py) | Quota-aware background sync daemon to Google Drive. |
| **Downloader** | [`firmware/cloud_downloader.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/cloud_downloader.py) | Incremental Firebase -> Drive session downloader. |
| **SmartThings Client** | [`firmware/smartthings_client.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/smartthings_client.py) | Authenticated client with persistent local token cache in `%LOCALAPPDATA%`. |
| **ML Standardizer** | [`firmware/pdm_ml_standardizer.py`](file:///g:/My%20Drive/PdM%20SideProject/firmware/pdm_ml_standardizer.py) | Canonical feature transformer for machine learning. |
| **Standardized Dataset** | [`data/pdm_ml_standardized_training_dataset.csv`](file:///g:/My%20Drive/PdM%20SideProject/data/pdm_ml_standardized_training_dataset.csv) | 7,414 rows across 10 real wash cycles. |
| **Background Noise Plan** | [`docs/handoffs/TODO_BACKGROUND_NOISE_AND_DATA_COLLECTION.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/TODO_BACKGROUND_NOISE_AND_DATA_COLLECTION.md) | Protocol for pump/compressor baseline recordings & 20-cycle campaign. |
