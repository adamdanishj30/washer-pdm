"""
calibration.py
Turns raw anomaly scores into numbers people can act on - honestly.

1. Baseline percentile (per routing key / phase)
   Using OUT-OF-FOLD healthy scores (each healthy cycle scored by a model
   that never saw it), u = fraction of healthy windows with a lower score.
   u = 0.99 means "more unusual than 99% of held-out healthy windows".
   This replaces v2's sigmoid "Machine Health 87.3%", which had no
   calibration behind it.

2. Traffic-light band per window
   green  u < 0.95,  amber 0.95 <= u < 0.995,  red u >= 0.995

3. Cycle-level decision (slow EWMA "persistence" statistic)
   Faults are persistent; a single loud 5-second window is not a fault.
   z_t = Phi^-1(u_t),  E_t = lam * z_t + (1 - lam) * E_{t-1},
   lam = 2 / (120 + 1)  ->  ~10 minutes of memory.
   The cycle is ABNORMAL if max_t E_t > h, with h = (largest healthy
   out-of-fold max E) + H_MARGIN_Z. The false-alarm rate is measured with
   NESTED leave-one-cycle-out, where h is set without the cycle being tested
   (ml/loco_eval.py).
   Why not CUSUM: tried first. On this data healthy cycles differ from each
   other by a persistent offset, and CUSUM integrates that offset over the
   whole cycle, so its threshold had to grow with cycle length (h ~ 240-500)
   and nothing short of a huge fault crossed it. A fixed-memory EWMA does
   not grow with cycle length. `cusum()` is kept for comparison plots.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & constants
# =============================================================================
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
from scipy.stats import norm

AMBER_U = 0.95
RED_U = 0.995
CUSUM_K = 0.5
PERSIST_WINDOWS = 120                       # 120 x 5 s = 10 min effective memory
EWMA_LAMBDA = 2.0 / (PERSIST_WINDOWS + 1)
H_MARGIN_Z = 0.25                           # additive margin above the worst healthy cycle (z units)
H_FLOOR = 0.75                              # never alarm below a sustained z of 0.75 (~p77)
ECDF_MAX_POINTS = 4000


# =============================================================================
# SECTION 2: Calibrator
# =============================================================================
@dataclass
class Calibrator:
    """Healthy out-of-fold score distribution per routing key + persistence threshold h."""
    ecdf: Dict[str, np.ndarray] = field(default_factory=dict)   # sorted healthy OOF scores
    h: float = H_FLOOR
    healthy_max_s: List[float] = field(default_factory=list)

    # ---------------------------------------------------------------- fitting
    @classmethod
    def from_oof(cls, scores: np.ndarray, routes: np.ndarray, sessions: np.ndarray) -> "Calibrator":
        cal = cls()
        for key in np.unique(routes):
            v = np.sort(scores[routes == key])
            if len(v) > ECDF_MAX_POINTS:                  # keep the artifact small, quantiles preserved
                v = np.quantile(v, np.linspace(0, 1, ECDF_MAX_POINTS))
            cal.ecdf[str(key)] = v
        # persistence threshold from the healthy cycles themselves (out-of-fold scores)
        u = cal.percentile(scores, routes)
        maxes = []
        for s in np.unique(sessions):
            m = sessions == s
            maxes.append(float(persistence(z_from_u(u[m])).max()))
        cal.healthy_max_s = maxes
        cal.h = max(H_FLOOR, max(maxes) + H_MARGIN_Z) if maxes else H_FLOOR
        return cal

    # ------------------------------------------------------------ application
    def percentile(self, scores: np.ndarray, routes: np.ndarray) -> np.ndarray:
        u = np.empty(len(scores))
        for key in np.unique(routes):
            m = routes == key
            ref = self.ecdf.get(str(key))
            if ref is None:                                # unseen route -> pooled reference
                ref = self.ecdf.get("__pooled__", np.array([0.0]))
            u[m] = np.searchsorted(ref, scores[m], side="right") / (len(ref) + 1.0)
        return u


# =============================================================================
# SECTION 3: Sequential statistics
# =============================================================================
def z_from_u(u: np.ndarray) -> np.ndarray:
    return norm.ppf(np.clip(u, 1e-4, 1 - 1e-4))


def cusum(z: np.ndarray, k: float = CUSUM_K) -> np.ndarray:
    s = np.zeros(len(z))
    acc = 0.0
    for i, v in enumerate(z):
        acc = max(0.0, acc + v - k)
        s[i] = acc
    return s


def ewma(z: np.ndarray, lam: float = EWMA_LAMBDA) -> np.ndarray:
    out = np.zeros(len(z))
    acc = 0.0
    for i, v in enumerate(z):
        acc = lam * v + (1 - lam) * acc
        out[i] = acc
    return out


def persistence(z: np.ndarray) -> np.ndarray:
    """The decision statistic: slow EWMA of calibrated z (restarted per cycle)."""
    return ewma(z, EWMA_LAMBDA)


def band(u: np.ndarray) -> np.ndarray:
    return np.where(u >= RED_U, "red", np.where(u >= AMBER_U, "amber", "green"))


def first_alarm_index(s: np.ndarray, h: float) -> int:
    """Index of the first window where the persistence statistic exceeds h, or -1."""
    idx = np.flatnonzero(s > h)
    return int(idx[0]) if len(idx) else -1
