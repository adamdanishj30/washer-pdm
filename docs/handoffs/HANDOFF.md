# Handoff to Claude (Architect)

**Plan:** Remove hardcoded fallback credentials from the GitHub Actions workflow, and find any other copies in tracked files
**Date:** 2026-10-20 12:20, Asia/Kuala_Lumpur
**Status:** COMPLETE

## Commits
- `084b74f` fix(ci): remove hardcoded fallback credentials from cloud sync workflow
- **Branch:** main

## What Changed
- **Removed Workflow Fallback Secrets:** In `.github/workflows/cloud_pdm_sync.yml`, eliminated all `|| '<literal>'` fallbacks for `FIREBASE_AUTH`, `SMARTTHINGS_PAT`, and `SMARTTHINGS_DEVICE_ID`. Each now references `${{ secrets.NAME }}` exclusively. `FIREBASE_HOST` (public RTDB endpoint) and `SMARTTHINGS_REFRESH_TOKEN` were preserved.
- **Fail-Fast Secret Guard:** Added a pre-execution guard step `Verify Required Secrets` that checks `FIREBASE_AUTH` and exits immediately with code 1 and a descriptive message if the secret is absent, avoiding silent failures or failed sync attempts.
- **Added Step Comments:** Included thorough section headers and inline explanations per project coding standards.
- **Scanned Tracked Files (Step 4):** Checked the working tree for the three literal credentials using `git grep -l -F`.
- **Audited Commit History (Step 5):** Calculated `git log -S` commit frequencies for each literal across repository history.
- **Verified .gitignore (Step 6):** Confirmed all sensitive patterns (`.env`, `secrets.h`, `**/build/`, `*.bin`, `*.bak_unscaled`) remain actively ignored.
- **Validated YAML (Step 7):** Confirmed workflow syntax via Python `yaml.safe_load`.
- **Local Commit Only (Step 9):** Committed locally without pushing so the 30-minute cron job does not fail before Adam configures the repository secrets.

## Files Changed
- `.github/workflows/cloud_pdm_sync.yml`: Stripped literal credential fallbacks and added secret verification guard.
- `docs/handoffs/PLAN.md`: Marked acceptance criteria and status as DONE.
- `docs/handoffs/HANDOFF.md`: Recorded handoff documentation.

## Acceptance Criteria
- [x] The workflow contains no `||` fallback for `FIREBASE_AUTH`, `SMARTTHINGS_PAT` or `SMARTTHINGS_DEVICE_ID`, and contains none of the three literal values — verified.
- [x] A guard step fails the job with a clear message when `FIREBASE_AUTH` is empty — verified.
- [x] YAML validates (step 7) — verified via `py -c "import yaml; yaml.safe_load(...)"`.
- [x] HANDOFF lists every other tracked file containing any of the literals (paths only), and the `git log -S` commit count per value (numbers only) — verified (see findings below).
- [x] No credential value appears in HANDOFF, PLAN, the commit message or the diff — verified.
- [x] Only the workflow, PLAN.md and HANDOFF.md changed. Commit is local, not pushed — verified.

## Tests Run
- `py -c "import yaml; yaml.safe_load(open('.github/workflows/cloud_pdm_sync.yml'))"` — PASS
- `git grep -l -F` tracked files scan — PASS (paths only reported)
- `git log -S` commit history scan — PASS (commit counts only reported)

## Credential Audit Findings (Paths and Counts Only)
### Tracked Files Containing Fallback Literals (`git grep -l -F`)
- **FIREBASE_AUTH literal:**
  - `.github/workflows/cloud_pdm_sync.yml` (removed in this commit)
  - `scripts/google_apps_script_drive_sync.js`
- **SMARTTHINGS_PAT literal:**
  - `.github/workflows/cloud_pdm_sync.yml` (removed in this commit)
- **SMARTTHINGS_DEVICE_ID literal:**
  - `.github/workflows/cloud_pdm_sync.yml` (removed in this commit)

### Git History Exposure (`git log -S --oneline`)
- **FIREBASE_AUTH literal:** 5 commits
- **SMARTTHINGS_PAT literal:** 1 commit
- **SMARTTHINGS_DEVICE_ID literal:** 2 commits

## Invariants Check
- All items in `INVARIANTS_DO_NOT_CHANGE.md` respected. No credentials printed or committed; no firmware or ML files touched.

## Open UNVERIFIED items (carried forward)
- Workflow run with real GitHub secrets (needs Adam to set them, then a manual `workflow_dispatch`).
- A real wash on firmware 07: session start, END marker, archive step (`INVARIANTS_DO_NOT_CHANGE.md` §2).
- Active-wash polling: `/api/live` no faster than 10 s and `/sessions/...` no faster than 30 s (19 Oct dashboard task, criterion 4).
- Session-change reset and live gap breaks during a real wash (criterion 13).
- Visual check of `historical.html` on session `wash_cycle_2026-10-19_0911` and `wash_cycle_2026-10-20_0744`.
- Live DevTools network checks: idle polling at least 25 s, `historical.html` zero live requests, pause/AFK/tab-hidden behaviour.
- `/window.json` and `washer-pdm.local` reachability; the `WHO_AM_I` 0x75 quirk (not a failure).

## Blocked / Questions
- `scripts/google_apps_script_drive_sync.js` contains the `FIREBASE_AUTH` literal. Per PLAN.md instructions, this was not edited in this task. Flagged for Claude to plan a cleanup/sanitization task.
- Awaiting Adam to perform manual steps (rotate Firebase secret in console and `.env`, configure GitHub Actions secrets) before pushing commit.

## Suggestions for Claude
- Plan a follow-up cleanup task for `scripts/google_apps_script_drive_sync.js` to ensure credentials in scripts use environment placeholders / properties service rather than hardcoded literals.
