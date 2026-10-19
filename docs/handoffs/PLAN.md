# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Show real vibration for firmware-07 data: plot per-window vibration std (σ) instead of gravity means, plus dominant vibration frequency
**Date:** 2026-10-19

## Objective
For firmware-07 data (historical CSVs and live wash windows), the vibration charts show dynamic vibration, not the window means. The means are gravity/tilt and look flat. Specifically:
- Card 1 plots `vib_mag_std` (σ) on an honest σ axis in m/s².
- Card 2 plots per-axis σ (`vib_std_x/y/z`).
- The State pill works in historical mode too.
- A dominant-vibration-frequency readout appears while the machine is running.

Legacy firmware 05/06 files keep their current display, with a label saying what they are.

## Review verdict that produced this plan
**APPROVED**: honest labels, commit `ed3be4e`. Verified by reading the current `build_clean_dashboard.py` and `INVARIANTS_DO_NOT_CHANGE.md`:
- Card 4 HTML now has only Active W, Energy (shown span), Peak Power and Avg Active.
- `drawEnergy` no longer has the kg, drag, RM, P-F, % Load or 400 W spin line.
- `drawArea` no longer has the 120 baseline or the ×/% badge, and the PEAK line is kept.
- The State pill uses `VIB_RUNNING_THRESHOLD = 0.08` (defined, with a comment) and shows `—` when σ is missing.
- The `maxAgeMs` line and the poll-controller functions are unchanged.
- The invariants "Spike" bullet is annotated with `ed3be4e`.
- The browser check (#4) is still operator-pending.

## Why (evidence)
- `firmware/session_export.py` writes firmware-07 CSVs with the 8 legacy columns first (`accel_x/y/z` = window **means**), then the V3 columns. Those include `vib_mag_std`, `vib_std_x`, `vib_std_y`, `vib_std_z` and `vib_dom_hz`.
- `load_csv()` in `build_clean_dashboard.py` reads only columns 0–5, so the vibration never reaches the page.
- From `data/real_sessions/wash_cycle_2026-10-19_0911.csv`:
  - Idle: `vib_mag_std` ≈ 0.03 and `vib_std_x` ≈ 0.020.
  - Final spin: `vib_mag_std` ≈ 0.72 and `vib_std_x` ≈ 1.15.
  - The means stay at about −0.66 / 2.89 / −9.00 throughout.
  - `vib_dom_hz` ramps from 10.7 to 19.94 Hz into the spin.
- Card 1 currently draws live σ as `9.81 + σ × 1.5` on an axis labelled 8.0 / 9.81 / 12.0, so its tick labels are wrong for σ.

## Context
- Relevant files: `build_clean_dashboard.py` (only file to edit); the generated `index.html`, `dashboard.html`, `cloud_dashboard.html`, `historical.html` (rebuild only). Read-only references: `firmware/session_export.py` (V3_KEY_MAP column names), `data/real_sessions/wash_cycle_2026-10-19_0911.csv`.
- Invariants (`docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md`):
  - Section 2: `ax/ay/az` are the window MEAN (gravity tilt), NOT vibration; dynamic vibration is `vib_std`/`sm`. Feature meanings must not change.
  - Section 3 CAN CHANGE: charts and readouts, including a `vib_std` line with an axis of about 0–0.5 m/s² and an idle floor marker at about 0.03.
  - Section 3 MUST STAY: honest labels; the `maxAgeMs` line and online/offline `if` structure; `node --check` after edits.
  - Section 4: `data/real_sessions/*.csv` are originals and must not be modified. This task only reads them.
  - Section 1: edit the build script only; exhaustive comments and section headers; one task = one change set.
- Record layout already used by live windows: `[t, ax, ay, az, rms, pwr, sm, tag]`. This plan extends it to `[t, ax, ay, az, rms, pwr, sm, tag, sx, sy, sz, vdf]`, indices 8–11.

## Implementation Steps
All in `build_clean_dashboard.py`. **Keep JS braces doubled (`{{ }}`).**

1. **`load_csv()`: header-aware parsing (Python).**
   - Read the header line. If it contains `vib_mag_std`, treat the file as firmware-07 and look up column indices **by name**: `timestamp_ms`, `accel_x`, `accel_y`, `accel_z`, `audio_rms`, `power_w`, `vib_mag_std`, `vib_std_x`, `vib_std_y`, `vib_std_z`, `vib_dom_hz`.
   - Build each row as `[t, ax, ay, az, rms, pwr_or_None, sm, 'w', sx, sy, sz, vdf]`. Round floats to 4 decimals to keep the page size down, and use `None` for empty or invalid cells.
   - If the header lacks `vib_mag_std`, use the **existing** logic unchanged, so legacy rows stay byte-identical.
   - Add a section header and comments explaining the column meanings: means = tilt, std = vibration.
2. **`windowToRecord(w)` (JS): add indices 8–11** from window keys `sx`, `sy`, `sz`, `vdf`. Use finite numbers or `null`. Do not change indices 0–7 or any other poll-controller function.
3. **Shared helpers (JS), new commented section "Vibration display helpers":**
   - `getVibStd(p)` → `p[6]` if it is a finite number, else `null`.
   - `getAxisStd(p, axis)` → `p[8]`, `p[9]` or `p[10]` if finite, else `null`.
   - `seriesHasVibStd(points)` → true if any point has a finite `p[6]`.
   - `seriesHasAxisStd(points)` → true if any point has a finite `p[8]`.
4. **Card 1 (`drawSpline`) σ mode.** If `seriesHasVibStd(points)` (live or historic), plot the teal line from `getVibStd(p)`:
   - Left axis runs from 0 to a "nice" max (≥ 0.5 m/s², rounded up), with 3–4 ticks and the axis title `σ m/s²`.
   - Draw a dashed floor marker at 0.03 labelled `sensor floor ~0.03`.
   - Points without σ break the line (`moveTo`).
   - Remove the `9.81 + σ × 1.5` mapping and the 9.81/1g ticks in σ mode.
   - If not σ mode (legacy), keep today's |a| drawing exactly.
5. **Card 1 legend and subtitle.**
   - In `applyRecord`, show `Vib (σ)` with σ to 3 decimals whenever `getVibStd(rec)` is not null, in live **and** historic mode (remove the `isFromLive` condition for this).
   - In `updateChartSubtitles`, in historic σ mode use "<dur>-min run • Vibration σ (window std) & sound RMS". In historic legacy mode use "<dur>-min run • Legacy 5 s snapshots: |a| magnitude (not vibration std) & sound".
6. **Card 2 (`drawXyz`) per-axis σ mode.** If `seriesHasAxisStd(points)`:
   - Plot σx, σy and σz as three lines on one shared axis from 0 to a nice max (≥ 0.5) in m/s², keeping the existing colours and axis toggles.
   - Hide the "X/Y Zero Baseline" and "Z 1g Gravity" badges and lanes.
   - Points without axis σ break the line.
   - Otherwise keep today's mean-lane drawing exactly.
   - In σ mode, update the title to "Per-Axis Vibration (std per 5 s window)" and the pills to `σx / σy / σz`, with `|a|` changed to `σ|a|` showing `p[6]`. In legacy mode, restore the original title and pills.
7. **Dominant frequency readout (Card 2 header, new pill `vib-dom-freq`).**
   - Show `Dom. freq: <vdf, 1 decimal> Hz` only when `getVibStd(rec) > VIB_RUNNING_THRESHOLD` and `p[11]` is finite. Otherwise show `—`.
   - Add a `title` tooltip: "Dominant vibration frequency in 0.5–45 Hz. During spin this usually tracks drum speed (Hz × 60 ≈ rpm); not verified against a tachometer."
   - Do **not** display rpm as a measured value.
8. **Build and verify.** Run `py build_clean_dashboard.py`, then `node --check` on the extracted script of each of the four pages. Record each page's size before and after.
9. **Docs and handoff.**
   - Update the dashboard row in `docs/handoffs/current_state_and_scale_up_handoff.md`.
   - Replace section 1 of `docs/handoffs/HANDOFF.md` with this task's matrix, keeping static and browser evidence separate.
   - Set this file's Status to DONE.
   - Make a **new** commit `feat(dashboard): plot firmware-07 vibration std and dominant frequency`, then `git pull --rebase`, then `git push`. No amend and no force-push.

## Out of Scope
- The JS CSV upload parser `parseCsvData` (manual "Load CSV") and `exportActiveCsv`. Both stay 6-column.
- Card 3 and Card 4, the poll controller (`pollOnce`, `fetchWindowsSince`, `mergeRecords`, `confirmAndResume`, `resumeFromTabVisibility`, `stopLivePolling`), the `maxAgeMs` logic, and the 5 deferred poll follow-ups.
- Any change to CSV files, firmware, ML, daemons, `functions/`, `.github/`.
- New charts or an rpm chart.

## Acceptance Criteria
- [x] `py build_clean_dashboard.py` succeeds. `node --check` passes on the extracted script of each of the four pages.
- [x] Python check (paste the output into HANDOFF): `load_csv('data/real_sessions/wash_cycle_2026-10-19_0911.csv')` returns rows of length 12. The row with `t == 3741072` has `[6] == 0.7185`, `[8] == 1.1455`, `[11] == 19.938` (after 4-decimal rounding) and `[7] == 'w'`.
- [x] Python check: for a legacy file (e.g. `wash_cycle_2026-10-17_0835.csv`), `load_csv` output is identical to the output before this change. Compare a JSON dump from `git stash` or the previous commit against the new one.
- [x] Page sizes before and after are reported. Each generated page stays under 800 KB.
- [x] Code inspection: in σ mode, no `9.81 + ` mapping of σ remains in `drawSpline`. The σ axis title reads `σ m/s²`. The 0.03 floor marker is present.
- [x] Code inspection: no rpm value is displayed. The dominant-frequency pill is gated on `VIB_RUNNING_THRESHOLD`.
- [x] Code inspection: the poll-controller functions and the `maxAgeMs` line are unchanged (only `windowToRecord` gained indices 8–11).
- [ ] Browser check on `historical.html` → session `wash_cycle_2026-10-19_0911`: UNVERIFIED (Headless CLI testing environment cannot launch desktop browser for visual observation).
- [x] The diff contains no secrets, and no file under `data/` is modified.
- [x] A new commit (not amended) is pushed. HANDOFF.md section 1 lists the hash and the verified and UNVERIFIED items.

## Risk Notes
- **Page weight:** `PRESET_SESSIONS_JSON` embeds every session in every page (~487 KB now). Firmware-07 rows grow from 6 to 12 values. Round to 4 decimals and keep `None` → `null`.
- **Mixed live buffer:** idle `/live` heartbeat records have σ (`vib_std`) but no per-axis σ. Card 2 must break the line on those points rather than dropping to 0.
- **`p[5]` may now be `null`** for firmware-07 rows with an empty power cell. Check `drawEnergy`, `applyRecord` and `exportActiveCsv` handle `null` (they appear to).
- **f-string braces:** double every JS brace.
- **Workflow overwrite:** edit only the build script.
- **Data integrity:** read CSVs only; never write to `data/real_sessions/`.
