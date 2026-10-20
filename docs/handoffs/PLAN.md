# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Remove hardcoded fallback credentials from the GitHub Actions workflow, and find any other copies in tracked files
**Date:** 2026-10-20

## Objective
`.github/workflows/cloud_pdm_sync.yml` still carries hardcoded fallback values for `FIREBASE_AUTH`, `SMARTTHINGS_PAT` and `SMARTTHINGS_DEVICE_ID` (the `secrets.X || '<literal>'` pattern). The repo link is a required hackathon submission item (due 23 Oct), so after this task no tracked file contains those literals and the workflow reads credentials only from GitHub secrets. Adam rotates the real credentials himself (see "Manual steps for Adam"); rotation is what makes the copies in git history useless.

## Review verdict that produced this plan
APPROVED (2026-10-20 12:10): commit `e8fe12a` (Load CSV parser reads firmware-07 columns). Claude diffed `build_clean_dashboard.py` (changes limited to the new header branch, comments and alert text; legacy loop, polling and `maxAgeMs` untouched) and re-ran parity independently on 5 real files: both firmware-07 files match Python `load_csv` with 0 mismatches and aligned nulls; all 3 legacy files give identical old/new output. Browser check still UNVERIFIED (Adam to do it).

Earlier: APPROVED commit `c6d37fe` (2-page brief: LOCO data label, two claims softened). Claude read the `.md` and `generate_2page_pdf.py`: the new LOCO wording is identical in both, `by Design` and `worldwide` are gone, the PDF (11:44:45) was rebuilt after the script (11:44:29), and the `Open UNVERIFIED items (carried forward)` section is present. Visual check of the PDF is taken from the handoff (Claude cannot open PDFs here). Claude could not run `git show` on the commit; file contents were checked instead.

## Why (evidence)
- `INVARIANTS_DO_NOT_CHANGE.md` §1 rule 2 and §5: no hardcoded fallback credentials anywhere; the workflow fallbacks "are to be removed, never copied".
- `current_state_and_scale_up_handoff.md` §4 step 1: rotate the Firebase secret and Wi-Fi password.
- `VIDEO_SCRIPT_AND_SLIDE_BLUEPRINT.md` Part 6: rotate secrets and check repo history before sharing the code link.

## Context
- File to edit: `.github/workflows/cloud_pdm_sync.yml` only.
- `FIREBASE_HOST` is the public database URL, not a secret; its fallback may stay.
- SmartThings PATs expire after 24 h, so that fallback is already dead, but it is still removed.
- **Never print, paste or log any credential value** in chat, HANDOFF, commit messages or test output. Report file paths and counts only.

## Implementation Steps
1. Before editing, copy the three literal fallback values from the workflow into local shell variables only (do not echo them). Keep them for steps 4 and 5.
2. In the workflow `env:` block, change `FIREBASE_AUTH`, `SMARTTHINGS_PAT` and `SMARTTHINGS_DEVICE_ID` to read `${{ secrets.NAME }}` with no `||` fallback. Leave `FIREBASE_HOST` and `SMARTTHINGS_REFRESH_TOKEN` as they are.
3. Add a step before "Execute Autonomous Cloud Sync" that fails the job with a clear message (e.g. `FIREBASE_AUTH secret is not set`) if `FIREBASE_AUTH` is empty, so a missing secret does not look like a silent sync failure. Add comments explaining each step (Adam's code-style rule).
4. Search every git-tracked file in the working tree (`git grep -l -F`, once per value) for the three literals. Report the matching file paths only. Do NOT edit any match outside the workflow; list them under Blocked / Questions for Claude to plan. `archive/` is included in this search (path list only; do not read the files).
5. For each literal, run `git log -S` with `--oneline` and report only the NUMBER of commits that contain it. This tells Adam how deep the history copies go.
6. Confirm `.gitignore` still ignores `.env`, `secrets.h`, `**/build/`, `*.bin`, `*.bak_unscaled`.
7. Validate the YAML: `py -c "import yaml,sys; yaml.safe_load(open('.github/workflows/cloud_pdm_sync.yml'))"` (install `pyyaml` if missing).
8. Write HANDOFF.md with the template, keeping the `Open UNVERIFIED items (carried forward)` section from the previous handoff and adding: "Workflow run with real GitHub secrets (needs Adam to set them, then a manual `workflow_dispatch`)".
9. Mark this plan DONE. Commit locally: `fix(ci): remove hardcoded fallback credentials from cloud sync workflow`. **Do NOT push.** Pushing before Adam sets the GitHub secrets makes the 30-min cron fail.

## Out of Scope
- Rewriting git history (BFG / filter-repo). Rotation makes old values useless; history rewriting is a separate decision for Adam.
- Any file other than the workflow (matches found in step 4 are reported, not fixed).
- Firmware, dashboard, ML, data, proposal files.
- Rotating credentials (manual, below).
- The workflow commits `index.html dashboard.html cloud_dashboard.html` but not `historical.html`; note it, do not change it.

## Manual steps for Adam (before Antigravity pushes)
1. Firebase console → Project settings → Service accounts → Database secrets: add a new secret, then delete the old one. Put the new one in `.env` (`FIREBASE_AUTH`) and in GitHub → repo Settings → Secrets and variables → Actions as `FIREBASE_AUTH`. Re-flash firmware 07 with the new secret via `flash_firmware.py` (not during a wash) and confirm `/api/live` updates.
2. SmartThings: revoke the old PAT at account.smartthings.com/tokens; set `SMARTTHINGS_DEVICE_ID` (and `SMARTTHINGS_REFRESH_TOKEN` if used) as GitHub secrets.
3. Change the Wi-Fi password, update `.env`, re-flash.
4. Add `OTA_PASS` to `.env`.
5. Tell Antigravity to push, then run the workflow once by hand (Actions tab → Run workflow) and check it passes.

## Acceptance Criteria
- [x] The workflow contains no `||` fallback for `FIREBASE_AUTH`, `SMARTTHINGS_PAT` or `SMARTTHINGS_DEVICE_ID`, and contains none of the three literal values.
- [x] A guard step fails the job with a clear message when `FIREBASE_AUTH` is empty.
- [x] YAML validates (step 7).
- [x] HANDOFF lists every other tracked file containing any of the literals (paths only), and the `git log -S` commit count per value (numbers only).
- [x] No credential value appears in HANDOFF, PLAN, the commit message or the diff.
- [x] Only the workflow, PLAN.md and HANDOFF.md changed. Commit is local, not pushed.

## Risk Notes
- **Leaking while fixing:** printing a value in a test log or handoff recreates the leak. Paths and counts only.
- **Broken cron:** removing the fallback before the GitHub secret exists makes every 30-min run fail. Hence no push until Adam confirms.
