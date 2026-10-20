# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Make the dashboard's "Load CSV" parser read firmware-07 files (σ view), and rebuild so the 20 Oct session is built in
**Date:** 2026-10-20

## Objective
Today a firmware-07 CSV opened with the **📁 Load CSV** button is shown in legacy mode (flat Ax/Ay/Az lanes, "Dom. freq: –", "State: –", subtitle "Legacy 5 s snapshots"), while the same kind of file built into the page (🧺) shows the σ view. After this task, a firmware-07 CSV loaded with Load CSV renders exactly like a built-in one, legacy CSVs behave exactly as before, and session `wash_cycle_2026-10-20_0744` is built into the pages.

## Queue note
The credentials task was moved, unchanged and not started, to `docs/handoffs/PLAN_QUEUED_remove_ci_fallback_credentials.md`. It becomes PLAN.md after this task is reviewed. Do not start it now.

## Why (evidence, found by Claude on 2026-10-20)
- `build_clean_dashboard.py`, JS `parseCsvData(text)` (around line 3410): reads columns by position only (`parts[0..5]` = t, ax, ay, az, rms, power) and returns 5- or 6-element records. It never reads `vib_mag_std`, `vib_std_x/y/z` or `vib_dom_hz`, so `seriesHasVibStd()` is false and the page falls back to legacy mode.
- The Python `load_csv(path)` (line 16) already detects firmware-07 by `'vib_mag_std' in headers` and builds 12-element records `[t, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf]`. The 19 Oct σ task (commit `03495d3`) updated only this Python path.
- Not a data or firmware problem: `wash_cycle_2026-10-19_0911.csv` and `wash_cycle_2026-10-20_0744.csv` have the identical 45-column header, 80,384 audio samples and ~1,013 accel samples per window, 11.96 windows/min, same sound scale, same gravity orientation.

## Context
- Invariants: `INVARIANTS_DO_NOT_CHANGE.md` §3. This is a CAN CHANGE (display-only) item. Edit `build_clean_dashboard.py` only; rebuild all four pages.
- MUST STAY: the `maxAgeMs` line and its `if/else` structure, polling cadence, `/api/live`, Firebase quota rules, honest labels (no rpm shown as measured).
- Code style: exhaustive inline comments and clear section headers (Adam is a beginner).

## Implementation Steps
1. In `parseCsvData(text)`, read the first non-empty line as a header. If it contains `vib_mag_std`, build a column-name → index map and parse each row into the same 12-element record the Python `load_csv` makes: `[t, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf]`, using columns `timestamp_ms, accel_x, accel_y, accel_z, audio_rms, power_w, vib_mag_std, vib_std_x, vib_std_y, vib_std_z, vib_dom_hz`. Empty or non-numeric optional values become `null` (same as Python `None`). Skip a row only if t, ax, ay, az or rms is not a number. Strip quotes as the current code does. Sort by t.
2. If the header does not contain `vib_mag_std` (legacy firmware 05/06, or no header), run the **existing** legacy logic unchanged. Do not alter its output in any way.
3. Comment the new branch: what each index means, and that it must match Python `load_csv` (and say so next to `load_csv` too).
4. Update the Load CSV alert text so it no longer implies only 5 columns are supported (e.g. mention firmware-07 files are read by header). Wording only.
5. Run `py build_clean_dashboard.py` so all four pages are regenerated and `wash_cycle_2026-10-20_0744` is built in as a 🧺 session.
6. Extract the inline `<script>` from each of the four pages and run `node --check` on each.
7. Parity test with Node (write it as a new file, e.g. `firmware/tests/test_csv_parser_parity.js` or a temporary script; say which in HANDOFF): extract `parseCsvData` from the built `historical.html`, run it on `data/real_sessions/wash_cycle_2026-10-20_0744.csv` and `wash_cycle_2026-10-19_0911.csv`, and compare with Python `load_csv` output for the same files: same row count, every record length 12, index 7 is `'w'`, every numeric field equal within 1e-4 (Python rounds to 4 decimals), nulls in the same places.
8. Legacy parity: run the OLD `parseCsvData` (from `git show HEAD:build_clean_dashboard.py`) and the NEW one on `data/real_sessions/wash_cycle_2026-10-17_0835.csv` and `wash_cycle_2026-10-12_1019.csv`; the outputs must be identical (JSON string compare).
9. Browser check (if a browser is available to you; else mark UNVERIFIED): open `historical.html`, use **Load CSV** on `wash_cycle_2026-10-20_0744.csv`, and confirm: Card 1 subtitle says "Vibration σ (window std) & sound RMS", Card 2 title "Per-Axis Vibration (std per 5 s window)", dominant-frequency pill shows a Hz value during spin, State pill shows Running/Idle. Then select the built-in 🧺 20 Oct session and confirm it looks the same.
10. Report page sizes before and after (all four must stay under 800 KB).
11. Write HANDOFF.md with the template. Keep the `Open UNVERIFIED items (carried forward)` section from the last handoff, and add the item below under "Data notes".
12. Commit only `build_clean_dashboard.py` and the four pages (plus the test file if kept): `fix(dashboard): read firmware-07 columns in Load CSV parser`. Then `pull --rebase` and `push` (Cloudflare deploys from GitHub). Report the hash. If `git status` shows other changes (e.g. under `data/`), do not commit them; list them in HANDOFF.

## Data notes (for HANDOFF, no action)
- Both firmware-07 sessions have `phase = none` / `phase_source = fallback` on every row: no SmartThings phase labels were saved. Claude will plan the SmartThings check separately.
- `load_class` is `MEDIUM` on every row of both files, so it does not describe the real load.

## Out of Scope
- Live polling, `windowToRecord`, `maxAgeMs`, any firmware, ML, daemon, `.github/` or proposal file.
- Any file under `data/` (read only).
- The SmartThings phase-label problem.
- The credentials task (queued).

## Acceptance Criteria
- [x] `py build_clean_dashboard.py` succeeds; `node --check` passes on all four pages.
- [x] Firmware-07 parity (step 7) passes for both files: same row counts, 12-element records, values within 1e-4, nulls aligned.
- [x] Legacy parity (step 8) passes: old and new parser output identical for both legacy files.
- [x] `wash_cycle_2026-10-20_0744` appears as a built-in 🧺 session in `historical.html`.
- [x] Browser check (step 9) done or marked UNVERIFIED.
- [x] Code inspection: `maxAgeMs` line and structure, polling functions, `windowToRecord` unchanged; no rpm value displayed.
- [x] Page sizes reported, all under 800 KB.
- [x] Only the build script, the four pages (and the optional test file) committed; no secrets in the diff; pushed; hash reported.

## Risk Notes
- **Legacy breakage:** the legacy branch must be byte-identical in behaviour; step 8 proves it.
- **Header row:** the old parser skipped the header by accident (`parseFloat('timestamp_ms')` is NaN). The new branch must not count the header as a data row.
- **Page size:** building in one more firmware-07 session adds roughly 60–80 KB per page.
- **Concurrent bot commits:** the GitHub workflow commits pages every 30 min; use `pull --rebase` and rebuild if the rebase touches the pages.
