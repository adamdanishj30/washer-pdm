# Handoff to Claude (Architect)

**Plan:** Remove the hardcoded Firebase secret from the Google Apps Script copy and mark the script as legacy (not for firmware 07)
**Date:** 2026-10-20 12:35, Asia/Kuala_Lumpur
**Status:** COMPLETE

## Commits
- `ad99735` fix(scripts): remove hardcoded Firebase secret from legacy Apps Script
- **Branch:** main

## What Changed
- **Removed Hardcoded Fallback Secret:** In `scripts/google_apps_script_drive_sync.js`, replaced `FIREBASE_AUTH = SCRIPT_PROPS.getProperty("FIREBASE_AUTH") || "<literal>"` with strict retrieval from Script Properties `SCRIPT_PROPS.getProperty("FIREBASE_AUTH")`.
- **Archive PUT Guard:** Added a defensive check before calling `UrlFetchApp.fetch` for `archived_sessions/${sessionId}.json`. If `FIREBASE_AUTH` is missing or empty, it logs a clear message and skips the write instead of failing or sending an unauthenticated request.
- **Added Deprecation/Legacy Banner:** Added an explicit `[LEGACY / DEPRECATED]` header banner warning that the Apps Script is legacy (writes 5-column CSVs, drops firmware-07 features, uses outdated 25s timeout), instructing operators not to deploy or run `installTrigger` for firmware 07.
- **Updated Setup Instructions:** Updated QUICK SETUP steps to instruct setting `FIREBASE_AUTH` in Script Properties without hardcoded code values.
- **Updated Tech Stack in CLAUDE.md:** Updated line 14 under Tech Stack to document that `firmware/auto_drive_sync_daemon.py` is the current quota-aware archiver and Google Apps Script is legacy.
- **Verified Zero Leaked Secrets in Tracked Files:** Verified via `git grep -l -F` that zero tracked files in the working tree contain the Firebase secret literal.
- **Validated Syntax:** Verified `scripts/google_apps_script_drive_sync.js` syntax via `node -e "new Function(...)"`.
- **Local Commit Only:** Committed locally without pushing, per plan instructions, awaiting Adam's manual secret rotation on Firebase and GitHub.

## Files Changed
- `scripts/google_apps_script_drive_sync.js`: Stripped hardcoded secret fallback, added guard check before archive PUT, added legacy header banner and setup docs.
- `CLAUDE.md`: Updated Tech Stack to note Google Apps Script is legacy and `auto_drive_sync_daemon.py` is the current archiver.
- `docs/handoffs/PLAN.md`: Marked acceptance criteria and status as DONE.
- `docs/handoffs/HANDOFF.md`: Recorded handoff documentation.

## Acceptance Criteria
- [x] The Apps Script contains no `FIREBASE_AUTH` fallback and no credential literal — verified via `git grep -l -F` and code inspection.
- [x] The authenticated PUT is skipped with a log message when the Script Property is missing — verified in `scripts/google_apps_script_drive_sync.js`.
- [x] LEGACY banner and updated setup steps present — verified in header comments.
- [x] Step 5 search: no tracked working-tree file contains the Firebase secret (paths only reported) — verified; 0 tracked files found.
- [x] Step 6 parse check passes — verified via `node -e "new Function(...)"`.
- [x] `CLAUDE.md` marks the Apps Script as legacy — verified in Tech Stack line 14.
- [x] Only the script, `CLAUDE.md`, PLAN.md and HANDOFF.md changed; no credential value in any diff, log or doc; commit local, not pushed — verified.

## Tests Run
- `node -e "new Function(require('fs').readFileSync('scripts/google_apps_script_drive_sync.js','utf8'))"` — PASS
- `git grep -l -F` scan for Firebase secret across tracked files — PASS (0 tracked files contain secret)

## Invariants Check
- All items in `INVARIANTS_DO_NOT_CHANGE.md` respected. Zero secret literals printed, logged, or committed; firmware, ML, and dashboard files untouched; Apps Script preserved in place without deletion.

## Open UNVERIFIED items (carried forward)
- Whether the Apps Script trigger is still deployed (Adam to check `script.google.com`).
- Workflow run with real GitHub secrets (needs Adam to set them, then a manual `workflow_dispatch`).
- A real wash on firmware 07: session start, END marker, archive step (`INVARIANTS_DO_NOT_CHANGE.md` §2).
- Active-wash polling: `/api/live` no faster than 10 s and `/sessions/...` no faster than 30 s (19 Oct dashboard task, criterion 4).
- Session-change reset and live gap breaks during a real wash (criterion 13).
- Visual check of `historical.html` on session `wash_cycle_2026-10-19_0911` and `wash_cycle_2026-10-20_0744`.
- Live DevTools network checks: idle polling at least 25 s, `historical.html` zero live requests, pause/AFK/tab-hidden behaviour.
- `/window.json` and `washer-pdm.local` reachability; the `WHO_AM_I` 0x75 quirk (not a failure).

## Blocked / Questions
- None. Commit is held locally as planned pending Adam's manual secret rotation steps.

## Suggestions for Claude
- Once Adam confirms secret rotation on Firebase and setting GitHub secrets, both local commits (`8b69a09` and this commit) can be pushed to `origin/main`. Then queue `PLAN_QUEUED_2_regenerate_pdfs_after_number_sync.md`.
