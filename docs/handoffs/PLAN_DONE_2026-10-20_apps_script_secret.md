# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Remove the hardcoded Firebase secret from the Google Apps Script copy and mark the script as legacy (not for firmware 07)
**Date:** 2026-10-20

## Objective
`scripts/google_apps_script_drive_sync.js` still has a hardcoded `FIREBASE_AUTH` fallback (`getProperty("FIREBASE_AUTH") || "<literal>"`). After this task the repo copy contains no credential, refuses to run its Firebase write without the Script Property, and carries a clear LEGACY banner so nobody re-deploys it for firmware 07. Both local commits (this one and `084b74f`) are then pushed together after Adam rotates the secret.

## Queue note
`docs/handoffs/PLAN_QUEUED_2_regenerate_pdfs_after_number_sync.md` (PDF regeneration) runs after this one. Do not start it now.

## Review verdict that produced this plan
APPROVED: commit `084b74f` (CI fallback credentials removed). Claude read the workflow on disk: no `||` fallback for the three credentials, none of the literals, guard step present, YAML structure intact. Local commit only, as planned. History exposure reported by count only (Firebase secret: 5 commits; PAT: 1; device ID: 2), so rotation remains the real fix. The handoff flagged this Apps Script file; Claude read it and found more than the literal (below).

## Why (evidence, Claude read the file on 2026-10-20)
- Line ~32: `FIREBASE_AUTH = SCRIPT_PROPS.getProperty("FIREBASE_AUTH") || "<literal>"`, the same leaked secret as the workflow. Invariants §1 rule 2: no hardcoded fallback credentials anywhere.
- It writes a **5-column legacy CSV** (`timestamp_ms, accel_x, accel_y, accel_z, audio_rms`) into `data/`. For firmware-07 sessions that drops `vib_mag_std`, `vib_dom_hz`, power and the other 40 columns. The quota-aware daemon (`firmware/auto_drive_sync_daemon.py`) is the current archiver and writes the full 45-column record to `data/real_sessions/`.
- Its offline rule (25 s of no change in `/live`) predates the firmware-07 idle heartbeat (60 s), so if it is still deployed it would treat every idle gap as "offline". There are no 19/20 Oct files in `data/` from it, which suggests it is not running, but only Adam can confirm on script.google.com.

## Context
- Edit `scripts/google_apps_script_drive_sync.js` only. Do not delete or move it (Invariants §1 rule 1).
- Code style: exhaustive inline comments and clear section headers.
- **Never print, paste or log the credential value** in chat, HANDOFF, commit messages or test output.

## Implementation Steps
1. Replace the `FIREBASE_AUTH` line so it reads only `SCRIPT_PROPS.getProperty("FIREBASE_AUTH")` with no fallback. Leave the public `FIREBASE_HOST` fallback as is.
2. Before the authenticated `archived_sessions` PUT, skip the write and `Logger.log` a clear message if `FIREBASE_AUTH` is empty (e.g. "FIREBASE_AUTH Script Property not set; archive marker not written"). Keep the rest of the function's behaviour unchanged.
3. Add a LEGACY banner at the top of the header comment: superseded for firmware 07 by `firmware/auto_drive_sync_daemon.py`; it writes 5-column legacy CSVs and drops firmware-07 features; do not deploy or re-run `installTrigger` for firmware 07; credentials come only from Script Properties.
4. Update the "QUICK SETUP" steps in the header to say: set `FIREBASE_AUTH` in Project Settings -> Script Properties first (no value in code).
5. Verify with `git grep -l -F` (using the literal from the workflow's git history held in a local shell variable, never echoed) that no tracked file in the working tree contains the Firebase secret any more. Report paths only.
6. Syntax check: `node --check` cannot parse Apps Script globals reliably, so run `node -e "new Function(require('fs').readFileSync('scripts/google_apps_script_drive_sync.js','utf8'))"` to confirm it parses.
7. Update `CLAUDE.md` Tech Stack: mark "Google Apps Script (Cloud-to-Drive auto sync)" as legacy, with the daemon as the current archiver. One line.
8. Write HANDOFF.md (keep `Open UNVERIFIED items (carried forward)`; add "Whether the Apps Script trigger is still deployed (Adam to check script.google.com)"). Commit locally: `fix(scripts): remove hardcoded Firebase secret from legacy Apps Script`. **Do NOT push** until Adam confirms the manual steps below.

## Manual steps for Adam (add to the rotation already listed in `PLAN_DONE_2026-10-20_ci_fallback_credentials.md`)
1. Open https://script.google.com and look for the Washer PdM project. If it exists, open Triggers (clock icon) and delete the `checkRigAndSyncToDrive` trigger. It is superseded and would stop working after rotation anyway.
2. Rotate the Firebase database secret (Firebase console -> Project settings -> Service accounts -> Database secrets: add new, delete old). Put the new one in `.env` and in GitHub Actions secrets as `FIREBASE_AUTH`; re-flash firmware 07 via `flash_firmware.py` when no wash is running and confirm `/api/live` updates.
3. Revoke the old SmartThings PAT; set `SMARTTHINGS_DEVICE_ID` (and `SMARTTHINGS_REFRESH_TOKEN` if used) as GitHub secrets.
4. Tell Antigravity to push both commits, then run the workflow once from the Actions tab and confirm it passes.

## Out of Scope
- Rewriting git history.
- Any other file except `CLAUDE.md` (one line).
- Changing what the Apps Script archives or its schedule (it is being retired, not fixed).
- Firmware, dashboard, ML, data, `.github/`.

## Acceptance Criteria
- [x] The Apps Script contains no `FIREBASE_AUTH` fallback and no credential literal.
- [x] The authenticated PUT is skipped with a log message when the Script Property is missing.
- [x] LEGACY banner and updated setup steps present.
- [x] Step 5 search: no tracked working-tree file contains the Firebase secret (paths only reported).
- [x] Step 6 parse check passes.
- [x] `CLAUDE.md` marks the Apps Script as legacy.
- [x] Only the script, `CLAUDE.md`, PLAN.md and HANDOFF.md changed; no credential value in any diff, log or doc; commit local, not pushed.
