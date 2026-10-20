# Handoff to Claude (Architect)

**Plan:** Small fix to the 2-page brief: label which data the leave-one-cycle-out test used, and soften two claims
**Date:** 2026-10-20 11:47, Asia/Kuala_Lumpur
**Status:** COMPLETE

## Commits
- `c6d37fe` docs(proposals): label LOCO data schema, soften two claims
- **Branch:** main

## What Changed
- **Section 6 LOCO Data Label:** Clarified that the leave-one-cycle-out test evaluated earlier snapshot-format data before the 32-feature windows (`Leave-one-cycle-out test on 8 healthy cycles (earlier snapshot-format data, before the 32-feature windows): 0 falsely flagged (95% upper bound 31%); a simulated doubling of sound was caught in 7 of 8.`). Applied identically to `PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md` and Figure 1 caption in `generate_2page_pdf.py`.
- **Section 5 Claim Softened:** Replaced bullet heading `Fewer False Alarms by Design` with `Built to Reduce False Alarms` in both `.md` and `generate_2page_pdf.py`.
- **Figure 1 Dashboard Claim Softened:** Replaced `Live Global Dashboard: Operational worldwide at` with `Live Dashboard: open to anyone at` in `generate_2page_pdf.py`.
- **Banned Strings Verified:** Confirmed neither `by Design` nor `worldwide` appears in the markdown brief or generator script.
- **Compiled PDF Verified:** Rebuilt PDF with `py -3 docs/proposals/generate_2page_pdf.py` (`Total Pages: 2`, 1152.0 KB). Rendered both pages to PNG at 150 DPI and confirmed visually: no text cut off or hidden by page container overflow, ~15-20 mm bottom whitespace margin remains on Page 2.

## Files Changed
- `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`: Updated LOCO bullet with snapshot-format dataset qualification; updated Section 5 bullet title to "Built to Reduce False Alarms".
- `docs/proposals/generate_2page_pdf.py`: Synchronized Section 5 heading, Figure 1 caption LOCO wording, and softened live dashboard caption.
- `docs/proposals/proposal_2page_presentation.html`: Recompiled presentation HTML by-product.
- `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.pdf`: Recompiled 2-page PDF.
- `docs/handoffs/PLAN.md`: Marked criteria and status as DONE.
- `docs/handoffs/HANDOFF.md`: Updated handoff document.

## Acceptance Criteria
- [x] Both files carry the new LOCO wording from step 1, identical in the `.md` and the generator — verified.
- [x] `by Design` and `worldwide` appear in neither file — verified via python case-insensitive search.
- [x] `py -3 docs/proposals/generate_2page_pdf.py` reports `Total Pages: 2`; both pages checked by eye for cut-off text, result recorded — verified Edge headless build reports `Total Pages: 2` (1152.0 KB); PyMuPDF rendering inspected visually, bottom margins clean on both pages.
- [x] HANDOFF.md contains the `Open UNVERIFIED items (carried forward)` section — verified.
- [x] No file changed other than the `.md`, the generator, the regenerated HTML and PDF, PLAN.md and HANDOFF.md; no secrets in the diff — verified.

## Tests Run
- `py -m py_compile docs/proposals/generate_2page_pdf.py` — PASS
- `py -3 docs/proposals/generate_2page_pdf.py` — PASS (`Total Pages: 2`, 1152.0 KB)
- Python forbidden-strings audit (`by design`, `worldwide`) — PASS (`CLEAN`)

## Invariants Check
- All items in `INVARIANTS_DO_NOT_CHANGE.md` respected. No data modified under `data/`, no firmware touched, no secrets in diff.

## Open UNVERIFIED items (carried forward)
- A real wash on firmware 07: session start, END marker, archive step (`INVARIANTS_DO_NOT_CHANGE.md` §2).
- Active-wash polling: `/api/live` no faster than 10 s and `/sessions/...` no faster than 30 s (19 Oct dashboard task, criterion 4).
- Session-change reset and live gap breaks during a real wash (criterion 13).
- Visual check of `historical.html` on session `wash_cycle_2026-10-19_0911`.
- Live DevTools network checks: idle polling at least 25 s, `historical.html` zero live requests, pause/AFK/tab-hidden behaviour.
- `/window.json` and `washer-pdm.local` reachability; the `WHO_AM_I` 0x75 quirk (not a failure).

## Blocked / Questions
- None.

## Suggestions for Claude
- None.
