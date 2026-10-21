"""
detectors.py
One-class anomaly detectors with a common interface + phase conditioning.

All detectors return an ANOMALY SCORE where larger = more unusual.
Scores are not probabilities; ml/calibration.py turns them into baseline
percentiles using out-of-fold healthy scores.

Models
------
* mahalanobis : robust-scaled features, Ledoit-Wolf shrinkage covariance,
                squared Mahalanobis distance. Transparent, has an exact
                per-feature decomposition (contributions sum to the score).
                With ~8 cycles this is the baseline the others must beat.
* iforest     : Isolation Forest (score = -score_samples).
* ocsvm       : One-Class SVM, RBF kernel (score = -decision_function).
                nu bounds the training outlier fraction; we keep nu small and
                calibrate the alarm threshold separately, so nu does NOT set
                the false-alarm rate.

Phase conditioning
------------------
PhaseConditioned fits one sub-model per phase group that has enough rows,
plus a pooled model for everything else. Rows with phase 'unlabelled' (no
SmartThings label) always use the pooled model.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports
# =============================================================================
from typing import Dict, Optional

import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.svm import OneClassSVM

POOLED = "__pooled__"


# =============================================================================
# SECTION 2: Base models
# =============================================================================
class MahalanobisModel:
    name = "mahalanobis"

    def fit(self, X: np.ndarray) -> "MahalanobisModel":
        self.scaler = RobustScaler(quantile_range=(10.0, 90.0)).fit(X)
        Z = self._z(X)
        lw = LedoitWolf().fit(Z)
        self.mu = lw.location_
        self.P = lw.precision_
        return self

    def _z(self, X: np.ndarray) -> np.ndarray:
        Z = self.scaler.transform(X)
        return np.clip(Z, -50, 50)           # guards against a broken sensor channel exploding the score

    def score(self, X: np.ndarray) -> np.ndarray:
        D = self._z(X) - self.mu
        return np.einsum("ij,jk,ik->i", D, self.P, D)

    def contributions(self, X: np.ndarray) -> np.ndarray:
        """Per-feature share of the squared distance: c_i = d_i * (P d)_i (sums to the score)."""
        D = self._z(X) - self.mu
        return D * (D @ self.P)


class IForestModel:
    name = "iforest"

    def __init__(self, n_estimators: int = 200, random_state: int = 42):
        self.n_estimators, self.random_state = n_estimators, random_state

    def fit(self, X: np.ndarray) -> "IForestModel":
        self.m = IsolationForest(n_estimators=self.n_estimators, random_state=self.random_state,
                                 contamination="auto", n_jobs=-1).fit(X)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        return -self.m.score_samples(X)


class OCSVMModel:
    name = "ocsvm"

    def __init__(self, nu: float = 0.02, max_train: int = 2500, random_state: int = 42):
        self.nu, self.max_train, self.random_state = nu, max_train, random_state

    def fit(self, X: np.ndarray) -> "OCSVMModel":
        self.scaler = StandardScaler().fit(X)
        Z = self.scaler.transform(X)
        if len(Z) > self.max_train:                  # O(n^2) kernel: subsample for speed
            idx = np.random.default_rng(self.random_state).choice(len(Z), self.max_train, replace=False)
            Z = Z[idx]
        self.m = OneClassSVM(kernel="rbf", nu=self.nu, gamma="scale").fit(Z)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        return -self.m.decision_function(self.scaler.transform(X))


MODEL_TYPES = {"mahalanobis": MahalanobisModel, "iforest": IForestModel, "ocsvm": OCSVMModel}


def make_model(name: str):
    return MODEL_TYPES[name]()


# =============================================================================
# SECTION 3: Phase-conditioned wrapper
# =============================================================================
class PhaseConditioned:
    """One sub-model per phase group with >= min_rows rows, plus a pooled model."""

    def __init__(self, model_name: str, min_rows: int = 150, conditioned: bool = True):
        self.model_name = model_name
        self.min_rows = min_rows
        self.conditioned = conditioned
        self.models: Dict[str, object] = {}

    def fit(self, X: np.ndarray, groups: np.ndarray) -> "PhaseConditioned":
        self.models = {POOLED: make_model(self.model_name).fit(X)}
        if self.conditioned:
            for g in np.unique(groups):
                if g == "unlabelled":
                    continue
                m = groups == g
                if m.sum() >= self.min_rows:
                    self.models[g] = make_model(self.model_name).fit(X[m])
        return self

    def route(self, groups: np.ndarray) -> np.ndarray:
        """Which sub-model scores each row."""
        return np.array([g if g in self.models else POOLED for g in groups], dtype=object)

    def score(self, X: np.ndarray, groups: np.ndarray) -> np.ndarray:
        r = self.route(groups)
        s = np.empty(len(X))
        for key in np.unique(r):
            m = r == key
            s[m] = self.models[key].score(X[m])
        return s

    def contributions(self, X: np.ndarray, groups: np.ndarray) -> Optional[np.ndarray]:
        if self.model_name != "mahalanobis":
            return None
        r = self.route(groups)
        C = np.zeros_like(X, dtype=float)
        for key in np.unique(r):
            m = r == key
            C[m] = self.models[key].contributions(X[m])
        return C
