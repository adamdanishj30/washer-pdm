# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Honest labels: remove fabricated Card 4 readouts, replace "Spike" with a vibration-based Idle/Running state
**Date:** 2026-10-19

## Objective
The dashboard shows only measured values or values directly computed from measurements. Every invented or unsupported claim is removed: estimated load in kg, "Motor Drag / Bearing Drag", ringgit cost, "P-F Health", "% Load", "parasitic friction", the 400 W "spin threshold", the fixed "normal baseline 120 RMS" and the "Spike" multiplier. The "Spike" pill becomes a provisional Idle/Running state based on dynamic vibration.

## Review verdict that produced this plan
**APPROVED** — live-poll controller, commit `5086684`. Reviewed by reading the current `build_clean_dashboard.py`. Not reviewed as a git diff: no shell access to the PC, and the commit was amended.
- Code matches the plan: cadence constants (10/25/30 s, nothing under 5 s); "2s" labels gone; epoch time base via `liveEpochMs`/`windowEpochMs`; no `uptime * 1000`; no `vdf` used as vibration; one source per state; `fetchWindowsSince` with a `$key` cursor (limit 120 for catch-up, 12 for the periodic fetch); `mergeRecords`; `stopLivePolling` reused everywhere; generation, session and mode guards on the periodic fetch; gap breaks in all four live stroke loops plus dashed markers; `afk_test_ms` hook. The MUST-STAY `maxAgeMs` line and the `if (d && (...)) {...} else {...}` structure are intact.
- Still operator-pending (not code defects): the DevTools checks for criteria 3 and 5–9, and the wash checks for criteria 4 and 13.
- Minor follow-ups, deferred to keep one task = one change set:
  1. Two `/api/live` requests at page load (`setViewMode('live')` and the `load` handler each start a poll).
  2. On AFK resume when the freeze happened while idle and a wash has since started, no 120-window catch-up runs; only the periodic 12-window fetch does.
  3. `windowToRecord` fills missing values with invented defaults (`rms` 120, `az` −9.81) instead of skipping the window.
  4. On `historical.html`, choosing "Live Rig Telemetry" shows a dead live view, because the page guard blocks polling. It should link to `index.html` instead.
  5. `afk_test_ms` below 10000 falls back to 5 min instead of clamping to 10000.

## Context
- Relevant files: `build_clean_dashboard.py` (only file to edit); the generated `index.html`, `dashboard.html`, `cloud_dashboard.html`, `historical.html` (rebuild only).
- Invariants (`docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md`):
  - Section 3 MUST STAY, honest labels: no RUL, P-F stage, ringgit cost or "health %" shown as measured facts. The ML only outputs an anomaly score and a cycle verdict. **Card 4 currently breaks this rule.**
  - Section 3 CAN CHANGE: the "Spike" label may be replaced by an idle/running label based on `vib_std`. The cut-off is provisional; retune it after the first firmware-07 wash.
  - Section 2: firmware's own vibration fallback threshold for "active" is `|a|` std > 0.08 m/s². Use the same 0.08 so the dashboard and firmware agree.
  - Section 3 MUST STAY: the `maxAgeMs` line and the online/offline `if` structure must stay; run `node --check` after edits.
  - Section 1: edit the build script only; exhaustive comments and section headers; one task = one change set.
- Evidence from `data/real_sessions/wash_cycle_2026-10-19_0911.csv`:
  - Final-spin power is about 340 W, so the "400 W centrifugal spin threshold" line is wrong for this machine.
  - Idle sound RMS is about 60–75 and wash about 150, so "normal baseline 120 RMS" is not a measured baseline.

## Implementation Steps
All edits are in `build_clean_dashboard.py`. **Keep JS braces doubled (`{{ }}`).**

1. **Card 4 header pills (HTML in `generate_html`).**
   - Delete the "Load: … kg (Auto)" pill (`energy-head-load`, `energy-head-class`) and the "Motor Drag" pill (`energy-head-drag`).
   - Keep "Active … W". Rename "Energy" to "Energy (shown span)" and keep `energy-head-kwh`.
2. **Card 4 stats bar (HTML).**
   - Delete "Cycle Est. Cost" (`energy-stat-cost`) and the whole "P-F Health" span (`energy-stat-pf`, including the initial text "100% [Point P: Optimal]").
   - Keep "Peak Power" and "Avg Active".
3. **Card 4 subtitle.** Change the static `sub-energy` text and the `hasRealPower` branch in `drawEnergy` to: "TP-Link Tapo P110 (1 Hz) • Active power and energy over the shown span". Remove "parasitic friction" and "motor load". Keep the not-tracked branch.
4. **`drawEnergy` logic.**
   - Delete the `estKg`/`lClass` block, the `elDrag` block, the `cycleCost` calculation and `elCost`, and the `elPf` block.
   - Delete the dashed 400 W spin guideline and its "CENTRIFUGAL SPIN THRESHOLD" badge.
   - Change the floating cursor pill to show only `"<W> W"` (no "% Load"). Keep "0.0 Watts (Not Tracked)".
   - Keep the kWh calculation and comment it as "average power × shown duration, an approximation from measured samples".
5. **Replace "Spike" with a State pill (Card 3 header HTML + `applyRecord`).**
   - Rename the pill text from "Spike:" to "State:" and keep the element id `timeline-head-spike` (or rename it consistently everywhere).
   - In `applyRecord`: if `rec[6]` (vib_std / `sm`) is a finite number, show `Running` when it is > `VIB_RUNNING_THRESHOLD` (new commented constant, `0.08` m/s²), else `Idle`. Otherwise show `—`.
   - Add a `title` tooltip: "Provisional: vibration std > 0.08 m/s² (same as firmware fallback); retune after first firmware-07 wash".
   - Remove `baselineRms`/`spikeRatio`.
6. **Card 3 area chart (`drawArea`).**
   - Delete the dashed 120 RMS baseline line and its "NORMAL BASELINE: 120 RMS" badge.
   - Change the floating cursor badge to show only `"<value> RMS"` (no "×" multiplier, no "+%").
   - Keep the PEAK line and badge, since peak is measured.
   - Keep the badge colour rule simple: one colour, or the existing `> 250` rule without any wording that implies abnormal.
7. **Invariants doc.** In `docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md` section 3 CAN CHANGE, append to the "Spike" bullet: `[DONE <date> in commit <hash>: replaced by provisional Idle/Running state, threshold 0.08 m/s²]`. No other edits to that file.
8. **Build and verify.** Run `py build_clean_dashboard.py`, then `node --check` on the extracted script of each of the four pages.
9. **Handoff.**
   - Replace section 1 of `docs/handoffs/HANDOFF.md` with this task's criteria matrix, using PASS / FAIL / UNVERIFIED and evidence, and keeping static and browser evidence separate.
   - Set this file's Status to DONE.
   - Commit with `fix(dashboard): remove unsupported Card 4 claims; replace Spike with Idle/Running`, then `git pull --rebase`, then `git push`.
   - **Do not amend or force-push a commit that is already pushed.** Make a new commit instead.

## Out of Scope
- The live-poll controller, including the 5 minor follow-ups listed above (separate task).
- Historical vibration view for firmware-07 files (`load_csv` reading `sm`, `sx/sy/sz`, `vdf`). That is the next planned task.
- Card 1/Card 2 chart logic, CSV import/export, the modal and banners.
- Firmware, ML, Python daemons, `functions/api/live.js`, `.github/workflows/`.
- `CLAUDE.md`, README and hackathon wording (docs claims are a separate task).

## Acceptance Criteria
- [ ] `py build_clean_dashboard.py` succeeds. `node --check` passes on the extracted script of each of the four pages.
- [ ] None of these strings appear in `build_clean_dashboard.py` or any generated page: `Cycle Est. Cost`, `RM 0.00`, `RM ${{`, `P-F Health`, `Point P`, `Motor Drag`, `Bearing Drag`, `estKg`, `% Load`, `parasitic`, `CENTRIFUGAL`, `SPIN THRESHOLD`, `NORMAL BASELINE`, `Spike:`, `spikeRatio`, `spikeMult`.
- [ ] Code inspection: `VIB_RUNNING_THRESHOLD = 0.08` exists with a comment that names it provisional and ties it to the firmware fallback. The State pill shows `—` when `rec[6]` is missing (legacy CSVs, historic mode).
- [ ] In a browser, on a firmware-07 historic session (`wash_cycle_2026-10-19_0911`) and on `index.html` (live, rig idle):
  - Card 4 shows only Active W, Energy (shown span), Peak Power and Avg Active.
  - Card 3 shows State and no baseline line.
  - No console errors.
  - Mark UNVERIFIED if not run in a browser.
- [ ] Code inspection: the `maxAgeMs` line and the online/offline `if` structure are unchanged, and the poll-controller functions (`pollOnce`, `fetchWindowsSince`, `mergeRecords`, `confirmAndResume`, `resumeFromTabVisibility`, `stopLivePolling`) are untouched.
- [ ] The INVARIANTS "Spike" bullet is annotated as DONE with the commit hash. No other invariant text changed.
- [ ] The diff contains no secrets.
- [ ] A new commit (not amended) is pushed. HANDOFF.md section 1 lists the hash and the verified and UNVERIFIED items.

## Risk Notes
- Deleting elements: every `getElementById` for a removed element must also be removed. The existing `if (el)` guards prevent crashes, but dead code should go.
- f-string braces: double every JS brace.
- Workflow overwrite: edit only the build script; the 30-min workflow regenerates the pages.
- The 0.08 m/s² threshold is provisional. Firmware-06 historic files carry no `vib_std`, so they correctly show `—`.
- Rewriting history: the previous task amended an already-pushed commit, which needs a force-push and can erase the 30-min workflow's commits on `main`. New commits only from now on.
