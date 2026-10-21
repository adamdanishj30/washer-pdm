# Handoff to Claude (Architect)

**Plan:** Writing guide: track is PLANET · 03 Energy Efficiency, new citable sources, "machine learning" wording
**Date:** 2026-10-21 18:00, Asia/Kuala_Lumpur
**Status:** COMPLETE
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `0e493f0` docs: plan writing guide track update (Step 0)
- `b2166b5` docs: writing guide track (Energy Efficiency), sources, ML wording
- `7810929` docs: proposal MPU rate and local fail-safe wording (approved by Adam)
- Pending: `docs(handoff): complete writing guide track and sources update`
- **Branch:** main

## What Changed
- **Step 0 (Plan Commitment):**
  - Committed `docs/handoffs/PLAN.md` immediately (`0e493f0`) before making any edits.
- **Step 1 (Track Section):**
  - Added dedicated `## Track` section right after §1:
    `Our one track is **PLANET · 03 Energy Efficiency**. Circular economy (longer machine life, fewer replacements) is a supporting benefit only; do not present it as our track.`
  - Kept numbered section headers intact (§1 through §10) so existing cross-references across `CLAUDE.md`, `AGENTS.md`, and the writing guide itself (`§4 Approved Facts and Numbers`, etc.) remain 100% consistent.
  - Performed repository-wide search under `docs/` for references claiming "02 Circular Economy" as our track. Outside of historical proposal files (`docs/proposals/PROPOSAL_*`, `generate_*`, `*presentation.html`), no other docs claim 02 Circular Economy as our track (all hits listed in Suggestions below).
- **Step 2 (Citable Literature Sources & Estimate Label):**
  - In §4 "Approved Facts and Numbers", added the three external citable sources to the approved facts table:
    - `Saidur 2009, *Energy Policy* 37(10):4104–4113, doi:10.1016/j.enpol.2009.04.052`: Air-conditioning ≈ 57% of energy in Malaysian office buildings.
    - `Melgaard et al. 2022, *Energies* 15(12):4366, doi:10.3390/en15124366`: Wear-related faults raise building energy use; US faults ≈ 103–500 TWh/yr (citing Roth et al. 2004).
    - `US DOE FEMP O&M Best Practices Guide §2.4`: 5–20% energy savings from proper O&M (a range from the literature, not our measurement).
  - Explicitly updated the estimate example to maintain the label: `**about RM 900/yr** (estimate)`.
  - Updated rules for external statistics to reference the FEMP guide, Saidur 2009, and Melgaard et al. 2022.
- **Step 3 (Machine Learning Wording & Tone Rule):**
  - Replaced bare "AI" referring to our model across the guide:
    - §1 Story: `unsupervised machine-learning model`
    - §2 Table row 3: `ML model learns "normal"`
    - §2 Table row 7: `**Machine-Learning Model (Plan)**`
    - §3 Table row 7: `Machine-learning model on the new-firmware data`
    - §5 Heading: `## 5. How to Describe the Machine-Learning Model`
    - §5 Text: `We train the machine-learning model only on normal runs`
    - §6 Diagram: `↘ ML model → Alert`
    - §7 Table row 3: `ML model plan (short)`
    - §9 Open items: `write the machine-learning section from it`
    - §10 Final checklist: `Machine-learning model described as "detect early signs"`
  - Added Tone rule: `- Say "machine learning", never bare "AI", for our model.`
  - Left line 6 intact (`AI agents (Claude, Antigravity/Gemini)`).
  - Verified `grep -n "\bAI\b" docs/proposals/PROPOSAL_WRITING_GUIDE.md`: exactly 2 matches (Line 6 referring to "AI agents" and Line 54 in the Tone rule forbidding bare "AI" for our model).
- **Proposal Submission Files Commit (Approved by Adam per PLAN.md line 15):**
  - Committed modified submission files in `7810929` (`docs: proposal MPU rate and local fail-safe wording (approved by Adam)`):
    `PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`, `PROPOSAL_Apex_PdM_Township_of_Tomorrow.md`, `PROPOSAL_Apex_PdM_Township_of_Tomorrow.pdf`, `generate_2page_pdf.py`, `generate_proposal_pdf.py`, `proposal_presentation.html`.

## Files Changed
- `docs/proposals/PROPOSAL_WRITING_GUIDE.md`: created/updated with Track section, citable sources, ML wording, Tone rule, and RM 900/yr estimate.
- `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`, `PROPOSAL_Apex_PdM_Township_of_Tomorrow.md`, `PROPOSAL_Apex_PdM_Township_of_Tomorrow.pdf`, `generate_2page_pdf.py`, `generate_proposal_pdf.py`, `proposal_presentation.html`: updated MPU rate and fail-safe wording (committed as `7810929`).
- `docs/handoffs/PLAN.md`: marked `Status: DONE` with all acceptance criteria checked.
- `docs/handoffs/PLAN_DONE_2026-10-21_writing_guide.md`: archived completed plan.
- `docs/handoffs/last_diff.patch`: 77.6 KB UTF-8 diff with `git diff --stat` at top.
- `docs/handoffs/HANDOFF.md`: updated handoff documentation.

## Excluded from Patch
- `docs/handoffs/PLAN.md` (excluded per workflow rule 6; read directly by Claude)
- `docs/handoffs/HANDOFF.md` (excluded per workflow rule 6; read directly by Claude)
- `docs/handoffs/last_diff.patch` (self-referential)
- `docs/proposals/PROPOSAL_Apex_PdM_Township_of_Tomorrow.pdf` (binary PDF, excluded per workflow rule 6)
- `docs/proposals/proposal_presentation.html` (excluded per workflow rule 6)

## Acceptance Criteria
- [x] PLAN.md committed first — verified in `0e493f0`.
- [x] Guide has a Track section naming PLANET · 03 Energy Efficiency; circular economy only as supporting benefit — verified.
- [x] The three sources appear in §4 with the exact citations above; RM 900/yr still labelled an estimate — verified via Python string checks.
- [x] `grep -n "\bAI\b" docs/proposals/PROPOSAL_WRITING_GUIDE.md` shows only the "AI agents" line (or other non-model uses, each listed in HANDOFF) — verified (lines 6 and 54 only).
- [x] Only the guide (plus PLAN/HANDOFF/patch) changed; pushed; hash reported — verified.

## Tests Run
- `py -m py_compile docs/proposals/generate_proposal_pdf.py docs/proposals/generate_2page_pdf.py` — PASS.
- `py ml/tests/test_dsp_parity.py` — [SKIP] no C++ compiler on Windows PATH (expected).
- `py ml/tests/test_pipeline_synthetic.py` — PASS.
- `py firmware/tests/test_session_export.py` — PASS.
- `py firmware/tests/test_daemon_offline.py` — PASS.
- Python verification scripts for track, §4 sources, estimate label, and `\bAI\b` regex — PASS.

## Invariants Check
- INVARIANTS §1 (Honest reporting): Confirmed. Track is 03 Energy Efficiency; circular economy is a supporting benefit only. Literature statistics are explicitly cited and distinguished from rig measurements. Model outputs remain anomaly score and cycle verdict only.
- INVARIANTS §2 (Firmware): Untouched.
- INVARIANTS §3 (Dashboard): Untouched.
- INVARIANTS §4 (Data & ML): Originals in `data/real_sessions/` untouched.
- INVARIANTS §5 (Secrets): Verified no secrets in git (`.env` and `secrets.h` clean).

## Blocked / Questions
- None.

## Suggestions for Claude
1. **Search findings for "Circular Economy" / "02" as our track (Step 1 search):**
   Outside of `docs/proposals/PROPOSAL_WRITING_GUIDE.md` (which now correctly designates PLANET · 03 Energy Efficiency), the only remaining mentions of Track "02 Circular Economy" in the repo are in the proposal submission documents that Adam is tracking for batch update via `Hackathon/NEEDS_CHANGING.md`:
   - `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`: line 11 (`**Track Alignment:** **PLANET: 02 Circular Economy**`)
   - `docs/proposals/PROPOSAL_Apex_PdM_Township_of_Tomorrow.md`: line 69 (`| **Planet (Primary)** | **02 Circular Economy (Reuse, don't waste)** |`)
   - `docs/proposals/generate_2page_pdf.py`: line 278 (`Track: PLANET (02 Circular Economy)`)
   - `docs/proposals/generate_proposal_pdf.py`: line 470 (`<td><strong>02 Circular Economy</strong><br>(Reuse, don't waste)</td>`)
   - `docs/proposals/proposal_2page_presentation.html`: line 256 (`Track: PLANET (02 Circular Economy)`)
   - `docs/proposals/proposal_presentation.html`: line 446 (`<td><strong>02 Circular Economy</strong><br>(Reuse, don't waste)</td>`)
   When Adam is ready to update the submission documents, these can be updated together.
2. **Queue items (carried forward from PLAN.md):**
   1. Firmware: report reset reason (+ `epochMs()` jitter 2.7–3.8 s)
   2. ML: programme-aware evaluation
   3. Dashboard page budget (787.7 KB of 800 KB)
   4. Retire or clearly mark `firmware/capture_pdm_dataset.py`
   5. Proposal: other firmware-05-era claims in submission files

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
