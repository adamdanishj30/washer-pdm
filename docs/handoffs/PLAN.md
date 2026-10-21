# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Stop writing a guessed load class; record real load (kg) in the session context file
**Date:** 2026-10-21

## Step 0 (do first, every task from now on)
Commit this PLAN.md before any other change: `docs: plan load_class retirement`. On 21 Oct a pull rolled PLAN.md back to an older committed copy and the task was lost; committing it first prevents that.

## Review verdict that produced this plan
APPROVED: `c597e60`, `03a883e` (dashboard wash-type badge, summary line, block shading, cursor vs run badges, review notes). Previous plan archived as `PLAN_DONE_2026-10-21_dashboard_badge.md`.

Checked by Claude: badges for all 13 sessions match the report; summary lines match (64/71/22/21 active min, 11.9 min heater on 20 Oct); screenshots show 1 heater + 3 spin shadings on 20 Oct and 1 spin on 21 Oct 0514, with "(inferred from power)"; "(at cursor)" labels and run-median row present; `maxAgeMs` line unchanged; `node --check` passes on all four pages (re-run by Claude); no "rpm" in the pages; patch is clean UTF-8.

Notes, no rework:
- Page size is now 787,709 bytes against the 800 KB limit: about 12 KB of headroom. Any future dashboard task must remove bytes before adding.
- The `?session=` URL parameter was not in the plan. It only looks up an existing session key, so it is safe; keep it, but list unplanned additions under "Suggestions for Claude" next time instead of shipping them.
- "Run median Dom. freq" is ~2 Hz because most running windows are drum tumbling, not spin. It is honest; a "spin-block median" (≈20 Hz) could be added later when page space allows.

## Objective
Adam asked (21 Oct) why every cycle says `load_class = MEDIUM`. It is a guess: `compute_weight_and_class()` (`firmware/smartthings_client.py`) averages power between 60–350 W in the first 30 rows; on firmware 07 those rows are fill at ~5–30 W, so nothing qualifies and it falls back to SmartThings water level, else a hard-coded 5 kg → MEDIUM. The kg formula `(W − 70) / 15` was never calibrated. The ML does not use it. After this task, new archived sessions say `unknown` instead of a guess, and real load can be recorded per session in `data/session_context.csv`.

## Context
- INVARIANTS §4: `data/real_sessions/*.csv` are originals (do not rewrite old values); the CSV column `load_class` must stay (schema). §1: honest reporting.
- Code style: exhaustive inline comments, section headers.

## Implementation Steps
1. `firmware/session_export.py`: write `load_class = "unknown"` for every new session. Keep calling nothing else that guesses. Leave `compute_weight_and_class()` in place but add a docstring warning "UNCALIBRATED heuristic, not used for exported data since 2026-10-21"; do not delete it (other scripts import it).
2. `data/session_context.csv`: add two columns at the end, `load_kg` and `load_source` (`manual` / `smartthings` / empty). Update `firmware/session_context.py` (load, save, upsert) so existing rows get empty values, `manual` rows keep their values, and backfill stays idempotent. Do not guess kg anywhere.
3. `data/pdm_feature_dictionary.json`: mark `load_class` (and `estimated_load_kg` if present) as "heuristic, uncalibrated; values in files archived before 2026-10-21 are guesses; new files write unknown". Wording only.
4. `ml/cycle_signature_report.py`: add a "Load (kg)" column from the sidecar (`-` when empty). Do not add load to the dashboard (no page budget).
5. `firmware/capture_pdm_dataset.py` still prints and stores `estimated_load_kg`, `load_class` and a "parasitic drag" derived from them. Do NOT change its maths in this task; add a printed line "(load estimate is an uncalibrated heuristic)" next to the load output, and list the file under "Suggestions for Claude" if you think it should be retired.
6. Tests: extend `firmware/tests/test_session_context.py` (new columns, manual load kept, idempotent backfill); update `firmware/tests/test_session_export.py` if it asserts a load class. Run all suites below.
7. HANDOFF with the template (keep `Open UNVERIFIED items`), `last_diff.patch` per workflow rule 6. Commit `fix(data): stop exporting guessed load_class; add load_kg to session context`. Pull --rebase, push.

## Out of Scope
- Rewriting any existing CSV in `data/real_sessions/` or `data/testing_data/`.
- Dashboard, firmware, ML pipeline/features/thresholds/LOCO.
- Building a new load estimator (needs weighed loads first).

## Acceptance Criteria
- [x] PLAN.md committed first (hash in HANDOFF).
- [x] A session exported by `session_export.py` in a test has `load_class = unknown` on every row.
- [x] `data/session_context.csv` has 13 rows and the new `load_kg`, `load_source` columns (empty); backfill twice gives an identical file; a `manual` row with `load_kg` survives backfill (unit test).
- [x] Data dictionary entry says heuristic/uncalibrated; report shows a Load (kg) column.
- [x] `py firmware/tests/test_session_context.py`, `py firmware/tests/test_session_export.py`, `py firmware/tests/test_daemon_offline.py`, `py ml/tests/test_pipeline_synthetic.py` pass; `py -m py_compile` on changed files.
- [x] No file under `data/real_sessions/` modified; no secrets; pushed; hashes reported.

## Queue (Claude will plan these next; do not start)
1. **Firmware: report reset reason.** 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot (rig reboots as the washer switches on). Add NEW `/live` fields `reset_reason` and `boot_count` (INVARIANTS §2 CAN CHANGE); consider fixing `epochMs()` jitter (2.7–3.8 s) in the same task. Needs a flash, so Adam confirms first.
2. **ML: programme-aware evaluation.** Once each signature class has ≥ 3 firmware-07 cycles, add LOCO results per class and test SmartThings-phase conditioning. Per-cycle normalisation is not allowed.
3. **Dashboard page budget.** Pages are at 787.7 KB of 800 KB; before any further dashboard feature, plan a size reduction (e.g. stop embedding testing sessions, or load session data from separate JSON files).
