# Predictive Maintenance (PdM) System Handoff Log

**Project:** Samsung WW10TP44DSX Washing Machine PdM & Multimodal Rig  
**Date:** 2026-10-19  
**Branch:** `main`  
**Deployment Target:** Cloudflare Pages (`https://washer-pdm.pages.dev`)  

---

## 1. Session: Honest Labels (Card 4 Readouts & State Pill)

### 1.1 Objective & Context
Ensure the web dashboard displays only measured values or directly computed values from physical measurements, removing all invented or uncalibrated claims per [`docs/handoffs/PLAN.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/PLAN.md) and [`docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md):
- Remove fabricated load in kg (`estKg`), "Motor Drag / Bearing Drag", estimated cycle cost in ringgit (`RM 0.00`), "P-F Health [Point P: Optimal]", and percentage load (`% Load`).
- Remove the arbitrary 400 W "spin threshold" dashed guideline and centrifugal spin badge.
- Remove the fixed "normal baseline 120 RMS" dashed line and badge from Card 3 area chart.
- Replace the sound-ratio "Spike:" pill with a provisional `State:` pill (`Running` vs `Idle`) based on dynamic vibration (`vib_std` > `0.08` m/s² matching firmware fallback threshold, or `—` when missing).
- Update Card 4 subtitle and stats bar to reflect only measured Tapo P110 power, shown span energy (kWh), peak power (W), and average active power (W).

### 1.2 Acceptance Criteria Verification Matrix

| # | Acceptance Criterion | Status | Verification Evidence / Testing Boundary |
|---|----------------------|--------|------------------------------------------|
| 1 | `py build_clean_dashboard.py` succeeds; `node --check` passes on all 4 pages | **PASS** | `py build_clean_dashboard.py` generated `index.html`, `dashboard.html`, `historical.html`, and `cloud_dashboard.html`. Script extracted inline `<script>` tags from each and ran `node --check`; all 4 passed with 0 errors. |
| 2 | Forbidden strings absent from `build_clean_dashboard.py` and all generated pages | **PASS** | Automated python AST scan confirmed 0 occurrences of all 16 forbidden strings: `Cycle Est. Cost`, `RM 0.00`, `RM ${{`, `P-F Health`, `Point P`, `Motor Drag`, `Bearing Drag`, `estKg`, `% Load`, `parasitic`, `CENTRIFUGAL`, `SPIN THRESHOLD`, `NORMAL BASELINE`, `Spike:`, `spikeRatio`, `spikeMult`. |
| 3 | `VIB_RUNNING_THRESHOLD = 0.08` defined with provisional comment; State pill shows `—` when `rec[6]` is missing | **PASS** | `VIB_RUNNING_THRESHOLD = 0.08` defined with comment matching requirement. In `applyRecord`, `rec[6]` is evaluated: displays `Running` when `vibStd > 0.08`, `Idle` when `<= 0.08`, and `—` when missing or non-finite. Tooltip `title` added. |
| 4 | In a browser, on a firmware-07 historic session (`wash_cycle_2026-10-19_0911`) and live (`index.html`): Card 4 shows only Active W, Energy (shown span), Peak Power and Avg Active; Card 3 shows State and no baseline line; no console errors | **UNVERIFIED (Pending manual browser check)** | Headless/CLI environment cannot launch desktop browser for human visual observation. Static AST and Node runtime check verified zero runtime syntax errors. Marked UNVERIFIED per invariant rule. |
| 5 | `maxAgeMs` line and online/offline structure unchanged; poll-controller functions untouched | **PASS** | Verified intact: `const maxAgeMs = (d.schema >= 3 && d.active === false) ? 75000 : 25000;`, opening `if/else`, and functions `pollOnce`, `fetchWindowsSince`, `mergeRecords`, `confirmAndResume`, `resumeFromTabVisibility`, and `stopLivePolling` were completely untouched. |
| 6 | INVARIANTS "Spike" bullet annotated as DONE | **PASS** | [`docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md) Section 3 CAN CHANGE Spike bullet updated to: `[DONE 2026-10-19 in commit ed3be4e: replaced by provisional Idle/Running state, threshold 0.08 m/s²]`. |
| 7 | Diff contains no secrets | **PASS** | Verified git diff: only public RTDB URL and UI canvas/DOM math; no credentials or private keys. |
| 8 | New commit (not amended) pushed to `origin/main` | **PASS** | Committed as `ed3be4e`, pushed to `origin/main` (no amend/force-push). |

### 1.3 Deviations & Clarifications
- None. All 6 implementation steps executed strictly according to [`docs/handoffs/PLAN.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/PLAN.md).

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
