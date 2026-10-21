"""
fault_injection.py
Severity-swept, physically-parameterised fault injection for validation.

Rules this module follows (fixes for v2's synthetic_fault_generator.py)
-----------------------------------------------------------------------
1. Inject ONLY into a held-out cycle, never into data the model trained on
   (v2 injected into the tail of the training set).
2. Inject into MEASUREMENTS (what the sensor/firmware reports), before
   feature computation - never directly into model features such as
   "parasitic_drag_w" (v2 did; the model then trivially "detects" the
   feature you edited).
3. Severity is in PHYSICAL units and swept from subtle to large, so the
   result is a curve "detection rate vs severity" and a minimum detectable
   severity, not a single PASS line.
4. A fault starts at `onset_frac` of the cycle and ramps in over ~3 minutes,
   so detection DELAY can be measured and the healthy first part of the cycle
   doubles as a false-alarm check.

Limits - state these when you report results
--------------------------------------------
* LEGACY data (one 8 ms audio snapshot + one accel sample per 5 s) cannot
  represent impulsive spall physics; the legacy faults are broadband level
  changes. They test "would the pipeline notice a sustained change of this
  size", not "would it notice a real bearing defect".
* WINDOWED faults use moment algebra for an independent added component
  (energy adds; kurtosis mixes by the formula in _mix_kurtosis). That is a
  model of how a spall would move the firmware features, not a recording of
  one. ml/waveform_fault_study.py does the stronger version: it adds
  synthetic spall impulses to REAL recorded audio clips and runs the exact
  firmware DSP on them.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & fault catalogue
# =============================================================================
from typing import Dict, List

import numpy as np
import pandas as pd

ROTATING_GROUPS = ("wash", "rinse", "spin", "unlabelled")   # where mechanical faults show up

# kind -> (schema, unit, severity levels, plain-language meaning)
FAULTS: Dict[str, Dict] = {
    # ---------------- legacy (firmware 05/06 snapshots) ----------------
    "acoustic_rise": dict(schema="legacy", unit="x RMS", levels=[0.10, 0.25, 0.50, 1.00],
                          meaning="sustained broadband noise increase (+10% .. +100% sound pressure)"),
    "vibration_rise": dict(schema="legacy", unit="m/s2 RMS", levels=[0.02, 0.05, 0.10, 0.20],
                           meaning="added random cabinet vibration (looser suspension / imbalance)"),
    "power_drag": dict(schema="both", unit="W", levels=[5.0, 10.0, 20.0, 40.0],
                       meaning="extra motor power to overcome friction"),
    # ---------------- windowed (firmware 07 features) ----------------
    "bearing_impulsive": dict(schema="windowed", unit="x hp RMS", levels=[0.10, 0.25, 0.50, 1.00],
                              meaning="impulsive 2-8 kHz energy (spall impacts), amplitude relative to "
                                      "the healthy high-band RMS"),
    "suspension_rocking": dict(schema="windowed", unit="m/s2 RMS", levels=[0.01, 0.02, 0.05, 0.10],
                               meaning="extra 0.5-15 Hz cabinet rocking (worn damper)"),
    "imbalance_1x": dict(schema="windowed", unit="m/s2 RMS", levels=[0.02, 0.05, 0.10, 0.20],
                         meaning="extra once-per-revolution vibration during spin"),
}

IMPULSE_KURTOSIS = 20.0      # kurtosis of an impact train (Gaussian = 3)
RAMP_WINDOWS = 36            # 36 x 5 s = 3 minute ramp-in


def faults_for_schema(schema: str, has_power: bool) -> List[str]:
    out = []
    for k, f in FAULTS.items():
        if f["schema"] in (schema, "both") and (k != "power_drag" or has_power):
            out.append(k)
    return out


# =============================================================================
# SECTION 2: Helpers
# =============================================================================
def _ramp(n: int, onset: int) -> np.ndarray:
    """0 before onset, linear 0->1 over RAMP_WINDOWS, then 1."""
    r = np.zeros(n)
    idx = np.arange(n)
    r[idx >= onset] = np.clip((idx[idx >= onset] - onset + 1) / RAMP_WINDOWS, 0, 1)
    return r


def _add_rms(base, added):
    """RMS of the sum of two independent components."""
    return np.sqrt(np.asarray(base, float) ** 2 + np.asarray(added, float) ** 2)


def _mix_kurtosis(k_b, s_b, k_i, s_i):
    """
    Kurtosis of X = B + I (independent, zero mean):
      E[X^4] = k_b s_b^4 + k_i s_i^4 + 6 s_b^2 s_i^2,   Var = s_b^2 + s_i^2
    """
    vb, vi = s_b ** 2, s_i ** 2
    return (k_b * vb ** 2 + k_i * vi ** 2 + 6 * vb * vi) / np.maximum((vb + vi) ** 2, 1e-12)


# =============================================================================
# SECTION 3: Injection
# =============================================================================
def inject(session_df: pd.DataFrame, kind: str, severity: float,
           onset_frac: float = 0.5, seed: int = 0) -> pd.DataFrame:
    """
    Return a copy of ONE session's raw rows with the fault applied and a
    `fault_active` column (ramp value 0..1). Columns are the CSV columns
    (measurements), not model features.
    """
    df = session_df.sort_values("row").copy()
    n = len(df)
    onset = int(onset_frac * n)
    ramp = _ramp(n, onset)
    rng = np.random.default_rng(seed)
    grp = df["phase_group"].to_numpy() if "phase_group" in df.columns else np.array(["unlabelled"] * n)
    rot = np.isin(grp, ROTATING_GROUPS).astype(float)
    a = ramp * severity

    if kind == "acoustic_rise":
        df["audio_rms"] = df["audio_rms"].astype(float) * (1.0 + a * rot)
    elif kind == "vibration_rise":
        for ax in ("accel_x", "accel_y", "accel_z"):
            df[ax] = df[ax].astype(float) + rng.normal(0.0, 1.0, n) * a * rot / np.sqrt(3)
    elif kind == "power_drag":
        df["power_w"] = df["power_w"].astype(float) + a * rot
        if "power_min" in df.columns:
            df["power_min"] = df["power_min"].astype(float) + a * rot
            df["power_max"] = df["power_max"].astype(float) + a * rot
    elif kind == "bearing_impulsive":
        hp = df["audio_hp_rms"].astype(float).to_numpy()
        s_i = a * rot * hp                                   # impulse RMS relative to healthy hp band
        df["audio_hp_kurtosis"] = _mix_kurtosis(df["audio_hp_kurtosis"].astype(float), hp, IMPULSE_KURTOSIS, s_i)
        df["audio_hp_rms"] = _add_rms(hp, s_i)
        rms = df["audio_rms"].astype(float).to_numpy()
        df["audio_kurtosis"] = _mix_kurtosis(df["audio_kurtosis"].astype(float), rms, IMPULSE_KURTOSIS, s_i)
        df["audio_rms"] = _add_rms(rms, s_i)
        # impulse energy split between the 2-4 kHz and 4-8 kHz bands
        df["audio_band_2k_4k"] = _add_rms(df["audio_band_2k_4k"].astype(float), s_i / np.sqrt(2))
        df["audio_band_4k_8k"] = _add_rms(df["audio_band_4k_8k"].astype(float), s_i / np.sqrt(2))
        peak_i = s_i * np.sqrt(IMPULSE_KURTOSIS) * 1.5
        df["audio_peak"] = np.maximum(df["audio_peak"].astype(float), peak_i)
        df["audio_crest"] = df["audio_peak"] / df["audio_rms"]
        df["audio_block_rms_max"] = _add_rms(df["audio_block_rms_max"].astype(float), 2.0 * s_i)
        # centroid moves toward ~4 kHz in proportion to the added energy share
        share = s_i ** 2 / np.maximum(df["audio_rms"].astype(float) ** 2, 1e-12)
        df["audio_centroid_hz"] = (1 - share) * df["audio_centroid_hz"].astype(float) + share * 4000.0
    elif kind in ("suspension_rocking", "imbalance_1x"):
        add = a * rot
        if kind == "imbalance_1x":
            add = add * np.isin(grp, ("spin", "unlabelled"))
            df["vib_dom_rms"] = _add_rms(df["vib_dom_rms"].astype(float), add)
            df["vib_band_15_30"] = _add_rms(df["vib_band_15_30"].astype(float), add)
        else:
            df["vib_band_0_5"] = _add_rms(df["vib_band_0_5"].astype(float), add / np.sqrt(2))
            df["vib_band_5_15"] = _add_rms(df["vib_band_5_15"].astype(float), add / np.sqrt(2))
        # horizontal plane carries the motion; split between x and y
        for ax in ("x", "y"):
            df[f"vib_std_{ax}"] = _add_rms(df[f"vib_std_{ax}"].astype(float), add / np.sqrt(2))
            df[f"vib_ptp_{ax}"] = df[f"vib_ptp_{ax}"].astype(float) + 2.83 * add / np.sqrt(2)
        df["vib_mag_std"] = _add_rms(df["vib_mag_std"].astype(float), 0.5 * add)
    else:
        raise ValueError(f"unknown fault kind {kind}")

    df["fault_active"] = ramp * rot
    return df
