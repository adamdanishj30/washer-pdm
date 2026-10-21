# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Repo hygiene: commit untracked source files (after a secrets scan) and mark `capture_pdm_dataset.py` as legacy
**Date:** 2026-10-21

## Step 0
Before ANY other git command (no pull, stash, checkout or reset first): `git add docs/handoffs/PLAN.md` and commit `docs: plan repo hygiene`. Then `git pull --rebase` (no `--autostash`).

## Review verdict that produced this plan
APPROVED: `ef627d7`, `f40d373` (synthetic test isolation, energy note). Adam asked on 21 Oct to finish the queue.

## Objective
Adam will put the repo link in the hackathon proposal. In the last patch, `ml/train_unsupervised_pdm.py` and `ml/tests/test_pipeline_synthetic.py` showed as `new file`, so source code may have been missing from git. Make sure every source file is tracked and nothing secret is. Also stop `firmware/capture_pdm_dataset.py` from looking like the production path. It still computes a load guess and "parasitic drag", and production archiving no longer uses it.

## Context
- `.gitignore` already excludes `.env`, `.env.local`, `secrets.h`, `.smartthings_token_cache.json`, `*.bin`, `**/build/`, `firmware/tapo-esp32-ref/`, `.agents/*`.
- `CLAUDE.md` lines ~55, 56, 62 and 76 present `capture_pdm_dataset.py` as a normal command or tool.
- Never read or list inside `archive/`. Never modify `data/real_sessions/*.csv`.

## Implementation Steps
1. Run `git status --porcelain --untracked-files=all` (gitignored files excluded). Put the full list in HANDOFF, grouped as: source (`.py`, `.ino`, `.h`, `.js`, `.html`, `.md`, `.json` configs), data (`data/`), and other. Skip anything under `archive/`, and only count it.
2. Secrets scan on every untracked **source** file before adding. Search case-insensitively for: `password`, `passwd`, `secret`, `token`, `api_key`, `apikey`, `auth=`, `FIREBASE_AUTH`, `WIFI_PASS`, `Bearer `, long base64-like strings (≥ 32 chars), and the Wi-Fi SSID `leo` assigned next to a password. List every hit in HANDOFF with file:line and whether it is a real value or just a variable name or comment. Do NOT add any file with a real value; list it under Blocked for Adam.
3. `git add` only the clean untracked source files, and commit `chore: track untracked source files (secrets-scanned)`. Do not add `data/` files in this task: list them, with sizes, for Adam to decide.
4. Also check what IS tracked: `git ls-files | grep -iE "\.env|secrets\.h|token_cache|\.bin$"` must be empty. If not, stop and report under Blocked. Do not rewrite history.
5. `firmware/capture_pdm_dataset.py`: add a banner at the top of the docstring: "LEGACY (not used by production archiving since firmware 07). Its load guess and 'parasitic drag' are uncalibrated heuristics, not measurements. Production path: `firmware/auto_drive_sync_daemon.py` + `firmware/session_export.py`." (Confirm those two paths are the production archive path. If not, name the right ones.) Add a one-line `print` warning with the same meaning at the start of `main()`. Do not change any computation.
6. `CLAUDE.md`: mark the capture-script commands (lines ~55–56) and the tree entry (~76) as "legacy, not the production path". Keep the `py_compile` line.
7. Run all tests (`ml/tests/*`, `firmware/tests/*`) and `py -m py_compile` on the edited script.
8. HANDOFF with the full template, the untracked-file list, the secrets-scan table, the carried-forward UNVERIFIED list, and an answer: "Is every `.py` under `ml/` and `firmware/` now tracked? yes/no". `last_diff.patch` per rule 6 (list newly tracked files by name and size in the stat, since their full content is not a change to review). Commit `chore: mark capture_pdm_dataset.py legacy`. Pull --rebase (no autostash), push.

## Out of Scope
History rewriting, deleting or moving files, `archive/`, `data/` contents, any computation change, firmware `.ino`, dashboard, proposal / `Hackathon/` / video files, secret rotation (Adam's job).

## Acceptance Criteria
- [x] PLAN.md committed before any other git command.
- [x] HANDOFF lists every untracked file found, grouped, and the secrets-scan result for each source file.
- [x] No file containing a real secret value was added. `git ls-files` shows no `.env`, `secrets.h`, token cache or `.bin`.
- [x] Every clean source file under `ml/`, `firmware/`, `docs/` and the repo root is tracked (`git status --porcelain` shows no untracked source).
- [x] `capture_pdm_dataset.py` has the LEGACY banner and warning, and its code diff is only those lines.
- [x] `CLAUDE.md` marks the capture script as legacy.
- [x] All tests pass (dsp parity SKIP allowed). Pushed; hashes reported.

## Queue (do not start; Claude plans these only when Adam asks)
1. **Dashboard page budget** (787.7 KB of 800 KB) before any new dashboard feature. Next plan.
2. **Firmware: report reset reason** (+ `epochMs()` jitter 2.7–3.8 s). Needs a flash, so only if Adam says yes.
3. **ML: programme-aware evaluation** once each signature class has ≥ 3 firmware-07 cycles (today: Long cold 1, Long hot 1, Quick 2 firmware-07). No per-cycle normalisation. Note: with 4 firmware-07 cycles, a default retrain now switches to the windowed schema (`MIN_WINDOWED_CYCLES = 3`) and overwrites `loco_report.*`. Do not retrain without a plan.
4. **Proposal submission files:** Adam's `Hackathon/NEEDS_CHANGING.md` batch, only when he says go.
