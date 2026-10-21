# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Record which wash programme each cycle used, and add a per-cycle signature report
**Date:** 2026-10-21

## Objective
Firmware-07 cycles differ a lot in length and shape because they are different wash programmes, not because the firmware is inconsistent (evidence below). The ML cannot tell programmes apart today because no programme or phase label is saved: every firmware-07 row has `phase = none`, `phase_source = fallback`. After this task, every archived cycle has a row in a new sidecar file `data/session_context.csv` with its programme (`washerCycle`), water temperature and spin level when SmartThings can provide them, and a new report `ml/models/cycle_signature_report.md` lists each cycle's measured signature (active minutes, heater minutes, spin blocks, data-quality counters) so cycles can be grouped by programme.

## Why (evidence, found by Claude on 2026-10-21 from `data/real_sessions/`)
- **Data capture is clean in all 4 firmware-07 cycles** (19 Oct 0911, 20 Oct 0744, 21 Oct 0514, 21 Oct 0631): window spacing 5.02 s with no gaps > 5.1 s; ~1,013 accel samples per window (200 Hz); 0 clipped samples; 5 Tapo readings per window; FIFO overflow only in the very first window after a boot; idle vibration floor `vib_mag_std` = 0.032 m/s² in all four; gravity vector identical (≈ -0.62, 2.88, -9.03), so the sensor has not moved.
- **Spin looks the same in every cycle:** every final spin block has `vib_dom_hz` p90 = 19.9–20.0 Hz (~1,200 rpm) at 300–900 W.
- **The programmes differ:**
  | Cycle | Active min | Heater (>1 kW) | Spin blocks (>200 W) |
  |---|---|---|---|
  | 19 Oct 0911 | 64 | none | 3 (≈37, 47, 61 min) |
  | 20 Oct 0744 | 71 | 11.9 min at 2,290 W | 3 (≈40, 51, 67 min) |
  | 21 Oct 0514 | 22 | none | 1 (≈18 min) |
  | 21 Oct 0631 | 21 | none | 1 (≈17 min) |
  The dashboard's 32.3 / 29.1 min include the 10-min idle tail (`IDLE_TIMEOUT_WINDOWS`), so the two 21 Oct cycles are ~21 min washes and match each other closely.
- **Earlier firmware looked consistent for two reasons:** (a) the legacy cycles with power data (16, 17 0718, 18 Oct) are the same ~64–76 min, 3-spin programme as 19 Oct, and (b) legacy rows hold one instantaneous accel sample per 5 s, so the dashboard plots gravity |a| ≈ 9.55 m/s² (std 0.2), which is flat whatever the washer does.
- **Dashboard badges are first-window values, not run summaries:** "Dom. freq" 19.1 / 9.0 / 1.5 / 29.6 Hz and the σx/σy/σz badges equal row 1 of each CSV (scrub at 0.0 m). Row 1 is a boot window (n_accel 962–965, 1 FIFO overflow) or someone loading the drum. Not part of this task (see Queue).
- **Programme info is dropped even when captured:** `firmware/smartthings_client.py` `query_smartthings()` already reads `samsungce.washerCycle`, water temperature and spin level, and `push_phase_to_firebase()` stores `cycle` and `water_temp`, but `fetch_session_phase_timeline()` returns only `ts, phase, machine_state, progress_pct, target_rpm`, so `cycle` and `water_temp` never reach the export. The live path also needs the PC daemon running during the wash and a valid token, which is why no 19–21 Oct cycle has labels (someone else runs the washes, often early morning).

## Context
- Invariants: `INVARIANTS_DO_NOT_CHANGE.md` §4 (Data and ML) and §1. `data/real_sessions/*.csv` are originals: do NOT rewrite them. That is why programme context goes into a NEW sidecar file, not new CSV columns.
- Do NOT change the firmware-07 45-column schema, `V3_KEY_MAP`, any feature definition, the ML pipeline, thresholds or the LOCO protocol.
- SmartThings is not Firebase, but keep calls minimal: no new polling loop; history lookups happen once per session at archive time (or once per session in the backfill command).
- Never print, log or commit tokens. Read them via the existing `get_valid_smartthings_token()`.
- Code style: exhaustive inline comments and clear section headers (Adam is a beginner).

## Implementation Steps
1. **Probe (read-only, do first):** check whether the SmartThings device history endpoint can return past washer events retroactively, e.g. `GET https://api.smartthings.com/v1/history/devices?locationId=<loc>&deviceId=<SMARTTHINGS_DEVICE_ID>` (locationId from `GET /v1/devices/<id>`). Query the time span of `wash_cycle_2026-10-21_0631` (epoch_ms in the CSV). Record in HANDOFF, without any token or ID values: whether it works, which capabilities/attributes appear (`washerJobState`, `washerCycle`, water temperature, spin level), how far back events go, and the page size/paging used. If it does not work, skip step 2 and say so in HANDOFF; still do steps 3–7.
2. **New module `firmware/smartthings_history.py`** (only if step 1 works): function `fetch_history_context(start_epoch_ms, end_epoch_ms) -> dict` returning `{"programme", "water_temp", "spin_level", "job_state_timeline": [{"ts", "job_state"}], "source": "smartthings_history"}`, or `{}` on any error (never raise into the daemon). Handle 401 the same way `query_smartthings()` does. One paged request sequence per call, no loops that retry faster than 30 s.
3. **Keep programme fields in `fetch_session_phase_timeline()`** (`firmware/smartthings_client.py`): add `cycle` and `water_temp` to each returned checkpoint. Additive only: keep existing keys and sort order, so `session_export.py` callers are unaffected.
4. **New sidecar `data/session_context.csv`**, one row per real session, columns: `session_file, start_epoch_ms, end_epoch_ms, programme, water_temp, spin_level, context_source, note`. `context_source` is one of `smartthings_live` (from the timeline in step 3), `smartthings_history` (step 2), `manual` (Adam typed it), `unknown`. Never overwrite a `manual` row. Write a small helper (in a new file `firmware/session_context.py`) to upsert one row by `session_file`.
5. **Archive hook:** in `firmware/auto_drive_sync_daemon.py`, after a firmware-07 session is archived, call the helper to add its context row: live timeline first, then history lookup, else `unknown`. One history lookup per session, ever (skip if the row exists and is not `unknown`).
6. **Backfill command:** `py firmware/session_context.py --backfill` adds rows for all existing `data/real_sessions/*.csv` (legacy rows get `context_source = unknown` unless the history endpoint reaches back that far; firmware-07 rows try history). Run it once and commit the resulting `data/session_context.csv`.
7. **New report script `ml/cycle_signature_report.py`** (new file, no edits to existing ML files) writing `ml/models/cycle_signature_report.md`. For every file in `data/real_sessions/`: schema (legacy / fw07), rows, recorded minutes, active minutes (power ≥ 8 W; legacy files with all-zero power: "n/a"), heater minutes (power > 1,000 W), high-power blocks (≥ 3 consecutive windows > 200 W: start min and max W), and for fw07 only: median/min `n_accel`, total `fifo_overflows`, total `accel_clip_samples`, max window gap (s), idle `vib_mag_std` median, spin `vib_dom_hz` p90, and "boot at start" = first `timestamp_ms` < 30,000. Join `programme` and `water_temp` from `data/session_context.csv`. End the report with a short "Grouping" table: cycles grouped by (programme if known, else signature: heater yes/no × number of spin blocks).
8. Tests: new `firmware/tests/test_session_context.py` (upsert keeps `manual` rows, adds new rows, idempotent backfill on a temp dir) and run the existing suites listed below.
9. Write HANDOFF.md with the template; keep the `Open UNVERIFIED items` section from the last handoff. Commit as two commits: `feat(data): record wash programme context per session` and `feat(ml): add per-cycle signature report`. Also commit the pending `.agents/rules/architect-handoff-workflow.md` change (Claude's fix from 20 Oct) as its own `docs:` commit. Pull --rebase and push.

## Out of Scope
- Any firmware (`.ino`/`.h`) change or flash. The boot-at-wash-start question is queued (see below).
- Dashboard / `build_clean_dashboard.py`.
- Any edit to `data/real_sessions/*.csv`, `V3_KEY_MAP`, `ml/feature_fusion.py`, `ml/detectors.py`, `ml/pipeline.py`, `ml/loco_eval.py`, thresholds, or retraining.
- Guessing phases or programmes from audio. The signature in step 7 is a descriptive report label, not a training input.
- Secret rotation (Adam's task).

## Acceptance Criteria
- [x] HANDOFF states the step-1 probe result (works / does not work, which attributes, how far back), with no tokens or IDs.
- [x] `fetch_session_phase_timeline()` returns `cycle` and `water_temp` and all previous keys; existing tests still pass.
- [x] `data/session_context.csv` exists with exactly one row per file in `data/real_sessions/` (13 today); running `--backfill` twice gives the same file; a `manual` row is never overwritten (unit test).
- [x] The daemon hook makes at most one history lookup per session and never fails the archive step if SmartThings errors (shown by a test or a dry-run log).
- [x] `ml/models/cycle_signature_report.md` reproduces these numbers within rounding: active minutes 64 / 71 / 22 / 21 for 19 Oct 0911 / 20 Oct 0744 / 21 Oct 0514 / 21 Oct 0631; heater 0 / 11.9 / 0 / 0 min; 3 / 4 / 1 / 1 high-power blocks (the 20 Oct heater counts as one block); spin `vib_dom_hz` p90 ≈ 20 Hz in all four; idle `vib_mag_std` median 0.032 in all four; boot at start = yes / yes / yes / no.
- [x] `py -m py_compile` on every new or changed `.py`; `py firmware/tests/test_session_export.py`, `py firmware/tests/test_daemon_offline.py`, `py firmware/tests/test_session_context.py`, `py ml/tests/test_pipeline_synthetic.py` all PASS.
- [x] No file under `data/real_sessions/` modified; no secrets in the diff; `last_diff.patch` written per workflow rule 6.

## Risk Notes
- **History endpoint is UNVERIFIED.** It is used by the SmartThings app but may be limited in what it returns or how far back. If it fails, the live daemon path plus `manual` rows are the fallback; Adam can ask whoever ran the wash or read the programme off the washer.
- **Token expiry:** PATs expire in 24 h; use the OAuth refresh path already in `get_valid_smartthings_token()`.
- **Concurrent bot commits:** the GitHub workflow commits `data/` every 30 min; `pull --rebase` before pushing and re-run `--backfill` if `data/real_sessions/` gained a file.

## Queue (Claude will plan these next; do not start)
1. **Firmware: report reset reason.** 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot (first `timestamp_ms` 8,239–9,264), i.e. the rig rebooted right as the washer was switched on. Add NEW `/live` fields `reset_reason` and `boot_count` (allowed by invariants §2 CAN CHANGE) to find out whether it is a brownout from a shared supply. Needs a flash, so Adam confirms first.
2. **Dashboard: label run-level badges.** Show Dom. freq and σx/σy/σz as running-window medians for the full run (or label them "at cursor"), so a boot window is not read as the cycle's value.
3. **ML: programme-aware evaluation.** Once each programme has ≥ 3 firmware-07 cycles, add LOCO results per programme group and test SmartThings-phase conditioning. Per-cycle normalisation is not allowed (it would leak the held-out cycle's statistics and erase slow faults).
