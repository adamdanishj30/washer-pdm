# Handoff to Claude (Architect)

**Plan:** Fix the cycle signature report (computed grouping, honest labels, correct gap) and the phantom sidecar row
**Date:** 2026-10-21 16:15, Asia/Kuala_Lumpur
**Status:** COMPLETE
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `dc23692` fix(data): reconcile session_context rows with real_sessions
- `1d61f00` fix(ml): compute signature grouping and honest labels in cycle report
- `8271097` docs(handoff): complete signature report honest labels and sidecar reconciliation
- `09accb3` docs(handoff): fix queue item ordering in PLAN.md
- **Branch:** main (pushed to origin/main)

## What Changed
- **Phantom Sidecar Row Root Cause & Resolution:**
  - *Root Cause Found:* In `firmware/tests/test_daemon_offline.py`, a simulated finished v3 session `wash_2026-10-20_081500` is archived to a temporary directory. Because `auto_drive_sync_daemon.py` called `upsert_session_context(ctx)` without an explicit `context_file` parameter, it fell back to `DEFAULT_CONTEXT_FILE` and wrote into the real `data/session_context.csv` on Drive during test execution.
  - *Fix Applied:* Updated `auto_drive_sync_daemon.py` to pass `context_file=DATA_DIR / "session_context.csv"` (which redirects to temp directory when `DATA_DIR` is mocked). Explicitly mocked `session_context.DEFAULT_CONTEXT_FILE = td / "session_context.csv"` in `test_daemon_offline.py`.
  - *Reconciliation Logic Added:* Updated `backfill_all_sessions()` in `firmware/session_context.py` to reconcile existing rows against physical CSV files in `data/real_sessions/`. Any row whose CSV file does not exist on disk is removed **unless** `context_source == 'manual'` (which is retained with a warning).
  - *Phantom Row Pruned:* Re-running backfill cleanly purged `wash_cycle_2026-10-20_0815.csv`. `data/session_context.csv` now has exactly 13 rows matching the 13 CSVs on disk. Idempotency verified: re-running produces a byte-identical file.
  - *Unit Test Added:* Added `test_backfill_reconciles_phantom_rows` to `firmware/tests/test_session_context.py` verifying phantom removal and manual row preservation (5/5 tests passing).
- **Partial Context for 16 Oct Session:**
  - In `resolve_context_for_session()`, added rule: if `programme` is unknown but `spin_level` or `water_temp` is present from live timeline data, set `context_source = "smartthings_live"` and `note = "partial: no programme"`. `wash_cycle_2026-10-16_0857.csv` now reflects `spin_level = 1200`, `smartthings_live`.
- **Computed Physical Grouping & Honest Labels (`ml/cycle_signature_report.py`):**
  - *Rule Constants Defined:* Extracted all thresholds to named constants at top of module (`HEATER_W = 1000.0`, `HEATER_MIN_THRESHOLD = 2.0`, `SPIN_MIN_W = 200.0`, `MIN_SPIN_WINDOWS = 20`, `MAX_POWER_NO_DATA_W = 50.0`, `QUICK_ACTIVE_MAX_MIN = 35.0`).
  - *Hardcoded Text Removed:* Deleted all hard-coded strings, invented commercial programme names ("Daily Wash", "40°C", "Express 15'", "Warm"), and manual cycle file lists from summary and grouping sections. `grep -n "Daily Wash\|40°C\|Express 15\|wash_cycle_2026" ml/cycle_signature_report.py` finds zero matches.
  - *Spin Block Counting:* Defined mechanical spin extraction blocks as $\ge 20$ consecutive windows (approx 100 s) where $200\text{ W} < \text{power} \le 1,000\text{ W}$ (heater windows $> 1,000\text{ W}$ excluded). Correctly outputs 3 spin blocks for 16 Oct, 17 Oct 0718, 18 Oct 0516, 19 Oct 0911, and 20 Oct 0744; 1 spin block for 21 Oct 0514 and 21 Oct 0631; and 0 blocks for unmetered runs.
  - *Dynamic Classification:* Computed signature classes objectively from physics rules:
    - `Long cold (inferred)` (4 cycles): `16 Oct 0857`, `17 Oct 0718`, `18 Oct 0516`, `19 Oct 0911`
    - `Long hot (inferred)` (1 cycle): `20 Oct 0744` (11.9 min heater > 1 kW)
    - `Quick (inferred)` (2 cycles): `21 Oct 0514`, `21 Oct 0631` (1 spin block, active < 35 min)
    - `No power data` (6 cycles): `11 Oct`, `12 Oct`, `15 Oct 1020`, `15 Oct morning`, `17 Oct 0835`, `19 Oct 0022`
  - *Invariant Assertion:* Added runtime assertion in `generate_cycle_signature_report()` verifying that every member satisfies its group's physical decision rule.
  - *Honest Programme Column:* Displays `unknown` across all 13 rows since no manual or live programme labels are available yet. Signature class is shown in its own column: "Signature (inferred from power)".
- **Corrected Max Gap & Epoch Jitter:**
  - Computed `Max Gap (s)` strictly from hardware `timestamp_ms` differences: exactly **5.02 s** for all four firmware-07 runs.
  - Added new column `Epoch Jitter Max (s)` displaying max $|Δ\text{epoch\_ms} - Δ\text{timestamp\_ms}| / 1000$ (2.74 s – 3.75 s) to make firmware clock drift transparent without causing false data-loss alarms.
- **Note on Previously Uncommitted Working Files:**
  - Acknowledged that prior commit `29ec51e` committed earlier working-tree Drive versions of `auto_drive_sync_daemon.py` (v2 quota-aware) and `smartthings_client.py` (OAuth token refresh). Changes were checked and contain zero secrets.

## Files Changed
- `firmware/auto_drive_sync_daemon.py`: explicitly passed `context_file` parameter in `archive_session()`.
- `firmware/tests/test_daemon_offline.py`: mocked `session_context.DEFAULT_CONTEXT_FILE` to prevent writing to production sidecar.
- `firmware/session_context.py`: added reconciliation logic in `backfill_all_sessions()` and partial timeline context rule.
- `firmware/tests/test_session_context.py`: added `test_backfill_reconciles_phantom_rows` unit test.
- `data/session_context.csv`: reconciled from 14 rows to exactly 13 rows; updated 16 Oct row with partial context.
- `ml/cycle_signature_report.py`: refactored with named rule constants, dynamic classification, dynamic summary/grouping generation, timestamp-based gap calculation, and epoch jitter.
- `ml/models/cycle_signature_report.md`: regenerated report with honest labels, dynamic grouping, spin block counts, and epoch jitter.
- `docs/handoffs/PLAN.md`: marked `Status: DONE` and checked all acceptance criteria.
- `docs/handoffs/HANDOFF.md`: updated handoff documentation.
- `docs/handoffs/last_diff.patch`: diff patch covering commits `dc23692` and `1d61f00`.

## Excluded from Patch
- None. (Binary files and HTML dashboards were excluded; `last_diff.patch` is ~49 KB and has `git diff --stat` prepended at the top).

## Acceptance Criteria
- [x] `grep -n "Daily Wash\|40°C\|Express 15\|wash_cycle_2026" ml/cycle_signature_report.py` finds no hard-coded session names or programme names in the summary/grouping code.
- [x] Spin block counts: 3 for 16 Oct 0857, 17 Oct 0718, 18 Oct 0516, 19 Oct 0911 and 20 Oct 0744; 1 for both 21 Oct cycles. Heater 11.9 min only on 20 Oct 0744.
- [x] Signature classes: `Long cold (inferred)` = 16 Oct 0857, 17 Oct 0718, 18 Oct 0516, 19 Oct 0911; `Long hot (inferred)` = 20 Oct 0744; `Quick (inferred)` = 21 Oct 0514, 21 Oct 0631; `No power data` = 11 Oct, 12 Oct, 15 Oct ×2, 17 Oct 0835, 19 Oct 0022.
- [x] Programme column is `unknown` for all 13 rows (no manual or SmartThings data yet).
- [x] Max Gap = 5.02 s for all four firmware-07 cycles; epoch jitter column present.
- [x] `data/session_context.csv` has exactly 13 rows, one per CSV in `data/real_sessions/`; HANDOFF explains where the `2026-10-20_0815` row came from.
- [x] Backfill twice → identical file; new reconcile test and existing tests pass: `py firmware/tests/test_session_context.py`, `py firmware/tests/test_session_export.py`, `py firmware/tests/test_daemon_offline.py`, `py ml/tests/test_pipeline_synthetic.py`; `py -m py_compile` on changed files.
- [x] No file under `data/real_sessions/` modified; no secrets in the diff.

## Tests Run
- `py -m py_compile firmware/smartthings_client.py firmware/session_context.py firmware/auto_drive_sync_daemon.py ml/cycle_signature_report.py firmware/tests/test_session_context.py firmware/tests/test_daemon_offline.py` — PASS
- `py firmware/tests/test_session_export.py` — PASS
- `py firmware/tests/test_daemon_offline.py` — PASS (isolated in temp directory, no sidecar pollution)
- `py firmware/tests/test_session_context.py` — PASS (5/5 unit tests pass, including phantom row reconciliation)
- `py ml/tests/test_pipeline_synthetic.py` — PASS (6/6 held-out cycles normal)
- `py firmware/session_context.py --backfill` — PASS (13 sessions registered, verified strictly idempotent)
- `py ml/cycle_signature_report.py` — PASS (`cycle_signature_report.md` generated with zero assertion errors)
- Grep check for forbidden hardcoded strings in `ml/cycle_signature_report.py` — PASS (0 matches)

## Invariants Check
- `data/real_sessions/*.csv` are untouched originals.
- Schema (45 columns), `V3_KEY_MAP`, and ML pipelines remain unmodified.
- No secrets committed or printed.
- Transparent reporting: only measured data reported; unmeasured programmes labeled `unknown`.

## Open UNVERIFIED items (carried forward)
- Whether the Apps Script trigger is still deployed (Adam to check `script.google.com`).
- Workflow run with real GitHub secrets (needs Adam to set them, then a manual `workflow_dispatch`).
- A real wash on firmware 07: session start, END marker, archive step (`INVARIANTS_DO_NOT_CHANGE.md` §2).
- Active-wash polling: `/api/live` no faster than 10 s and `/sessions/...` no faster than 30 s (19 Oct dashboard task, criterion 4).
- Session-change reset and live gap breaks during a real wash (criterion 13).
- Visual check of `historical.html` on session `wash_cycle_2026-10-19_0911` and `wash_cycle_2026-10-20_0744`.
- Live DevTools network checks: idle polling at least 25 s, `historical.html` zero live requests, pause/AFK/tab-hidden behaviour.
- `/window.json` and `washer-pdm.local` reachability; the `WHO_AM_I` 0x75 quirk (not a failure).

## Blocked / Questions
- None.

## Suggestions for Claude
- The rule constants defined in `ml/cycle_signature_report.py` (`HEATER_W = 1000.0`, `HEATER_MIN_THRESHOLD = 2.0`, `SPIN_MIN_W = 200.0`, `MIN_SPIN_WINDOWS = 20`, `QUICK_ACTIVE_MAX_MIN = 35.0`) can be imported or mirrored directly in `build_clean_dashboard.py` for queue item 1 (dashboard programme badge and run-level badges).
