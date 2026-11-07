"""
test_pipeline_default_unchanged.py
Safety test for the optional `conditioned=` argument that Apex Lens added to
PdmPipeline.fit (approved by Adam on 7 Nov 2026). It proves the deployed
behaviour did not change:

  (a) no argument + no SmartThings labels  -> pooled model (conditioned False)
  (b) no argument + >= 50% SmartThings rows -> per-phase model (conditioned True)
  (c) fit(...) and fit(..., conditioned=None) give identical scores

Uses SYNTHETIC cycles only. Run:  py ml/tests/test_pipeline_default_unchanged.py
"""
# =============================================================================
# SECTION 1: Imports
# =============================================================================
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ml.feature_fusion import compute_features  # noqa: E402
from ml.pipeline import PdmPipeline  # noqa: E402
from ml.tests.test_pipeline_synthetic import make_cycle  # noqa: E402


# =============================================================================
# SECTION 2: Helpers
# =============================================================================
def features(labelled: bool) -> pd.DataFrame:
    """4 synthetic cycles turned into model features, with or without SmartThings phase labels."""
    parts = []
    for i in range(4):
        d = make_cycle(300 + i)
        d["session"] = f"c{i}"
        d["row"] = np.arange(len(d))               # window order inside the cycle
        if not labelled:
            d["phase"] = None                       # firmware-07 washes really have no labels
            d["phase_source"] = "none"
        parts.append(d)
    # compute_features also attaches phase_group / phase_source (resolve_phases)
    return compute_features(pd.concat(parts, ignore_index=True), schema="windowed")


# =============================================================================
# SECTION 3: Checks
# =============================================================================
def main() -> int:
    unl = features(labelled=False)
    p_default = PdmPipeline("mahalanobis").fit(unl, "windowed", True)
    assert p_default.conditioned is False, "unlabelled data must give a pooled model by default"

    lab = features(labelled=True)
    p_lab = PdmPipeline("mahalanobis").fit(lab, "windowed", True)
    assert p_lab.conditioned is True, "SmartThings-labelled data must be phase-conditioned by default"

    p_none = PdmPipeline("mahalanobis").fit(lab, "windowed", True, conditioned=None)
    a = p_lab.score(lab)["score"].to_numpy()
    b = p_none.score(lab)["score"].to_numpy()
    assert np.array_equal(a, b), "conditioned=None must behave exactly like no argument"

    print("[PASS] PdmPipeline default behaviour unchanged by the conditioned= override")
    return 0


if __name__ == "__main__":
    sys.exit(main())
