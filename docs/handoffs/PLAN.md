# Plan for Antigravity

**Status:** READY  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Fix: the auto-sync workflow must also commit `preset_sessions.js` (and `historical.html`)
**Date:** 2026-10-21

## Step 0
Before ANY other git command (no pull, stash, checkout or reset first): `git add docs/handoffs/PLAN.md` and commit `docs: plan preset_sessions deploy fix`. Then `git pull --rebase` (no `--autostash`).

## Review verdict that produced this plan
CHANGES NEEDED (small) on `065c7af`, `a441cb0` (shared `preset_sessions.js`). The page change itself is good. Claude checked: the pages are 153,000 / 153,016 B with no inline `const PRESET_SESSIONS`, the `?v=97c517e051` tag matches the sha256 of `preset_sessions.js`, the file holds 30 sessions and its JSON is the same length as the old inline object, and the `build_clean_dashboard.py` diff is only the emission and the `<script src>` tag. The live 200 is confirmed. (30 sessions including test fixtures is right; the plan's "13" was Claude's mistake.)

**The problem:** `.github/workflows/cloud_pdm_sync.yml` line 60 runs `git add data/ index.html dashboard.html cloud_dashboard.html`. When the 30-minute job archives a new wash and rebuilds, it commits pages that point at a new `?v=` hash and a new `FIRST_SESSION_KEY`, but not the new `preset_sessions.js`. Cloudflare then serves the old data under the new hash, so the newest wash is missing, and code that reads `LOADED_SESSIONS[activeSessionKey]` without a guard (e.g. `index.html` ~lines 2302, 3300) can get `undefined`. `historical.html` was already missing from that list before this change.

## Objective
Every path that commits rebuilt dashboard pages must also commit `preset_sessions.js` and `historical.html`. A missing session key must never throw.

## Implementation Steps
1. `.github/workflows/cloud_pdm_sync.yml`: change the `git add` line to `git add data/ index.html dashboard.html cloud_dashboard.html historical.html preset_sessions.js`. No other change to the workflow (secrets, schedule and steps untouched).
2. Search the repo (excluding `archive/`) for any other `git add` or commit of the dashboard pages (`scripts/`, `firmware/`, `functions/`, `.agents/`, README or CLAUDE commands). Fix each one the same way and list them all in HANDOFF. If there are none, say so.
3. In `build_clean_dashboard.py`'s page script, guard the reads of `LOADED_SESSIONS[activeSessionKey]` that are not guarded yet. If the key is missing, fall back to the first key of `LOADED_SESSIONS` (or to the live view if it is empty), with no exception. Touch only those lines. List each line changed.
4. Test: build normally, then edit a COPY of a built page (in a temp dir, never the repo files) so `activeSessionKey` is a key that is not in `PRESET_SESSIONS`. Open it headless over a local HTTP server and confirm 0 uncaught errors. Then re-run your 4-page headless check on the real build (0 errors, 31 dropdown options).
5. In `CLAUDE.md`, next to the dashboard build command, add one line: "Deploys need `preset_sessions.js` committed with the pages."
6. HANDOFF with the full template plus the carried-forward UNVERIFIED list. `last_diff.patch` per rule 6. Commit `fix(deploy): commit preset_sessions.js and historical.html with dashboard pages`. Pull --rebase (no autostash), push. Confirm the live `index.html` still loads (curl 200 for both files).

## Out of Scope
Polling, Firebase, charts, badge, session discovery, workflow secrets or schedule, `data/`, firmware, ML, proposal / `Hackathon/` / video files.

## Acceptance Criteria
- [ ] PLAN.md committed before any other git command.
- [ ] The workflow's `git add` includes `historical.html` and `preset_sessions.js`, and it is the only workflow change.
- [ ] HANDOFF lists every other place that commits pages, with fixes or "none found".
- [ ] Missing-key test: 0 uncaught errors on the temp copy. The real 4-page check still gives 0 errors and 31 options.
- [ ] Page-script diff touches only the guarded `LOADED_SESSIONS[activeSessionKey]` reads.
- [ ] Pushed; live files 200; hashes reported.

## Queue (do not start; Claude plans these only when Adam asks)
1. **Firmware: report reset reason** (+ `epochMs()` jitter 2.7–3.8 s). Needs a flash, so only if Adam says yes.
2. **ML: programme-aware evaluation** once each signature class has ≥ 3 firmware-07 cycles (today: Long cold 1, Long hot 1, Quick 2 firmware-07). No per-cycle normalisation, and no default retrain without a plan.
3. **Track the 7 untracked real session CSVs** if Adam says yes.
4. **Proposal submission files:** Adam's `Hackathon/NEEDS_CHANGING.md` batch, only when he says go.
