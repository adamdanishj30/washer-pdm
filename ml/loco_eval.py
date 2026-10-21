"""
loco_eval.py
Nested leave-one-cycle-out (LOCO) evaluation - the numbers you can defend.

For every healthy cycle c (outer loop):
  1. Fit a PdmPipeline on the OTHER cycles. Inside, its calibration uses
     an inner LOCO over those cycles only, so the persistence threshold h and the
     percentile tables never see cycle c.
  2. Score cycle c as recorded            -> false alarm?  (healthy test)
  3. For each fault kind x severity, inject into cycle c's MEASUREMENTS from
     the middle of the cycle on, recompute features, score
                                           -> detected? how fast?
Outputs per model:
  * false-alarm cycles k / n, with a one-sided 95% Clopper-Pearson upper bound
  * share of healthy windows flagged red / amber
  * detection rate and median delay for every fault kind x severity
  * minimum detectable severity per fault kind (>= 75% of cycles detected
    with no alarm before the fault started)
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports
# =============================================================================
import time
import zlib
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.stats import beta

from ml.fault_injection import FAULTS, faults_for_schema, inject
from ml.feature_fusion import compute_features, resolve_phases, session_power_valid
from ml.pipeline import WINDOW_S, PdmPipeline

DETECT_RATE_FOR_MDS = 0.75
ONSET_FRAC = 0.5


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound on a rate after k events in n trials."""
    if n == 0:
        return 1.0
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


# =============================================================================
# SECTION 2: One outer fold
# =============================================================================
def _outer_fold(raw: pd.DataFrame, test_sid: str, model: str, schema: str,
                use_power: bool, faults: List[str]) -> Dict:
    train_raw = raw[raw["session"] != test_sid]
    test_raw = raw[raw["session"] == test_sid]
    pipe = PdmPipeline(model_name=model).fit(compute_features(train_raw, schema), schema, use_power)

    # --- healthy test ---
    sc = pipe.score(compute_features(test_raw, schema))
    summ = pipe.summarize(sc)
    fold = {"session": test_sid, "h": pipe.calibrator.h,
            "healthy_alarm": summ["cycle_decision"] == "ABNORMAL",
            "triggered_by": summ["triggered_by"],
            "healthy_max_persistence": summ["max_persistence"],
            "healthy_red": float((sc["band"] == "red").mean()),
            "healthy_amber": float((sc["band"] == "amber").mean()),
            "faults": []}

    # --- injected faults (same model, same threshold) ---
    test_ph = resolve_phases(test_raw)
    n = len(test_ph)
    onset = int(ONSET_FRAC * n)
    for kind in faults:
        for sev in FAULTS[kind]["levels"]:
            f_raw = inject(test_ph, kind, sev, onset_frac=ONSET_FRAC, seed=zlib.crc32(f'{test_sid}|{kind}'.encode()))
            f_raw = f_raw.drop(columns=["fault_active", "phase_group", "phase_source"])
            fs = pipe.score(compute_features(f_raw, schema)).sort_values("row")
            alarm, _ = pipe.alarm_series(fs)
            pre = int(np.flatnonzero(alarm[:onset])[0]) if alarm[:onset].any() else -1
            post_idx = np.flatnonzero(alarm[onset:])
            detected = len(post_idx) > 0
            fold["faults"].append({
                "kind": kind, "severity": sev,
                "alarm_before_onset": pre >= 0,
                "detected": bool(detected),
                "clean_detect": bool(detected and pre < 0),
                "delay_min": float(post_idx[0] * WINDOW_S / 60.0) if detected else None,
                "post_red": float((fs["band"].to_numpy()[onset:] == "red").mean()),
            })
    return fold


# =============================================================================
# SECTION 3: Full evaluation for one model
# =============================================================================
def evaluate(raw: pd.DataFrame, model: str, schema: str, verbose: bool = True) -> Dict:
    sessions = sorted(raw["session"].unique())
    pv = session_power_valid(raw)
    use_power = all(pv.values())
    faults = faults_for_schema(schema, use_power)
    t0 = time.time()
    folds = []
    for sid in sessions:
        folds.append(_outer_fold(raw, sid, model, schema, use_power, faults))
        if verbose:
            f = folds[-1]
            print(f"    [{model}] held-out {sid:<32} healthy max persistence {f['healthy_max_persistence']:>6.2f} "
                  f"(h={f['h']:.2f}) -> {('FALSE ALARM via ' + '+'.join(f['triggered_by'])) if f['healthy_alarm'] else 'normal'}")

    n = len(folds)
    k = sum(f["healthy_alarm"] for f in folds)
    res = {
        "model": model, "schema": schema, "uses_power": use_power, "n_cycles": n,
        "false_alarm_cycles": k,
        "false_alarm_rate_upper95": round(cp_upper(k, n), 3),
        "healthy_window_red_pct": round(100 * float(np.mean([f["healthy_red"] for f in folds])), 2),
        "healthy_window_amber_pct": round(100 * float(np.mean([f["healthy_amber"] for f in folds])), 2),
        "per_cycle": [{kk: f[kk] for kk in ("session", "healthy_alarm", "triggered_by", "healthy_max_persistence", "h")} for f in folds],
        "faults": {}, "seconds": round(time.time() - t0, 1),
    }
    rows = pd.DataFrame([dict(session=f["session"], **x) for f in folds for x in f["faults"]])
    for kind in faults:
        per_sev = []
        for sev in FAULTS[kind]["levels"]:
            r = rows[(rows["kind"] == kind) & (rows["severity"] == sev)]
            d = r["delay_min"].dropna()
            per_sev.append({"severity": sev,
                            "clean_detect_rate": round(float(r["clean_detect"].mean()), 3),
                            "detect_rate": round(float(r["detected"].mean()), 3),
                            "median_delay_min": round(float(d.median()), 1) if len(d) else None,
                            "post_onset_red_pct": round(100 * float(r["post_red"].mean()), 1)})
        mds = next((p["severity"] for p in per_sev if p["clean_detect_rate"] >= DETECT_RATE_FOR_MDS), None)
        res["faults"][kind] = {"unit": FAULTS[kind]["unit"], "meaning": FAULTS[kind]["meaning"],
                               "levels": per_sev, "min_detectable_severity": mds}
    return res


# =============================================================================
# SECTION 4: Markdown report
# =============================================================================
def to_markdown(results: List[Dict], data_notes: List[str]) -> str:
    L = ["# Leave-one-cycle-out evaluation (nested, healthy baseline + injected faults)", ""]
    L += ["Generated by `py ml/train_unsupervised_pdm.py`. Every number below comes from a model "
          "that never saw the cycle it was tested on (threshold and percentile tables included).", ""]
    if data_notes:
        L += ["## Data caveats", ""] + [f"- {n}" for n in data_notes] + [""]
    L += ["## Healthy cycles: false alarms", "",
          "| model | false-alarm cycles | 95% upper bound on false-alarm rate | healthy windows red | amber |",
          "|---|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['model']} | {r['false_alarm_cycles']} / {r['n_cycles']} | "
                 f"{100 * r['false_alarm_rate_upper95']:.0f}% | {r['healthy_window_red_pct']}% | "
                 f"{r['healthy_window_amber_pct']}% |")
    L += ["", "The upper bound is wide because there are only a few cycles; it narrows only with more "
          "healthy cycles (about 30 alarm-free cycles are needed to claim < 10%).", ""]
    L += ["## Injected faults: clean detection rate by severity", "",
          "Clean detection = cycle alarm (overall model OR an indicator: 10-min EWMA of calibrated z above its threshold) after the fault started AND no alarm before it. "
          "Faults start halfway through the held-out cycle and ramp in over 3 minutes.", ""]
    for r in results:
        L += [f"### {r['model']}", "", "| fault | unit | " + " | ".join(
            f"sev {i + 1}" for i in range(4)) + " | min detectable |", "|---|---|---|---|---|---|---|"]
        for kind, f in r["faults"].items():
            cells = [f"{p['severity']:g}: {100 * p['clean_detect_rate']:.0f}%"
                     + (f" ({p['median_delay_min']} min)" if p["median_delay_min"] is not None else "")
                     for p in f["levels"]]
            mds = f["min_detectable_severity"]
            L.append(f"| {kind} | {f['unit']} | " + " | ".join(cells) + f" | {mds if mds is not None else 'not reached'} |")
        L.append("")
    L += ["## What these results do and do not show", "",
          "- They show the false-alarm behaviour on the recorded healthy cycles and how large a sustained, "
          "physically-parameterised change must be before the pipeline reliably flags it.",
          "- They do NOT show that real bearing or damper faults would be detected: injected faults are "
          "models (see `ml/fault_injection.py` for the limits), and no real fault data exists yet.",
          "- Component labels (acoustic / vibration / power indicators) say where a deviation is, not "
          "which part failed. No remaining-useful-life estimate is made: that needs real degradation data.", ""]
    return "\n".join(L)
