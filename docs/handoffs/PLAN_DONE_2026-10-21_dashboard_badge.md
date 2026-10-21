# Plan for Antigravity

**Status:** DONE  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Dashboard: wash-type badge, cycle summary line, shaded heater/spin blocks, and run-level badges
**Date:** 2026-10-21

## Review verdict that produced this plan
APPROVED: `dc23692`, `1d61f00` (signature report fix + sidecar reconcile). Previous plan archived as `PLAN_DONE_2026-10-21_signature_fix.md`.

Checked against the files on Drive: grouping is computed from named constants (`classify_signature()`), with an assertion per member; no invented programme names; classes and spin-block counts match Claude's independent numbers (Long cold 16/17 0718/18/19 Oct, Long hot 20 Oct, Quick 21 Oct ×2, No power data ×6); Max Gap 5.02 s from `timestamp_ms`; `data/session_context.csv` has 13 rows; the phantom row's cause (daemon test writing to the real sidecar) is found and fixed; no secrets; patch is UTF-8.

Minor notes, no rework needed (fold into this task where it touches the same file, else leave):
- Report §1 says "zero clipping across all sessions"; clipping is only measured on firmware-07 sessions. Reword to "across all firmware-07 sessions" (in `ml/cycle_signature_report.py`, step 7 below).
- `firmware/tests/test_daemon_offline.py` sets `sc.DEFAULT_CONTEXT_FILE` without restoring it. Wrap in try/finally (step 7 below).
- Nice corroboration: the 16 Oct SmartThings spin setting of 1200 rpm matches the ~20 Hz measured spin peak.
- Epoch jitter is 2.7–3.8 s, larger than expected; stays queued with the firmware task.

## Objective
Adam asked (2026-10-21) for the website to show what kind of wash each archived cycle was, so viewers understand why peak counts and lengths differ. After this task, when a built-in (🧺) session is selected on any page: a wash-type badge shows the programme (if known) or the inferred signature class, a one-line summary gives active minutes / heater minutes / spin blocks, heater and spin blocks are shaded on the charts, and the Dom. freq and σ badges are clearly either "at cursor" values or full-run summaries, never an unlabelled first window.

## Context
- `build_clean_dashboard.py` only (INVARIANTS §3 CAN CHANGE, display-only). Rebuild all four pages. MUST STAY: `maxAgeMs` line and its `if/else` structure, polling cadence, `/api/live`, Firebase quota rules, honest labels (no rpm or "health %" shown as measured; inferred classes must say inferred).
- One source of truth for the rules: import `count_spin_blocks`, `classify_signature` and the constants from `ml/cycle_signature_report.py` at build time. Do NOT re-implement the thresholds in Python or JS.
- Programme/temp come from `data/session_context.csv` only when `context_source` is `smartthings_live`, `smartthings_history` or `manual` and `programme != unknown`.
- Page size: pages are ~770 KB and the limit is 800 KB. Embed only a few numbers per session (no per-window arrays).
- Code style: exhaustive inline comments, clear section headers.

## Implementation Steps
1. **Build-time summary (Python).** In `discover_all_sessions()`, for each real session add a `summary` dict to `sessions[s_key]`: `signature` (class string), `programme` (or null), `water_temp` (or null), `active_min`, `heater_min`, `spin_blocks`, `blocks` = list of `{type: "heater"|"spin", i0, i1}` row-index spans, and `run_medians` = medians over running windows (`vib_mag_std > 0.08`) of `vib_dom_hz`, `vib_std_x/y/z`, `vib_mag_std` (null for legacy files). Use the shared functions from `ml/cycle_signature_report.py` (refactor there only if a helper must return spans; keep its report output byte-identical apart from the step-7 wording).
2. **Wash-type badge.** Next to the archive title (`titleTimeline`), show a pill: programme name + water temp when known (label "SmartThings" or "manual"), else the signature class with the text "inferred from power"; `No power data` and `Unclassified` shown as such. Testing sessions (🧪), Load-CSV files and live mode show no badge (Load CSV: "not classified"). Add a short tooltip explaining the rule (heater > 1 kW, spin = ≥ 20 windows at 200–1,000 W).
3. **Summary line.** Under the title (replace or extend `subTimeline`): e.g. "64 min active · no heater · 3 spin blocks" (heater shown as "12 min heater" when > 0). Keep the recorded duration visible but say the last ~10 min is the idle tail when the session ended by idle timeout (recorded − active ≥ 8 min).
4. **Shaded blocks.** In full-run view, shade heater spans (amber) and spin spans (teal/blue) on the power chart and the Card 1 vibration chart, with a small legend. Use the row-index spans from step 1. Window view (40-point) shades only the visible part. Live mode: no shading.
5. **Badges at cursor vs run.** For historic sessions: keep the existing cursor readouts but label them "at cursor" (e.g. "Dom. freq (at cursor)"). Add run-level readouts from `run_medians`: "Run median: Dom. freq X Hz · σx/σy/σz …". Do not show rpm. Live mode unchanged.
6. **Rebuild & checks.** `py build_clean_dashboard.py`; extract the script from all four pages and `node --check` each; report page sizes before/after (all < 800 KB).
7. **Small fixes from review:** reword the clipping sentence in `ml/cycle_signature_report.py` and regenerate the report; wrap the `DEFAULT_CONTEXT_FILE` override in `firmware/tests/test_daemon_offline.py` with try/finally.
8. **Browser check** (if available, else UNVERIFIED): `historical.html`, select 19 Oct 0911 → "Long cold (inferred from power)", "64 min active · no heater · 3 spin blocks", 3 spin shadings; 20 Oct 0744 → "Long hot", 1 heater + 3 spin shadings; 21 Oct 0514 → "Quick", 1 spin shading; 11 Oct → "No power data", no shading. Screenshot each into `docs/handoffs/screens/` (new folder) and list them in HANDOFF.
9. HANDOFF with the template (keep `Open UNVERIFIED items`), `last_diff.patch` per workflow rule 6 (generated pages excluded, sizes listed). Commits: `feat(dashboard): wash-type badge, cycle summary and block shading`, `fix: review notes (report wording, test isolation)`. Pull --rebase, push (Cloudflare deploys from GitHub).

## Out of Scope
- Live polling, `windowToRecord`, `maxAgeMs`, firmware, ML pipeline/features/thresholds/LOCO, `data/real_sessions/*.csv`, `.github/`.
- Classifying Load-CSV files in JS (would duplicate the rules).
- The load_class change (queued).

## Acceptance Criteria
- [x] Badge text per session matches `ml/models/cycle_signature_report.md` §2 for all 13 real sessions (list them in HANDOFF); every inferred badge contains "inferred".
- [x] Summary line values equal the report's Active Min, Heater Min and Spin Blocks.
- [x] Shaded spans: 3 spin for 16/17 0718/18/19 Oct; 1 heater + 3 spin for 20 Oct; 1 spin for each 21 Oct; none for No-power sessions.
- [x] Cursor badges are labelled "at cursor"; run medians shown for firmware-07 sessions; no rpm anywhere.
- [x] Thresholds are imported from `ml/cycle_signature_report.py` (grep shows no duplicated 1000/200/20 thresholds in the build script).
- [x] `node --check` passes on all four pages; all pages < 800 KB (sizes reported).
- [x] `maxAgeMs` line/structure, polling functions and `windowToRecord` unchanged (say how verified).
- [x] Report regenerated with the clipping wording fix; `py firmware/tests/test_daemon_offline.py`, `py firmware/tests/test_session_context.py`, `py firmware/tests/test_session_export.py` pass.
- [x] Browser check done with screenshots, or marked UNVERIFIED.
- [x] Only the build script, the four pages, the report script/report, the test file and screenshots committed; no secrets; pushed; hashes reported.

## Risk Notes
- **Page size** is the tightest constraint (~30 KB headroom). If over, drop `run_medians` for legacy sessions first, then shorten tooltip text.
- **Import path:** the build script runs from the repo root; importing `ml.cycle_signature_report` must not trigger report generation on import (guard with `if __name__ == "__main__"`, check it is already so).
- **Concurrent bot commits:** the workflow rebuilds pages every 30 min; `pull --rebase` and rebuild if the rebase touches pages.

## Queue (Claude will plan these next; do not start)
1. **Data: retire the `load_class` heuristic (Adam asked 2026-10-21 why every cycle is MEDIUM).** `compute_weight_and_class()` averages power between 60–350 W in the first 30 rows; on firmware 07 those rows are fill/soak at ~5–30 W, so nothing qualifies and it falls back to SmartThings water level, else a hard-coded 5 kg → MEDIUM. The kg formula `(W − 70) / 15` was never calibrated; the ML does not use it. Plan: keep the CSV column (schema must stay) but write `unknown` for new sessions, add `load_kg` and `load_source` (manual / smartthings) to `data/session_context.csv`, label old values as heuristic in the data dictionary; re-introduce an estimate only after calibrating against weighed loads.
2. **Firmware: report reset reason.** 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot (rig reboots as the washer switches on). Add NEW `/live` fields `reset_reason` and `boot_count` (INVARIANTS §2 CAN CHANGE); in the same task consider fixing `epochMs()` jitter (2.7–3.8 s). Needs a flash, so Adam confirms first.
3. **ML: programme-aware evaluation.** Once each signature class has ≥ 3 firmware-07 cycles, add LOCO results per class and test SmartThings-phase conditioning. Per-cycle normalisation is not allowed (leaks held-out statistics, erases slow faults).
