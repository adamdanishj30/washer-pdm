# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Small fix to the 2-page brief: label which data the leave-one-cycle-out test used, and soften two claims
**Date:** 2026-10-20

## Objective
The previous task (commit `8eec5dd`, sync of the 2-page brief) is reviewed and its steps were all done correctly. One honesty problem and two wording nits remain. After this task, the brief no longer suggests the leave-one-cycle-out (LOCO) result was measured on the 32-feature firmware-07 windows, and two claims that we have not shown are softened. Nothing else changes.

## Review verdict that produced this plan
CHANGES NEEDED (minor) on `8eec5dd`. All steps 1-15 and the track change were applied in both the `.md` and `generate_2page_pdf.py`; none of the banned strings remain; both files agree. Open points:
1. **Mixed evidence (must fix).** Section 6 puts "32 signal features per 5-second window (firmware-07 window record)" right next to the LOCO result. The LOCO test ran on the 8 earlier snapshot-format cycles (legacy schema, per `ml/models/loco_report.md` and CLAUDE.md), not on firmware-07 windows. A judge will read it as one validated pipeline. The same source (`ml/models/loco_report.md`) is the approved fact; only the label is missing.
2. **Nit.** "Fewer False Alarms by Design" states as fact something we have not measured (0 of 8 with a 31% upper bound).
3. **Nit.** "Live Global Dashboard: Operational worldwide" is a stronger claim than "public site".

## Why (evidence)
- `docs/proposals/PROPOSAL_WRITING_GUIDE.md` §4 (updated today by Claude): the LOCO row now says it must always be described as run on the earlier snapshot-format cycles.
- `docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md` §1 rule 3 and §4 (mixed firmware data must stay distinguishable; honest labels).

## Context
- Files to edit: `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md`, `docs/proposals/generate_2page_pdf.py`, then regenerate the PDF and the HTML by-product.
- Apply every change in BOTH the `.md` and the generator text wherever the passage exists in both.
- Keep length close to the original: the page boxes hide overflow.

## Implementation Steps
1. Section 6 "Model validation" (the `.md` bullet and the Figure 1 caption bullet in the generator). New wording: `Leave-one-cycle-out test on 8 healthy cycles (earlier snapshot-format data, before the 32-feature windows): 0 falsely flagged (95% upper bound 31%); a simulated doubling of sound was caught in 7 of 8.`
2. Section 5, bullet title `Fewer False Alarms by Design` becomes `Built to Reduce False Alarms`. Leave the rest of the bullet as it is.
3. Generator only, Figure 1 caption: `Live Global Dashboard: Operational worldwide at` becomes `Live Dashboard: open to anyone at`.
4. Search the `.md` and the generator for `by Design` and `worldwide`; none may remain.
5. Run `py -3 docs/proposals/generate_2page_pdf.py`; confirm `Total Pages: 2`.
6. Render both PDF pages to PNG and check the bottom of each page for cut-off text, as before. Record what you saw.
7. Write `HANDOFF.md` with the template, and add a section `Open UNVERIFIED items (carried forward)` listing these, each with its source, so they are not lost when the handoff is rewritten:
   - A real wash on firmware 07: session start, END marker, archive step (INVARIANTS §2).
   - Active-wash polling: `/api/live` no faster than 10 s and `/sessions/...` no faster than 30 s (19 Oct dashboard task, criterion 4).
   - Session-change reset and live gap breaks during a real wash (criterion 13).
   - Visual check of `historical.html` on session `wash_cycle_2026-10-19_0911`.
   - Live DevTools network checks: idle polling at least 25 s, `historical.html` zero live requests, pause/AFK/tab-hidden behaviour.
   - `/window.json` and `washer-pdm.local` reachability; the `WHO_AM_I` 0x75 quirk (not a failure).
8. Mark this plan DONE. Commit locally: `docs(proposals): label LOCO data schema, soften two claims`. Do not push unless the user says so.

## Out of Scope
- The master dossier (`PROPOSAL_Apex_PdM_Township_of_Tomorrow.md` and `generate_proposal_pdf.py`), the video script, the deck and the Q&A pack (Claude handles those next).
- Any firmware, dashboard, ML, daemon or `.github/` change; any file under `data/`.
- Secret rotation (manual task for Adam).

## Acceptance Criteria
- [x] Both files carry the new LOCO wording from step 1, identical in the `.md` and the generator.
- [x] `by Design` and `worldwide` appear in neither file.
- [x] `py -3 docs/proposals/generate_2page_pdf.py` reports `Total Pages: 2`; both pages checked by eye for cut-off text, result recorded.
- [x] HANDOFF.md contains the `Open UNVERIFIED items (carried forward)` section.
- [x] No file changed other than the `.md`, the generator, the regenerated HTML and PDF, PLAN.md and HANDOFF.md; no secrets in the diff.

## Risk Notes
- **Overflow:** the LOCO line gets about 60 characters longer; check page 2 bottom by eye.
- **Two sources of text:** edit both the `.md` and the generator in the same commit.
