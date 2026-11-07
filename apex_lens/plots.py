"""
plots.py
render_plot for Apex Lens: one fixed-size chart (800 x 450 px) per call,
always with THIS washer's normal range behind it, plus a one-line caption
holding the numbers the chart shows (so every number an LLM quotes from a
chart can be traced back to text).

Kinds
-----
trace    up to 3 signals over time; phases shaded; per-phase normal band
         (p10..p90 of the other washes' windows in that phase) in grey;
         bad-accelerometer windows hatched; red detector windows marked
         with ticks if detector_score was called for this wash first.
bands    sound band energies and vibration band RMS for one phase:
         this wash's median vs the other washes' median, with their IQR.
         Frequency content is shown as bands, never as raw waveforms.
overlay  one signal's spread per phase (box plots): this wash vs the
         pooled windows of the other washes.

Read-only: returns PNG bytes, writes nothing to disk.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & constants
# =============================================================================
import io
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")                      # no screen needed
import matplotlib.pyplot as plt            # noqa: E402
import numpy as np                         # noqa: E402
import pandas as pd                        # noqa: E402

from apex_lens.store import PHASES, WINDOW_S  # noqa: E402

if TYPE_CHECKING:
    from apex_lens.tools import ApexLens

W_IN, H_IN, DPI = 8.0, 4.5, 100            # 800 x 450 px
PHASE_COLOURS = {"idle": "#ffffff", "tumble": "#e8f0fb", "heat": "#fdeedd", "spin": "#e9f6ec"}
AUDIO_BANDS = [("audio_band_0_250", "0-250"), ("audio_band_250_500", "250-500"), ("audio_band_500_1k", "0.5-1k"),
               ("audio_band_1k_2k", "1-2k"), ("audio_band_2k_4k", "2-4k"), ("audio_band_4k_8k", "4-8k")]
VIB_BANDS = [("vib_band_0_5", "0-5"), ("vib_band_5_15", "5-15"), ("vib_band_15_30", "15-30"),
             ("vib_band_30_60", "30-60")]


# =============================================================================
# SECTION 2: Helpers
# =============================================================================
def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI)          # fixed size: no bbox_inches="tight"
    plt.close(fig)
    return buf.getvalue()


def _values(lens: "ApexLens", wash_id: str, col: str) -> pd.Series:
    from apex_lens.tools import _valid
    return _valid(lens.store.get(wash_id), col)


def _ref_windows(lens: "ApexLens", refs: Sequence[str], col: str, ph: str) -> np.ndarray:
    """All usable windows of `col` in phase `ph` across the reference washes."""
    vals = []
    for r in refs:
        w = lens.store.get(r)
        v = _values(lens, r, col)[w.df["phase"] == ph].dropna().to_numpy()
        vals.append(v)
    return np.concatenate(vals) if vals else np.array([])


def _ref_medians(lens: "ApexLens", refs: Sequence[str], col: str, ph: str) -> np.ndarray:
    from apex_lens.tools import MIN_PHASE_WINDOWS
    out = []
    for r in refs:
        w = lens.store.get(r)
        m = w.df["phase"] == ph
        if m.sum() >= MIN_PHASE_WINDOWS and col in w.df.columns:
            out.append(_values(lens, r, col)[m].median())
    return np.array([x for x in out if np.isfinite(x)])


def _med(x) -> float:
    """Median ignoring NaN; NaN (printed '-') when nothing is usable, without a warning."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else float("nan")


def _runs(mask: np.ndarray) -> List[Tuple[int, int]]:
    """(start, end) index pairs of consecutive True values."""
    idx = np.flatnonzero(np.diff(np.concatenate([[0], mask.astype(int), [0]])))
    return list(zip(idx[::2], idx[1::2]))


# =============================================================================
# SECTION 3: The three kinds
# =============================================================================
def _trace(lens, wash_id, signals, phase) -> Tuple[bytes, str]:
    from apex_lens.tools import SIGNAL_COLS, fmt
    w = lens.store.get(wash_id)
    refs = lens.store.reference_ids(wash_id)
    df = w.df
    sel = np.ones(len(df), bool) if phase is None else (df["phase"] == phase).to_numpy()
    if not sel.any():
        raise ValueError(f"wash {wash_id} has no '{phase}' phase")
    t = df["t_min"].to_numpy()
    fig, axes = plt.subplots(len(signals), 1, figsize=(W_IN, H_IN), sharex=True, squeeze=False)
    caption = []
    scored = lens._scored.get(wash_id)
    for ax, name in zip(axes[:, 0], signals):
        col, unit = SIGNAL_COLS[name]
        y = _values(lens, wash_id, col).to_numpy()
        # phase shading and per-phase normal band
        bits = []
        for ph in PHASES:
            pm = (df["phase"] == ph).to_numpy() & sel
            for a, b in _runs(pm):
                ax.axvspan(t[a], t[b - 1] + WINDOW_S / 60, color=PHASE_COLOURS[ph], zorder=0, lw=0)
            if ph == "idle" or not pm.any():
                continue
            rw = _ref_windows(lens, refs, col, ph)
            if len(rw) >= 20:
                lo, hi = np.percentile(rw, [10, 90])
                for a, b in _runs(pm):
                    ax.fill_between([t[a], t[b - 1]], lo, hi, color="#9a9a9a", alpha=0.35, lw=0, zorder=1)
                bits.append(f"{ph} {fmt(_med(y[pm]))} (normal p10-p90 {fmt(lo)}-{fmt(hi)})")
            else:
                bits.append(f"{ph} {fmt(_med(y[pm]))} (normal: insufficient data)")
        ax.plot(t[sel], y[sel], color="#1f4e8c", lw=0.8, zorder=2)
        if col.startswith("vib_"):
            for a, b in _runs((~df["vib_ok"].to_numpy()) & sel):
                ax.axvspan(t[a], t[b - 1], facecolor="none", hatch="///", edgecolor="#c0392b", lw=0, zorder=3)
        if scored is not None:
            red = scored.loc[scored["band"] == "red", "row"].to_numpy()
            red = red[sel[red]]
            if len(red):
                ax.plot(t[red], np.full(len(red), np.nanmax(y[sel]) if np.isfinite(y[sel]).any() else 0),
                        "|", color="#c0392b", ms=6, zorder=4)
        ax.set_ylabel(f"{name}\n({unit})", fontsize=8)
        ax.tick_params(labelsize=7)
        caption.append(f"{name} median per phase: " + "; ".join(bits))
    axes[-1, 0].set_xlabel("minutes from start", fontsize=8)
    fig.suptitle(f"wash {wash_id}" + (f", {phase} only" if phase else "")
                 + " | grey = normal p10-p90 from other washes | hatched = bad accelerometer"
                 + (" | red ticks = detector red windows" if scored is not None else ""), fontsize=8)
    fig.tight_layout()
    return _png(fig), "chart: " + " || ".join(caption)


def _bands(lens, wash_id, phase) -> Tuple[bytes, str]:
    from apex_lens.tools import fmt
    w = lens.store.get(wash_id)
    refs = lens.store.reference_ids(wash_id)
    ph = phase or "spin"
    m = w.df["phase"] == ph
    if m.sum() < 6:
        raise ValueError(f"wash {wash_id} has no '{ph}' phase long enough to plot")
    fig, axes = plt.subplots(1, 2, figsize=(W_IN, H_IN))
    caption = []
    for ax, bands, title, unit in ((axes[0], AUDIO_BANDS, "sound bands (Hz)", "fw units"),
                                   (axes[1], VIB_BANDS, "vibration bands (Hz)", "m/s2")):
        mine, med, q1, q3, labels = [], [], [], [], []
        for col, lab in bands:
            if col not in w.df.columns:
                continue
            labels.append(lab)
            mine.append(_values(lens, wash_id, col)[m].median())
            rm = _ref_medians(lens, refs, col, ph)
            med.append(np.median(rm) if len(rm) else np.nan)
            q1.append(np.percentile(rm, 25) if len(rm) else np.nan)
            q3.append(np.percentile(rm, 75) if len(rm) else np.nan)
        x = np.arange(len(labels))
        med, q1, q3 = map(np.asarray, (med, q1, q3))
        ax.bar(x - 0.2, med, 0.4, yerr=[med - q1, q3 - med], color="#9a9a9a", label="normal median (IQR)",
               capsize=2)
        ax.bar(x + 0.2, mine, 0.4, color="#1f4e8c", label="this wash")
        ax.set_xticks(x, labels, fontsize=7)
        ax.set_yscale("log")
        ax.set_title(f"{title}, {ph}", fontsize=9)
        ax.set_ylabel(unit, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7)
        caption.append(f"{title.split()[0]} {ph} this/normal: "
                       + "; ".join(f"{lab} {fmt(a)}/{fmt(b)}" for lab, a, b in zip(labels, mine, med)))
    n = len(_ref_medians(lens, refs, "audio_rms", ph))
    fig.suptitle(f"wash {wash_id}: band energies in {ph} vs {n} other washes", fontsize=9)
    fig.tight_layout()
    return _png(fig), "chart: " + " || ".join(caption) + f" (n_ref={n})"


def _overlay(lens, wash_id, signal) -> Tuple[bytes, str]:
    from apex_lens.tools import SIGNAL_COLS, fmt
    col, unit = SIGNAL_COLS[signal]
    w = lens.store.get(wash_id)
    refs = lens.store.reference_ids(wash_id)
    data, labels, bits = [], [], []
    for ph in PHASES:
        if ph == "idle":
            continue
        mine = _values(lens, wash_id, col)[w.df["phase"] == ph].dropna().to_numpy()
        ref = _ref_windows(lens, refs, col, ph)
        if len(mine) < 6:
            continue
        if len(ref) < 20:
            bits.append(f"{ph} {fmt(np.median(mine))} (normal: insufficient data)")
            ref = np.array([np.nan])
        else:
            bits.append(f"{ph} {fmt(np.median(mine))} vs normal {fmt(np.median(ref))}")
        data += [ref[np.isfinite(ref)], mine]
        labels += [f"{ph}\nnormal", f"{ph}\nthis"]
    if not data:
        raise ValueError(f"wash {wash_id} has no running phase with usable '{signal}' data")
    fig, ax = plt.subplots(figsize=(W_IN, H_IN))
    bp = ax.boxplot(data, showfliers=False, patch_artist=True)
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor("#cfcfcf" if i % 2 == 0 else "#a9c4e8")
    ax.set_xticks(np.arange(1, len(labels) + 1), labels, fontsize=7)
    ax.set_ylabel(f"{signal} ({unit})", fontsize=8)
    ax.set_title(f"wash {wash_id}: {signal} per phase, this wash vs {len(refs)} other washes (5 s windows)",
                 fontsize=9)
    fig.tight_layout()
    return _png(fig), f"chart: {signal} median per phase: " + "; ".join(bits)


# =============================================================================
# SECTION 4: Entry point
# =============================================================================
def render(lens: "ApexLens", wash_id: str, kind: str = "trace", signals: Optional[Sequence[str]] = None,
           phase: Optional[str] = None) -> Tuple[bytes, str]:
    from apex_lens.registry import PHASES as PH, PLOT_KINDS, SIGNALS
    w = lens.store.get(wash_id)                      # KeyError -> error text for unknown ids
    if kind not in PLOT_KINDS:
        raise ValueError(f"kind must be one of {PLOT_KINDS}")
    if phase is not None and phase not in PH:
        raise ValueError(f"phase must be one of {PH}")
    if isinstance(signals, str):
        signals = [signals]
    signals = list(signals or (["power_mean", "sound_rms", "vib_level"] if kind == "trace" else ["vib_level"]))
    bad = [s for s in signals if s not in SIGNALS]
    if bad or not 1 <= len(signals) <= 3:
        raise ValueError(f"signals: 1 to 3 of {SIGNALS}")
    if not w.is_wash:
        raise ValueError(f"{wash_id} is not a wash; nothing to plot against normal")
    if kind == "trace":
        return _trace(lens, wash_id, signals, phase)
    if kind == "bands":
        return _bands(lens, wash_id, phase)
    return _overlay(lens, wash_id, signals[0])
