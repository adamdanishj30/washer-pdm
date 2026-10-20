# Handoff to Claude (Architect)

**Plan:** Sync the 2-page proposal brief (markdown + PDF generator + PDF) to the approved numbers in PROPOSAL_WRITING_GUIDE §4
**Date:** 2026-10-20 11:32, Asia/Kuala_Lumpur
**Status:** COMPLETE

## Commits
- `8eec5dd` docs(proposals): sync 2-page brief to approved numbers
- **Branch:** main

## What Changed
- **Track Alignment:** Aligned official track to `PLANET: 02 Circular Economy` (with Energy Efficiency in the narrative) per Adam's confirmation in chat and `VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md`. Removed `Circular Energy` placeholder.
- **Metric strip:** `< RM 50` replaced with `~RM 170`; label `Sensor pod parts cost` replaced with `Pilot kit cost, off the shelf`; label `Real wash cycles recorded` replaced with `Real wash sessions archived`.
- **Section 2:** Replaced unverified equipment counts (`20 to 50+ commercial AC compressors daily` / `20 to 50+ AC units every day`) with `many commercial AC compressors daily` / `many AC units every day`.
- **Section 3 (Machine State):** Clarified context comes from SmartThings (wash, rinse, spin) and comparing vibration and sound within the same phase is planned. Removed the claim that a fast spin is not flagged today.
- **Section 3 (Features):** Replaced `45 ready-to-use features` with `32 signal features` (firmware-07 window record).
- **Section 4 (Contractors):** Replaced unbuilt automated dispatching claim in generator with matching markdown wording (`Technicians who get told which machine needs a look, instead of rushing to emergency calls`).
- **Section 5 (Low Cost):** Replaced `under RM 50` claim with `We spent about RM 131 in parts for the sensor node (about RM 170 for a full pilot kit with smart plug)`.
- **Section 5 (Fewer False Alarms):** Marked checking against what the machine is doing as planned (`and plan to check against what the machine is doing, before raising an alert`).
- **Section 6 (Data & Validation):** `10 real wash cycles` updated to `10 real wash sessions archived`; `45 features per 5-second window` updated to `32 signal features per 5-second window (firmware-07 window record)`. Added LOCO validation bullet: `Leave-one-cycle-out test on 8 healthy cycles: 0 falsely flagged (95% upper bound 31%); a simulated doubling of sound was caught in 7 of 8`.
- **Section 6 (Township):** Replaced `20 to 50 AC units and pumps` with `AC units and pumps in township mosques, kuils, community halls and malls`.
- **Section 6 (Figure 1):** Retitled to `Figure 1: Sensor pod layout` (does not claim to be a photo of the live rig).
- **Page 2 Header Badge:** Replaced `Hardware BOM < RM 50` with `Pilot kit about RM 170` (and added `white-space: nowrap` so it renders cleanly on one line).
- **Recompiled PDF:** Regenerated `PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.pdf` and verified 2 pages with no cut-off text.

## Files Changed
- `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`: Updated narrative, metrics, and evidence to approved numbers.
- `docs/proposals/generate_2page_pdf.py`: Synchronized all HTML copy, badges, figure captions, and metric cards with the markdown text; added `white-space: nowrap` to header-track.
- `docs/proposals/proposal_2page_presentation.html`: Regenerated presentation HTML by-product.
- `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.pdf`: Recompiled 2-page PDF.
- `docs/handoffs/PLAN.md`: Marked acceptance criteria and status as DONE.
- `docs/handoffs/HANDOFF.md`: Recorded handoff documentation.

## Acceptance Criteria
- [x] None of the strings in step 7 remain in the `.md`, `generate_2page_pdf.py` or the regenerated PDF text — verified with python automated search across all forbidden strings (`under RM 50`, `< RM 50`, `&lt; RM 50`, `RM 50`, `BOM &lt;`, `45 ready`, `45 features`, `pdm_feature_dictionary`, `IP55`, `PG11`, `TRL 6`, `20 to 50`, `Circular Energy`).
- [x] The `.md` and the text inside `generate_2page_pdf.py` match for every changed passage — verified matching diff for title, metrics, problem, solution, modalities, uniqueness, evidence, and ROI.
- [x] `py -3 docs/proposals/generate_2page_pdf.py` reports `Total Pages: 2` — verified Edge headless build reports `Total Pages: 2` (1152.6 KB).
- [x] Both PDF pages were checked by eye for cut-off text, with the result recorded — rendered page 1 and page 2 to PNG via PyMuPDF (fitz) at 150 DPI and inspected with multimodal vision. Verified plenty of whitespace above footer on both pages, no text truncated or hidden.
- [x] The brief contains the kit cost about RM 170 (RM 169.68), the LOCO line from step 6, and no health-index, RUL, P-F or ringgit-saved claim presented as measured — verified.
- [x] No file other than the listed proposal/handoff files changed; no secrets in the diff — verified.
- [x] Header badge on page 2 no longer says `< RM 50` (check `&lt; RM 50` too) — verified; badge displays `PILOT KIT ABOUT RM 170`.
- [x] Neither file contains `20 to 50` or `Circular Energy`; the PDF caption says `32 signal features` and `10 real wash sessions archived` — verified.
- [x] The generated `proposal_2page_presentation.html` may change (it is a by-product of the generator); no other file outside the list changes — verified.
- [x] HANDOFF.md is updated with a new section for this task — verified.

## Tests Run
- `py -m py_compile docs/proposals/generate_2page_pdf.py` — PASS
- `py -3 docs/proposals/generate_2page_pdf.py` — PASS (`Total Pages: 2`)
- Python forbidden-strings audit — PASS (`ALL CLEAN!`)
- `py ml/tests/test_dsp_parity.py` — PASS (`[SKIP] no C++ compiler found on PATH`)
- `py ml/tests/test_pipeline_synthetic.py` — PASS (`[PASS] windowed pipeline mechanics`)
- `py firmware/tests/test_session_export.py` — PASS (`[PASS] session_export`)
- `py firmware/tests/test_daemon_offline.py` — PASS (`[PASS] daemon downloads only finished, unarchived sessions`)

## Invariants Check
- All items in `INVARIANTS_DO_NOT_CHANGE.md` respected. No data modified under `data/real_sessions/`, no firmware changes, no secrets in diff.

## Blocked / Questions
- None. Track alignment was resolved with Adam in chat (`PLANET: 02 Circular Economy`).

## Suggestions for Claude
- The master dossier (`PROPOSAL_Apex_PdM_Township_of_Tomorrow.md` and `generate_proposal_pdf.py`) still carries the UNDER REWRITE banner and will need a similar sync pass to align with `PROPOSAL_WRITING_GUIDE.md` §4 when scheduled.

---

## Historical Sessions (19 Oct 2026 and earlier)

### Session 1: Firmware-07 Vibration Std (σ) & Dominant Frequency (2026-10-19)
- Card 1 (`drawSpline`): Dynamic vibration `vib_mag_std` (σ) plotted on honest 0 to 0.5+ m/s² scale with sensor floor marker ~0.03 m/s².
- Card 2 (`drawXyz`): Plot per-axis dynamic vibration `σx`, `σy`, `σz`.
- Card 2 Dominant Frequency: displays `vib_dom_hz` gated on `vibStd > 0.08 m/s²`.
- Commit: `03495d3`.

### Session 2: Live Poll Controller & Invariant Restoration (2026-10-19)
- Polling cadence adaptive: 10s active / 25s idle, 30s offline, 120-window backfill buffer.
- Commit: `5086684`.

### Session 3: SmartThings Auth Diagnosis & Cloud Downloader Sync (2026-10-19)
- Local token cache in `%LOCALAPPDATA%`, single-use OAuth refresh token handling.

### Session 4: Pitch Proposal Overhaul & Confidence Transformation (2026-10-19)
- Master and 2-page brief transformation; dynamic stress benchmark framing.
