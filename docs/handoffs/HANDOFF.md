# Handoff to Claude (Architect)

**Plan:** Measured energy per wash: add kWh and peak W to the cycle signature report and the writing guide  
**Date:** 2026-10-21 19:15, Asia/Kuala_Lumpur  
**Status:** COMPLETE  
**Diff Patch:** [last_diff.patch](file:///g:/My%20Drive/PdM%20SideProject/docs/handoffs/last_diff.patch)

## Commits
- `06595ff` docs: plan energy per wash (Step 0)
- `f576438` ml: energy per wash in cycle signature report; guide energy row
- **Branch:** main

## What Changed
- **Step 0 (Plan Commitment):**
  - Executed `git pull` (already up to date, no autostash) and committed `docs/handoffs/PLAN.md` (`06595ff`).
- **Step 1 (`ml/cycle_signature_report.py` - Energy & Peak Calculation):**
  - Updated `analyze_session_csv()` to compute `energy_kwh` ($\sum \text{power\_w} \times \text{dt\_seconds} / 3{,}600{,}000$, rounded to 3 decimal places) and `peak_power_w` ($\max(\text{power\_w})$, rounded to whole W).
  - Explicitly set both `energy_kwh` and `peak_power_w` to `None` when `max_power < 50.0` W or `signature_class == "No power data"`.
  - Added columns "Energy (kWh)" and "Peak W" to Table 2 (Section 2) in the markdown report (formatting unmetered runs as `n/a`).
  - Added dynamically computed per-class energy summary lines under Section 1 class list (`Long cold: 0.10–0.11 kWh per wash`, `Long hot: 0.55 kWh per wash`, `Quick: 0.03–0.04 kWh per wash`, `No power data: n/a (unmetered runs)`).
  - Added clarifying note that energy is integrated from 1 Hz smart-plug power averaged per window, representing total washer electrical draw (not an anomaly/fault signal).
  - Preserved all existing classification thresholds, rules, and constants.
- **Step 2 (`ml/tests/test_cycle_signature_energy.py` - Unit Tests):**
  - Added comprehensive test suite operating purely in `tempfile.TemporaryDirectory()` (never touching `data/` or `ml/models/`).
  - Test 1: Constant 1,000 W for 720 windows at 5.0 s $\rightarrow$ exact 1.000 kWh and 1,000 W peak.
  - Test 2: Low-power cycle (< 50 W) $\rightarrow$ `energy_kwh` is `None`, `peak_power_w` is `None`, and `signature_class` is `"No power data"`.
  - Test 3: Firmware-07 cycle (dt = 5.024 s) with 720 windows at 1,000 W $\rightarrow$ exact 1.005 kWh ($720 \times 1000 \times 5.024 / 3.6e6 = 1.0048$).
  - Test 4: Variable power profile with distinct intervals $\rightarrow$ exact peak power and integral.
- **Step 3 (`ml/models/cycle_signature_report.md` - Report Regeneration):**
  - Regenerated report via `py ml/cycle_signature_report.py`.
  - Diff confirms only the new columns and lines were added; classes, member files, and data quality counters are 100% identical.
- **Step 4 (`docs/proposals/PROPOSAL_WRITING_GUIDE.md` - Facts & Rules):**
  - In §3 Say column, added: `"A heated wash used about 5× the energy of a cold wash on our rig (measured)"`.
  - In §4, added row **"Energy per wash (measured)"**: Quick: 0.03–0.04 kWh per wash (peak 302–373 W); Long cold: 0.10–0.11 kWh per wash (peak 401–774 W); Long hot: 0.55 kWh per wash (peak 2,290 W); heated wash used about 5× the energy of a cold wash; sourced to `ml/models/cycle_signature_report.md`; rule: "one household washer, measured by the smart plug; never present as an AC, township or fault saving".

---

## Cycle Energy & Peak Comparison Table (Script vs Claude's Figures)

| Session File | Schema | Script Energy (kWh) | Script Peak W | Claude's Energy (kWh) | Claude's Peak W | Difference / Explanation |
|---|---|---|---|---|---|---|
| `wash_cycle_2026-10-11_1019.csv` | legacy | n/a | n/a | n/a | n/a | Match (unmetered, max 0.0 W) |
| `wash_cycle_2026-10-12_1019.csv` | legacy | n/a | n/a | n/a | n/a | Match (unmetered, max 0.0 W) |
| `wash_cycle_2026-10-15_1020.csv` | legacy | n/a | n/a | n/a | n/a | Match (unmetered, max 0.0 W) |
| `wash_cycle_2026-10-15_morning.csv` | legacy | n/a | n/a | n/a | n/a | Match (unmetered, max 0.0 W) |
| `wash_cycle_2026-10-16_0857.csv` | legacy | 0.101 | 774 | 0.101 | 774 | Exact match (diff: 0.000 kWh, 0 W) |
| `wash_cycle_2026-10-17_0718.csv` | legacy | 0.113 | 565 | 0.113 | 565 | Exact match (diff: 0.000 kWh, 0 W) |
| `wash_cycle_2026-10-17_0835.csv` | legacy | n/a | n/a | n/a | n/a | Match (unmetered, max 5.0 W < 50 W) |
| `wash_cycle_2026-10-18_0516.csv` | legacy | 0.106 | 401 | 0.107 | 401 | Diff: -0.001 kWh (within 0.005 kWh tolerance). Legacy session with dt=5.0 s has unrounded energy = 0.10607 kWh $\rightarrow$ rounds to 0.106 kWh. (If dt=5.024 s was assumed, it would be 0.10658 $\rightarrow$ 0.107 kWh). |
| `wash_cycle_2026-10-19_0022.csv` | legacy | n/a | n/a | n/a | n/a | Match (unmetered, max 1.3 W < 50 W) |
| `wash_cycle_2026-10-19_0911.csv` | fw07 | 0.112 | 420 | 0.112 | 420 | Exact match (diff: 0.000 kWh, 0 W) |
| `wash_cycle_2026-10-20_0744.csv` | fw07 | 0.549 | 2290 | 0.549 | 2,290 | Exact match (diff: 0.000 kWh, 0 W) |
| `wash_cycle_2026-10-21_0514.csv` | fw07 | 0.036 | 373 | 0.036 | 373 | Exact match (diff: 0.000 kWh, 0 W) |
| `wash_cycle_2026-10-21_0631.csv` | fw07 | 0.029 | 302 | 0.029 | 302 | Exact match (diff: 0.000 kWh, 0 W) |

*All 7 metered sessions match within 0.001 kWh and 0 W. All 6 unmetered sessions show `n/a`.*

---

## Root Cause of `ml/models/loco_report.md` mtime at 18:23 MYT

**Cause Identified:** In `ml/tests/test_pipeline_synthetic.py` (lines 65–88), the test reads the bytes of real model artifacts into an in-memory dictionary `backup`:
```python
models = ROOT / "ml" / "models"
backup = {p: p.read_bytes() for p in models.glob("pdm_detector*")} if models.is_dir() else {}
backup.update({p: p.read_bytes() for p in models.glob("loco_report*")})
try:
    res = subprocess.run([sys.executable, str(ROOT / "ml" / "train_unsupervised_pdm.py"), ...])
    ...
finally:
    for p, b in backup.items():
        p.write_bytes(b)
```
When `ml/tests/test_pipeline_synthetic.py` was executed at 18:23 MYT during verification, `train_unsupervised_pdm.py` overwrote `ml/models/loco_report.md` with synthetic evaluation outputs, and then the `finally:` block wrote the original bytes back via `p.write_bytes(b)`.
The write-back restored byte-identical content, but updated the OS filesystem modified timestamp (`mtime`).
*(Listed below in Suggestions as a bug to isolate test outputs).*

---

## Files Changed
- `ml/cycle_signature_report.py`: calculated `energy_kwh` and `peak_power_w` in `analyze_session_csv()`, added columns to Table 2, added per-class energy summary lines under Section 1 class list.
- `ml/tests/test_cycle_signature_energy.py`: unit test for energy calculation, dt scaling, and unmetered None handling.
- `ml/models/cycle_signature_report.md`: regenerated report with energy and peak W columns.
- `docs/proposals/PROPOSAL_WRITING_GUIDE.md`: added §3 Say line and §4 "Energy per wash (measured)" row.
- `docs/handoffs/PLAN.md`: marked `Status: DONE`.
- `docs/handoffs/PLAN_DONE_2026-10-21_energy_per_wash.md`: archived copy of completed plan.
- `docs/handoffs/last_diff.patch`: 22.9 KB UTF-8 diff.
- `docs/handoffs/HANDOFF.md`: updated handoff documentation.

## Excluded from Patch
- `docs/handoffs/PLAN.md` (read directly by Claude per Rule 6)
- `docs/handoffs/HANDOFF.md` (read directly by Claude per Rule 6)
- `docs/handoffs/last_diff.patch` (self-referential)

## Acceptance Criteria
- [x] PLAN.md committed first, after a plain `git pull` — verified in `06595ff`.
- [x] Report §2 has "Energy (kWh)" and "Peak W" for all 13 sessions; the 6 No power data rows show `n/a` — verified.
- [x] Classes and member lists in the report are unchanged from the previous version (diff shows only the new columns and lines) — verified via `git diff`.
- [x] Script values match Claude's figures within 0.005 kWh and 1 W, or each difference is explained — verified (maximum difference is 0.001 kWh on 18 Oct due to dt=5.0 s rounding; all others 0.000 kWh and 0 W).
- [x] New test passes and writes nothing under `data/` or `ml/models/`; existing tests still pass — verified.
- [x] Guide §4 energy row and §3 Say line exist, are sourced to the report and carry the "one household washer" rule — verified.
- [x] HANDOFF answers what rewrote `loco_report.md` — verified (diagnosed to `ml/tests/test_pipeline_synthetic.py`).
- [x] Pushed; hashes reported — verified.

## Tests Run
- `py -m py_compile ml/cycle_signature_report.py ml/tests/test_cycle_signature_energy.py` — PASS.
- `py ml/tests/test_cycle_signature_energy.py` — PASS (4/4 tests: 1,000 W 720 windows, unmetered <50 W None, fw-07 dt=5.024 s scaling, variable power).
- `py firmware/tests/test_session_export.py` — PASS.
- `py firmware/tests/test_daemon_offline.py` — PASS.
- `py build_clean_dashboard.py` — PASS.

## Invariants Check
- INVARIANTS §1 (Honest reporting): Confirmed. Measured energy is total washer draw; not presented as an AC or township saving, or fault signal.
- INVARIANTS §2 (Firmware): Untouched.
- INVARIANTS §3 (Dashboard): Untouched (verified `build_clean_dashboard.py` succeeds).
- INVARIANTS §4 (Data & ML): Originals in `data/real_sessions/` untouched; no model retraining performed; classification rules and thresholds strictly preserved.
- INVARIANTS §5 (Secrets): Verified no secrets in git (`.env` and `secrets.h` clean).

## Blocked / Questions
- None.

## Suggestions for Claude
1. **Bug in `ml/tests/test_pipeline_synthetic.py`:** Synthetic tests should direct outputs to a temporary directory (e.g. `--output-dir <tempdir>`) rather than overwriting files in `ml/models/` and restoring them via byte write-backs, which alters the production file mtime.
2. **Carried-forward Queue items:**
   - Firmware: report reset reason (+ `epochMs()` jitter 2.7–3.8 s).
   - ML: programme-aware evaluation once each signature class has $\ge 3$ firmware-07 cycles.
   - Dashboard page budget (787.7 KB of 800 KB).
   - Retire or clearly mark `firmware/capture_pdm_dataset.py`.
   - Proposal submission files: Adam's `Hackathon/NEEDS_CHANGING.md` batch.

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
