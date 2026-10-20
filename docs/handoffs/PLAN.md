# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Re-export the 3 stale Hackathon PDFs with a small reusable script, and add two handoff rules (diff file, no amending)
**Date:** 2026-10-20

## Objective
`Hackathon/SCRIPT_READ_ALOUD.pdf`, `VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.pdf` and `SDP_HACKATHON_BRIEFING_SUMMARY.pdf` were hand-printed before Claude's 12:30 edits, so speakers may record from old lines. After this task they match their `.md` sources and can be re-made with one command. Two workflow rules are also added to save review effort.

## Review verdict that produced this plan
APPROVED: `8fe52df` (2-page brief PDF regenerated; 2 pages, no cut-off, stale strings gone). Light review (handoff only; PDF-only task). Hash question resolved: `084b74f` -> `8b69a09` and `ad99735` -> `98892ba` were amends to write each commit's own hash into HANDOFF, which changes the hash every time. Harmless (unpushed, scopes clean, no credentials) but must stop (rule 2 below).

## Implementation Steps
1. Create `Hackathon/export_md_pdfs.py` (exhaustive comments, section headers): for each of the three `.md` files, convert Markdown to HTML (`pip install markdown`; enable the `tables` and `fenced_code` extensions), wrap it in a simple print stylesheet (A4, readable font, table borders, no page-breaking inside table rows), and print it to the same-named `.pdf` with Edge headless, the same way `docs/proposals/generate_2page_pdf.py` does. Write the intermediate HTML to a temp folder, not into `Hackathon/`.
2. Run it. Open each PDF (render pages to PNG) and check: tables readable and not cut at the right edge, the `SCRIPT_READ_ALOUD` P4 section shows "eleven recorded wash sessions" and the "Then the AI learns…" line, and `VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT` shows "v3.1" and the 2:41 row. Report page counts.
3. Add two rules to `.agents/rules/architect-handoff-workflow.md` (create a "Handoff rules" section if needed):
   - Rule 1: Every handoff saves the full diff of the task's commit(s) to `docs/handoffs/last_diff.patch` (overwrite each time; exclude binary files and generated pages `index.html`, `dashboard.html`, `cloud_dashboard.html`, `historical.html`, `*.pdf`, `proposal_*presentation.html`; list excluded files by name with their size change). HANDOFF links to it.
   - Rule 2: Never `git commit --amend`. Record the commit hash in HANDOFF without committing HANDOFF again, or commit HANDOFF in a separate follow-up commit.
4. Write HANDOFF.md (keep `Open UNVERIFIED items (carried forward)`), and apply rule 1 for this task. Commit locally: `docs(hackathon): add md-to-pdf export script, re-export stale PDFs`. Do not push (pushing waits for Adam's secret rotation).

## Out of Scope
- Any text change in the `.md` sources (report wrong numbers; don't fix them).
- The 2-page brief, the master dossier, firmware, dashboard, ML, data, `.github/`.

## Acceptance Criteria
- [x] `Hackathon/export_md_pdfs.py` regenerates all three PDFs in one run.
- [x] Each PDF checked by eye (tables, no cut-off); the two content checks in step 2 pass; page counts reported.
- [x] Both rules added to `.agents/rules/architect-handoff-workflow.md`.
- [x] `docs/handoffs/last_diff.patch` exists for this task.
- [x] No amend; only the script, the three PDFs, the rules file, PLAN.md, HANDOFF.md and the patch file changed; not pushed.
