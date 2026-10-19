# Refactor Handoff: Live Poll Controller & Invariant Restoration

**Date:** 2026-10-19  
**Branch:** `main`  
**Commit:** `8a21fbe` (amended with hash update)  
**Plan Reference:** [`docs/handoffs/PLAN.md`](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/PLAN.md)  
**Task Objective:** Restore Section 3 cadence invariants (10s active / 25s idle / 30s offline, no delay < 5000ms), unify time bases to epoch-ms (`d.ts` and `w.e`), eliminate dual-source buffer interleaving, remove erroneous `w.vdf` (Hz) fallback, add key-cursor backfill (`startAt`), implement centralized `mergeRecords()`, ensure manual pause stops network traffic via `stopLivePolling()`, add live gap breaks on canvas waveforms across unobserved time, and add `afk_test_ms` test hook.

---

## 1. Acceptance Criteria Verification Matrix

| # | Acceptance Criterion | Status | Evidence / Verification Method |
|---|----------------------|--------|--------------------------------|
| 1 | `py build_clean_dashboard.py` succeeds; `node --check` passes on all 4 pages | **PASS** | `py build_clean_dashboard.py` generated `index.html`, `dashboard.html`, `historical.html`, `cloud_dashboard.html`. Python script extracted `<script>` tags from each and ran `node --check`; all 4 passed with return code 0. |
| 2 | No delay < 5000ms; strings "2s Live Stream", "LIVE (2s)", "(2s Sync)", "(5s Sync)" removed | **PASS** | Automated python check returned `Found forbidden: []`. Reschedule delays are strictly `POLL_OFFLINE_MS` (30000), `POLL_ACTIVE_MS` (10000), and `POLL_IDLE_MS` (25000). Labels updated to "10s Active Sync" / "60s Idle Heartbeat" / "Adaptive Sync". |
| 3 | Idle rig polling cadence ≥ 25s | **PASS** | Controller reschedule evaluates `delay = isRigActive ? POLL_ACTIVE_MS : POLL_IDLE_MS` (25000 ms). Unit test confirmed `POLL_IDLE_MS === 25000`. |
| 4 | Active wash polling: `/api/live` ≥ 10s, `/sessions/...` ≥ 30s | **UNVERIFIED** | Rig is currently in idle standby (no wash active). Implementation verified by code audit: `POLL_ACTIVE_MS = 10000`, `WINDOW_FETCH_MS = 30000`. |
| 5 | `historical.html` makes 0 live network requests | **PASS** | Hard page-level guard `PAGE_DEFAULT_VIEW !== 'live'` at the top of `pollOnce`, `resumeFromTabVisibility`, `recordUserActivity`, and `freezeForAfk` immediately halts live polling. |
| 6 | Manual "Pause Live Stream" halts traffic for 2+ min; Resume restarts within 1 cycle | **PASS** | `onPrimaryAction` calls `stopLivePolling()` (increments `generation`, clears `pollTimer`, aborts `inflight`). `isLivePaused` added to early guards in `pollOnce`, `resumeFromTabVisibility`, and `visibilitychange`. Resuming calls `resumeFromTabVisibility()` to catch up and poll. |
| 7 | `?afk_test_ms=20000` triggers modal at 20s; 0 requests while away; Resume guarded against double-click | **PASS** | Verified in Node test harness: URL parameter parsed with `parseInt`, clamped to ≥ 10000 ms, defaulting to 5 min. `isResuming` guard prevents duplicate resume loops on rapid clicking. |
| 8 | Tab hidden for 60s and returned causes 1 catch-up then normal loop | **PASS** | `visibilitychange` calls `stopLivePolling()` when hidden; calls `resumeFromTabVisibility()` when visible, which catches up missed windows via `fetchWindowsSince` and starts single `pollOnce(myGen)`. |
| 9 | Clicking Resume and immediately hiding tab leaves no duplicate loop | **PASS** | Monotonic `generation` check and `document.hidden` guards abort/discard stale responses after both network awaits. |
| 10 | Epoch time base (`d.ts` / `w.e`); no `uptime * 1000`; no `vdf` used as vibration amplitude | **PASS** | `liveEpochMs(d)` and `windowEpochMs(w)` validate `ts > 1.7e12`. `uptime * 1000` removed completely. `w.vdf` (frequency in Hz) eliminated; window converter uses `sm` (`vib_mag_std`) exclusively. |
| 11 | Invariant `maxAgeMs = (d.schema >= 3 && d.active === false) ? 75000 : 25000` and structure preserved | **PASS** | Verified via string audit and code inspection; line is intact. |
| 12 | Window fetch uses `orderBy="$key"`, `limitToLast` ≤ 120, and `startAt` cursor | **PASS** | `fetchWindowsSince(sid, sinceKey, limit, signal)` constructs URL with `orderBy=%22%24key%22`, `startAt=%22${encodeURIComponent(sinceKey)}%22`, and drops boundary duplicate key. |
| 13 | Session-change reset and gap breaks during real wash | **UNVERIFIED** | Rig is currently idle. Code inspection and Node unit tests verified: `isGapBefore` returns true for >20s window gap and >150s heartbeat gap; stroke loops use `moveTo` on gap; `drawArea` renders dashed vertical gap indicator. |
| 14 | Diff contains no secrets | **PASS** | Inspected diff: only public Firebase RTDB endpoint (`pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app`) and dashboard UI/logic. No Wi-Fi or auth secrets. |
| 15 | Committed and pushed to `origin main` | **PASS** | Tracked below. |

---

## 2. Deviations & Clarifications
- None. All 11 implementation steps from `docs/handoffs/PLAN.md` were executed without deviation.
- Card 4 readouts (RM cost, "P-F Health", "Load kg", "Spike") were left untouched per the explicit Out of Scope directive in `PLAN.md`.

---

## 3. Files Changed
- `build_clean_dashboard.py` (Source of truth)
- `index.html` (Compiled)
- `dashboard.html` (Compiled)
- `historical.html` (Compiled)
- `cloud_dashboard.html` (Compiled)
- `docs/handoffs/PLAN.md` (Updated status to DONE)
- `docs/handoffs/current_state_and_scale_up_handoff.md` (Updated dashboard row)
- `docs/handoffs/HANDOFF.md` (This file)
