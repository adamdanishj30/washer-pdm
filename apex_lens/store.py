"""
store.py
Loads firmware-07 wash recordings and prepares them for the Apex Lens tools.

What happens to each wash
-------------------------
1. Only firmware-07 (windowed) CSVs are used. Legacy 05/06 snapshots have a
   different meaning per row and are never mixed in.
2. Accelerometer integrity check per window. The MPU-6050 FIFO can desync
   (seen on 24 Oct, 27 Oct 06:24 and 2 Nov 06:37), which rotates the axes and
   produces fake vibration. A window's vibration data is marked bad when
     | |a| - 9.81 | > 1.5 m/s^2, or accel_clip_samples > 0, or
     the gravity vector is more than 30 deg away from the median of the first
     60 windows.
   Bad windows are left out of every vibration statistic and of the detector.
3. Phases from power only (no SmartThings labels exist for these washes):
     idle   - before the first / after the last active window (power >= 20 W)
     heat   - >= 20 consecutive windows above 1000 W (heater)
     spin   - >= 20 consecutive windows in 200..1000 W (drum extraction)
     tumble - everything else between start and end (fill, wash, rinse,
              drain and pauses cannot be told apart from power alone)
4. Wash class inferred from power with ml/cycle_signature_report.py rules
   (Quick / Long cold / Long hot). It is an inference, not the programme the
   user picked.

Virtual washes
--------------
`register()` adds a wash under any id (for example a recording with an
injected fault, stored under a neutral name so an LLM cannot tell from the
id). Every tool works the same on real and virtual washes.
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

from ml.cycle_signature_report import classify_signature, count_spin_blocks, find_signature_blocks

BASE_DIR = Path(__file__).resolve().parent.parent
REAL_SESSIONS_DIR = BASE_DIR / "data" / "real_sessions"

WINDOW_S = 5.024
ACTIVE_W = 20.0                 # below this the washer is idle or paused
MIN_ACTIVE_WINDOWS = 60         # a "wash" needs at least ~5 min of active power
G = 9.81
G_TOL = 1.5                     # m/s^2
TILT_MAX_DEG = 30.0
TILT_REF_WINDOWS = 60
PHASES = ("idle", "tumble", "heat", "spin")
VIB_COLS = ("vib_std_x", "vib_std_y", "vib_std_z", "vib_ptp_x", "vib_ptp_y", "vib_ptp_z", "vib_mag_std",
            "vib_dom_hz", "vib_dom_rms", "vib_band_0_5", "vib_band_5_15", "vib_band_15_30", "vib_band_30_60")


# =============================================================================
# SECTION 2: Per-wash preparation
# =============================================================================
def is_windowed(df: pd.DataFrame) -> bool:
    return "audio_kurtosis" in df.columns and df["audio_kurtosis"].notna().mean() > 0.5


def vib_bad_mask(df: pd.DataFrame) -> np.ndarray:
    """True where the window's accelerometer data cannot be trusted."""
    acc = df[["accel_x", "accel_y", "accel_z"]].astype(float).to_numpy()
    mag = np.linalg.norm(acc, axis=1)
    bad = np.abs(mag - G) > G_TOL
    if "accel_clip_samples" in df.columns:
        bad |= df["accel_clip_samples"].fillna(0).to_numpy() > 0
    ref = np.nanmedian(acc[:TILT_REF_WINDOWS], axis=0)
    if np.all(np.isfinite(ref)) and np.linalg.norm(ref) > 0:
        unit = acc / np.maximum(mag[:, None], 1e-9)
        cosang = unit @ (ref / np.linalg.norm(ref))
        bad |= np.degrees(np.arccos(np.clip(cosang, -1, 1))) > TILT_MAX_DEG
    bad |= ~np.isfinite(mag)
    return bad


def power_phases(power: np.ndarray) -> np.ndarray:
    """Phase per window from power only (see module docstring)."""
    p = np.nan_to_num(np.asarray(power, float), nan=0.0)
    n = len(p)
    ph = np.array(["idle"] * n, dtype=object)
    active = np.flatnonzero(p >= ACTIVE_W)
    if len(active) == 0:
        return ph
    ph[active[0]:active[-1] + 1] = "tumble"
    for b in find_signature_blocks(p.tolist()):
        ph[b["i0"]:b["i1"] + 1] = "heat" if b["type"] == "heater" else "spin"
    return ph


@dataclass
class Wash:
    wash_id: str
    df: pd.DataFrame                 # raw CSV rows + `row`, `t_min`, `phase`, `vib_ok`
    source: str = "recording"        # file name, or a note for virtual washes
    is_wash: bool = True
    wash_class: str = "Unclassified"
    notes: List[str] = field(default_factory=list)
    origin: Optional[str] = None     # recording a virtual wash was made from
    reference: bool = True           # may this wash define "normal" for others?

    @property
    def n(self) -> int:
        return len(self.df)

    @property
    def duration_min(self) -> float:
        return self.n * WINDOW_S / 60.0


def prepare(df: pd.DataFrame, wash_id: str, source: str = "recording") -> Wash:
    df = df.reset_index(drop=True).copy()
    df["row"] = np.arange(len(df))
    df["t_min"] = df["row"] * WINDOW_S / 60.0
    p = df["power_w"].astype(float).to_numpy() if "power_w" in df.columns else np.zeros(len(df))
    df["phase"] = power_phases(p)
    df["vib_ok"] = ~vib_bad_mask(df)
    w = Wash(wash_id=wash_id, df=df, source=source)

    n_active = int((p >= ACTIVE_W).sum())
    if n_active < MIN_ACTIVE_WINDOWS:
        w.is_wash = False
        w.notes.append(f"not a wash: only {n_active} windows with power >= {ACTIVE_W:.0f} W")
    heater_min = float((df["phase"] == "heat").sum()) * WINDOW_S / 60.0
    spin_blocks = count_spin_blocks(np.nan_to_num(p).tolist())
    active_min = float((df["phase"] != "idle").sum()) * WINDOW_S / 60.0
    w.wash_class = classify_signature(float(np.nanmax(p)) if len(p) else 0.0, round(heater_min, 1),
                                      spin_blocks, active_min).replace(" (inferred)", "")
    n_bad = int((~df["vib_ok"]).sum())
    if n_bad:
        w.notes.append(f"{n_bad} of {len(df)} windows have bad accelerometer data (excluded from vibration)")
    return w


# =============================================================================
# SECTION 3: Store
# =============================================================================
class WashStore:
    """All washes the tools can see, keyed by id."""

    def __init__(self) -> None:
        self.washes: Dict[str, Wash] = {}

    @classmethod
    def from_dir(cls, folder: Path = REAL_SESSIONS_DIR, ids: Optional[Sequence[str]] = None) -> "WashStore":
        st = cls()
        for p in sorted(Path(folder).glob("wash_cycle_*.csv")):
            df = pd.read_csv(p)
            if len(df) < 3 or not is_windowed(df):
                continue
            wid = p.stem.replace("wash_cycle_", "")
            if ids is not None and wid not in ids:
                continue
            st.washes[wid] = prepare(df, wid, source=p.name)
        return st

    def register(self, wash_id: str, df: pd.DataFrame, source: str = "virtual",
                 origin: Optional[str] = None) -> Wash:
        """Add a virtual wash. It never joins the reference set ("normal")."""
        cols = [c for c in df.columns if c not in ("row", "t_min", "phase", "vib_ok", "fault_active",
                                                   "session", "phase_group")]
        w = prepare(df[cols], wash_id, source=source)
        w.origin, w.reference = origin, False
        self.washes[wash_id] = w
        return w

    def get(self, wash_id: str) -> Wash:
        if wash_id not in self.washes:
            raise KeyError(f"unknown wash id '{wash_id}'. Call list_washes for valid ids.")
        return self.washes[wash_id]

    def reference_ids(self, wash_id: str) -> List[str]:
        """
        Washes that define 'normal' for `wash_id`: every other recorded wash,
        never the wash itself and never the recording it was made from
        (otherwise a fault-injected copy would be compared with its own
        healthy original).
        """
        w = self.get(wash_id)
        skip = {wash_id, w.origin}
        return [k for k, x in self.washes.items() if k not in skip and x.reference and x.is_wash]
