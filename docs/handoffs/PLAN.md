# Plan for Antigravity

**Status:** READY  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Writing guide: track is PLANET · 03 Energy Efficiency, new citable sources, "machine learning" wording
**Date:** 2026-10-21

## Step 0
Commit this PLAN.md first: `docs: plan writing guide track update`.

## Review verdict that produced this plan
APPROVED: `14b43bf`, `7a9ad79` (dictionary honesty fix). You archived the plan as `PLAN_DONE_2026-10-21_dictionary_honesty.md`.

Checked by Claude: all five legacy fields read "LEGACY CONTRACT FIELD. Not measured and not a model output…" in both `data/pdm_feature_dictionary.json` and `firmware/capture_pdm_dataset.py`; no "Measured / Nyquist / CUSUM" left in the JSON; the capture script's other changes are only the embedded schema made to match the JSON (no maths changed); HANDOFF follows the full template with the carried-forward UNVERIFIED list. Good.

Your "50 Hz MPU" finding (proposal `.md`, `generate_proposal_pdf.py`, `proposal_presentation.html`) is noted. Those are submission files that Adam is batching in `Hackathon/NEEDS_CHANGING.md`; do NOT edit them in this task.

## Objective
Adam chose one hackathon track on 21 Oct: **PLANET · 03 Energy Efficiency**, with circular economy only as a supporting benefit. The Drive copies in `Hackathon/` were already updated. This task brings the repo's writing guide in line so future drafts by people or agents follow it.

## Context
- Docs only. File: `docs/proposals/PROPOSAL_WRITING_GUIDE.md` (source of truth for allowed numbers, per CLAUDE.md Document Map).
- Project rule for pitch wording: say "machine learning" (or "an unsupervised machine-learning model"), never a bare "AI" for our model.

## Implementation Steps
1. Add a short section near the top (after §1, renumber if needed) **"Track"**: "Our one track is PLANET · 03 Energy Efficiency. Circular economy (longer machine life, fewer replacements) is a supporting benefit only; do not present it as our track." Search the whole guide (and any other file under `docs/` outside `docs/proposals/PROPOSAL_*`, `generate_*`, `*presentation.html`) for "Circular Economy" / "02" as our track and fix only in the guide; list other hits in HANDOFF.
2. In §4 "Approved Facts and Numbers", add the citable sources:
   - Saidur 2009, *Energy Policy* 37(10):4104–4113, doi:10.1016/j.enpol.2009.04.052: air-conditioning ≈ 57% of energy in Malaysian office buildings.
   - Melgaard et al. 2022, *Energies* 15(12):4366, doi:10.3390/en15124366: wear-related faults raise building energy use; US faults ≈ 103–500 TWh/yr (citing Roth et al. 2004).
   - US DOE FEMP O&M Best Practices Guide §2.4: 5–20% energy savings from proper O&M (a range from the literature, not our measurement).
   - Keep "about RM 900/yr" labelled as an estimate wherever it appears.
3. Replace bare "AI" that refers to our model with "machine learning" / "ML model" in the guide (§1 story, §2 table rows 3 and 7 incl. the heading "AI Model (Plan)" → "Machine-Learning Model (Plan)", §5 heading and text, §6 diagram, §7 table, §9, §10). Leave line 6 ("AI agents (Claude, Antigravity/Gemini)") as is. Add a Tone rule: "Say 'machine learning', never bare 'AI', for our model."
4. HANDOFF with the full template (keep the carried-forward UNVERIFIED list). `last_diff.patch` per rule 6. Commit `docs: writing guide track (Energy Efficiency), sources, ML wording`. Pull --rebase, push.

## Out of Scope
Proposal `.md`/PDF/HTML, `generate_*.py`, `Hackathon/` files, video files, code.

## Acceptance Criteria
- [ ] PLAN.md committed first.
- [ ] Guide has a Track section naming PLANET · 03 Energy Efficiency; circular economy only as supporting benefit.
- [ ] The three sources appear in §4 with the exact citations above; RM 900/yr still labelled an estimate.
- [ ] `grep -n "\bAI\b" docs/proposals/PROPOSAL_WRITING_GUIDE.md` shows only the "AI agents" line (or other non-model uses, each listed in HANDOFF).
- [ ] Only the guide (plus PLAN/HANDOFF/patch) changed; pushed; hash reported.

## Queue (Claude will plan these next; do not start)
1. **Firmware: report reset reason** (+ `epochMs()` jitter 2.7–3.8 s). 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot. Needs a flash, so Adam confirms first.
2. **ML: programme-aware evaluation** once each signature class has ≥ 3 firmware-07 cycles. No per-cycle normalisation.
3. **Dashboard page budget** (787.7 KB of 800 KB) before any new dashboard feature.
4. **Retire or clearly mark `firmware/capture_pdm_dataset.py`** (still computes a load guess and "parasitic drag"; production archiving no longer uses it). Antigravity suggestion, 21 Oct.
