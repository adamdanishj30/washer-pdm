"""
train_unsupervised_pdm.py  (v3)
Train the Washer PdM anomaly detector on healthy cycles and evaluate it honestly.

Steps
-----
1. Load data/real_sessions/*.csv (each file = one wash cycle).
2. Pick the schema (firmware-07 window features if enough such cycles exist,
   else the legacy snapshot schema) and audit the data (phase labels,
   power availability, sensor re-mounting).
3. Nested leave-one-cycle-out evaluation of every requested model
   (Mahalanobis, Isolation Forest, One-Class SVM) on healthy cycles and on
   severity-swept injected faults -> ml/models/loco_report.{md,json}.
4. Fit the deployment model on ALL cycles (calibrated out-of-fold) and save
   ml/models/pdm_detector.joblib + pdm_detector_meta.json.

There is no "[PASS] Supervisor Mandate" line any more: the report states
what was measured, including the parts that are weak.

Usage
-----
  py ml/train_unsupervised_pdm.py                       # evaluate all 3 models, deploy Mahalanobis
  py ml/train_unsupervised_pdm.py --model iforest       # deploy Isolation Forest instead
  py ml/train_unsupervised_pdm.py --skip-eval           # just fit + save (fast)
  py ml/train_unsupervised_pdm.py --schema legacy
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & paths
# =============================================================================
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.feature_fusion import (REAL_SESSIONS_DIR, compute_features, detect_schema,  # noqa: E402
                               load_sessions, session_power_valid)
from ml.loco_eval import evaluate, to_markdown  # noqa: E402
from ml.pipeline import PdmPipeline  # noqa: E402

MODELS_DIR = BASE_DIR / "ml" / "models"
ARTIFACT = MODELS_DIR / "pdm_detector.joblib"
META = MODELS_DIR / "pdm_detector_meta.json"
MIN_WINDOWED_CYCLES = 3
ARTIFACT_VERSION = 3


# =============================================================================
# SECTION 2: Data audit (printed and written into the report)
# =============================================================================
def audit(raw: pd.DataFrame, schema: str) -> List[str]:
    notes = []
    n = raw["session"].nunique()
    notes.append(f"{n} healthy cycles, {len(raw):,} windows of 5 s; effective sample size for "
                 f"cycle-level claims is {n}, not {len(raw):,} (consecutive windows are strongly correlated).")
    ph = compute_features(raw, schema)
    lab = (ph["phase_source"] == "smartthings").mean()
    notes.append(f"SmartThings phase labels present on {100 * lab:.0f}% of windows"
                 + (" -> the model is NOT phase-conditioned (one pooled model for the whole cycle)."
                    if lab < 0.5 else " -> per-phase sub-models are used."))
    pv = session_power_valid(raw)
    bad = [s for s, ok in pv.items() if not ok]
    if bad:
        notes.append(f"Power unusable in {len(bad)}/{n} cycles ({', '.join(bad)}) -> power features excluded.")
    g = raw.groupby("session")[["accel_x", "accel_y", "accel_z"]].median()
    shift = np.linalg.norm(g.to_numpy() - g.to_numpy()[0], axis=1).max()
    if shift > 0.3:
        notes.append(f"Accelerometer gravity vector moved by up to {shift:.2f} m/s^2 between cycles "
                     f"(sensor re-mounted/tilted) -> only orientation-independent vibration features are used.")
    if schema == "legacy":
        notes.append("Legacy data = one instantaneous accel sample + one 8 ms audio RMS per 5 s. Impulsive "
                     "(bearing) and spectral features cannot be computed; collect firmware-07 cycles.")
    return notes


# =============================================================================
# SECTION 3: Main
# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="Train + evaluate the unsupervised PdM detector (v3)")
    ap.add_argument("--model", default="mahalanobis", choices=["mahalanobis", "iforest", "ocsvm"],
                    help="model to deploy (default: mahalanobis, the transparent baseline)")
    ap.add_argument("--eval-models", default="mahalanobis,iforest,ocsvm",
                    help="comma list of models to evaluate with nested LOCO")
    ap.add_argument("--schema", default="auto", choices=["auto", "legacy", "windowed"])
    ap.add_argument("--skip-eval", action="store_true", help="skip nested LOCO (fit + save only)")
    ap.add_argument("--data-dir", default=str(REAL_SESSIONS_DIR))
    ap.add_argument("--models-dir", default=str(MODELS_DIR),
                    help="directory where model artifacts and reports are saved (default: ml/models)")
    a = ap.parse_args()

    models_dir = Path(a.models_dir)
    artifact_path = models_dir / "pdm_detector.joblib"
    meta_path = models_dir / "pdm_detector_meta.json"
    loco_json_path = models_dir / "loco_report.json"
    loco_md_path = models_dir / "loco_report.md"

    # --- 3a: load + choose schema ---
    paths = sorted(p for p in Path(a.data_dir).glob("*.csv") if ".bak" not in p.name)
    raw_all = load_sessions(paths)
    per_session_schema = {s: detect_schema(g) for s, g in raw_all.groupby("session")}
    n_win = sum(v == "windowed" for v in per_session_schema.values())
    schema = a.schema if a.schema != "auto" else ("windowed" if n_win >= MIN_WINDOWED_CYCLES else "legacy")
    keep = [s for s, v in per_session_schema.items() if v == schema]
    raw = raw_all[raw_all["session"].isin(keep)].copy()
    print(f"[DATA] {len(keep)} cycle(s) with schema '{schema}' "
          f"({n_win} firmware-07 cycle(s) available; need {MIN_WINDOWED_CYCLES} to switch)")
    notes = audit(raw, schema)
    for n in notes:
        print("  -", n)

    # --- 3b: nested LOCO evaluation ---
    results = []
    if not a.skip_eval:
        for m in [x.strip() for x in a.eval_models.split(",") if x.strip()]:
            print(f"\n[EVAL] nested leave-one-cycle-out: {m}")
            results.append(evaluate(raw, m, schema))
        models_dir.mkdir(parents=True, exist_ok=True)
        loco_json_path.write_text(json.dumps(
            {"generated": datetime.now().isoformat(timespec="seconds"), "schema": schema,
             "data_notes": notes, "results": results}, indent=2), encoding="utf-8")
        md = to_markdown(results, notes)
        loco_md_path.write_text(md, encoding="utf-8")
        print("\n" + md)

    # --- 3c: deployment model on all cycles ---
    pv = session_power_valid(raw)
    use_power = all(pv.values())
    pipe = PdmPipeline(model_name=a.model).fit(compute_features(raw, schema), schema, use_power)
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"version": ARTIFACT_VERSION, "pipeline": pipe}, artifact_path)
    meta = {"version": ARTIFACT_VERSION, "trained_at": datetime.now().isoformat(timespec="seconds"),
            **pipe.describe(), "data_notes": notes,
            "evaluation": [{k: r[k] for k in ("model", "false_alarm_cycles", "n_cycles",
                                              "false_alarm_rate_upper95")} for r in results]}
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    try:
        artifact_disp = artifact_path.relative_to(BASE_DIR)
        meta_disp = meta_path.relative_to(BASE_DIR)
        loco_disp = f"{loco_md_path.relative_to(BASE_DIR)} / .json"
    except ValueError:
        artifact_disp = artifact_path
        meta_disp = meta_path
        loco_disp = f"{loco_md_path} / .json"

    print(f"\n[SAVE] {artifact_disp} ({a.model}, persistence threshold h = {pipe.calibrator.h:.2f})")
    print(f"[SAVE] {meta_disp}")
    if results:
        print(f"[SAVE] {loco_disp}")


if __name__ == "__main__":
    main()
