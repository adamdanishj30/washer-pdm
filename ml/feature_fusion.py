"""
feature_fusion.py  (v3)
Feature extraction + early fusion for the Washer PdM anomaly detector.

What changed from v2 and why
----------------------------
* NO fitting side effects. v2's fit() computed phase statistics on ALL data
  and wrote them to disk, so every later evaluation leaked the test cycle
  into its own normalisation. Here every transform is either stateless or
  uses only the cycle being transformed (see "self-referenced" below).
  All learned normalisation lives inside the detectors (ml/detectors.py),
  which are fitted per LOCO fold.
* Pruned features. v2 fed audio RMS, log RMS and dB (three monotonic copies)
  plus raw accel axes and |a| to the model. Isolation Forest picks features
  at random, so duplicates silently over-weight one signal.
* Orientation-independent vibration features. The rig's accelerometer was
  re-mounted between 16 and 17 Oct 2026 (accel_y median 1.42 -> 2.14 m/s^2).
  Raw axis values would flag every later cycle as "anomalous" because of
  the mounting, not the machine. We use deviations from each cycle's own
  median gravity vector instead.
* Power is optional. 4 of the 8 baseline cycles have no Tapo power at all
  and one more has a dead channel (max 5 W). Power features are used only
  when every training cycle has valid power.
* Two input schemas:
    LEGACY   - firmware 05/06 snapshots (one sample per 5 s).
    WINDOWED - firmware 07 window features (full-signal statistics).

"Self-referenced" transforms: a cycle's median gravity vector is computed
from that cycle alone, both in training and at inference. It is a per-cycle
calibration (like taring a scale), not information from other cycles.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & constants
# =============================================================================
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REAL_SESSIONS_DIR = BASE_DIR / "data" / "real_sessions"

LEGACY_RMS_RATIO = 256000.0 / 16384.0   # firmware-06 amplified divisor (rectified on load)
ROLL_WINDOWS = 12                       # 12 x 5 s = 1 minute rolling context
EPS = 1e-6

# SmartThings washerJobState -> operational group
PHASE_GROUPS: Dict[str, Sequence[str]] = {
    "idle": ("stop", "pause", "finish", "offline", "idle", "none"),
    "sensing": ("weightsensing", "sensing", "weight_sensing"),
    "wash": ("wash", "soak", "tumble", "agitation", "prewash"),
    "rinse": ("rinse", "drain", "spin_rinse"),
    "spin": ("spin", "high_spin", "extract", "drying"),
}
POWER_VALID_MIN_P95_W = 50.0            # a cycle whose 95th-pct power < 50 W has no usable power data


# =============================================================================
# SECTION 2: Loading
# =============================================================================
def load_sessions(paths: Optional[Sequence[Path]] = None) -> pd.DataFrame:
    """
    Load session CSVs into one frame with a `session` column (file stem) and
    a `row` column (order inside the session). Backup files are ignored.
    """
    if paths is None:
        paths = sorted(p for p in REAL_SESSIONS_DIR.glob("*.csv") if ".bak" not in p.name)
    frames = []
    for p in paths:
        df = pd.read_csv(p)
        if len(df) < 3:
            continue
        df["session"] = Path(p).stem
        df["row"] = np.arange(len(df))
        frames.append(df)
    if not frames:
        raise FileNotFoundError("no session CSVs found")
    return pd.concat(frames, ignore_index=True)


def detect_schema(df: pd.DataFrame) -> str:
    """'windowed' for firmware-07 data (has audio_kurtosis values), else 'legacy'."""
    if "audio_kurtosis" in df.columns and df["audio_kurtosis"].notna().mean() > 0.5:
        return "windowed"
    return "legacy"


# =============================================================================
# SECTION 3: Phase resolution (with explicit provenance)
# =============================================================================
def _map_phase(raw) -> Optional[str]:
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None
    p = str(raw).strip().lower()
    for grp, names in PHASE_GROUPS.items():
        if p in names:
            return grp if p != "none" else None
    return None


def resolve_phases(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds `phase_group` and `phase_source`:
      smartthings - label came from the SmartThings timeline (phase_source
                    column of firmware-07 CSVs, or a non-'none' label);
      none        - no label. We deliberately do NOT invent phases from
                    audio loudness (v2 did: that makes "audio is unusual for
                    this phase" circular, because the phase was guessed
                    from the audio).
    """
    out = df.copy()
    groups = out["phase"].map(_map_phase) if "phase" in out.columns else pd.Series([None] * len(out))
    if "phase_source" in out.columns:
        src = np.where(out["phase_source"].astype(str) == "smartthings", "smartthings", "none")
        groups = groups.where(src == "smartthings", None)
    else:
        src = np.where(groups.notna(), "smartthings", "none")
    out["phase_group"] = groups.fillna("unlabelled")
    out["phase_source"] = src
    return out


def session_power_valid(df: pd.DataFrame) -> Dict[str, bool]:
    """Per session: does the Tapo power column contain a real washer load?"""
    if "power_w" not in df.columns:
        return {s: False for s in df["session"].unique()}
    p95 = df.groupby("session")["power_w"].quantile(0.95)
    return {s: bool(v >= POWER_VALID_MIN_P95_W) for s, v in p95.items()}


# =============================================================================
# SECTION 4: Feature definitions
# =============================================================================
@dataclass
class FeatureSpec:
    """Which features a model uses (stored with the model so inference matches)."""
    schema: str
    use_power: bool
    names: List[str] = field(default_factory=list)
    groups: Dict[str, str] = field(default_factory=dict)   # feature -> acoustic | vibration | power


LEGACY_BASE = {
    "audio_log_rms": "acoustic",          # log loudness of the 8 ms snapshot
    "audio_log_rms_roll_mean": "acoustic",  # 1-min mean loudness (sustained level)
    "audio_log_rms_roll_std": "acoustic",   # 1-min variability (rattles, knocks)
    "vib_dev": "vibration",               # |a - cycle median gravity vector|  (orientation-free)
    "vib_dev_roll_mean": "vibration",
    "vib_dev_roll_std": "vibration",
}
LEGACY_POWER = {"power_log": "power", "power_log_roll_std": "power"}

WINDOWED_BASE = {
    "audio_log_rms": "acoustic",
    "audio_crest": "acoustic",
    "audio_log_kurtosis": "acoustic",
    "audio_log_hp_rms": "acoustic",
    "audio_log_hp_kurtosis": "acoustic",
    "audio_burst_ratio": "acoustic",      # log(block max / window rms): short bursts
    "audio_centroid_khz": "acoustic",
    "audio_shape_0_250": "acoustic",      # log(band rms / total rms): spectral SHAPE, loudness-free
    "audio_shape_250_500": "acoustic",
    "audio_shape_500_1k": "acoustic",
    "audio_shape_1k_2k": "acoustic",
    "audio_shape_2k_4k": "acoustic",
    "audio_shape_4k_8k": "acoustic",
    "vib_log_std_xy": "vibration",        # horizontal-plane dynamic level (tilt-insensitive enough)
    "vib_log_std_z": "vibration",
    "vib_log_mag_std": "vibration",
    "vib_dom_hz": "vibration",            # ~drum speed
    "vib_log_dom_rms": "vibration",
    "vib_log_band_0_5": "vibration",
    "vib_log_band_5_15": "vibration",
    "vib_log_band_15_30": "vibration",
    "vib_log_band_30_60": "vibration",
}
WINDOWED_POWER = {"power_log": "power", "power_log_std": "power"}


def make_spec(schema: str, use_power: bool) -> FeatureSpec:
    base, pw = (LEGACY_BASE, LEGACY_POWER) if schema == "legacy" else (WINDOWED_BASE, WINDOWED_POWER)
    groups = dict(base)
    if use_power:
        groups.update(pw)
    return FeatureSpec(schema=schema, use_power=use_power, names=list(groups), groups=groups)


# =============================================================================
# SECTION 5: Feature computation (per session, no cross-session state)
# =============================================================================
def _rolling(s: pd.Series, fn: str) -> pd.Series:
    r = s.rolling(ROLL_WINDOWS, min_periods=3)
    return getattr(r, fn)()


def _legacy_session(g: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=g.index)
    rms = g["audio_rms"].astype(float)
    rms = np.where(rms > 2500.0, rms / LEGACY_RMS_RATIO, rms)        # firmware-06 scale bug
    a = np.log1p(np.clip(rms, 0, None))
    out["audio_log_rms"] = a
    out["audio_log_rms_roll_mean"] = _rolling(pd.Series(a, index=g.index), "mean")
    out["audio_log_rms_roll_std"] = _rolling(pd.Series(a, index=g.index), "std")
    acc = g[["accel_x", "accel_y", "accel_z"]].astype(float).to_numpy()
    g0 = np.nanmedian(acc, axis=0)                                    # this cycle's static gravity vector
    dev = np.linalg.norm(acc - g0, axis=1)
    out["vib_dev"] = dev
    out["vib_dev_roll_mean"] = _rolling(pd.Series(dev, index=g.index), "mean")
    out["vib_dev_roll_std"] = _rolling(pd.Series(dev, index=g.index), "std")
    if "power_w" in g.columns:
        p = np.log1p(np.clip(g["power_w"].astype(float), 0, None))
        out["power_log"] = p
        out["power_log_roll_std"] = _rolling(pd.Series(p, index=g.index), "std")
    return out


def _lg(x) -> np.ndarray:
    return np.log(np.clip(np.asarray(x, dtype=float), EPS, None))


def _windowed_session(g: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=g.index)
    rms = g["audio_rms"].astype(float)
    out["audio_log_rms"] = _lg(rms)
    out["audio_crest"] = g["audio_crest"].astype(float)
    out["audio_log_kurtosis"] = _lg(g["audio_kurtosis"])
    out["audio_log_hp_rms"] = _lg(g["audio_hp_rms"])
    out["audio_log_hp_kurtosis"] = _lg(g["audio_hp_kurtosis"])
    out["audio_burst_ratio"] = _lg(g["audio_block_rms_max"]) - _lg(rms)
    out["audio_centroid_khz"] = g["audio_centroid_hz"].astype(float) / 1000.0
    for b in ["0_250", "250_500", "500_1k", "1k_2k", "2k_4k", "4k_8k"]:
        out[f"audio_shape_{b}"] = _lg(g[f"audio_band_{b}"]) - _lg(rms)
    sxy = np.sqrt(g["vib_std_x"].astype(float) ** 2 + g["vib_std_y"].astype(float) ** 2)
    out["vib_log_std_xy"] = _lg(sxy)
    out["vib_log_std_z"] = _lg(g["vib_std_z"])
    out["vib_log_mag_std"] = _lg(g["vib_mag_std"])
    out["vib_dom_hz"] = g["vib_dom_hz"].astype(float)
    out["vib_log_dom_rms"] = _lg(g["vib_dom_rms"])
    for b in ["0_5", "5_15", "15_30", "30_60"]:
        out[f"vib_log_band_{b}"] = _lg(g[f"vib_band_{b}"])
    if "power_w" in g.columns:
        out["power_log"] = np.log1p(np.clip(g["power_w"].astype(float), 0, None))
        if "power_std" in g.columns:
            out["power_log_std"] = np.log1p(np.clip(g["power_std"].astype(float), 0, None))
    return out


def compute_features(df: pd.DataFrame, schema: Optional[str] = None) -> pd.DataFrame:
    """
    Returns df with feature columns appended (all candidate features; select
    with a FeatureSpec). Rolling statistics never cross session boundaries
    (v2 computed them across the concatenated sessions).
    """
    schema = schema or detect_schema(df)
    fn = _legacy_session if schema == "legacy" else _windowed_session
    parts = [fn(g.sort_values("row")) for _, g in df.groupby("session", sort=False)]
    feats = pd.concat(parts).reindex(df.index)
    # Some firmware-07 CSV columns (audio_crest, vib_dom_hz) share a name with a
    # feature: keep ONE column (the feature) so selections never duplicate.
    out = pd.concat([df.drop(columns=[c for c in feats.columns if c in df.columns]), feats], axis=1)
    return resolve_phases(out)


def feature_matrix(df_feat: pd.DataFrame, spec: FeatureSpec) -> np.ndarray:
    """Feature matrix with NaNs replaced by the column median (first rows of rolling stats)."""
    X = np.array(df_feat[spec.names].astype(float).to_numpy(), dtype=float, copy=True)
    if np.isnan(X).any():
        med = np.nanmedian(X, axis=0)
        med = np.where(np.isnan(med), 0.0, med)
        r, c = np.where(np.isnan(X))
        X[r, c] = med[c]
    return X
