# Handoff to Claude (Architect)

**Plan:** ML: first honest nested-LOCO report on the firmware-07 washes (report only, deployed model untouched) + refresh the handoff facts  
**Date:** 2026-10-31 19:45, Asia/Kuala_Lumpur  
**Status:** COMPLETE  
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `3df211f` docs: plan firmware-07 LOCO report (Step 0)
- `88e367b` feat(firmware): reset reason and manual test mode (Step 0)
- `(to be committed)` docs(ml): firmware-07 nested LOCO report and handoff refresh (Step 6)
- **Branch:** `main`

---

## 1. Inventory of Sessions (`data/real_sessions/`)
A complete, non-destructive audit of all 28 CSV session files currently in `data/real_sessions/` was performed using `ml.feature_fusion.detect_schema` (windowed = schema 3 with $\ge 50\%$ valid `audio_kurtosis`, else legacy):

| File | Schema | Cols | Start Time (MYT) | Dur (min) | Windows | Max Power (W) | End Reason / Sync Note | Pair Relationship | Flags / Triage Decision |
|---|---|---|---|---|---|---|---|---|---|
| `wash_cycle_2026-10-11_1019.csv` | legacy | 6 | boot+5s | 35.9 | 422 | 0.0 | unknown | - | `pwr<50W` (0.0 W, pre-Tapo) |
| `wash_cycle_2026-10-12_1019.csv` | legacy | 6 | boot+10s | 102.8 | 1216 | 0.0 | unknown | - | `pwr<50W` (0.0 W, pre-Tapo) |
| `wash_cycle_2026-10-15_1020.csv` | legacy | 8 | boot+10s | 23.2 | 276 | 0.0 | unknown | - | `pwr<50W` (0.0 W, pre-Tapo) |
| `wash_cycle_2026-10-15_morning.csv` | legacy | 6 | boot+6s | 102.9 | 1216 | 0.0 | unknown | - | `pwr<50W` (0.0 W, pre-Tapo) |
| `wash_cycle_2026-10-16_0857.csv` | legacy | 8 | boot+10s | 74.8 | 857 | 773.5 | unknown | - | Clean (OK) |
| `wash_cycle_2026-10-17_0718.csv` | legacy | 8 | boot+11s | 75.7 | 854 | 565.1 | unknown | - | Clean (OK) |
| `wash_cycle_2026-10-17_0835.csv` | legacy | 8 | boot+11s | 70.3 | 792 | 5.0 | unknown | - | `pwr<50W` (5.0 W, Tapo comms drop) |
| `wash_cycle_2026-10-18_0516.csv` | legacy | 8 | boot+10s | 71.4 | 828 | 401.4 | adopted existing file | - | Clean (OK) |
| `wash_cycle_2026-10-19_0022.csv` | legacy | 8 | boot+6s | 14.3 | 167 | 1.3 | adopted existing verified file | - | `dur<15m` (14.3m); `pwr<50W` (1.3W); **manual_stop/test session** |
| `wash_cycle_2026-10-19_0911.csv` | windowed | 45 | 2026-10-19 09:11 | 65.7 | 786 | 419.8 | adopted existing verified file | Pair twin: `wash_cycle_2026-10-19_091125.csv` (8-col) | Clean (OK) |
| `wash_cycle_2026-10-19_091125.csv` | legacy | 8 | boot+8s | 65.7 | 786 | 419.8 | unknown | Pair twin: `wash_cycle_2026-10-19_0911.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-20_0744.csv` | windowed | 45 | 2026-10-20 07:43 | 80.7 | 965 | 2290.1 | adopted existing file | Pair twin: `wash_cycle_2026-10-20_074403.csv` (8-col) | Clean (OK, hot sanitise) |
| `wash_cycle_2026-10-20_074403.csv` | legacy | 8 | boot+9s | 80.7 | 965 | 2290.1 | unknown | Pair twin: `wash_cycle_2026-10-20_0744.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-21_0514.csv` | windowed | 45 | 2026-10-21 05:14 | 32.3 | 387 | 372.6 | adopted existing file | Pair twin: `wash_cycle_2026-10-21_051418.csv` (8-col) | Clean (OK, quick) |
| `wash_cycle_2026-10-21_051418.csv` | legacy | 8 | boot+8s | 32.3 | 387 | 372.6 | unknown | Pair twin: `wash_cycle_2026-10-21_0514.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-21_0631.csv` | windowed | 45 | 2026-10-21 06:31 | 29.1 | 348 | 302.4 | adopted existing verified file | Pair twin: `wash_cycle_2026-10-21_063130.csv` (8-col) | Clean (OK, quick) |
| `wash_cycle_2026-10-21_063130.csv` | legacy | 8 | boot+4615s | 29.1 | 348 | 302.4 | unknown | Pair twin: `wash_cycle_2026-10-21_0631.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-24_0631.csv` | windowed | 45 | 2026-10-24 06:31 | 75.3 | 900 | 451.2 | unknown | Pair twin: `wash_cycle_2026-10-24_063152.csv` (8-col) | Clean (OK) |
| `wash_cycle_2026-10-24_063152.csv` | legacy | 8 | boot+13s | 75.3 | 900 | 451.2 | unknown | Pair twin: `wash_cycle_2026-10-24_0631.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-27_0624.csv` | windowed | 45 | 2026-10-27 06:24 | 86.8 | 1038 | 606.8 | unknown | Pair twin: `wash_cycle_2026-10-27_062440.csv` (8-col) | Clean (OK) |
| `wash_cycle_2026-10-27_062440.csv` | legacy | 8 | boot+8s | 86.8 | 1038 | 606.8 | unknown | Pair twin: `wash_cycle_2026-10-27_0624.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-27_0918.csv` | windowed | 45 | 2026-10-27 09:18 | 91.9 | 1098 | 386.6 | unknown | Pair twin: `wash_cycle_2026-10-27_091820.csv` (8-col) | Clean (OK) |
| `wash_cycle_2026-10-27_091820.csv` | legacy | 8 | boot+8s | 91.9 | 1098 | 386.6 | unknown | Pair twin: `wash_cycle_2026-10-27_0918.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-28_0832.csv` | windowed | 45 | 2026-10-28 08:32 | 95.0 | 1135 | 324.1 | unknown | Pair twin: `wash_cycle_2026-10-28_083241.csv` (8-col) | Clean (OK) |
| `wash_cycle_2026-10-28_083241.csv` | legacy | 8 | boot+8s | 95.0 | 1135 | 324.1 | unknown | Pair twin: `wash_cycle_2026-10-28_0832.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-29_0625.csv` | windowed | 45 | 2026-10-29 06:25 | 65.7 | 786 | 519.9 | unknown | Pair twin: `wash_cycle_2026-10-29_062521.csv` (8-col) | Clean (OK) |
| `wash_cycle_2026-10-29_062521.csv` | legacy | 8 | boot+8s | 65.7 | 786 | 519.9 | unknown | Pair twin: `wash_cycle_2026-10-29_0625.csv` (45-col) | Clean (OK, legacy export) |
| `wash_cycle_2026-10-30_072649.csv` | legacy | 8 | boot+8s | 87.7 | 1048 | 519.3 | unknown | - | Clean (OK, 8-col only) |

### Key Observations from Inventory
1. **Windowed (Schema 3, 45-column) Cycles:** Exactly **9 unique cycles** exist (`wash_cycle_2026-10-19_0911`, `wash_cycle_2026-10-20_0744`, `wash_cycle_2026-10-21_0514`, `wash_cycle_2026-10-21_0631`, `wash_cycle_2026-10-24_0631`, `wash_cycle_2026-10-27_0624`, `wash_cycle_2026-10-27_0918`, `wash_cycle_2026-10-28_0832`, `wash_cycle_2026-10-29_0625`).
2. **Duplicate Export Pairs:** Every one of the 9 windowed sessions was also exported as an 8-column legacy twin file (`_HHMMSS.csv`). Because `train_unsupervised_pdm.py` filters strictly on detected schema (`windowed`), only the 45-column files are kept; zero twin legacy files were ingested, ensuring **no wash cycle was counted twice**.
3. **Flagged Files:** 
   - `wash_cycle_2026-10-19_0022.csv`: flagged as a test session (14.3 min duration, 1.3 W max power, manual stop at midnight).
   - 5 unmetered/aborted runs flagged for power < 50 W (`1011_1019`, `1012_1019`, `1015_1020`, `1015_morning`, `1017_0835`).
   - None of the 9 windowed cycles were flagged; all 9 windowed cycles represent valid, full wash sessions (>15 min, 302–2290 W max power).

---

## 2. Nested Leave-One-Cycle-Out (LOCO) Evaluation Results
Ran `py ml/train_unsupervised_pdm.py --schema windowed --models-dir ml/outputs/fw07_loco_2026-10-31` with the unchanged evaluation protocol:
- **Output Directory:** `ml/outputs/fw07_loco_2026-10-31/` (completely isolated; `ml/models/` deployed model is untouched).
- **Data:** 9 healthy cycles, 7,443 windows of 5.024 s. Effective sample size $N = 9$. Pilot evaluation ($N < 20$).
- **SmartThings Labels:** 0% on recorded cycles (API 403) $\rightarrow$ pooled cycle model (not phase-conditioned).
- **Vibration Orientation:** Gravity shifted up to 15.46 m/s² between cycle mountings $\rightarrow$ orientation-free features used.

### Headline Results: False Alarms on Healthy Cycles
| Model | False-Alarm Cycles | 95% Upper Bound (Rule of Three) | Healthy Windows Red | Amber |
|---|---|---|---|---|
| **Mahalanobis** | **2 / 9** | **55%** | 0.26% | 5.11% |
| **Isolation Forest** | **2 / 9** | **55%** | 2.44% | 1.57% |
| **One-Class SVM** | **2 / 9** | **55%** | 0.11% | 4.42% |

*False Alarm Root Cause Analysis:*
- **False Alarm 1 (`wash_cycle_2026-10-20_0744`):** Flagged via electrical power indicator. This is the only 60°C hot sanitise cycle in the dataset (heater pulled 2,290 W for 11.9 minutes). Held-out from cold cycles, its power distribution is an outlier.
- **False Alarm 2 (`wash_cycle_2026-10-27_0624`):** Flagged via overall + vibration indicator. Experienced strong spin extraction dynamics with peak power 606.8 W and dynamic vibration magnitude reaching 5.5 m/s².

### Headline Results: Injected Fault Sensitivity (Mahalanobis)
- **Acoustic Impulsive Fault (`bearing_impulsive`):** **Min detectable reached at 1.0 $\times$ hp RMS** (Severity 4 achieved 78% clean detection with a median detection time of 7.5 min; Severity 3 achieved 44% in 19.7 min).
- **Vibration Faults (`suspension_rocking`, `imbalance_1x`):** Min detectable **not reached** (44% clean detection at max Severity 4; protocol requires $\ge 70\%$ for detection threshold).
- **Electrical Drag Fault (`power_drag`):** Min detectable **not reached** (11% detection across all severities).

---

## 3. Facts Refreshed in `docs/handoffs/current_state_and_scale_up_handoff.md`
- "Last updated" set to today: **2026-10-31**.
- Updated firmware-07 cycle count to **9 windowed cycles** in §2 and §5.
- Documented SmartThings 403 token expiration and resulting pooled model constraint in §3.
- Added firmware-07 headline numbers under §3 alongside the legacy results.
- Removed dead link to `TODO_BACKGROUND_NOISE_AND_DATA_COLLECTION.md` in §4 item 3.
- Marked down-weighting `ab0` and multimodal gating as **WAITING ON ADAM (changes MUST-STAY ML design)**.
- Linked `docs/hardware_guides/PARTS_TO_PURCHASE.md` in §6.

---

## 4. Open UNVERIFIED Items (carried forward)
1. Apps Script trigger (legacy sync mechanism).
2. Workflow run with GitHub secrets (Tapo / Firebase secrets rotation pending).
3. Real-wash session start / END marker / archive on hardware.
4. Active-wash adaptive polling verification during a live wash.
5. Session-change reset in web dashboard during live wash transition.
6. `historical.html` live check in browser.
7. DevTools network check (no excessive polling or Firebase quota consumption).
8. `/window.json` and `WHO_AM_I` 0x75 register read quirk on hardware.
9. Real weighed laundry load entry in `data/session_context.csv` (requires Adam to weigh a load).

---

## 5. Files Changed
- `docs/handoffs/PLAN.md`: Marked status DONE.
- `docs/handoffs/current_state_and_scale_up_handoff.md`: Updated cycle counts, report links, and dead link fixes.
- `docs/handoffs/HANDOFF.md`: Updated with full inventory, LOCO results, and carried-forward unverified items.
- `docs/handoffs/last_diff.patch`: Unified diff of current documentation changes.
- `ml/outputs/fw07_loco_2026-10-31/loco_report.md`: Generated firmware-07 nested LOCO evaluation report.
- `ml/outputs/fw07_loco_2026-10-31/loco_report.json`: JSON machine-readable evaluation results.

## Excluded from Commit
- `ml/outputs/fw07_loco_2026-10-31/pdm_detector.joblib` (binary model artifact; per Step 6, commit only `.md` and `.json`).
- `ml/outputs/fw07_loco_2026-10-31/pdm_detector_meta.json`.

---

## 6. Acceptance Criteria Verification
- [x] PLAN.md committed before any other git command (`3df211f`); 25 Oct firmware commit status reported (`88e367b`).
- [x] HANDOFF has the inventory table; duplicate pairs and suspected test sessions are marked; no wash counted twice.
- [x] Report generated in `ml/outputs/fw07_loco_2026-10-31/` with schema `windowed`; `git diff --stat ml/models/` is empty.
- [x] `git diff` shows no change to any `.py` under `ml/` or to any file in `data/real_sessions/`.
- [x] Report states n cycles (9), false-alarm cycles (2 / 9) and the 95% upper bound (55%); labelled pilot because n < 20.
- [x] Handoff doc updated as in step 4; dead link gone; gating step marked WAITING ON ADAM.
- [x] Existing tests still pass (`test_dsp_parity.py` skipped g++, `test_pipeline_synthetic.py` PASS, `test_session_export.py` PASS, `test_daemon_offline.py` PASS).
- [ ] Pushed; hash reported (Step 6).

---

## 7. Tests Run
- `py ml/train_unsupervised_pdm.py --schema windowed --models-dir ml/outputs/fw07_loco_2026-10-31` — **PASS**
- `py ml/tests/test_pipeline_synthetic.py` — **PASS**
- `py firmware/tests/test_session_export.py` — **PASS**
- `py firmware/tests/test_daemon_offline.py` — **PASS**
