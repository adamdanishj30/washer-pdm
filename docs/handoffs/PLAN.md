# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Stop the synthetic ML test writing to the real `ml/models/`; clarify the energy note
**Date:** 2026-10-21

## Step 0
Before ANY other git command (no pull, stash, checkout or reset first): `git add docs/handoffs/PLAN.md` and commit `docs: plan isolate synthetic test outputs`. Then `git pull --rebase` (no `--autostash`).

## Review verdict that produced this plan
APPROVED: `06595ff`, `f576438` (energy per wash). You archived the plan as `PLAN_DONE_2026-10-21_energy_per_wash.md`.

Checked by Claude: `energy_kwh` / `peak_power_w` computed in `analyze_session_csv()` with the existing `dt_seconds`; `None` → `n/a` for all 6 No power data rows; classes, member lists and counters unchanged in the regenerated report; script values match Claude's within 0.001 kWh (18 Oct 0.106 vs 0.107 is the legacy 5.0 s step, accepted); the new test uses a temp dir; guide §4 row and §3 Say line carry the "one household washer" rule. Your diagnosis of the `loco_report.md` mtime is correct and is the task below.

## Objective
`ml/tests/test_pipeline_synthetic.py` runs `train_unsupervised_pdm.py`, which writes the synthetic model and LOCO report over the REAL `ml/models/pdm_detector.joblib`, `pdm_detector_meta.json` and `loco_report.{md,json}`, then restores the old bytes in `finally`. While the test runs, the deployed detector is a synthetic one, and if the process is killed before `finally`, the real artifacts are lost. Make the test write only to a temp dir.

Also, one wording fix: the report says energy comes from "1 Hz smart-plug power averaged per window", which is true for firmware 07 only. Legacy rows are a single power snapshot every 5 s, and "Peak W" is the highest per-row value, not an instantaneous peak.

## Context
- `ml/train_unsupervised_pdm.py`: `MODELS_DIR`, `ARTIFACT`, `META` are module constants (lines ~53–55). It writes in lines ~122–144. argparse is in `main()` (~line 92) and already has `--data-dir`.
- `ml/tests/test_pipeline_synthetic.py` lines ~63–86: backup/restore block, reads `models / "loco_report.json"` and `models / "pdm_detector_meta.json"`.
- Check whether any other file imports `MODELS_DIR`, `ARTIFACT` or `META` from `train_unsupervised_pdm` (grep `ml/` and `firmware/`). Their default behaviour must not change.

## Implementation Steps
1. `train_unsupervised_pdm.py`: add `--models-dir` (default: the current `ml/models` path). Derive the artifact, meta and report paths from it inside `main()`, and use those for every write and for the `[SAVE]` print. Keep the module constants as defaults, so imports elsewhere still work. Make no change to training, evaluation or thresholds.
2. `test_pipeline_synthetic.py`: pass `--models-dir <tempdir>/models`, read both JSONs from there, and delete the backup/restore block. Keep every assertion unchanged.
3. `ml/cycle_signature_report.py`: replace the energy note with: "Energy is integrated from the smart-plug power on each row: on firmware 07 a per-window mean of 1 Hz readings, on legacy runs a single reading every 5 s. Peak W is the highest row value, not an instantaneous peak. This is the washer's total electrical draw, not a fault signal." Regenerate `ml/models/cycle_signature_report.md`. Only that note may change in the diff, plus the Generated line.
4. Proof: before and after running the synthetic test, record the size and mtime of every file in `ml/models/`, and put both lists in HANDOFF (they must be identical). Run all tests.
5. HANDOFF with the full template plus the carried-forward UNVERIFIED list. `last_diff.patch` per rule 6. Commit `ml: synthetic test writes to temp models dir; energy note wording`. Pull --rebase (no autostash), push.

## Out of Scope
Model training logic, thresholds, features, retraining on real data, `loco_report.md` content, classification rules, dashboard, firmware, proposal / `Hackathon/` / video files, `data/`.

## Acceptance Criteria
- [ ] PLAN.md committed before any other git command.
- [ ] `py ml/train_unsupervised_pdm.py --help` shows `--models-dir`; with no flag, it writes to `ml/models/` exactly as before.
- [ ] `test_pipeline_synthetic.py` has no backup/restore and passes. The `ml/models/` size and mtime list is identical before and after the run.
- [ ] Every test assertion is unchanged (diff shows only path changes in the test).
- [ ] The cycle signature report diff shows only the new energy note and the Generated line.
- [ ] Pushed; hashes reported.

## Queue (Claude will plan these next; do not start)
1. **Firmware: report reset reason** (+ `epochMs()` jitter 2.7–3.8 s). 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot. Needs a flash, so Adam confirms first.
2. **ML: programme-aware evaluation** once each signature class has ≥ 3 firmware-07 cycles. No per-cycle normalisation.
3. **Dashboard page budget** (787.7 KB of 800 KB) before any new dashboard feature.
4. **Retire or clearly mark `firmware/capture_pdm_dataset.py`** (still computes a load guess and "parasitic drag"; production archiving no longer uses it). Antigravity suggestion, 21 Oct.
5. **Proposal submission files** (track "02 Circular Economy" hits, session counts, energy-per-wash line, other firmware-05-era claims such as `/live.json` at 1 Hz): Adam's `Hackathon/NEEDS_CHANGING.md` batch, only when he says go.
