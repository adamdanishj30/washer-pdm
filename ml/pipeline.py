"""
pipeline.py
End-to-end PdM model: features -> phase-conditioned detector -> calibrated
percentiles -> persistence (slow EWMA) cycle decision, plus three explainable indicators.

Fitting a PdmPipeline on a set of healthy cycles
------------------------------------------------
1. Leave-one-cycle-out INSIDE the training set: for each training cycle,
   fit on the others and score it -> out-of-fold (OOF) healthy scores.
2. Calibrator (percentiles + persistence threshold h) from those OOF scores only.
3. Final detector fitted on all training cycles.
Nothing about a cycle outside the training set is ever used, so wrapping
this in an outer LOCO loop (ml/loco_eval.py) gives an honest estimate.

Cycle decision
--------------
ABNORMAL if, for a sustained period (10-min EWMA), EITHER the overall model
OR any indicator is above its own out-of-fold-calibrated threshold. On the
legacy data the acoustic indicator alone was far more sensitive to a
sustained sound change than the pooled model (whose other features dilute
it); nested LOCO measures the false-alarm cost of the combined rule.

Indicators (replace v2's "Tub Bearing Health %" / "Damper Health %")
--------------------------------------------------------------------
Separate Mahalanobis models on the ACOUSTIC, VIBRATION and POWER feature
subsets, calibrated the same way. Each reports a baseline percentile:
  acoustic indicator  - "the sound is more unusual than X% of healthy windows"
                         (where bearing / friction problems would show first)
  vibration indicator - same for cabinet vibration (suspension / imbalance)
  power indicator     - same for electrical draw (friction drag)
They say WHERE the deviation is, not which component failed: we have no
fault labels to learn component diagnosis from.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports
# =============================================================================
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ml.calibration import (Calibrator, band, cusum, first_alarm_index, persistence, z_from_u)
from ml.detectors import PhaseConditioned
from ml.feature_fusion import FeatureSpec, feature_matrix, make_spec

CONDITION_MIN_LABELLED = 0.5        # condition on phase only if >= 50% of training rows have SmartThings labels
WINDOW_S = 5.0


# =============================================================================
# SECTION 2: Pipeline
# =============================================================================
@dataclass
class PdmPipeline:
    model_name: str = "mahalanobis"
    spec: Optional[FeatureSpec] = None
    conditioned: bool = False
    detector: Optional[PhaseConditioned] = None
    calibrator: Optional[Calibrator] = None
    indicators: Dict[str, Dict] = field(default_factory=dict)  # group -> {spec_idx, det, cal}
    train_sessions: List[str] = field(default_factory=list)

    # ------------------------------------------------------------- utilities
    @staticmethod
    def _oof(model_name: str, X: np.ndarray, groups: np.ndarray, sessions: np.ndarray,
             conditioned: bool):
        """Leave-one-cycle-out scores for every row (needs >= 2 sessions)."""
        scores = np.empty(len(X))
        routes = np.empty(len(X), dtype=object)
        for s in np.unique(sessions):
            te = sessions == s
            det = PhaseConditioned(model_name, conditioned=conditioned).fit(X[~te], groups[~te])
            scores[te] = det.score(X[te], groups[te])
            routes[te] = det.route(groups[te])
        return scores, routes

    # ------------------------------------------------------------------ fit
    def fit(self, df_feat: pd.DataFrame, schema: str, use_power: bool) -> "PdmPipeline":
        sessions = df_feat["session"].to_numpy()
        if len(np.unique(sessions)) < 3:
            raise ValueError("need at least 3 healthy cycles for leave-one-cycle-out calibration")
        self.train_sessions = sorted(np.unique(sessions).tolist())
        self.spec = make_spec(schema, use_power)
        groups = df_feat["phase_group"].to_numpy().astype(object)
        labelled = (df_feat["phase_source"] == "smartthings").mean()
        self.conditioned = bool(labelled >= CONDITION_MIN_LABELLED)
        X = feature_matrix(df_feat, self.spec)

        # --- main detector ---
        oof, routes = self._oof(self.model_name, X, groups, sessions, self.conditioned)
        self.calibrator = Calibrator.from_oof(oof, routes, sessions)
        self.detector = PhaseConditioned(self.model_name, conditioned=self.conditioned).fit(X, groups)

        # --- explainable indicators (Mahalanobis on feature subsets) ---
        self.indicators = {}
        for grp in ("acoustic", "vibration", "power"):
            idx = [i for i, n in enumerate(self.spec.names) if self.spec.groups[n] == grp]
            if not idx:
                continue
            Xi = X[:, idx]
            o, r = self._oof("mahalanobis", Xi, groups, sessions, self.conditioned)
            self.indicators[grp] = {
                "idx": idx,
                "cal": Calibrator.from_oof(o, r, sessions),
                "det": PhaseConditioned("mahalanobis", conditioned=self.conditioned).fit(Xi, groups),
            }
        return self

    # ---------------------------------------------------------------- score
    def score(self, df_feat: pd.DataFrame) -> pd.DataFrame:
        """Per-window outputs; sequential statistics restart for every session."""
        X = feature_matrix(df_feat, self.spec)
        groups = df_feat["phase_group"].to_numpy().astype(object)
        s = self.detector.score(X, groups)
        routes = self.detector.route(groups)
        u = self.calibrator.percentile(s, routes)
        out = pd.DataFrame({"session": df_feat["session"].to_numpy(), "row": df_feat["row"].to_numpy(),
                            "timestamp_ms": df_feat["timestamp_ms"].to_numpy(),
                            "phase_group": groups, "score": s, "baseline_pct": 100.0 * u,
                            "band": band(u)}, index=df_feat.index)
        z = z_from_u(u)
        ps = np.zeros(len(out))
        cs = np.zeros(len(out))
        for sess in out["session"].unique():
            m = (out["session"] == sess).to_numpy()
            ps[m] = persistence(z[m])
            cs[m] = cusum(z[m])
        out["z"] = z
        out["persistence"] = ps          # decision statistic (alarm when > h)
        out["cusum"] = cs                # reference only
        out["window_decision"] = np.where(u >= 0.995, "ABNORMAL", "NORMAL")
        for grp, ind in self.indicators.items():
            Xi = X[:, ind["idx"]]
            si = ind["det"].score(Xi, groups)
            ui = ind["cal"].percentile(si, ind["det"].route(groups))
            out[f"{grp}_indicator_pct"] = 100.0 * ui
            zi = z_from_u(ui)
            pi = np.zeros(len(out))
            for sess in out["session"].unique():
                m = (out["session"] == sess).to_numpy()
                pi[m] = persistence(zi[m])
            out[f"{grp}_persistence"] = pi
        C = self.detector.contributions(X, groups)
        if C is not None:
            top = np.argsort(-C, axis=1)[:, :3]
            out["top_features"] = [", ".join(self.spec.names[j] for j in row) for row in top]
        return out

    # ------------------------------------------------------- cycle decision
    def thresholds(self) -> Dict[str, float]:
        """Decision tests: overall model + one per indicator, each with its own h."""
        t = {"overall": self.calibrator.h}
        for grp, ind in self.indicators.items():
            t[grp] = ind["cal"].h
        return t

    def alarm_series(self, scored_session: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Window-by-window alarm for ONE session (sorted by row): True where ANY
        test's persistence statistic is above its threshold. Also returns the
        first alarm index per test (-1 = never).
        """
        g = scored_session
        firsts, alarm = {}, np.zeros(len(g), dtype=bool)
        for test, h in self.thresholds().items():
            col = "persistence" if test == "overall" else f"{test}_persistence"
            above = g[col].to_numpy() > h
            alarm |= above
            idx = np.flatnonzero(above)
            firsts[test] = int(idx[0]) if len(idx) else -1
        return alarm, firsts

    # -------------------------------------------------------------- summary
    def summarize(self, scored: pd.DataFrame) -> Dict:
        """Cycle-level verdict for ONE session's scored windows."""
        g = scored.sort_values("row")
        s = g["persistence"].to_numpy()
        alarm, firsts = self.alarm_series(g)
        idx = np.flatnonzero(alarm)
        i = int(idx[0]) if len(idx) else -1
        res = {
            "windows": int(len(g)),
            "cycle_decision": "ABNORMAL" if i >= 0 else "NORMAL",
            "triggered_by": [t for t, f in firsts.items() if f >= 0],
            "max_persistence": round(float(s.max()), 3),
            "threshold_h": round(float(self.calibrator.h), 3),
            "first_alarm_min": round(i * WINDOW_S / 60.0, 1) if i >= 0 else None,
            "pct_windows_amber": round(100.0 * (g["band"] == "amber").mean(), 1),
            "pct_windows_red": round(100.0 * (g["band"] == "red").mean(), 1),
            "median_baseline_pct": round(float(g["baseline_pct"].median()), 1),
            "p95_baseline_pct": round(float(g["baseline_pct"].quantile(0.95)), 1),
        }
        for grp, ind in self.indicators.items():
            res[f"{grp}_indicator_p95"] = round(float(g[f"{grp}_indicator_pct"].quantile(0.95)), 1)
            res[f"{grp}_max_persistence"] = round(float(g[f"{grp}_persistence"].max()), 3)
            res[f"{grp}_threshold_h"] = round(float(ind["cal"].h), 3)
        if "top_features" in g.columns:
            red = g[g["band"] == "red"]
            if len(red):
                counts = pd.Series(", ".join(red["top_features"]).split(", ")).value_counts()
                res["top_features_in_red_windows"] = counts.head(3).index.tolist()
        return res

    def describe(self) -> Dict:
        return {
            "model": self.model_name,
            "schema": self.spec.schema,
            "features": self.spec.names,
            "uses_power": self.spec.use_power,
            "phase_conditioned": self.conditioned,
            "sub_models": sorted(self.detector.models.keys()),
            "persistence_threshold_h": {k: round(v, 3) for k, v in self.thresholds().items()},
            "healthy_oof_max_persistence": [round(v, 3) for v in self.calibrator.healthy_max_s],
            "train_sessions": self.train_sessions,
        }
