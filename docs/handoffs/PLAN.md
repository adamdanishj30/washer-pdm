# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Sync the 2-page proposal brief (markdown + PDF generator + PDF) to the approved numbers in PROPOSAL_WRITING_GUIDE §4
**Date:** 2026-10-20

## Objective
The 2-page brief (`docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`, its text inside `docs/proposals/generate_2page_pdf.py`, and the compiled PDF) still contains claims that the 2026-10-20 documentation sync found to be wrong. After this task, the markdown, the generator script and the PDF say the same thing, and contain only approved numbers. The brief may be submitted as an optional supporting document (due 23 Oct 2026, 11:59 PM), so this must be done and checked by eye before then.

## Review verdict that produced this plan
Not a code review. Documentation sync by Claude (see `archive/ARCHIVE_LOG_2026-10-20.md`). The previous plan (firmware-07 vibration σ on the dashboard) is DONE; its handoff is in section 1 of `HANDOFF.md`.

## Why (evidence)
- Pod cost: `Hackathon/HARDWARE_BOM_AND_COST_BREAKDOWN.md` (receipts) totals RM 169.68 net paid for the kit and RM 131.07 for the node without the smart plug. Three boards alone are RM 82.88. "Under RM 50" is an unvalidated volume target.
- Features: a firmware-07 window record is 45 CSV columns, of which 32 are signal features (`V3_KEY_MAP` in `firmware/session_export.py`). `data/pdm_feature_dictionary.json` is the legacy 31-field contract, not the source of "45 features".
- Phase conditioning: `ml/models/loco_report.md` states the evaluated model is NOT phase-conditioned (0% of windows carry phase labels).
- Sessions: 10 archived, 8 healthy legacy cycles in the evaluation set (6,461 windows); result 0 of 8 healthy cycles flagged, 95% upper bound 31%.

## Context
- Allowed numbers and the Say / Plan / Don't-say table: `docs/proposals/PROPOSAL_WRITING_GUIDE.md` §3–4 (already synced).
- The brief's text lives in BOTH the `.md` and `generate_2page_pdf.py`; the page boxes have fixed height and hide overflow, so "Total Pages: 2" does not prove nothing was cut off.
- Invariants that apply: `INVARIANTS_DO_NOT_CHANGE.md` §1 (never delete data, no secrets, honest labels, one task = one change set).
- Files to edit: `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`, `docs/proposals/generate_2page_pdf.py`, then regenerate `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.pdf`.

## Implementation Steps
Apply each replacement in BOTH the `.md` and the matching text inside `generate_2page_pdf.py`. Keep wording length similar so the 2-page layout still fits.
1. Header stats row: `< RM 50` becomes `~RM 170`; label `Sensor pod parts cost` becomes `Pilot kit cost, off the shelf`; label `Real wash cycles recorded` becomes `Real wash sessions archived`.
2. Section 3, "Machine State": say it gives context (from SmartThings) and that comparing within the same phase is planned. Remove the claim that a fast spin "is not flagged" today.
3. Section 3, dual-core bullet: `45 ready-to-use features` becomes `32 signal features`.
4. Section 5, Low Cost bullet: replace "under RM 50 ... (about RM 170 for a full pilot kit with smart plug)" with "about RM 131 in parts for the sensor node (about RM 170 for a full pilot kit with smart plug)". Keep the point that industrial sensors cost thousands.
5. Section 5, Fewer False Alarms bullet: keep "checks vibration, sound and power together"; mark checking "against what the machine is doing" as planned.
6. Section 6, Data in hand: `45 features per 5-second window (data/pdm_feature_dictionary.json)` becomes `32 signal features per 5-second window (firmware-07 window record)`. Add one short bullet: `Leave-one-cycle-out test on 8 healthy cycles: 0 falsely flagged (95% upper bound 31%); a simulated doubling of sound was caught in 7 of 8.`
7. Search all three files for these strings and confirm none remain: `under RM 50`, `< RM 50`, `45 ready`, `45 features`, `pdm_feature_dictionary`, `IP55`, `PG11`, `TRL 6`.
8. Run `py -3 docs/proposals/generate_2page_pdf.py`; confirm `Total Pages: 2`.
9. Open the PDF and check the bottom of both pages by eye for cut-off text (the page boxes hide overflow). Record what you saw in HANDOFF.
10. Update `PROPOSAL_WRITING_GUIDE.md` §9 checklist if applicable; write `HANDOFF.md` with the template; mark this plan DONE. Commit locally: `docs(proposals): sync 2-page brief to approved numbers`. Do not push unless the user says so.

## Out of Scope
- The master dossier (`PROPOSAL_Apex_PdM_Township_of_Tomorrow.md` and `generate_proposal_pdf.py`). It carries an UNDER REWRITE banner and is a separate, larger task.
- `data/pdm_feature_dictionary.json` (legacy contract; leave as is) and any CSV under `data/`.
- Any firmware, dashboard, ML, daemon or `.github/` change.
- Rotating the Firebase secret and Wi-Fi password (a manual task for Adam, see the current-state handoff §4 step 1).

## Acceptance Criteria
- [x] None of the strings in step 7 remain in the `.md`, `generate_2page_pdf.py` or the regenerated PDF text.
- [x] The `.md` and the text inside `generate_2page_pdf.py` match for every changed passage (paste a short diff summary into HANDOFF).
- [x] `py -3 docs/proposals/generate_2page_pdf.py` reports `Total Pages: 2`.
- [x] Both PDF pages were checked by eye for cut-off text, with the result recorded (mark UNVERIFIED if no viewer is available).
- [x] The brief contains the kit cost about RM 170 (RM 169.68), the LOCO line from step 6, and no health-index, RUL, P-F or ringgit-saved claim presented as measured.
- [x] No file other than the three listed (plus HANDOFF.md and PLAN.md) changed; no secrets in the diff.

## Risk Notes
- **Overflow:** longer wording can push text past the fixed-height page boxes without changing the page count. Keep replacements about the same length, and check by eye.
- **Two sources of text:** editing only the `.md` leaves the PDF unchanged. Both must change in the same commit.
- **Cost wording:** use "off the shelf", "retail" and "about"; the figures are one-off retail prices and are to be confirmed against receipts.

## Amendment 2026-10-20 (Claude review of the current files; Status stays READY)
Checked on disk at 10:56: the brief `.md`, `generate_2page_pdf.py` and the PDF (last saved 19 Oct 19:17) are still unchanged, so this plan has not been executed yet. Reading them found gaps in the steps above. Do steps 1-10 AND the extra steps below.

### Gaps in step 7 (the search)
The generator is HTML, so `< RM 50` is written there as `&lt; RM 50`. A search for the plain string misses it. Also search for: `&lt; RM 50`, `RM 50`, `BOM &lt;`, `20 to 50`, `Circular Energy`.

### Extra steps (apply in BOTH the `.md` and the generator text where the passage exists in both)
11. Page 2 header badge in the generator only: `Hardware BOM &lt; RM 50` becomes `Pilot kit about RM 170`. (Not in the `.md`.)
12. Generator Figure 1 caption: `45 features per 5-second window` becomes `32 signal features per 5-second window`. The caption also says `10 real wash cycles`: change to `10 real wash sessions archived`. Do the same for the `10 real wash cycles` in section 6 of both files. (Guide §4: 10 sessions archived, 8 healthy cycles in the evaluation set.)
13. Equipment counts are not allowed until confirmed (guide §4 "Not allowed until confirmed"). Replace `20 to 50+ commercial AC compressors daily` / `20 to 50+ AC units every day` (section 2) and `20 to 50 AC units and pumps` (section 6) with wording that gives no count, for example `many AC units` / `AC units and pumps`.
14. Section 4, contractors bullet in the generator: `empowered with automated, predictive repair dispatching` is a feature we have not built. Use the `.md` wording instead (technicians told which machine needs a look).
15. Figure 1 caption says "Our Working Sensor Pod & Live Dashboard" but the image is `washer_electronics_layout_diagram.jpg` (a layout diagram, not a photo). Retitle it `Figure 1: Sensor pod layout` and do not describe it as a photo of the live rig. Do not add or swap images in this task.

### DECISION FOR ADAM (ask in chat; do not change until answered)
The brief says track `PLANET (Energy Efficiency & Circular Economy)` and the generator badge says `Track: PLANET (Circular Energy)` (not a real track name). `VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md` says the official pick is `PLANET -> 02 Circular Economy`, with energy in the story only. The rules say pick one focus area. Brief, video and deck must name the same track. Recommended: `PLANET: 02 Circular Economy`, with energy kept as part of the story.

### Extra acceptance criteria
- [x] Header badge on page 2 no longer says `< RM 50` (check `&lt; RM 50` too).
- [x] Neither file contains `20 to 50` or `Circular Energy`; the PDF caption says `32 signal features` and `10 real wash sessions archived`.
- [x] The generated `proposal_2page_presentation.html` may change (it is a by-product of the generator); no other file outside the list changes.
- [x] HANDOFF.md is updated with a new section for this task (the current HANDOFF.md still ends at the 19 Oct sessions).
