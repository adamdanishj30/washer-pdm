# Handoff to Claude (Architect)

**Plan:** Stop the synthetic ML test writing to the real `ml/models/`; clarify the energy note  
**Date:** 2026-10-21 19:35, Asia/Kuala_Lumpur  
**Status:** COMPLETE  
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `ef627d7` docs: plan isolate synthetic test outputs (Step 0)
- `f40d373` ml: synthetic test writes to temp models dir; energy note wording
- **Branch:** main (pushed to origin/main)

## What Changed
- **Step 0 (Plan Commitment & Rebase):**
  - Committed `docs/handoffs/PLAN.md` before any other git operations (`ef627d7`). Rebase verified up to date with `origin/main`.
- **Step 1 (`ml/train_unsupervised_pdm.py` - `--models-dir` CLI Argument):**
  - Added `--models-dir` argument to `argparse` in `main()` with default set to the module constant `MODELS_DIR` (`ml/models`).
  - Derived `artifact_path`, `meta_path`, `loco_json_path`, and `loco_md_path` dynamically from `models_dir`.
  - Used these derived paths for all file writes (`loco_report.json`, `loco_report.md`, `pdm_detector.joblib`, `pdm_detector_meta.json`).
  - Updated `[SAVE]` prints to format relative paths when inside `BASE_DIR`, and fallback to paths when pointing to external temp directories without crashing.
  - Kept module constants `MODELS_DIR`, `ARTIFACT`, `META` intact at the top of the file so any external module imports remain unaffected.
  - No changes made to training logic, evaluation, or thresholds.
- **Step 2 (`ml/tests/test_pipeline_synthetic.py` - Temp Directory Isolation):**
  - Replaced target output directory with `<tempdir>/models` (`models = d / "models"`).
  - Passed `--models-dir str(models)` to the subprocess executing `train_unsupervised_pdm.py`.
  - Read `loco_report.json` and `pdm_detector_meta.json` directly from the temp models directory.
  - Removed the `backup` and `finally: p.write_bytes(b)` dictionary and restore block entirely.
  - Kept every test assertion completely unchanged.
- **Step 3 (`ml/cycle_signature_report.py` & `ml/models/cycle_signature_report.md` - Energy Note Wording):**
  - Replaced the energy note on line 496 of `ml/cycle_signature_report.py` with:
    `"Energy is integrated from the smart-plug power on each row: on firmware 07 a per-window mean of 1 Hz readings, on legacy runs a single reading every 5 s. Peak W is the highest row value, not an instantaneous peak. This is the washer's total electrical draw, not a fault signal."`
  - Regenerated `ml/models/cycle_signature_report.md`. `git diff` confirms that only the `Generated:` timestamp and the energy note changed.
- **Step 4 (Proof of Real Model Isolation):**
  - Recorded file sizes and nanosecond modification timestamps (`st_mtime_ns`) of all files in `ml/models/` before and after running `test_pipeline_synthetic.py`.
  - Verified they are 100% identical (see proof table below).

---

## Proof: `ml/models/` Immutability Across Synthetic Test Execution

| File Name | Size (Bytes) Before | Size (Bytes) After | mtime_ns Before | mtime_ns After | Match Status |
|---|---|---|---|---|---|
| `cycle_signature_report.md` | 7,401 | 7,401 | 1792582211537000000 | 1792582211537000000 | Identical |
| `desktop.ini` | 352 | 352 | 1792464240904223800 | 1792464240904223800 | Identical |
| `loco_report.json` | 13,701 | 13,701 | 1792578190031000000 | 1792578190031000000 | Identical |
| `loco_report.md` | 3,353 | 3,353 | 1792578190005000000 | 1792578190005000000 | Identical |
| `pdm_detector.joblib` | 183,735 | 183,735 | 1792578189978000000 | 1792578189978000000 | Identical |
| `pdm_detector_meta.json` | 1,783 | 1,783 | 1792578189993000000 | 1792578189993000000 | Identical |

*All 6 files retained their exact byte sizes and nanosecond filesystem timestamps. The real production model artifacts and reports were completely untouched.*

---

## Files Changed
- `ml/train_unsupervised_pdm.py`: added `--models-dir` argument; derived write/print paths in `main()`.
- `ml/tests/test_pipeline_synthetic.py`: directed outputs to temp directory; removed backup/restore block; assertions unchanged.
- `ml/cycle_signature_report.py`: clarified energy calculation note for firmware-07 vs legacy rows and Peak W meaning.
- `ml/models/cycle_signature_report.md`: regenerated markdown report reflecting the updated note.
- `docs/handoffs/PLAN.md`: marked `Status: DONE`.
- `docs/handoffs/PLAN_DONE_2026-10-21_isolate_synthetic_test.md`: archived completed plan.
- `docs/handoffs/last_diff.patch`: 15.5 KB UTF-8 git diff patch.
- `docs/handoffs/HANDOFF.md`: updated handoff documentation.

## Excluded from Patch
- `docs/handoffs/PLAN.md` (read directly by Claude per Rule 6)
- `docs/handoffs/HANDOFF.md` (read directly by Claude per Rule 6)
- `docs/handoffs/last_diff.patch` (self-referential)

## Acceptance Criteria
- [x] PLAN.md committed before any other git command — verified in commit `ef627d7`.
- [x] `py ml/train_unsupervised_pdm.py --help` shows `--models-dir`; with no flag, it writes to `ml/models/` exactly as before — verified via `--help` output and default path checks.
- [x] `test_pipeline_synthetic.py` has no backup/restore and passes. The `ml/models/` size and mtime list is identical before and after the run — verified: test passes with exit code 0, proof table shows 100% identical sizes and nanosecond timestamps.
- [x] Every test assertion is unchanged (diff shows only path changes in the test) — verified via diff inspection.
- [x] The cycle signature report diff shows only the new energy note and the Generated line — verified via `git diff ml/models/cycle_signature_report.md`.
- [x] Pushed; hashes reported — verified: pushed `ef627d7..f40d373` to `origin/main`.

## Tests Run
- `py ml/train_unsupervised_pdm.py --help` — PASS (shows `--models-dir`).
- `py -m py_compile ml/train_unsupervised_pdm.py ml/tests/test_pipeline_synthetic.py ml/cycle_signature_report.py` — PASS.
- `py ml/tests/test_pipeline_synthetic.py` — PASS (`[PASS] windowed pipeline mechanics`, 0 errors).
- `py ml/tests/test_dsp_parity.py` — SKIP (no C++ compiler on Windows PATH).
- `py ml/tests/test_cycle_signature_energy.py` — PASS (4/4 tests pass).
- `py firmware/tests/test_session_export.py` — PASS.
- `py firmware/tests/test_daemon_offline.py` — PASS.
- `py ml/predict_pdm.py --file data/real_sessions/wash_cycle_2026-10-21_0631.csv` — PASS (scored with production Mahalanobis detector).

## Invariants Check
- INVARIANTS §1 (Golden rules): No data overwritten in `data/real_sessions/`; secrets untouched; honest reporting preserved.
- INVARIANTS §2 (Firmware): Untouched.
- INVARIANTS §3 (Dashboard): Untouched.
- INVARIANTS §4 (Data & ML): Evaluation protocol and models preserved; no retraining of production artifacts on real data; legacy vs fw-07 schema separation preserved.
- INVARIANTS §5 (Automation & Secrets): No secrets committed or exposed.

## Blocked / Questions
- None.

## Suggestions for Claude
1. **Queue items (carried forward):**
   - Firmware: report reset reason (+ `epochMs()` jitter 2.7–3.8 s). 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot.
   - ML: programme-aware evaluation once each signature class has $\ge 3$ firmware-07 cycles. No per-cycle normalisation.
   - Dashboard page budget (787.7 KB of 800 KB) before any new dashboard feature.
   - Retire or clearly mark `firmware/capture_pdm_dataset.py` (still computes a load guess and "parasitic drag").
   - Proposal submission files: Adam's `Hackathon/NEEDS_CHANGING.md` batch.

## Open UNVERIFIED Items (carried forward)
1. Apps Script trigger (legacy sync mechanism).
2. Workflow run with GitHub secrets (Tapo / Firebase secrets rotation pending).
3. Real-wash session start / END marker / archive on hardware.
4. Active-wash adaptive polling verification during a live wash.
5. Session-change reset in web dashboard during live wash transition.
6. `historical.html` visual check in browser (done headlessly on 2026-10-21 16:38, live user confirmation pending).
7. DevTools network check (no excessive polling or Firebase quota consumption).
8. `/window.json` and `WHO_AM_I` 0x75 register read quirk on hardware.
9. Real weighed laundry load entry in `data/session_context.csv` (requires Adam to weigh a load and record values).

## Ready for Next Plan
- [x] Antigravity is stopped and waiting for the next plan in `docs/handoffs/PLAN.md`.
