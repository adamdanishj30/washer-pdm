# Architect ↔ Executor Handoff Workflow (Washer PdM SideProject)

This rule applies ONLY to this repository. It sits alongside `AGENTS.md` and
`CLAUDE.md`; it does not replace them. If anything here conflicts with
`docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md`, the invariants file wins.

---

## 1. Roles

- **Claude (Architect / Reviewer):** plans work, sets acceptance criteria,
  reviews results. Writes `docs/handoffs/PLAN.md`.
- **Antigravity (Executor):** implements the plan, runs tests, commits, and
  writes `docs/handoffs/HANDOFF.md`.
- The user moves between the two. Both sides read and write the files above,
  so nothing needs to be copy-pasted.

---

## 2. Before Starting Any Task

1. Read `docs/handoffs/PLAN.md`. If it is missing, empty, or marked `Status: DONE`,
   stop and ask the user what to do. Do not invent a task.
2. Read `docs/handoffs/INVARIANTS_DO_NOT_CHANGE.md` before editing firmware,
   dashboards, scripts, or ML code.
3. Follow the Archive Quarantine rule: never read, scan, or grep `archive/`
   unless the user gives an exact path.
4. If a step in the plan is unclear or would break an invariant, stop and write
   the question into `HANDOFF.md` (section "Blocked / Questions") instead of guessing.

---

## 3. Execution Rules

- Do only what `PLAN.md` asks. Out-of-scope improvements go under
  "Suggestions for Claude" in `HANDOFF.md`, not into the code.
- Code style: every new or changed function gets clear section headers and
  thorough inline comments explaining what each block does and why.
- Never read, print, or commit `.env`, `secrets.h`, Wi-Fi keys, Firebase
  secrets, or SmartThings tokens. Use `.env.example` / `secrets.h.example` for
  placeholders only.
- Firebase quota: never add PC-side polling faster than 30 s (dashboard viewer cadence is set in `INVARIANTS_DO_NOT_CHANGE.md` §3) and never re-download
  archived sessions.
- Never flash firmware to the ESP32 (`flash_firmware.py --port ...`) unless the
  plan explicitly says to AND the user confirms in chat. Compile-only is fine.
- Tapo P110 relay must stay ON. Never add code that switches it off.

---

## 4. Verification (required before committing)

Run whichever apply to the files you changed, and record each result:

- Python syntax: `py -m py_compile <changed .py files>`
- ML: `py ml/tests/test_dsp_parity.py`, `py ml/tests/test_pipeline_synthetic.py`
- Firmware/daemon: `py firmware/tests/test_session_export.py`,
  `py firmware/tests/test_daemon_offline.py`
- Firmware compile (no flash) when `.ino`/`.h` files changed.
- Dashboards: `py build_clean_dashboard.py` when dashboard sources changed.
- Every acceptance criterion in `PLAN.md` must be checked off or explained.

If a test fails and you cannot fix it within the plan's scope, do NOT commit.
Write the failure into `HANDOFF.md` and stop.

---

## 5. Git

- Commit with Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
- One logical change per commit.
- Commit locally. Push only when PLAN.md or the user says so (`INVARIANTS_DO_NOT_CHANGE.md` §6 requires a push for a change to go live, because Cloudflare builds from GitHub).
- Run `git status` before committing and confirm no secrets or `archive/`
  files are staged.
- **Never `git commit --amend`:** Do not amend commits to write their own hash into `HANDOFF.md`. Record the commit hash in `HANDOFF.md` without committing `HANDOFF.md` again, or commit `HANDOFF.md` in a separate follow-up commit.

---

## 6. Handoff Rules

1. **Diff Patch (`docs/handoffs/last_diff.patch`):** Every handoff saves the diff of the task's commit(s) to `docs/handoffs/last_diff.patch` (overwrite each time). HANDOFF.md links to it.
   - **Write it as UTF-8 with git itself, never with PowerShell `>`** (PowerShell writes UTF-16, which doubles the size and is unreadable to Claude). Use: `git diff <first>^ <last> --output=docs/handoffs/last_diff.patch -- . ":(exclude)*.pdf" ":(exclude)index.html" ":(exclude)dashboard.html" ":(exclude)cloud_dashboard.html" ":(exclude)historical.html" ":(exclude)docs/proposals/proposal_*presentation.html" ":(exclude)docs/handoffs/PLAN.md" ":(exclude)docs/handoffs/HANDOFF.md" ":(exclude)docs/handoffs/last_diff.patch"`.
   - Exclude PLAN.md and HANDOFF.md (Claude reads those directly) and the generated or binary files above; list excluded files by name with their size change in HANDOFF.
   - Check before handing off: the file starts with `diff --git` when opened as text, and contains no NUL bytes. If it is over 40 KB, put `git diff --stat` at the top and say in HANDOFF which file makes it large.
2. **No Amending:** Never run `git commit --amend`. Record the commit hash in `HANDOFF.md` without committing `HANDOFF.md` again, or commit `HANDOFF.md` in a separate follow-up commit.

---

## 7. Write the Handoff

Overwrite `docs/handoffs/HANDOFF.md` with exactly this template:

```markdown
# Handoff to Claude (Architect)

**Plan:** <title from PLAN.md>
**Date:** <YYYY-MM-DD HH:MM, Asia/Kuala_Lumpur>
**Status:** COMPLETE | PARTIAL | BLOCKED
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `<short hash>` <message>
- **Branch:** <branch>

## What Changed
- <bullet per change>

## Files Changed
- `<path>`: <what changed>

## Excluded from Patch
- `<filename>` (<size change or reason>)

## Acceptance Criteria
- [x] <criterion> — <how it was verified>
- [ ] <criterion> — <why not met>

## Tests Run
- `<command>` — PASS / FAIL (<short reason if FAIL>)

## Invariants Check
- <confirm no item in INVARIANTS_DO_NOT_CHANGE.md was altered, or list any concern>

## Blocked / Questions
- <questions needing an architecture decision, or "None">

## Suggestions for Claude
- <out-of-scope ideas noticed, or "None">
```

Then mark `PLAN.md` as `Status: DONE` and tell the user:
"Done. Ask Claude to review docs/handoffs/HANDOFF.md."
