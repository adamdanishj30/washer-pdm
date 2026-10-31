# Plan for Antigravity

**Status:** READY  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** ML: first honest nested-LOCO report on the firmware-07 washes (report only, deployed model untouched) + refresh the handoff facts
**Date:** 2026-10-31

## Step 0
Before ANY other git command (no pull, stash, checkout or reset first): `git add docs/handoffs/PLAN.md` and commit `docs: plan firmware-07 LOCO report`. Then `git pull --rebase` (no `--autostash`).
Then run `git status`. If the 25 Oct firmware work (reset reason + `/start_test` / `/stop_test`, see the 25 Oct HANDOFF) is still uncommitted, commit ONLY those files as `feat(firmware): reset reason and manual test mode` before you start, and report the hash. Do not change them.

## Review verdict that produced this plan
No code verdict this time. Adam asked Claude (31 Oct) whether the scale-up plan in `docs/handoffs/current_state_and_scale_up_handoff.md` is feasible. Verdict: FEASIBLE IN PARTS. The first blocker is that every ML claim still rests on the 8 **legacy** cycles: `ml/models/loco_report.md` was never regenerated on firmware-07 data, although `MIN_WINDOWED_CYCLES = 3` has been met since 21 Oct. The handoff file is also stale (it says 4 firmware-07 cycles and links a TODO file that does not exist).
Note: the 25 Oct HANDOFF (reset reason, manual test mode) has not been reviewed by Claude yet. Adam can say "review" for it separately.

## Objective
Produce the first nested leave-one-cycle-out report on the firmware-07 (45-column, schema 3) washes with the **unchanged** protocol, without touching the deployed model, and correct the handoff's facts so the next plans start from the truth.

## Implementation Steps
1. **Inventory (no edits to data).** List every file in `data/real_sessions/` with: schema detected by `ml/feature_fusion.detect_schema`, start time, duration (min), number of windows, max power (W), `end_reason` if known. Put the table in HANDOFF.
   - Some washes exist twice (e.g. `wash_cycle_2026-10-24_0631.csv` 45-col and `wash_cycle_2026-10-24_063152.csv` 8-col legacy export of the same wash). Mark each pair. A wash must never be counted twice in any one evaluation.
   - Flag (do not delete, do not move) any file that looks like a test, not a wash: duration < 15 min, max power < 50 W, or a `manual_stop`/test session (e.g. check `wash_cycle_2026-10-19_0022.csv`). List the flags; Adam decides.
2. **Run the evaluation into a separate folder**, never `ml/models/`:
   `py ml/train_unsupervised_pdm.py --schema windowed --models-dir ml/outputs/fw07_loco_2026-10-31`
   If step 1 flagged files, run on a temp copy of `data/real_sessions/` without them via `--data-dir` (copy, never edit the originals) and say which files were left out.
3. Do not change any model, feature, threshold, calibration, fault-injection or `loco_eval.py` code. If the run crashes on firmware-07 data, stop, write the traceback in HANDOFF, and do not "fix" the protocol.
4. **Docs (facts only):** in `docs/handoffs/current_state_and_scale_up_handoff.md`:
   - Update "Last updated" to today, the firmware-07 cycle count in §2 and §5 (from step 1), and add one line under §3 pointing to the new report with its headline numbers (false-alarm cycles n/N + 95% upper bound, min detectable acoustic and vibration fault). Keep the legacy result too, labelled "legacy".
   - §4 item 3: remove the dead link to `TODO_BACKGROUND_NOISE_AND_DATA_COLLECTION.md` and mark the "down-weight `ab0` + multimodal gating" sub-step **WAITING ON ADAM (changes MUST-STAY ML design)**.
   - Add one line: SmartThings history returns 403 with the current token, so past washes have no phase labels; the model stays pooled (not phase-conditioned).
   - Add one line under §6 linking `docs/hardware_guides/PARTS_TO_PURCHASE.md`.
5. HANDOFF with the full template, including the carried-forward UNVERIFIED list (Apps Script trigger; workflow run with GitHub secrets; real-wash session start / END / archive; active-wash adaptive polling; session-change reset; `historical.html` live check; DevTools network check; `/window.json` + WHO_AM_I quirk; weighed laundry load). `last_diff.patch` per the rules.
6. Commit `ml/outputs/fw07_loco_2026-10-31/loco_report.md` and `.json` (NOT the `.joblib`) plus the handoff doc as `docs(ml): firmware-07 nested LOCO report and handoff refresh`. Pull --rebase (no autostash), push. Report the hash.

## Out of Scope
`ml/models/` (deployed model, `loco_report.md`), any ML code, thresholds, `data/real_sessions/*.csv` (no edits, moves or deletes), firmware, dashboard, workflow, secrets, proposal / `Hackathon/` / video files, `archive/`.

## Acceptance Criteria
- [ ] PLAN.md committed before any other git command; 25 Oct firmware commit status reported.
- [ ] HANDOFF has the inventory table; duplicate pairs and suspected test sessions are marked; no wash counted twice.
- [ ] Report generated in `ml/outputs/fw07_loco_2026-10-31/` with schema `windowed`; `git diff --stat ml/models/` is empty.
- [ ] `git diff` shows no change to any `.py` under `ml/` or to any file in `data/real_sessions/`.
- [ ] Report states n cycles, false-alarm cycles and the 95% upper bound (rule of three); it is labelled a pilot because n < 20.
- [ ] Handoff doc updated as in step 4; dead link gone; gating step marked WAITING ON ADAM.
- [ ] Existing tests still pass: `py ml/tests/test_dsp_parity.py`, `py ml/tests/test_pipeline_synthetic.py`, `py firmware/tests/test_session_export.py`, `py firmware/tests/test_daemon_offline.py`.
- [ ] Pushed; hash reported.

## Queue (do not start; Claude plans these only when Adam asks)
1. **Archiver: close sessions cut off at the wall** (from the 25 Oct HANDOFF suggestion). Adam's father switches the wall power off when the wash ends, so the 10-min idle END marker is never written. In `cloud_downloader.py` / the daemon: if a session has had no new window for > 15 min and `/live` is offline or IDLE, archive it with `end_reason: "ungraceful_poweroff"`. PC side only; no firmware change; ≥ 30 s polling rule unchanged.
2. **WAITING ON ADAM: down-weight `ab0`/RMS + multimodal gating** (acoustic alarm only if P > 15 W or σv > 0.1 m/s²). Changes the MUST-STAY ML design. If Adam says yes: the gate values are fixed up front from idle data and physics, written in the plan before any LOCO run, and any weights are fitted inside each LOCO fold (no leakage).
3. **Noise baselines + tagged perturbation runs** (needs Adam/his father at home): 2–3 min clips with the washer off (compressor on/off, pump on/off) via `collect_audio_clips.py`; 2–3 safe runs tagged via `/tag` (unbalanced load, soft mat). Confirm one tag appears in `session_meta` before relying on `/tag`.
4. **ML: programme-aware evaluation** once each power-inferred class (Quick / Long cold / Long hot) has ≥ 3 firmware-07 cycles. Classes are labelled "inferred from power". No per-cycle normalisation.
5. **Q1. AUC + modality ablation report** (from `PLAN_QUEUE_mafaulda_methods.md`; software only, never touches `ml/models/`).
6. **Q2. Background-noise nuisance test** (new fault kind, held-out cycle's own idle-tail audio, firmware-07 only).
7. **Q3. WAITING ON ADAM: firmware order-tracked 1X/2X vibration keys** (new keys only; RAM check; `V3_KEY_MAP` + parity test; no flash during a wash).
8. **Docs: writing guide track = Planet · 03 Energy Efficiency** (`PLAN_QUEUE_writing_guide.md`). Check first whether it is already done.

## Waiting on Adam (not Antigravity's job)
- Rotate the Firebase secret and Wi-Fi password; re-add the `FIREBASE_AUTH` repo secret (30-min sync job failing since 21 Oct).
- Decide whether the real session CSVs go into git.
- Fix rig power (23 Oct reboots; 24 Oct reset reason `TASK_WDT`). Parts list: `docs/hardware_guides/PARTS_TO_PURCHASE.md`.
- Removed from the queue: the reset-reason firmware item (done, flashed 25 Oct) and the hackathon `NEEDS_CHANGING.md` batch (submission closed 23 Oct).
