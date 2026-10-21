# Plan for Antigravity

**Status:** READY  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Measured energy per wash: add kWh and peak W to the cycle signature report and the writing guide
**Date:** 2026-10-21

## Step 0
`git pull` first (do NOT use `--autostash`), then commit this PLAN.md: `docs: plan energy per wash`.

## Review verdict that produced this plan
APPROVED: `4f4f9ea`, `6cdff0f`, `8439d1b`, `6739fd6` (writing guide facts as of 21 Oct). You archived the plan as `PLAN_DONE_2026-10-21_writing_guide_facts.md`.

Checked by Claude against the data: 13 files in `data/real_sessions/`; firmware-07 windows 786 / 965 / 387 / 348; 9,114 training rows; LOCO set = the 8 legacy cycles you listed (they sum to the 6,461 windows in `loco_report.md`); every row of the 4 firmware-07 CSVs is `phase = none` / `fallback`; final-spin `vib_dom_hz` mode is 19.9 Hz (19, 20 Oct) and 20.0 Hz (both 21 Oct); wash-type counts match `cycle_signature_report.md`; `load_class` / `MEDIUM` gone; UDP / 50 Hz under Not allowed; current-state sentence agrees. Your mtime explanation (autostash + stash apply, contents identical) is accepted.

One question to answer in this HANDOFF: `ml/models/loco_report.md` got a new mtime at 18:23 MYT during your task, and its contents look unchanged. Say what wrote it (a test, a training run, a stash?). If a test writes to the real `ml/models/` report, list that as a bug in Suggestions and do not fix it in this task.

## Objective
Our track is Energy Efficiency, and the guide's facts refresh dropped the only measured energy numbers we had (20 Oct hot wash peak 2,290 W, 0.55 kWh; 19 Oct peak 420 W, 0.11 kWh). Make energy per wash a computed, sourced number for every metered cycle, so the pitch can say what the rig actually measured: a heated wash uses about five times the energy of a cold one. This is measured on one household washer; it is not an AC or township saving.

## Context
- `ml/cycle_signature_report.py` already reads `power_w` per row and uses `dt_seconds = 5.024` (firmware 07) or `5.0` (legacy) in `analyze_session_csv()`. Report is `ml/models/cycle_signature_report.md`.
- Claude's own check (Σ `power_w` × dt ÷ 3.6e6): 16 Oct 0.101, 17 Oct 07:18 0.113, 18 Oct 0.107, 19 Oct 0.112, 20 Oct 0.549, 21 Oct 05:14 0.036, 21 Oct 06:31 0.029 kWh; peak `power_w` 774 / 565 / 401 / 420 / 2,290 / 373 / 302 W. Your numbers must come from the script; report any difference over 0.005 kWh.
- No-power-data cycles (max power < 50 W) get `n/a`, never 0.

## Implementation Steps
1. In `analyze_session_csv()`, add `energy_kwh` (Σ `power_w` × `dt_seconds` ÷ 3,600,000, rounded to 3 dp) and `peak_power_w` (max `power_w`, rounded to whole W). Both `None` for the No power data class. Do not change any classification rule or constant.
2. Add two columns, "Energy (kWh)" and "Peak W", to the §2 table of the generated report, plus a short per-class line under the class list (e.g. "Long cold: 0.10–0.11 kWh per wash"). State in the report that energy is integrated from the 1 Hz smart-plug power averaged per window, and that it is the washer's total draw, not a fault signal.
3. Add `ml/tests/test_cycle_signature_energy.py`: a synthetic in-memory or temp-dir CSV (never `data/`) with constant 1,000 W for 720 windows at 5.0 s → 1.000 kWh and peak 1,000 W; a < 50 W file → `None`. Run it and the existing tests.
4. Regenerate `ml/models/cycle_signature_report.md` with `py ml/cycle_signature_report.py`.
5. In `docs/proposals/PROPOSAL_WRITING_GUIDE.md` §4 add a row **"Energy per wash (measured)"**: per-class ranges from the report (Quick, Long cold, Long hot), the ratio hot vs cold rounded to a whole number, source `ml/models/cycle_signature_report.md`, and the rule "one household washer, measured by the smart plug; never present as an AC, township or fault saving". Add to the §3 Say column: "A heated wash used about N× the energy of a cold wash on our rig (measured)".
6. HANDOFF with the full template, a table of each cycle's kWh and peak W (script vs Claude's figures above), the loco_report answer, and the carried-forward UNVERIFIED list. `last_diff.patch` per rule 6. Commit `ml: energy per wash in cycle signature report; guide energy row`. Pull --rebase (no autostash), push.

## Out of Scope
Classification rules and constants, ML models and `loco_report.md`, training dataset rebuild, dashboard, firmware, proposal `.md`/PDF/HTML, `generate_*.py`, `Hackathon/`, video files, `data/` files (read only).

## Acceptance Criteria
- [ ] PLAN.md committed first, after a plain `git pull`.
- [ ] Report §2 has "Energy (kWh)" and "Peak W" for all 13 sessions; the 6 No power data rows show `n/a`.
- [ ] Classes and member lists in the report are unchanged from the previous version (diff shows only the new columns and lines).
- [ ] Script values match Claude's figures within 0.005 kWh and 1 W, or each difference is explained.
- [ ] New test passes and writes nothing under `data/` or `ml/models/`; existing tests still pass.
- [ ] Guide §4 energy row and §3 Say line exist, are sourced to the report and carry the "one household washer" rule.
- [ ] HANDOFF answers what rewrote `loco_report.md`.
- [ ] Pushed; hashes reported.

## Queue (Claude will plan these next; do not start)
1. **Firmware: report reset reason** (+ `epochMs()` jitter 2.7–3.8 s). 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot. Needs a flash, so Adam confirms first.
2. **ML: programme-aware evaluation** once each signature class has ≥ 3 firmware-07 cycles. No per-cycle normalisation.
3. **Dashboard page budget** (787.7 KB of 800 KB) before any new dashboard feature.
4. **Retire or clearly mark `firmware/capture_pdm_dataset.py`** (still computes a load guess and "parasitic drag"; production archiving no longer uses it). Antigravity suggestion, 21 Oct.
5. **Proposal submission files** (track "02 Circular Economy" hits, session counts, other firmware-05-era claims such as `/live.json` at 1 Hz): Adam's `Hackathon/NEEDS_CHANGING.md` batch, only when he says go.
