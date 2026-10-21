# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Fix the cycle signature report (computed grouping, honest labels, correct gap) and the phantom sidecar row
**Date:** 2026-10-21

## Review verdict that produced this plan
CHANGES NEEDED on `e5725da`, `29ec51e`, `4b668b6` (session context sidecar + signature report). Previous plan archived as `PLAN_DONE_2026-10-21_session_context.md`.

What passed: the SmartThings 403 probe is reported correctly with no tokens or IDs; `fetch_session_phase_timeline()` change is additive and correct; the daemon hook is wrapped in try/except and only runs for schema 3; `manual` rows are protected; no `data/real_sessions/` file was modified; no secret values in the diff; per-cycle numbers in report §2–§4 (active minutes, heater minutes, block counts, spin p90, idle floor, boot at start) match Claude's independent check.

What failed (verified by Claude against the files on Drive):
1. **Grouping in the report is hard-coded, not computed** (`ml/cycle_signature_report.py` lines ~304–306 and ~374–377 are literal strings). It is also wrong: Group A ("3 spin blocks") lists `wash_cycle_2026-10-17_0835.csv`, which has no power data (max 5 W, its own row says 0 blocks), and the report's own table shows 5 and 4 blocks for 16 Oct and 18 Oct.
2. **Invented programme names.** "Daily Wash (Cold)", "Daily Wash (Warm / 40°C)", "Quick Wash / Express 15'" are not measured; every row's programme is `unknown`. This breaks the honest-labels rule (INVARIANTS §3 / §1.3).
3. **Max Gap column is wrong.** It reads 7.75–8.78 s because it diffs `epoch_ms`, which jitters (firmware `epochMs()` adds `millis() % 1000` to an RTC second). `timestamp_ms` (device `millis()`) shows every window exactly 5.024 s apart, max 5.024 s.
4. **Phantom sidecar row.** `data/session_context.csv` has 14 rows, including `wash_cycle_2026-10-20_0815.csv`, which does not exist in `data/real_sessions/` (13 CSVs). HANDOFF says 13. Acceptance criterion "exactly one row per file" is not met.
5. **Minor:** the 16 Oct row has `spin_level = 1200` but `context_source = unknown`.

Note (no action): commit `29ec51e` also committed earlier, previously uncommitted Drive versions of `auto_drive_sync_daemon.py` (v2 quota-aware) and `smartthings_client.py` (token refresh). Claude checked: the task's own changes are only the hook (~11 lines) and the timeline keys; the rest was already the working code on Drive. No secrets. Fine to keep; say so in HANDOFF.

Also note: Antigravity's DONE edit of PLAN.md overwrote Claude's 21 Oct update to queue item 2 (dashboard programme badge, requested by Adam). It is restored in the Queue below.

## Context
- Invariants §1 (honest reporting, no scope creep), §4 (`data/real_sessions/*.csv` read-only; do not touch ML pipeline, features, thresholds or LOCO).
- Code style: exhaustive inline comments and section headers.

## Implementation Steps
1. **Compute the grouping** in `ml/cycle_signature_report.py`; delete all hard-coded session names, minutes and programme names from the summary and grouping sections. Rules (put them as named constants at the top so the dashboard task can reuse the same values):
   - `HEATER_W = 1000`; heater minutes = windows with power > 1,000 W × window length.
   - **Spin block** = ≥ 20 consecutive windows with 200 W < power ≤ 1,000 W (the heater is NOT a spin block; keep the existing "high-power blocks" table in §4 as is, but add a separate "Spin blocks" count column to §2).
   - Signature class: no usable power (max power < 50 W) → `No power data`; heater > 2 min and spin blocks ≥ 2 → `Long hot (inferred)`; no heater and spin blocks ≥ 3 → `Long cold (inferred)`; no heater and spin blocks = 1 and active < 35 min → `Quick (inferred)`; anything else → `Unclassified`.
   - Every group member must satisfy its group's rule (assert it in code).
2. **Honest programme column.** The "Programme" column shows the sidecar `programme` only when `context_source` is `smartthings_live`, `smartthings_history` or `manual`; otherwise `unknown`. Signature class goes in its own column labelled "Signature (inferred from power)". Remove the words "Daily Wash", "40°C", "Express 15'", "Warm" and any °C value unless it comes from the sidecar. The executive summary is generated from the computed groups (counts and member dates), not typed text.
3. **Fix Max Gap:** compute from `timestamp_ms` differences. Add a separate column "Epoch jitter max (s)" = max |Δepoch_ms − Δtimestamp_ms| / 1000, so the firmware clock jitter is visible but not mistaken for data loss.
4. **Phantom row:** find where `wash_cycle_2026-10-20_0815.csv` came from (a temp/test path writing to the real sidecar, a file that existed during backfill and was moved, or a git-tracked file missing on Drive) and report it in HANDOFF. Then make `--backfill` reconcile: rows whose `session_file` is not in `data/real_sessions/` are removed **unless** `context_source = manual` (keep those and print a warning). Add a unit test for that. Make sure the tests only ever write to a temp directory.
5. **Minor:** if programme is unknown but `water_temp` or `spin_level` came from the live timeline, set `context_source = smartthings_live` and `note = "partial: no programme"`.
6. Re-run `py firmware/session_context.py --backfill` (twice, identical), `py ml/cycle_signature_report.py`, and the tests below. Write HANDOFF with the template (keep the `Open UNVERIFIED items` section). Commit `fix(ml): compute signature grouping and honest labels in cycle report` and `fix(data): reconcile session_context rows with real_sessions`. Pull --rebase, push. Write `last_diff.patch` per workflow rule 6.

## Out of Scope
- Dashboard, firmware, ML pipeline/features/thresholds/LOCO, `data/real_sessions/*.csv`.
- The firmware `epochMs()` jitter (queued, below).
- Retrying the SmartThings history endpoint.

## Acceptance Criteria
- [x] `grep -n "Daily Wash\|40°C\|Express 15\|wash_cycle_2026" ml/cycle_signature_report.py` finds no hard-coded session names or programme names in the summary/grouping code.
- [x] Spin block counts: 3 for 16 Oct 0857, 17 Oct 0718, 18 Oct 0516, 19 Oct 0911 and 20 Oct 0744; 1 for both 21 Oct cycles. Heater 11.9 min only on 20 Oct 0744.
- [x] Signature classes: `Long cold (inferred)` = 16 Oct 0857, 17 Oct 0718, 18 Oct 0516, 19 Oct 0911; `Long hot (inferred)` = 20 Oct 0744; `Quick (inferred)` = 21 Oct 0514, 21 Oct 0631; `No power data` = 11 Oct, 12 Oct, 15 Oct ×2, 17 Oct 0835, 19 Oct 0022.
- [x] Programme column is `unknown` for all 13 rows (no manual or SmartThings data yet).
- [x] Max Gap = 5.02 s for all four firmware-07 cycles; epoch jitter column present.
- [x] `data/session_context.csv` has exactly 13 rows, one per CSV in `data/real_sessions/`; HANDOFF explains where the `2026-10-20_0815` row came from.
- [x] Backfill twice → identical file; new reconcile test and existing tests pass: `py firmware/tests/test_session_context.py`, `py firmware/tests/test_session_export.py`, `py firmware/tests/test_daemon_offline.py`, `py ml/tests/test_pipeline_synthetic.py`; `py -m py_compile` on changed files.
- [x] No file under `data/real_sessions/` modified; no secrets in the diff.

## Queue (Claude will plan these next; do not start)
1. **Dashboard: programme badge and run-level badges (Adam asked for this on 2026-10-21, so viewers understand why peaks differ between cycles).** Display-only, `build_clean_dashboard.py` (INVARIANTS §3 CAN CHANGE). (a) Each archived session gets a programme badge: the SmartThings/manual programme from `data/session_context.csv` when known, otherwise the inferred signature class from `ml/cycle_signature_report.py` rules (Quick / Long cold / Long hot / Unclassified), marked "inferred from power". (b) A one-line signature under the title: active minutes (excluding the 10-min idle tail), heater minutes, number of spin blocks. (c) Shade heater and spin blocks on the power and vibration charts with a small legend. (d) Show Dom. freq and σx/σy/σz as running-window medians for the full run (or label them "at cursor"), so a boot window is not read as the cycle's value. Same thresholds as the report.
2. **Firmware: report reset reason.** 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot, i.e. the rig rebooted right as the washer was switched on. Add NEW `/live` fields `reset_reason` and `boot_count` (INVARIANTS §2 CAN CHANGE). In the same firmware task, consider fixing `epochMs()` jitter (RTC second + `millis() % 1000` are not aligned). Needs a flash, so Adam confirms first.
4. **Data: retire the `load_class` heuristic (Adam asked 2026-10-21 why every cycle is MEDIUM).** `compute_weight_and_class()` in `firmware/smartthings_client.py` averages power between 60–350 W in the first 30 rows; on firmware 07 those rows are fill/soak at ~5–30 W, so nothing qualifies and it falls back to SmartThings water level, else a hard-coded 5 kg → MEDIUM. The kg formula `(W − 70) / 15` was never calibrated. The ML does not use it. Plan: keep the CSV column (schema must stay) but write `unknown` for new sessions, add `load_kg` and `load_source` (manual / smartthings) to `data/session_context.csv`, and label the old values as heuristic in the dictionary. Only re-introduce an estimate after calibrating against weighed loads.
3. **ML: programme-aware evaluation.** Once each signature class has ≥ 3 firmware-07 cycles, add LOCO results per class and test SmartThings-phase conditioning. Per-cycle normalisation is not allowed (it would leak the held-out cycle's statistics and erase slow faults).
