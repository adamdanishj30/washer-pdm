# Handoff to Claude (Architect)

**Plan:** Writing guide §4 and current-state doc: bring facts up to 21 Oct (4 firmware-07 cycles, inferred wash types, no load guess)
**Date:** 2026-10-21 18:25, Asia/Kuala_Lumpur
**Status:** COMPLETE
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `4f4f9ea` docs: plan writing guide facts refresh (Step 0)
- `6cdff0f` docs: current-state note (external edit)
- `8439d1b` docs: writing guide facts as of 21 Oct
- Pending: `docs(handoff): complete writing guide facts refresh`
- **Branch:** main

## What Changed
- **Step 0 (Plan Commitment & External Edit):**
  - Committed `docs/handoffs/PLAN.md` immediately (`4f4f9ea`).
  - Separately committed the external Drive modification to `docs/handoffs/current_state_and_scale_up_handoff.md` (`6cdff0f`), recording its diff below.
- **Step 1 (Writing Guide §4 Facts Update from Repository Files):**
  - Updated "Wash sessions recorded" to 13 (8 legacy LOCO evaluation cycles, 4 complete firmware-07 cycles, 1 short un-evaluated cycle).
  - Updated "Firmware-07 cycles" to 4 complete cycles (786, 965, 387, 348 windows; 2,486 total). Confirmed model in `ml/models/loco_report.md` is evaluated on legacy cycles and has not been retrained on firmware-07 data yet.
  - Verified `phase` and `phase_source` across all 4 firmware-07 CSVs: all rows contain `phase = none` and `phase_source = fallback`. Stated "planned".
  - Replaced "Programme / load per cycle" with two dedicated rows:
    - **"Wash type"**: classes inferred from power (4 Long cold, 1 Long hot, 2 Quick, 6 No power data) sourced from `ml/models/cycle_signature_report.md`, with the rule "always say 'inferred from power'; programme names are not logged".
    - **"Load weight"**: not recorded (`load_kg` is blank in `data/session_context.csv` across all cycles until a physical weighed load is entered).
    - Removed every occurrence of `load_class` and `MEDIUM` from the guide (`grep` returns 0 hits).
  - Updated "Training-ready rows" to 9,114 (verified from `data/pdm_ml_standardized_training_dataset.csv`; noted "(was 8,379 before the two 21 Oct quick washes)").
  - Extended "Drum frequency in final spin" to confirm ≈ 20 Hz (19.9–20.0 Hz ≈ 1,200 rpm) across all 4 firmware-07 cycles based on `vib_dom_hz` in the CSVs and `cycle_signature_report.md` §3.
  - Added row **"Local fail-safe (firmware 07)"**: HTTP on home network serving `/window.json`, `/accel.csv` (2.56 s of raw 200 Hz vibration), and `/clip.wav`, marked reachability `[UNVERIFIED]`.
  - Added "UDP broadcast" and "50 Hz vibration" to "Not allowed".
- **Step 2 (Writing Guide §3 Say/Plan Table):**
  - Updated cell from "11 wash sessions recorded, 8,379 data rows" to "13 wash sessions recorded, 9,114 data rows".
  - Added to Say column: "The website labels each wash type, inferred from power".
  - Clarified Plan column: "Phase badge on the website (wash / rinse / spin; planned once machine state is saved with the data, distinct from the wash-type badge)".
- **Step 3 (Current-State Doc Reality Checks):**
  - Updated line ~50 reality checks sentence to 13 sessions, 9,114 training rows, 4 firmware-07 cycles, wash types inferred from power (4 Long cold, 1 Long hot, 2 Quick, 6 No power data), and load not recorded.
  - Updated "Last updated" line to 2026-10-21. Zero other changes made.
- **Explanation for File Mtimes at 18:01 MYT:**
  - During the previous session's push preparation, a `git pull --rebase --autostash` command stashed working tree files. When `git stash apply 72833de` was executed, git touched and wrote back `wash_cycle_2026-10-15_1020.csv`, `wash_cycle_2026-10-16_0857.csv`, `wash_cycle_2026-10-17_0718.csv`, and `data/pdm_ml_standardized_training_dataset.csv`. All file contents were confirmed byte-identical to prior commits; no data or numbers were altered.

## External Edit Diff (`6cdff0f`)
```diff
diff --git a/docs/handoffs/current_state_and_scale_up_handoff.md b/docs/handoffs/current_state_and_scale_up_handoff.md
--- a/docs/handoffs/current_state_and_scale_up_handoff.md
+++ b/docs/handoffs/current_state_and_scale_up_handoff.md
@@ -47,6 +47,8 @@ Current real-data result (legacy snapshot schema, Mahalanobis, nested LOCO): 0/8
 ## 5. Hackathon story [PROPOSAL]
 Pitch what is true: a low-cost, non-destructive multimodal edge sensor that learns each machine's own healthy baseline and flags sustained departures, with every claim backed by a leave-one-cycle-out report. Do not claim remaining-life or cost savings yet; frame them as what the platform enables once degradation data is collected. Strong, defensible points: on-device DSP (raw audio never leaves the device), tiny Firebase footprint, per-asset baselines (no labelled faults needed), transparent per-feature explanations.
 
+Sources of truth for pitch material: event facts in `Hackathon/SDP_HACKATHON_BRIEFING_SUMMARY.md`, allowed numbers in `docs/proposals/PROPOSAL_WRITING_GUIDE.md` §4, video script and deck outline in `Hackathon/VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md`. Reality checks (synced 2026-10-20): pilot kit RM 169.68 net paid (node RM 131.07; receipts in `Hackathon/HARDWARE_BOM_AND_COST_BREAKDOWN.md`; sub-RM 50 is unvalidated); 11 sessions are recorded as of 20 Oct (8,379 training rows), of which 8 healthy legacy cycles form the LOCO set and 2 are complete firmware-07 cycles (19 and 20 Oct; neither has SmartThings phase labels, programme and load not logged); the evaluated model is pooled (not phase-conditioned); the mount is VHB tape (magnetic is a proposal); a firmware-07 window record is 45 columns with 32 signal features.
+
 ## 6. From rig to mass-producible prototype [PROPOSAL]
```

## Facts Changed Summary Table

| Fact / Item | Old Value | New Value | Source File |
|---|---|---|---|
| Wash sessions recorded (§3 & §4) | 11 (as of 20 Oct): 8 older healthy LOCO, 2 complete fw-07, 1 short older session | 13 (as of 21 Oct): 8 older healthy LOCO, 4 complete fw-07, 1 short older session | `data/real_sessions/`, `ml/models/loco_report.md` |
| Firmware-07 cycles (§4) | 2 complete (786 and 965 windows) | 4 complete (786, 965, 387, 348 windows; 2,486 total). Evaluated model is trained on 8 legacy cycles, not retrained on fw-07 yet | `data/real_sessions/`, `ml/models/loco_report.md` |
| Machine state (phase labels) (§4) | None saved yet across 2 fw-07 cycles | None saved yet: every row across all 4 fw-07 cycles has `phase = none`, `phase_source = fallback` | `data/real_sessions/` (4 fw-07 CSVs) |
| Wash type (replaces Programme / load per cycle) (§4) | Programme / load per cycle: Not recorded; `load_class` a constant `MEDIUM` | Classes inferred from power: Long cold (4), Long hot (1), Quick (2), No power data (6). Always say "inferred from power" | `ml/models/cycle_signature_report.md` |
| Load weight (new row) (§4) | (bundled in old row with `load_class MEDIUM`) | Not recorded (`load_kg` is blank in `data/session_context.csv` across all cycles until a physical weighed load is entered) | `data/session_context.csv` |
| Training-ready rows (§3 & §4) | 8,379 (rebuilt 20 Oct 11:28; was 7,414) | 9,114 (as of 21 Oct; was 8,379 before the two 21 Oct quick washes) | `data/pdm_ml_standardized_training_dataset.csv` (`session_source` counts) |
| Drum frequency in final spin (§4) | 19.9 Hz ≈ 1,200 rpm, in both firmware-07 cycles (19 and 20 Oct) | ≈ 20 Hz (19.9–20.0 Hz ≈ 1,200 rpm), confirmed across all 4 firmware-07 cycles (19.9 Hz on 19 and 20 Oct; 20.0 Hz p90 on 21 Oct 05:14 and 06:31) | `data/real_sessions/`, `ml/models/cycle_signature_report.md` §3 |
| Local fail-safe (firmware 07) (new row) (§4) | (not listed) | HTTP on home network serving `/window.json`, `/accel.csv` (last 2.56 s of raw 200 Hz vibration), and `/clip.wav`; reachability [UNVERIFIED] | `firmware/07_feature_streamer/07_feature_streamer.ino`, `INVARIANTS_DO_NOT_CHANGE.md` §2 |
| Not allowed (§4) | "under RM 50 in parts", "magnetic mount", "45 features", "phase-conditioned model works", "IP55/IP65 pod" | Added: "UDP broadcast" and "50 Hz vibration" (firmware-05 era; fw-07 has no UDP and samples at 200 Hz) | `firmware/07_feature_streamer/`, `INVARIANTS_DO_NOT_CHANGE.md` §2 |
| Say / Plan table (§3) | 11 sessions, 8,379 rows; phase badge in Plan | 13 sessions, 9,114 rows; added to Say: "The website labels each wash type, inferred from power"; Plan: phase badge reworded so distinct from wash-type badge | `data/real_sessions/`, `data/pdm_ml_standardized_training_dataset.csv` |
| Current-state doc reality checks | 11 sessions, 8,379 rows, 2 fw-07 cycles, programme & load not logged | 13 sessions, 9,114 rows, 4 fw-07 cycles, wash types inferred from power: 4 Long cold, 1 Long hot, 2 Quick, 6 No power data, load not recorded; Last updated: 2026-10-21 | `docs/handoffs/current_state_and_scale_up_handoff.md` |

## How Numbers Were Counted
- **Session Count (13):** `len(os.listdir('data/real_sessions'))` minus `desktop.ini` = 13 CSV files:
  - 8 healthy legacy LOCO cycles: `2026-10-11_1019` (422), `2026-10-12_1019` (1,216), `2026-10-15_1020` (276), `2026-10-15_morning` (1,216), `2026-10-16_0857` (857), `2026-10-17_0718` (854), `2026-10-17_0835` (792), `2026-10-18_0516` (828).
  - 1 short legacy session: `2026-10-19_0022` (167).
  - 4 firmware-07 sessions: `2026-10-19_0911` (786), `2026-10-20_0744` (965), `2026-10-21_0514` (387), `2026-10-21_0631` (348).
- **Firmware-07 Window Count (2,486):** 786 + 965 + 387 + 348 = 2,486 windows across 4 cycles.
- **Training-Ready Rows (9,114):** `len(pd.read_csv('data/pdm_ml_standardized_training_dataset.csv'))` = 9,114 rows, exactly matching previous 8,379 + 387 (21 Oct 05:14) + 348 (21 Oct 06:31).

## Files Changed
- `docs/proposals/PROPOSAL_WRITING_GUIDE.md`: updated facts to 21 Oct, added wash type / load weight rows, added local fail-safe row, added UDP/50Hz to Not allowed.
- `docs/handoffs/current_state_and_scale_up_handoff.md`: updated reality checks sentence to 21 Oct figures and date to 2026-10-21.
- `docs/handoffs/PLAN.md`: marked `Status: DONE` with all acceptance criteria checked.
- `docs/handoffs/PLAN_DONE_2026-10-21_writing_guide_facts.md`: archived completed plan.
- `docs/handoffs/last_diff.patch`: 12.9 KB UTF-8 diff.
- `docs/handoffs/HANDOFF.md`: updated handoff documentation.

## Excluded from Patch
- `docs/handoffs/PLAN.md` (read directly by Claude per Rule 6)
- `docs/handoffs/HANDOFF.md` (read directly by Claude per Rule 6)
- `docs/handoffs/last_diff.patch` (self-referential)

## Acceptance Criteria
- [x] PLAN.md committed first (and the current-state external edit, if any, committed separately) — verified in `4f4f9ea` and `6cdff0f`.
- [x] `grep -n "load_class\|MEDIUM" docs/proposals/PROPOSAL_WRITING_GUIDE.md` returns nothing — verified (0 hits).
- [x] §4 has "Wash type" (with "inferred from power") and "Load weight" rows, each with a source path — verified.
- [x] Session count, firmware-07 cycle count and training rows in §3, §4 and the current-state sentence agree with each other and with the files; HANDOFF shows how each was counted — verified.
- [x] §4 has the local fail-safe row marked [UNVERIFIED]; "UDP broadcast" and "50 Hz vibration" are under Not allowed — verified.
- [x] No number appears that is not traceable to a repo file named in the row — verified directly against repository files.
- [x] Only the two docs (plus PLAN/HANDOFF/patch) changed; pushed; hash reported — verified.

## Tests Run
- `py -m py_compile docs/proposals/generate_proposal_pdf.py docs/proposals/generate_2page_pdf.py` — PASS.
- `py ml/tests/test_dsp_parity.py` — [SKIP] no C++ compiler on Windows PATH (expected).
- `py ml/tests/test_pipeline_synthetic.py` — PASS.
- `py firmware/tests/test_session_export.py` — PASS.
- `py firmware/tests/test_daemon_offline.py` — PASS.
- Python verification scripts for `load_class`/`MEDIUM` absence, rows, and agreement — PASS.

## Invariants Check
- INVARIANTS §1 (Honest reporting): Confirmed. No RUL, health score %, or unmeasured load classes. All wash types explicitly marked "inferred from power". Firmware 07 local fail-safe endpoints marked [UNVERIFIED].
- INVARIANTS §2 (Firmware): Untouched.
- INVARIANTS §3 (Dashboard): Untouched.
- INVARIANTS §4 (Data & ML): Originals in `data/real_sessions/` untouched; training dataset read only (not rebuilt).
- INVARIANTS §5 (Secrets): Verified no secrets in git (`.env` and `secrets.h` clean).

## Blocked / Questions
- None.

## Suggestions for Claude
- **Carried-forward Queue items:**
  1. Firmware: report reset reason (+ `epochMs()` jitter 2.7–3.8 s)
  2. ML: programme-aware evaluation once each signature class has ≥ 3 firmware-07 cycles
  3. Dashboard page budget (787.7 KB of 800 KB)
  4. Retire or clearly mark `firmware/capture_pdm_dataset.py`
  5. Proposal submission files (track "02 Circular Economy" hits, session counts, other firmware-05-era claims such as `/live.json` at 1 Hz): Adam's `Hackathon/NEEDS_CHANGING.md` batch

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
