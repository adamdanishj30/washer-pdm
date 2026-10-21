"""
predict_pdm.py  (v3)
Score wash cycles with the trained detector and print an honest report.

Outputs for a cycle
-------------------
* CYCLE DECISION   NORMAL / ABNORMAL  (persistence statistic vs threshold h)
* Baseline percentile of each 5 s window and its traffic-light band
  (green < 95th pct, amber 95-99.5, red >= 99.5 of held-out healthy windows)
* Acoustic / vibration / power INDICATORS: where a deviation sits.
  (v2 printed "Tub Bearing Health 98.7%" and a remaining-useful-life in
  cycles and ringgit; with no fault data those numbers had no basis, so
  they are gone.)
* A per-window CSV in ml/outputs/ for dashboards.

Usage
-----
  py ml/predict_pdm.py --file data/real_sessions/wash_cycle_2026-10-18_0516.csv
  py ml/predict_pdm.py --benchmark                  # every cycle in data/real_sessions
  py ml/predict_pdm.py --file <csv> --test-fault acoustic_rise --severity 0.5

NOTE: --benchmark on the TRAINING cycles is optimistic (the model has seen
them). The honest numbers are in ml/models/loco_report.md.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & paths
# =============================================================================
import argparse
import sys
from pathlib import Path
from typing import Dict, Tuple

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.fault_injection import FAULTS, inject  # noqa: E402
from ml.feature_fusion import REAL_SESSIONS_DIR, compute_features, load_sessions, resolve_phases  # noqa: E402
from ml.pipeline import PdmPipeline  # noqa: E402

ARTIFACT = BASE_DIR / "ml" / "models" / "pdm_detector.joblib"
OUT_DIR = BASE_DIR / "ml" / "outputs"


# =============================================================================
# SECTION 2: Predictor
# =============================================================================
class PdmPredictor:
    def __init__(self, artifact: Path = ARTIFACT) -> None:
        if not artifact.is_file():
            raise FileNotFoundError(f"{artifact} not found - run: py ml/train_unsupervised_pdm.py")
        obj = joblib.load(artifact)
        if not isinstance(obj, dict) or obj.get("version") != 3:
            raise RuntimeError("model artifact is not v3 - retrain with ml/train_unsupervised_pdm.py")
        self.pipe: PdmPipeline = obj["pipeline"]

    def score_frame(self, raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Dict]]:
        scored = self.pipe.score(compute_features(raw, self.pipe.spec.schema))
        return scored, {s: self.pipe.summarize(g) for s, g in scored.groupby("session")}

    def score_file(self, path: Path) -> Tuple[pd.DataFrame, Dict]:
        scored, summ = self.score_frame(load_sessions([path]))
        return scored, next(iter(summ.values()))


# =============================================================================
# SECTION 3: Reporting
# =============================================================================
def plain_language(s: Dict) -> str:
    """One sentence a facility manager can act on."""
    if s["cycle_decision"] == "ABNORMAL":
        trig = [t for t in s["triggered_by"] if t != "overall"]
        where = trig[0] if trig else max(("acoustic", "vibration", "power"), key=lambda g: s.get(f"{g}_indicator_p95", -1))
        return (f"ABNORMAL: the machine behaved unlike its healthy baseline for a sustained period "
                f"(first flagged {s['first_alarm_min']} min into the cycle); the deviation is mostly "
                f"{where}. Inspect, and compare with the next cycles before acting.")
    if s["pct_windows_amber"] + s["pct_windows_red"] > 15:
        return "NORMAL overall, but more unusual moments than a typical healthy cycle - keep watching."
    return "NORMAL: within the range of the healthy cycles recorded so far."


def print_report(name: str, s: Dict, pipe: PdmPipeline) -> None:
    print("\n" + "=" * 78)
    print(f" CYCLE REPORT: {name}")
    print("=" * 78)
    print(f" Decision            : {s['cycle_decision']}"
          + (f"  (triggered by: {', '.join(s['triggered_by'])})" if s['triggered_by'] else ""))
    print(f" Persistence vs h    : overall {s['max_persistence']}/{s['threshold_h']}"
          + "".join(f" | {g} {s[f'{g}_max_persistence']}/{s[f'{g}_threshold_h']}"
                    for g in ("acoustic", "vibration", "power") if f"{g}_max_persistence" in s))
    print(f" Windows             : {s['windows']}  | amber {s['pct_windows_amber']}%  | red {s['pct_windows_red']}%")
    print(f" Baseline percentile : median {s['median_baseline_pct']}, 95th {s['p95_baseline_pct']} "
          f"(100 = more unusual than every held-out healthy window)")
    for g in ("acoustic", "vibration", "power"):
        if f"{g}_indicator_p95" in s:
            print(f" {g.capitalize():<10} indicator: 95th-pct window at baseline percentile {s[f'{g}_indicator_p95']}")
    if s.get("top_features_in_red_windows"):
        print(f" Drivers (red windows): {', '.join(s['top_features_in_red_windows'])}")
    print(f" Summary             : {plain_language(s)}")
    print(f" Model               : {pipe.model_name}, schema {pipe.spec.schema}, "
          f"phase-conditioned={pipe.conditioned}, power={'yes' if pipe.spec.use_power else 'no'}")
    print("=" * 78)


# =============================================================================
# SECTION 4: CLI
# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="Score wash cycles with the v3 PdM detector")
    ap.add_argument("--file", help="session CSV to score")
    ap.add_argument("--benchmark", action="store_true", help="score every cycle in data/real_sessions")
    ap.add_argument("--test-fault", choices=sorted(FAULTS), help="inject a fault into --file first")
    ap.add_argument("--severity", type=float, default=None, help="fault severity (default: 3rd level)")
    a = ap.parse_args()
    pred = PdmPredictor()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if a.benchmark:
        paths = sorted(p for p in REAL_SESSIONS_DIR.glob("*.csv") if ".bak" not in p.name)
        scored, summ = pred.score_frame(load_sessions(paths))
        print("\nNOTE: these cycles were used for training -> optimistic. See ml/models/loco_report.md.\n")
        print(f"{'cycle':<36} {'decision':<9} {'max persist':>11} {'red %':>6} {'amber %':>8} "
              f"{'acoustic p95':>12} {'vibration p95':>13}")
        for sid, s in summ.items():
            print(f"{sid:<36} {s['cycle_decision']:<9} {s['max_persistence']:>11} {s['pct_windows_red']:>6} "
                  f"{s['pct_windows_amber']:>8} {s.get('acoustic_indicator_p95', '-'):>12} "
                  f"{s.get('vibration_indicator_p95', '-'):>13}")
        scored.to_csv(OUT_DIR / "benchmark_scored.csv", index=False)
        return

    path = Path(a.file) if a.file else REAL_SESSIONS_DIR / "wash_cycle_2026-10-18_0516.csv"
    if a.test_fault:
        raw = resolve_phases(load_sessions([path]))
        sev = a.severity if a.severity is not None else FAULTS[a.test_fault]["levels"][2]
        raw = inject(raw, a.test_fault, sev).drop(columns=["fault_active", "phase_group", "phase_source"])
        scored, summ = pred.score_frame(raw)
        s = next(iter(summ.values()))
        name = f"{path.stem} + injected {a.test_fault} ({sev:g} {FAULTS[a.test_fault]['unit']}, from mid-cycle)"
    else:
        scored, s = pred.score_file(path)
        name = path.stem
    print_report(name, s, pred.pipe)
    out = OUT_DIR / f"{path.stem}{'_' + a.test_fault if a.test_fault else ''}_scored.csv"
    scored.to_csv(out, index=False)
    print(f" Per-window output   : {out.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
