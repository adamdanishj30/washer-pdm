"""
session_export.py
One shared implementation of "Firebase session batches -> archived CSV".

Before this module, cloud_downloader.py, cloud_multimodal_sync.py and
auto_drive_sync_daemon.py each carried their own copy of the CSV writer.
They now all call `export_session_to_csv()` here.

Two record schemas are supported:

* LEGACY (firmware 04/05/06): one instantaneous snapshot every 5 s
      {"t", "ts", "ax", "ay", "az", "rms", "pwr"}
  -> written exactly as before (8 columns), so old files stay identical.

* V3 (firmware 07): one feature vector per 5.024 s window, compact keys
  (see V3_KEY_MAP). -> written as the same first 8 columns (so
  build_clean_dashboard.py keeps working) PLUS the window features.

Column meaning for V3 rows: accel_x/y/z are window MEANS (gravity/tilt),
audio_rms is the full-window RMS, power_w is the mean of ~5 Tapo samples.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & paths
# =============================================================================
import csv
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REAL_DIR = DATA_DIR / "real_sessions"
TEST_DIR = DATA_DIR / "testing_data"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from firmware.smartthings_client import (  # noqa: E402
    estimate_point_phase_fallback,
    fetch_session_phase_timeline,
)

LEGACY_COLUMNS = ["timestamp_ms", "accel_x", "accel_y", "accel_z", "audio_rms", "power_w", "phase", "load_class"]

# Firmware-07 compact key -> CSV column. Order here = column order in the CSV.
V3_KEY_MAP: List[Tuple[str, str]] = [
    ("e", "epoch_ms"), ("na", "n_audio"), ("nv", "n_accel"), ("np", "n_power"),
    ("ov", "fifo_overflows"), ("vc", "accel_clip_samples"),
    ("apk", "audio_peak"), ("acr", "audio_crest"), ("aku", "audio_kurtosis"),
    ("ahr", "audio_hp_rms"), ("ahk", "audio_hp_kurtosis"),
    ("abm", "audio_block_rms_max"), ("ab9", "audio_block_rms_p90"), ("acn", "audio_centroid_hz"),
    ("ab0", "audio_band_0_250"), ("ab1", "audio_band_250_500"), ("ab2", "audio_band_500_1k"),
    ("ab3", "audio_band_1k_2k"), ("ab4", "audio_band_2k_4k"), ("ab5", "audio_band_4k_8k"),
    ("sx", "vib_std_x"), ("sy", "vib_std_y"), ("sz", "vib_std_z"),
    ("px", "vib_ptp_x"), ("py", "vib_ptp_y"), ("pz", "vib_ptp_z"),
    ("sm", "vib_mag_std"), ("vdf", "vib_dom_hz"), ("vdr", "vib_dom_rms"),
    ("vb0", "vib_band_0_5"), ("vb1", "vib_band_5_15"), ("vb2", "vib_band_15_30"), ("vb3", "vib_band_30_60"),
    ("pmn", "power_min"), ("pmx", "power_max"), ("psd", "power_std"),
]
V3_COLUMNS = LEGACY_COLUMNS + [c for _, c in V3_KEY_MAP] + ["phase_source"]

# Historic session IDs whose file names were chosen by hand (kept so a forced
# re-download writes to the SAME file instead of creating duplicates).
LEGACY_FILENAME_OVERRIDES = {
    "wash_1020": "wash_cycle_2026-10-15_1020.csv",
}

MIN_REAL_SESSION_ROWS = 150      # shorter sessions are bench tests -> testing_data/
LEGACY_RMS_RATIO = 256000.0 / 16384.0


# =============================================================================
# SECTION 2: Batch parsing
# =============================================================================
def _sort_key(k: Any):
    s = str(k)
    if s.startswith("w") and s[1:].isdigit():
        return (0, int(s[1:]))
    if s.isdigit():
        return (0, int(s))
    return (1, s)


def batches_to_rows(batches: Any) -> List[Dict[str, Any]]:
    """Firebase node (dict or list) -> chronologically sorted list of records."""
    if isinstance(batches, dict):
        items = [v for _, v in sorted(batches.items(), key=lambda kv: _sort_key(kv[0]))]
    elif isinstance(batches, list):
        items = list(batches)
    else:
        return []
    return [r for r in items if isinstance(r, dict) and "ax" in r]


def is_v3(rows: List[Dict[str, Any]]) -> bool:
    """Firmware-07 windows carry kurtosis ('aku'); legacy snapshots never do."""
    return any("aku" in r for r in rows[:5])


def first_epoch_ms(rows: List[Dict[str, Any]]) -> Optional[float]:
    for r in rows:
        for key in ("e", "ts"):
            v = r.get(key)
            if isinstance(v, (int, float)) and v > 1_700_000_000_000:
                return float(v)
    return None


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _fmt(v: Optional[float], nd: int = 6) -> str:
    if v is None:
        return ""
    return f"{v:.{nd}g}"


# =============================================================================
# SECTION 3: File naming & routing
# =============================================================================
def format_session_filename(session_id: str, first_ts_ms: Optional[float] = None) -> str:
    """wash_cycle_YYYY-MM-DD_HHMM.csv (same rule the daemons always used)."""
    if session_id in LEGACY_FILENAME_OVERRIDES:
        return LEGACY_FILENAME_OVERRIDES[session_id]
    if session_id.startswith("wash_202"):
        clean = session_id.replace("wash_", "")
        for fmt in ("%Y-%m-%d_%H%M%S", "%Y-%m-%d_%H%M", "%Y%m%d_%H%M%S", "%Y%m%d_%H%M"):
            try:
                n = len(datetime.now().strftime(fmt))
                dt = datetime.strptime(clean[:n], fmt)
                return f"wash_cycle_{dt.strftime('%Y-%m-%d_%H%M')}.csv"
            except ValueError:
                pass
        return f"wash_cycle_{clean}.csv"
    if first_ts_ms and first_ts_ms > 1_700_000_000_000:
        dt = datetime.fromtimestamp(first_ts_ms / 1000.0)
        return f"wash_cycle_{dt.strftime('%Y-%m-%d_%H%M')}.csv"
    return f"wash_cycle_{datetime.now().strftime('%Y-%m-%d')}_{session_id.replace('wash_', '')}.csv"


def target_path(session_id: str, rows: List[Dict[str, Any]]) -> Path:
    fname = format_session_filename(session_id, first_epoch_ms(rows))
    is_test = len(rows) < MIN_REAL_SESSION_ROWS or "test" in fname.lower()
    return (TEST_DIR if is_test else REAL_DIR) / fname


# =============================================================================
# SECTION 4: Phase matching (SmartThings timeline, LOCF, fallback)
# =============================================================================
def _phase_for(row_epoch: Optional[float], timeline: List[Dict[str, Any]]) -> Optional[str]:
    """Last SmartThings checkpoint at or before the row (+15 s tolerance)."""
    if not timeline or not row_epoch:
        return None
    valid = [c for c in timeline if c["ts"] <= row_epoch + 15000]
    return valid[-1]["phase"] if valid else None


# =============================================================================
# SECTION 5: Export
# =============================================================================
def export_session_to_csv(session_id: str, batches: Any, st_info: Optional[dict] = None,
                          out_path: Optional[Path] = None) -> Optional[Path]:
    """
    Write one session to data/real_sessions/ or data/testing_data/.
    Returns the path written, or None if the session has < 3 records.
    """
    rows = batches_to_rows(batches)
    if len(rows) < 3:
        print(f"  [SKIP] session '{session_id}' has only {len(rows)} records")
        return None

    v3 = is_v3(rows)
    path = out_path or target_path(session_id, rows)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load class heuristic was uncalibrated ((W - 70) / 15); retired 2026-10-21.
    # We maintain the CSV column for schema stability, but always write "unknown" for new sessions.
    # Actual verified wash load (kg) is tracked in data/session_context.csv.
    load_class = "unknown"
    timeline = fetch_session_phase_timeline(session_id)
    first_ts = first_epoch_ms(rows)
    total_ms = (rows[-1].get("t", 0) - rows[0].get("t", 0)) if rows else 0

    # Legacy firmware 06 sometimes ran with an amplified RMS divisor: rectify.
    scale = 1.0
    if not v3:
        rms_vals = sorted(float(r["rms"]) for r in rows if _num(r.get("rms")) is not None)
        if rms_vals and rms_vals[len(rms_vals) // 2] > 1200.0:
            scale = LEGACY_RMS_RATIO

    last_phase = "none"
    n_st = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(V3_COLUMNS if v3 else LEGACY_COLUMNS)
        for r in rows:
            t = int(_num(r.get("t")) or 0)
            ax, ay, az = (_num(r.get(k)) for k in ("ax", "ay", "az"))
            rms = _num(r.get("rms"))
            if rms is not None:
                rms = rms / scale
            pwr = _num(r.get("pwr") if "pwr" in r else r.get("power"))
            vm = math.sqrt((ax or 0) ** 2 + (ay or 0) ** 2 + (az or 0) ** 2)

            # epoch of this row: v3 has "e"; legacy has server "ts" or first_ts + t
            row_epoch = _num(r.get("e")) or _num(r.get("ts"))
            if (not row_epoch or row_epoch < 1_700_000_000_000) and first_ts:
                row_epoch = first_ts + (t - rows[0].get("t", 0))

            phase = _phase_for(row_epoch, timeline)
            source = "smartthings" if phase and phase != "none" else "fallback"
            if source == "smartthings":
                n_st += 1
            else:
                phase = estimate_point_phase_fallback(pwr or 0.0, vm, rms or 0.0, t,
                                                      total_duration_ms=total_ms, last_phase=last_phase)
            if phase and phase not in ("none", "stop"):
                last_phase = phase

            if v3:
                base = [t, _fmt(ax, 5), _fmt(ay, 5), _fmt(az, 5), _fmt(rms, 6), _fmt(pwr, 5), phase, load_class]
                extra = [_fmt(_num(r.get(k)), 13 if k == "e" else 6) for k, _ in V3_KEY_MAP]
                w.writerow(base + extra + [source])
            else:
                w.writerow([t, f"{ax or 0:.2f}", f"{ay or 0:.2f}", f"{az or 0:.2f}",
                            f"{rms or 0:.1f}", f"{pwr or 0:.1f}", phase, load_class])

    shown = path.relative_to(BASE_DIR) if path.is_relative_to(BASE_DIR) else path
    print(f"  [SUCCESS] {shown}  ({len(rows)} {'windows' if v3 else 'snapshots'}, "
          f"load {load_class}, SmartThings phase on {n_st}/{len(rows)} rows)")
    if n_st == 0:
        print("  [WARN] no SmartThings phase labels matched this session - check the daemon was "
              "polling SmartThings while the washer ran (phase-conditioned ML needs them)")
    return path
