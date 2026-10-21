# Plan for Antigravity

**Status:** READY  <!-- WAITING = no task yet | READY = execute | DONE = finished -->
**Title:** Fix misleading health-index descriptions in the feature dictionary (follow-up to load_class)
**Date:** 2026-10-21

## Step 0
Commit this PLAN.md first: `docs: plan dictionary honesty fix`.

## Review verdict that produced this plan
CHANGES NEEDED on `020e93e` (load_class retirement). Previous plan archived by you as `PLAN_DONE_2026-10-21_load_class.md`.

What passed (checked by Claude): PLAN.md committed first (`bb8aca3`); `session_export.py` writes `load_class = "unknown"` and no longer calls the heuristic; `compute_weight_and_class()` has the warning docstring; `data/session_context.csv` has 13 rows with empty `load_kg,load_source`; tests cover manual load surviving backfill; report has a Load (kg) column; no `data/real_sessions/` change; no secrets; patch UTF-8.

What failed:
1. **`data/pdm_feature_dictionary.json` now claims the health indices are measured.** The commit changed `bearing_health_index`, `damper_health_index` and `machine_health_index` descriptions to "Measured primarily via 16 kHz INMP441…", "Measured via low-frequency MPU-6050…", "Smoothed via EWMA/CUSUM at the cycle level". This was not in the plan and breaks the honest-labels rule (INVARIANTS §3, CLAUDE.md: "its health-index and parasitic-drag fields are not model outputs"). It is also factually wrong: "50 Hz MPU-6050, Nyquist 25 Hz" (firmware 07 samples at 200 Hz) and "CUSUM" (tried and rejected, see `ml/calibration.py`).
2. **HANDOFF did not follow the template:** missing "Excluded from Patch", "Acceptance Criteria" checklist, "Invariants Check", "Blocked / Questions"; dropped the carried-forward `Open UNVERIFIED items`; patch is 48.7 KB with no `git diff --stat` at the top (workflow rule 6).

Notes (no action): `firmware/session_export.py` and `firmware/tests/test_session_export.py` show as new files in git, so earlier working code was committed for the first time. That is fine; say so in HANDOFF when it happens. The dictionary was also re-indented (arrays split over lines); acceptable.

## Implementation Steps
1. In `data/pdm_feature_dictionary.json`, set the description of `bearing_health_index`, `damper_health_index`, `machine_health_index`, `parasitic_drag_w` and `parasitic_drag_pct` to: "LEGACY CONTRACT FIELD. Not measured and not a model output. The ML outputs only an anomaly score and a cycle verdict (see ml/README.md)." Keep `type` and `unit`. Keep the load_class / estimated_load_kg wording you added.
2. Make the embedded schema in `firmware/capture_pdm_dataset.py` `save_feature_dictionary()` produce exactly the same descriptions (it rewrites the JSON every run, so the two must match). Do not change any maths in that script.
3. Search the rest of the repo outside `archive/` (`docs/`, `ml/`, `firmware/`, `build_clean_dashboard.py`) for "Nyquist limit (25 Hz)" or "50 Hz MPU": report any hits in HANDOFF under "Suggestions for Claude"; do not edit them in this task.
4. Run `py firmware/capture_pdm_dataset.py --help` (or import the module and call `save_feature_dictionary()` into a temp dir) to show the generated JSON equals the committed file. Do not run a live capture.
5. HANDOFF using the full template from `.agents/rules/architect-handoff-workflow.md` §7, including `Open UNVERIFIED items (carried forward)` from the 21 Oct 16:38 handoff (Apps Script trigger; workflow run with GitHub secrets; real-wash session start/END/archive; active-wash polling; session-change reset; historical.html visual check; DevTools network checks; `/window.json` and `WHO_AM_I` 0x75 quirk) plus "real weighed load entry". `last_diff.patch` per rule 6 with `--stat` on top if over 40 KB. Commit `fix(data): dictionary health fields are legacy, not measured`. Pull --rebase, push.

## Out of Scope
Everything else; no code logic changes.

## Acceptance Criteria
- [ ] PLAN.md committed first.
- [ ] `grep -n "Measured\|Nyquist\|CUSUM" data/pdm_feature_dictionary.json` → no hits.
- [ ] The five legacy fields carry the LEGACY CONTRACT FIELD wording in both the JSON and `capture_pdm_dataset.py`; generated JSON equals the committed file.
- [ ] HANDOFF follows the full template, with the carried-forward UNVERIFIED list.
- [ ] `py -m py_compile firmware/capture_pdm_dataset.py`; `py firmware/tests/test_session_export.py` passes; no secrets; pushed.

## Queue (Claude will plan these next; do not start)
1. **Firmware: report reset reason** (+ `epochMs()` jitter 2.7–3.8 s). 3 of 4 firmware-07 sessions start ~8 s after an ESP32 boot. Needs a flash, so Adam confirms first.
2. **ML: programme-aware evaluation** once each signature class has ≥ 3 firmware-07 cycles. No per-cycle normalisation.
3. **Dashboard page budget** (787.7 KB of 800 KB) before any new dashboard feature.
4. **Docs: track is now PLANET · 03 Energy Efficiency (Adam, 21 Oct).** Update `docs/proposals/PROPOSAL_WRITING_GUIDE.md` (and any repo doc naming "02 Circular Economy" as our track) to say the one track is Energy Efficiency, with circular economy as a supporting benefit only. Add the two new citable sources used in the proposal: Saidur 2009, *Energy Policy* 37(10):4104–4113, doi:10.1016/j.enpol.2009.04.052 (air-conditioning ≈ 57% of energy in Malaysian office buildings), and Melgaard et al. 2022, *Energies* 15(12):4366, doi:10.3390/en15124366 (wear-related faults raise building energy use; US faults ≈ 103–500 TWh/yr, citing Roth et al. 2004). Note that the 5–20% O&M energy-savings range is in US DOE FEMP O&M guide §2.4. The RM 900/yr figure stays labelled as an estimate. Docs only. The Drive copies in `Hackathon/` were already updated by Claude on 21 Oct.
