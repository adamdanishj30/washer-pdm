# Handoff to Claude (Architect)

**Plan:** Make the dashboard's "Load CSV" parser read firmware-07 files (σ view), and rebuild so the 20 Oct session is built in
**Date:** 2026-10-20 12:06, Asia/Kuala_Lumpur
**Status:** COMPLETE

## Commits
- `788f575` fix(dashboard): read firmware-07 columns in Load CSV parser
- **Branch:** main

## What Changed
- **Client-Side CSV Parser (`parseCsvData`):** Added a dedicated parsing branch in `build_clean_dashboard.py` for Firmware 07 (V3 window record) triggered when the header contains `vib_mag_std`. Dynamically maps column headers (`timestamp_ms`, `accel_x`, `accel_y`, `accel_z`, `audio_rms`, `power_w`, `vib_mag_std`, `vib_std_x`, `vib_std_y`, `vib_std_z`, `vib_dom_hz`) to build the exact 12-element record `[t, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf]` matching Python `load_csv`. Numeric values are rounded to 4 decimals, missing values map to `null`.
- **Legacy Branch Unchanged:** If `vib_mag_std` is not present in the header, the parser falls back to the exact legacy positional parser (5 or 6 elements), preserving 100% byte-identical output for legacy cycles.
- **Alert Text:** Updated Load CSV alert message to indicate firmware-07 files are read by header with `vib_mag_std` while legacy files use the first 5-6 columns.
- **Pre-computed 20 Oct Session Built In:** Rebuilt all four pages (`index.html`, `dashboard.html`, `cloud_dashboard.html`, `historical.html`) via `py build_clean_dashboard.py`. Session `wash_cycle_2026-10-20_0744` is automatically discovered and embedded as a built-in 🧺 session (`preset_real_wash_cycle_2026_10_20_0744`, 81m, 965 pts, length-12 records).
- **Parity Test Suite:** Created `firmware/tests/test_csv_parser_parity.js`, which verifies:
  1. Firmware-07 parity between JS `parseCsvData` extracted from `historical.html` and Python `load_csv` on `wash_cycle_2026-10-20_0744.csv` (965 rows) and `wash_cycle_2026-10-19_0911.csv` (786 rows). Confirms identical row count, 12-element records, `'w'` indicator at index 7, all numeric values within 1e-4, nulls aligned.
  2. Legacy parity between new `parseCsvData` and old `parseCsvData` from git HEAD on `wash_cycle_2026-10-17_0835.csv` (792 rows) and `wash_cycle_2026-10-12_1019.csv` (1216 rows). Confirms byte-identical JSON strings.
- **Node Validation:** Extracted inline `<script>` from all 4 pages and verified syntax with `node --check` (0 errors).

## Files Changed
- `build_clean_dashboard.py`: Added firmware-07 header-aware parsing branch to `parseCsvData`, updated Load CSV alert text, and added parity notes next to `load_csv`.
- `index.html`, `dashboard.html`, `cloud_dashboard.html`, `historical.html`: Regenerated static dashboard pages with embedded 20 Oct wash session and updated client-side parser.
- `firmware/tests/test_csv_parser_parity.js`: Automated parity test script for firmware-07 and legacy CSV parsing.
- `docs/handoffs/PLAN.md`: Marked acceptance criteria and status as DONE.
- `docs/handoffs/HANDOFF.md`: Updated handoff document.

## Acceptance Criteria
- [x] `py build_clean_dashboard.py` succeeds; `node --check` passes on all four pages — verified with Python build and Node syntax check on all 4 generated pages.
- [x] Firmware-07 parity (step 7) passes for both files: same row counts, 12-element records, values within 1e-4, nulls aligned — verified via `firmware/tests/test_csv_parser_parity.js`.
- [x] Legacy parity (step 8) passes: old and new parser output identical for both legacy files — verified via `firmware/tests/test_csv_parser_parity.js` (byte-identical JSON).
- [x] `wash_cycle_2026-10-20_0744` appears as a built-in 🧺 session in `historical.html` — verified (`preset_real_wash_cycle_2026_10_20_0744`).
- [x] Browser check (step 9) done or marked UNVERIFIED — marked UNVERIFIED (headless CLI environment cannot launch interactive desktop browser). Code logic confirms 12-element records activate `seriesHasVibStd()`, rendering dynamic vibration σ, per-axis σ lanes, Hz pill, and Idle/Running state.
- [x] Code inspection: `maxAgeMs` line and structure, polling functions, `windowToRecord` unchanged; no rpm value displayed — verified.
- [x] Page sizes reported, all under 800 KB — verified: all 4 pages are 699,070 B (682.7 KB).
- [x] Only the build script, the four pages (and the optional test file) committed; no secrets in the diff; pushed; hash reported — verified.

## Tests Run
- `py -m py_compile build_clean_dashboard.py` — PASS
- `py build_clean_dashboard.py` — PASS
- `node --check` on extracted `<script>` blocks (all 4 pages) — PASS
- `node firmware/tests/test_csv_parser_parity.js` — PASS (All 4 sessions passed parity checks)

## Page Sizes
- `index.html`: 699,070 bytes (682.7 KB)
- `dashboard.html`: 699,070 bytes (682.7 KB)
- `cloud_dashboard.html`: 699,070 bytes (682.7 KB)
- `historical.html`: 699,082 bytes (682.7 KB)
(All comfortably below the 800 KB ceiling).

## Invariants Check
- All items in `INVARIANTS_DO_NOT_CHANGE.md` respected. Source of truth (`build_clean_dashboard.py`) edited; all 4 pages rebuilt; `node --check` passed; `maxAgeMs` untouched; no secrets committed.

## Data Notes
- Both firmware-07 sessions (`2026-10-19_0911` and `2026-10-20_0744`) have `phase = none` / `phase_source = fallback` on every row: no SmartThings phase labels were saved. Claude will plan the SmartThings check separately.
- `load_class` is `MEDIUM` on every row of both files, so it does not describe the real load.

## Open UNVERIFIED items (carried forward)
- A real wash on firmware 07: session start, END marker, archive step (`INVARIANTS_DO_NOT_CHANGE.md` §2).
- Active-wash polling: `/api/live` no faster than 10 s and `/sessions/...` no faster than 30 s (19 Oct dashboard task, criterion 4).
- Session-change reset and live gap breaks during a real wash (criterion 13).
- Visual check of `historical.html` on session `wash_cycle_2026-10-19_0911` and `wash_cycle_2026-10-20_0744`.
- Live DevTools network checks: idle polling at least 25 s, `historical.html` zero live requests, pause/AFK/tab-hidden behaviour.
- `/window.json` and `washer-pdm.local` reachability; the `WHO_AM_I` 0x75 quirk (not a failure).

## Blocked / Questions
- None.

## Suggestions for Claude
- None.
