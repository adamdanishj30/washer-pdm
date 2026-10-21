# Handoff to Claude (Architect)

**Plan:** Dashboard: wash-type badge, cycle summary line, shaded heater/spin blocks, and run-level badges
**Date:** 2026-10-21 16:38, Asia/Kuala_Lumpur
**Status:** COMPLETE
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `03a883e` fix: review notes (report wording, test isolation)
- `c597e60` feat(dashboard): wash-type badge, cycle summary and block shading
- **Branch:** main (pushed to origin/main)

## What Changed
- **Review Notes Fixes (`03a883e`):**
  - *Report Clipping Clarification:* In `ml/cycle_signature_report.py`, reworded sensor integrity statement from "across all sessions" to "across all firmware-07 sessions", since accelerometer clipping is tracked starting in firmware 07. Regenerated `ml/models/cycle_signature_report.md` (verified byte-identical except wording and generation timestamp).
  - *Test Isolation:* Wrapped `sc.DEFAULT_CONTEXT_FILE` and `sc.REAL_SESSIONS_DIR` overrides in `firmware/tests/test_daemon_offline.py` with `try ... finally` block, restoring original module defaults after test completion.
  - *Shared Block Finding Helper:* Added `find_signature_blocks(powers)` to `ml/cycle_signature_report.py` to identify contiguous row-index spans for heater (> 1 kW) and spin extraction (200 W < power <= 1000 W, >= 20 windows) for dashboard chart shading without duplicating thresholds.
- **Build-Time Physical Summaries (`build_clean_dashboard.py`):**
  - Imported named constants (`HEATER_W`, `SPIN_MIN_W`, `MAX_POWER_NO_DATA_W`) and functions (`classify_signature`, `count_spin_blocks`, `find_signature_blocks`, `load_session_context_map`) from `ml/cycle_signature_report.py`. Grep verified zero duplicated numeric threshold constants in `build_clean_dashboard.py` or JavaScript.
  - In `discover_all_sessions()`, computed lightweight `summary` dict for all real sessions containing: `signature`, `programme` (or null), `water_temp` (or null), `context_source`, `active_min`, `heater_min`, `spin_blocks`, `blocks` (span indices `[{type, i0, i1}]`), and `run_medians` (`vib_dom_hz`, `vib_std_x/y/z`, `vib_mag_std` for active running windows `vib_mag_std > 0.08`).
- **Wash-Type Badge & Subtitle Summary Line:**
  - Added `#badge-wash-type` pill next to timeline title `#title-timeline`. Displays programme + temp (labeled `SmartThings` or `manual`) if verified in sidecar, else inferred signature class with explicit `(inferred from power)` label. Testing sessions (🧪) hide the badge; custom Load-CSV files show `not classified`.
  - Added tooltip explaining physical classification rules (heater > 1 kW, spin >= 20 windows at 200–1,000 W).
  - Extended `#sub-timeline` with active machine summary: e.g. `64 min active · no heater · 3 spin blocks • 65.7 min recorded • wash_cycle_2026-10-19_0911`. When `recorded - active >= 8 min`, appends `(~10 min idle tail)` to clarify timeout idle windows.
- **Chart Shading for Heater & Spin Spans:**
  - In `drawSpline()` (Card 1) and `drawEnergy()` (Card 4), rendered shaded vertical background spans: amber (`rgba(251, 146, 60, 0.16)`) for heater blocks and teal (`rgba(0, 240, 210, 0.14)`) for mechanical spin extraction blocks.
  - Handled both full-run view and 40-point window views. Shading disabled in live streaming mode.
  - Added subtle chart legend indicators (`#legend-spline-blocks` and `#legend-energy-blocks`) showing Heater / Spin color swatches when blocks are present.
- **Cursor Readouts vs Run-Level Medians:**
  - Re-labeled cursor telemetry badges in Card 2 to explicitly state `(at cursor)` in historical mode (`Dom. freq (at cursor):`, `σx (at cursor):`, `σy (at cursor):`, `σz (at cursor):`, `σ|a| (at cursor):`).
  - Added `#card2-run-medians` row displaying full-run running-window medians (`Run median (active): Dom. freq X Hz • σx/σy/σz X / Y / Z m/s² • σ|a| M m/s²`). Hidden for legacy sessions and live mode.
  - Removed all occurrences of `rpm` from tooltips and text.
- **URL Parameter for Direct Session Loading:**
  - Supported `?session=<id_or_date>` parameter in `historical.html` to facilitate testing and direct navigation.
- **Visual Browser Verification:**
  - Captured full-resolution screenshots with headless Microsoft Edge into `docs/handoffs/screens/`.

## Files Changed
- `ml/cycle_signature_report.py`: added `find_signature_blocks()`, reworded clipping sentence to "across all firmware-07 sessions".
- `ml/models/cycle_signature_report.md`: regenerated report.
- `firmware/tests/test_daemon_offline.py`: wrapped context file override in `try ... finally`.
- `build_clean_dashboard.py`: imported signature constants & helpers, computed session summaries, added wash-type badge, summary line, block shading in `drawSpline`/`drawEnergy`, `(at cursor)` labels, and run medians row.
- `index.html`, `historical.html`, `dashboard.html`, `cloud_dashboard.html`: regenerated dashboard pages.
- `docs/handoffs/screens/historical_19_oct_0911.png`: browser screenshot of Long cold session with 3 spin blocks and run medians.
- `docs/handoffs/screens/historical_20_oct_0744.png`: browser screenshot of Long hot session with 1 heater + 3 spin blocks and idle tail note.
- `docs/handoffs/screens/historical_21_oct_0514.png`: browser screenshot of Quick session with 1 spin block.
- `docs/handoffs/screens/historical_11_oct_1019.png`: browser screenshot of unmetered session (No power data, no shading, legacy labels).
- `docs/handoffs/PLAN.md`: marked `Status: DONE` and checked all criteria.
- `docs/handoffs/HANDOFF.md`: updated handoff documentation.
- `docs/handoffs/last_diff.patch`: diff patch covering task changes (excluding generated HTML and screenshots).

## Excluded from Patch
- `index.html`: generated output (770,701 -> 787,693 bytes, +16.9 KB)
- `historical.html`: generated output (770,713 -> 787,709 bytes, +17.0 KB)
- `dashboard.html`: generated output (770,701 -> 787,693 bytes, +16.9 KB)
- `cloud_dashboard.html`: generated output (770,701 -> 787,693 bytes, +16.9 KB)
- `docs/handoffs/screens/*.png`: binary screenshot images (~180 KB - 275 KB each)
- All pages remain safely under the 800 KB ceiling (maximum page is 769.2 KB).

## Acceptance Criteria
- [x] Badge text per session matches `ml/models/cycle_signature_report.md` §2 for all 13 real sessions; every inferred badge contains "inferred":
  1. `wash_cycle_2026-10-11_1019.csv`: `No power data`
  2. `wash_cycle_2026-10-12_1019.csv`: `No power data`
  3. `wash_cycle_2026-10-15_morning.csv`: `No power data`
  4. `wash_cycle_2026-10-15_1020.csv`: `No power data`
  5. `wash_cycle_2026-10-16_0857.csv`: `Long cold (inferred from power)`
  6. `wash_cycle_2026-10-17_0718.csv`: `Long cold (inferred from power)`
  7. `wash_cycle_2026-10-17_0835.csv`: `No power data`
  8. `wash_cycle_2026-10-18_0516.csv`: `Long cold (inferred from power)`
  9. `wash_cycle_2026-10-19_0022.csv`: `No power data`
  10. `wash_cycle_2026-10-19_0911.csv`: `Long cold (inferred from power)`
  11. `wash_cycle_2026-10-20_0744.csv`: `Long hot (inferred from power)`
  12. `wash_cycle_2026-10-21_0514.csv`: `Quick (inferred from power)`
  13. `wash_cycle_2026-10-21_0631.csv`: `Quick (inferred from power)`
- [x] Summary line values equal the report's Active Min, Heater Min and Spin Blocks:
  - 19 Oct 0911: `64 min active · no heater · 3 spin blocks`
  - 20 Oct 0744: `71 min active · 11.9 min heater · 3 spin blocks`
  - 21 Oct 0514: `22 min active · no heater · 1 spin block`
  - 21 Oct 0631: `21 min active · no heater · 1 spin block`
  - Unmetered sessions: `No electrical power data tracked for this cycle`
- [x] Shaded spans: 3 spin for 16/17 0718/18/19 Oct; 1 heater + 3 spin for 20 Oct; 1 spin for each 21 Oct; none for No-power sessions.
- [x] Cursor badges are labelled "at cursor"; run medians shown for firmware-07 sessions; no rpm anywhere (verified 0 matches for 'rpm' across code and generated pages).
- [x] Thresholds are imported from `ml/cycle_signature_report.py` (grep shows no duplicated 1000/200/20 thresholds in the build script).
- [x] `node --check` passes on all four pages; all pages < 800 KB (769.2 KB actual).
- [x] `maxAgeMs` line/structure, polling functions and `windowToRecord` unchanged (`git diff -S` verified 0 diffs).
- [x] Report regenerated with clipping wording fix; `py firmware/tests/test_daemon_offline.py`, `py firmware/tests/test_session_context.py`, `py firmware/tests/test_session_export.py` all PASS.
- [x] Browser check done with screenshots into `docs/handoffs/screens/` and verified visually.
- [x] Only designated files committed, pushed to `origin/main` (hashes reported).

## Tests Run
- `py -m py_compile build_clean_dashboard.py ml/cycle_signature_report.py firmware/tests/test_daemon_offline.py` — PASS
- `py firmware/tests/test_daemon_offline.py` — PASS
- `py firmware/tests/test_session_context.py` — PASS (5/5 tests pass)
- `py firmware/tests/test_session_export.py` — PASS
- `py ml/cycle_signature_report.py` — PASS
- `node --check` on `index.html`, `historical.html`, `dashboard.html`, `cloud_dashboard.html` — PASS (4/4 pages)
- Headless Edge browser screenshot verification — PASS (4/4 sessions captured)

## Invariants Check
- `data/real_sessions/*.csv` are untouched originals.
- Schema (45 columns), `V3_KEY_MAP`, and ML pipelines remain unmodified.
- No secrets committed or printed.
- Source of truth `build_clean_dashboard.py` edited; all 4 HTML pages kept synchronized.
- Dark theme tokens respected (`--bg-body: #1e2229`, `--teal-accent: #00f0d2`, `--coral-accent: #fb923c`).

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
- The queue item 1 is completed. The next queued items are ready:
  1. **Data:** Retire `load_class` heuristic in `firmware/smartthings_client.py` (`(W - 70) / 15` uncalibrated formula).
  2. **Firmware:** ESP32 reset reason reporting (`/live` fields `reset_reason`, `boot_count`) and `epochMs()` RTC/millis alignment (requires Adam's flash confirmation).
  3. **ML:** Programme-aware LOCO evaluation once each signature class accumulates >= 3 cycles.
