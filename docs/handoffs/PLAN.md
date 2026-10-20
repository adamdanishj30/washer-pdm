# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Regenerate the 2-page brief PDF (and the Hackathon doc PDFs, if they have a generator) after Claude's 20 Oct number sync
**Date:** 2026-10-20

## Review verdict that produced this plan
APPROVED (2026-10-20 12:50): commit `ad99735` (Apps Script secret removed). Claude read `scripts/google_apps_script_drive_sync.js` on disk: no credential literal, `FIREBASE_AUTH` from Script Properties only, the authenticated PUT is skipped with a log message when it is missing, LEGACY banner present; `CLAUDE.md` names the daemon as the current archiver. One inconsistency: the handoff says to push "`8b69a09` and this commit", but the CI credentials commit was reported as `084b74f`. Step 0 below resolves it.

## Objective
Claude updated the text of several docs on 20 Oct 12:30 (numbers re-counted after the 20 Oct wash; one labelled model-test line added; "4 sensors" changed to "3 sensors, machine state planned"). The PDFs were not regenerated, so they are stale. After this task, every PDF matches its source text.

## What Claude changed (text only, already saved)
- `docs/proposals/PROPOSAL_WRITING_GUIDE.md` §2, §3, §4, §7: 11 sessions, 8,379 rows, 19.9 Hz in both firmware-07 washes, phase labels not saved, programme/load not logged, LOCO wording rules, 3 sensors.
- `docs/proposals/PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.md` and `generate_2page_pdf.py` (same changes in both): metric strip 11 / 3, "Machine State (planned)", "66-minute cycle on 19 Oct" (was "latest"), data-in-hand 11 sessions / 8,379 rows.
- `docs/proposals/HACKATHON_INFO_AND_AI_EXECUTIVE_SUMMARY.md`: numbers, 3 sensors, LOCO line, two new judge Q&As; Q2 = 175 words, Q3 = 178 words (limits 180).
- `Hackathon/VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md` (v3.1) and `Hackathon/SCRIPT_READ_ALOUD.md`: demo segment 2:36 and 2:41 lines, slides 6 and 8, ML note, decision line.
- `Hackathon/SDP_HACKATHON_BRIEFING_SUMMARY.md` §10 and `docs/handoffs/current_state_and_scale_up_handoff.md` §5: numbers.

## Implementation Steps
0. Read-only check, no push: run `git log origin/main..HEAD --oneline` and paste the full list into HANDOFF. Expected: `084b74f` (CI fallback credentials) and `ad99735` (Apps Script), plus this task's commit once made. Explain any other hash (e.g. `8b69a09`): which task it came from and whether it was rebased or amended. Run `git show --stat` on each unpushed commit and confirm none touches a file outside what its plan allowed and none adds a credential (check with the local-variable method from the CI plan; never print a value).
1. Run `py -3 docs/proposals/generate_2page_pdf.py`; confirm `Total Pages: 2`.
2. Render both pages to PNG and check the bottom of each page by eye for cut-off text (the page boxes hide overflow). The "Machine State (planned)" box text is ~10 characters longer than before; check that box too.
3. Search the regenerated PDF text for `7,414`, `10 real`, `Archived`, `latest 66`, and confirm none remain; confirm `8,379` and `11` appear.
4. `Hackathon/*.pdf` (VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT, SCRIPT_READ_ALOUD, SDP_HACKATHON_BRIEFING_SUMMARY): find how they were produced (search the repo for a generator or the command used). If there is a generator, regenerate them and check by eye. If there is none, do NOT invent one: list them in HANDOFF as stale so Adam can re-export or delete them.
5. Write HANDOFF.md (keep the `Open UNVERIFIED items (carried forward)` section). Commit locally: `docs(proposals): regenerate PDFs after 20 Oct number sync`. Push only if Adam says so.

## Out of Scope
- Any text change (if you find a wrong number, report it; do not fix it).
- The master dossier (`PROPOSAL_Apex_PdM_Township_of_Tomorrow.*`, under rewrite).
- Firmware, dashboard, ML, data, `.github/`.

## Acceptance Criteria
- [x] 2-page PDF regenerated, `Total Pages: 2`, both pages checked by eye, no cut-off text.
- [x] Step 3 search clean.
- [x] Hackathon PDFs regenerated with their real generator, or listed as stale in HANDOFF.
- [x] Only PDFs, the regenerated `proposal_2page_presentation.html`, PLAN.md and HANDOFF.md changed.
- [x] Step 0: unpushed commit list pasted into HANDOFF, every hash explained, `git show --stat` scope confirmed, no credentials. Nothing pushed (pushing waits for Adam's secret rotation).
