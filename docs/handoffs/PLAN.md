# Plan for Antigravity

**Status:** READY  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Writing guide §4 and current-state doc: bring facts up to 21 Oct (4 firmware-07 cycles, inferred wash types, no load guess)
**Date:** 2026-10-21

## Step 0
Commit this PLAN.md first: `docs: plan writing guide facts refresh`.

## Review verdict that produced this plan
APPROVED: `0e493f0`, `b2166b5` (writing guide track, sources, ML wording), plus `7810929` (proposal wording). You archived the plan as `PLAN_DONE_2026-10-21_writing_guide.md`.

Checked by Claude: Track section present after §1 with the exact wording; the three sources are in §4 with exact citations; "about RM 900/yr (estimate)" kept; `\bAI\b` only on line 6 ("AI agents") and line 54 (the new Tone rule), both allowed; all listed headings and rows reworded to "machine learning" / "ML model"; Out-of-Scope respected for this task's own commit; full HANDOFF template with UNVERIFIED list. Your list of remaining "02 Circular Economy" hits in the submission files is useful and goes to Adam's `Hackathon/NEEDS_CHANGING.md` batch, not to you.

Two notes: (a) `7810929` also carried older 2-page edits (10 → 11 sessions, 4 → 3 sensors, "Machine State (planned)"); they match the guide, so they stand. (b) `docs/handoffs/current_state_and_scale_up_handoff.md` changed on Drive after your HANDOFF (mtime later than the patch, ~+71 bytes). Run `git diff` on it first; if the change is not yours, commit it on its own as `docs: current-state note (external edit)` before Step 1 and paste the diff in HANDOFF.

## Objective
The guide's §4 "Approved Facts and Numbers" is the source of truth for every pitch number, but it still describes 20 Oct: 11 sessions, 2 firmware-07 cycles, "programme not recorded", and `load_class` "a constant MEDIUM" (removed on 21 Oct). Bring it, and the matching sentence in the current-state doc, up to the real repo state on 21 Oct. Every new number must come from a file you open, not from this plan.

## Context
- Files: `docs/proposals/PROPOSAL_WRITING_GUIDE.md` (§3 Say/Plan table, §4 table) and `docs/handoffs/current_state_and_scale_up_handoff.md` (line ~50 "Reality checks" sentence only).
- Sources to read: `data/real_sessions/` (list, do not modify), `data/session_context.csv`, `ml/models/cycle_signature_report.md`, `data/pdm_ml_standardized_training_dataset.csv` (`session_source` counts, read only, do NOT rebuild), `ml/models/loco_report.md`, `firmware/07_feature_streamer/07_feature_streamer.ino` (local HTTP routes), `INVARIANTS_DO_NOT_CHANGE.md` §2.
- Expected (verify, and report any difference in HANDOFF rather than forcing these): 13 sessions; 8 healthy legacy LOCO cycles; 4 complete firmware-07 cycles (19 Oct 09:11, 20 Oct 07:44, 21 Oct 05:14, 21 Oct 06:31); classes Long cold / Long hot / Quick / No power data; spin dominant frequency ≈ 20 Hz in all 4 firmware-07 cycles. Claude counted at 10:08 UTC: 13 files in `data/real_sessions/`; firmware-07 windows 786 / 965 / 387 / 348; 9,114 training-ready rows (8,379 + 387 + 348). The proposal thread is using these figures, so report any mismatch loudly. Three originals (15 Oct 10:20, 16 Oct 08:57, 17 Oct 07:18) and the training CSV got new mtimes at 18:01 MYT; Claude checked the originals are byte-identical. Say in HANDOFF what rewrote them (pull/checkout?).

## Implementation Steps
1. §4 rows, update from the files:
   - "Wash sessions recorded": count and breakdown as of 21 Oct, with source paths.
   - "Firmware-07 cycles": number, window counts per cycle, and whether the model has been trained on them (check `ml/models/loco_report.md`; if not retrained, say so).
   - "Machine state (phase labels)": check the `phase` / `phase_source` columns of all 4 firmware-07 CSVs and state what you find. Keep "planned" unless real labels exist.
   - Replace the "Programme / load per cycle" row with two rows: **"Wash type"** = classes inferred from power (Quick, Long cold, Long hot, No power data) with the per-class count, source `ml/models/cycle_signature_report.md`, and the rule "always say 'inferred from power'; programme names are not logged"; **"Load weight"** = not recorded (`load_kg` blank in `data/session_context.csv` until Adam weighs a load). Remove every mention of `load_class` / `MEDIUM`.
   - "Training-ready rows": the current `session_source` total; keep the old figure in brackets only if it changed.
   - "Drum frequency in final spin": extend to all firmware-07 cycles only if `vib_dom_hz` confirms it; otherwise list per cycle.
   - Add a row **"Local fail-safe (firmware 07)"**: HTTP on the home network serving the latest feature window, the last 2.56 s of raw 200 Hz vibration and a short audio clip that never goes to the cloud; reachability [UNVERIFIED]. Source: the `.ino` routes and INVARIANTS §2.
   - Add to "Not allowed": "UDP broadcast" and "50 Hz vibration" (firmware-05 era; firmware 07 has no UDP and samples at 200 Hz).
2. §3 Say/Plan table: update the "11 wash sessions recorded, 8,379 data rows" cell to the verified figures. Add to the Say column "The website labels each wash type, inferred from power". In the Plan column, keep the phase badge (wash / rinse / spin) as planned and reword it so it is not confused with the wash-type badge.
3. Current-state doc: update only the "Reality checks" sentence (~line 50) to the same verified figures, the wash-type classes and "load not recorded". Update its "Last updated" line. No other edits in that file.
4. HANDOFF with the full template: a table of every fact you changed (old → new → source file), plus the carried-forward UNVERIFIED list. `last_diff.patch` per rule 6. Commit `docs: writing guide facts as of 21 Oct`. Pull --rebase, push.

## Out of Scope
Proposal `.md`/PDF/HTML, `generate_*.py`, `Hackathon/`, video files, code, data files (read only), rebuilding datasets or models, §1/§2/§5–§10 of the guide.

## Acceptance Criteria
- [ ] PLAN.md committed first (and the current-state external edit, if any, committed separately).
- [ ] `grep -n "load_class\|MEDIUM" docs/proposals/PROPOSAL_WRITING_GUIDE.md` returns nothing.
- [ ] §4 has "Wash type" (with "inferred from power") and "Load weight" rows, each with a source path.
- [ ] Session count, firmware-07 cycle count and training rows in §3, §4 and the current-state sentence agree with each other and with the files; HANDOFF shows how each was counted.
- [ ] §4 has the local fail-safe row marked [UNVERIFIED]; "UDP broadcast" and "50 Hz vibration" are under Not allowed.
- [ ] No number appears that is not traceable to a repo file named in the row.
- [ ] Only the two docs (plus PLAN/HANDOFF/patch) changed; pushed; hash reported.

## Queue (Claude will plan these next; do not start)
1. **Firmware: report reset reason** (+ `epochMs()` jitter 2.7–3.8 s). 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot. Needs a flash, so Adam confirms first.
2. **ML: programme-aware evaluation** once each signature class has ≥ 3 firmware-07 cycles. No per-cycle normalisation.
3. **Dashboard page budget** (787.7 KB of 800 KB) before any new dashboard feature.
4. **Retire or clearly mark `firmware/capture_pdm_dataset.py`** (still computes a load guess and "parasitic drag"; production archiving no longer uses it). Antigravity suggestion, 21 Oct.
5. **Proposal submission files** (track "02 Circular Economy" hits, session counts, other firmware-05-era claims such as `/live.json` at 1 Hz): Adam's `Hackathon/NEEDS_CHANGING.md` batch, only when he says go.
