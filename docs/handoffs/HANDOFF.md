# Handoff to Claude (Architect)

**Plan:** Fix misleading health-index descriptions in the feature dictionary (follow-up to load_class)
**Date:** 2026-10-21 17:30, Asia/Kuala_Lumpur
**Status:** COMPLETE
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `14b43bf` docs: plan dictionary honesty fix (Step 0)
- `7a9ad79` fix(data): dictionary health fields are legacy, not measured
- Pending: `docs(handoff): complete dictionary honesty fix`
- **Branch:** main (pushed to origin/main)

## What Changed
- **Step 0 (Plan Commitment):**
  - Committed `docs/handoffs/PLAN.md` immediately (`14b43bf`) before modifying any code.
- **Step 1 (Honest Descriptions in Feature Dictionary):**
  - In `data/pdm_feature_dictionary.json`, updated the description of all five legacy fields (`parasitic_drag_w`, `parasitic_drag_pct`, `bearing_health_index`, `damper_health_index`, and `machine_health_index`) to strictly state:
    `"LEGACY CONTRACT FIELD. Not measured and not a model output. The ML outputs only an anomaly score and a cycle verdict (see ml/README.md)."`
  - Preserved their existing types and units.
  - Kept the previous uncalibrated heuristic wording for `load_class` and `estimated_load_kg`.
  - Removed all occurrences of `Measured`, `Nyquist`, and `CUSUM` from the dictionary (`grep -E -n "Measured|Nyquist|CUSUM" data/pdm_feature_dictionary.json` returns 0 hits).
- **Step 2 (Synchronized Embedded Schema in Capture Script):**
  - In `firmware/capture_pdm_dataset.py`, updated `save_feature_dictionary()` schema definition to match `data/pdm_feature_dictionary.json` byte-for-byte.
  - Handled directory path reporting safely if written outside `BASE_DIR`.
  - Zero maths or capture logic changes in `capture_pdm_dataset.py`.
- **Step 3 (Search for "50 Hz MPU" / "Nyquist limit"):**
  - Scanned the entire repository outside `archive/`. Zero hits for "Nyquist limit" outside of `PLAN.md` and `last_diff.patch`. Hits for "50 Hz MPU" located in legacy proposal files are documented under "Suggestions for Claude" below.
- **Step 4 (Schema Verification):**
  - Verified that `save_feature_dictionary()` executed via Python generates a JSON file byte-identical to `data/pdm_feature_dictionary.json`.
  - Verified `py firmware/capture_pdm_dataset.py --help` runs cleanly without invoking live capture.

## Files Changed
- `data/pdm_feature_dictionary.json`: updated descriptions for `parasitic_drag_w`, `parasitic_drag_pct`, `bearing_health_index`, `damper_health_index`, and `machine_health_index`.
- `firmware/capture_pdm_dataset.py`: updated embedded schema in `save_feature_dictionary()` to produce the identical JSON.
- `docs/handoffs/PLAN.md`: marked `Status: DONE` with all acceptance criteria checked.
- `docs/handoffs/PLAN_DONE_2026-10-21_dictionary_honesty.md`: archived copy of completed plan.
- `docs/handoffs/last_diff.patch`: 15.6 KB clean UTF-8 patch of code and data changes.
- `docs/handoffs/HANDOFF.md`: updated handoff documentation.

## Excluded from Patch
- `docs/handoffs/PLAN.md` (excluded per workflow rule 6; read directly by Claude)
- `docs/handoffs/HANDOFF.md` (excluded per workflow rule 6; read directly by Claude)
- `docs/handoffs/last_diff.patch` (self-referential)

## Acceptance Criteria
- [x] PLAN.md committed first — verified in `14b43bf`.
- [x] `grep -n "Measured\|Nyquist\|CUSUM" data/pdm_feature_dictionary.json` → no hits — verified (exit code 1, zero matches).
- [x] The five legacy fields carry the LEGACY CONTRACT FIELD wording in both the JSON and `capture_pdm_dataset.py`; generated JSON equals the committed file — verified via python equality assertion.
- [x] HANDOFF follows the full template, with the carried-forward UNVERIFIED list — verified.
- [x] `py -m py_compile firmware/capture_pdm_dataset.py`; `py firmware/tests/test_session_export.py` passes; no secrets; pushed — verified.

## Tests Run
- `py -m py_compile firmware/capture_pdm_dataset.py` — PASS (0 errors).
- `py firmware/tests/test_session_export.py` — PASS (all rows have `load_class == "unknown"`).
- `py firmware/tests/test_session_context.py` — PASS (6/6 tests OK).
- `py firmware/capture_pdm_dataset.py --help` — PASS.
- JSON byte-identity assertion — PASS (`save_feature_dictionary()` output == `data/pdm_feature_dictionary.json`).
- Grep honesty check (`grep -E "Measured|Nyquist|CUSUM" data/pdm_feature_dictionary.json`) — PASS (0 hits).

## Invariants Check
- INVARIANTS §1 (Honest reporting): Confirmed. No RUL, health-index percentages, or parasitic drag claims are presented as measured facts or model outputs.
- INVARIANTS §3 (Dashboard): Untouched.
- INVARIANTS §4 (Data & ML): Originals in `data/real_sessions/` untouched; `load_class` column preserved.
- INVARIANTS §5 (Secrets): Verified no secrets in git (`.env` and `secrets.h` clean).

## Blocked / Questions
- None.

## Suggestions for Claude
1. **Hits for "50 Hz MPU" in Proposal Documents (Step 3 Search Results):**
   The phrase `"50 Hz MPU"` appears in several proposal files that were drafted during earlier stages of the project (firmware 05/06) before firmware 07 upgraded to 200 Hz FIFO burst acquisition with a 44 Hz anti-alias DLPF:
   - `docs/proposals/PROPOSAL_Apex_PdM_Township_of_Tomorrow.md` (lines 180, 516)
   - `docs/proposals/generate_proposal_pdf.py` (lines 535, 896)
   - `docs/proposals/proposal_presentation.html` (lines 511, 872)
   *Recommendation:* When Claude plans Queue Item 4 (*Docs: track is now PLANET · 03 Energy Efficiency*), these technical descriptions can be updated to reference "200 Hz MPU-6050 FIFO burst reading with 44 Hz DLPF".
2. **Retirement of `firmware/capture_pdm_dataset.py`:**
   Carried forward from previous handoff: consider formal deprecation/retirement since `auto_drive_sync_daemon.py` and `session_export.py` handle all production archiving.

## Open UNVERIFIED Items (carried forward)
1. Apps Script trigger (legacy sync mechanism).
2. Workflow run with GitHub secrets (Tapo / Firebase secrets rotation pending).
3. Real-wash session start / END marker / archive on hardware.
4. Active-wash adaptive polling verification during a live wash.
5. Session-change reset in web dashboard during live wash transition.
6. `historical.html` visual check in browser (done headlessly on 2026-10-21 16:38, live user confirmation pending).
7. DevTools network check (no excessive polling or Firebase quota consumption).
8. `/window.json` and `WHO_AM_I` 0x75 register read quirk on hardware.
9. Real weighed laundry load entry in `data/session_context.csv` (requires Adam to weigh a load and record values).

## Ready for Next Plan
- [x] Antigravity is stopped and waiting for the next plan in `docs/handoffs/PLAN.md`.
