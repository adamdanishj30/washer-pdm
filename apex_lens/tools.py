"""
tools.py
The Apex Lens tools. Each tool does the computing and returns a SHORT text
answer for an LLM: a header line, then a compact header-once table (CSV
style, rounded numbers). Full data never goes into the answer; it stays in
the WashStore and is addressed by wash id.

Design rules (from the literature review, Papers/mcp/MCP_RESEARCH_NOTES.md)
---------------------------------------------------------------------------
* The LLM never reads the raw window table (a 70-min wash is ~840 windows x
  ~35 numbers). Tools summarise; detail comes on request.
* Header-once tables, rounded to 3 significant figures, no Markdown pipes.
* Every number in an answer must come from a tool output, so tool outputs
  carry their own units and reference counts.
* "Unusual compared with this household's normal washes" is the strongest
  claim a tool makes. No tool names a failing component: there are no fault
  labels to learn that from.

Tools
-----
list_washes()                                    what is available
wash_overview(wash_id)                           phases, power, energy, data quality
compare_to_normal(wash_id, sensor_group, phase)  this wash vs other washes, per phase
detector_score(wash_id, baseline)                one-class detector verdict, pooled or per phase
similar_washes(wash_id, k)                       the k most similar past washes and how they differ
render_plot(wash_id, kind, signals, phase)       one 800x450 PNG with the normal range shaded

Use `ApexLens.call(name, **args)` (text only) or `call_full` (text + PNG):
they add the per-call `ref:` line, the `quality:` lines, the output budget
and turn errors into text. Tool names and schemas live in registry.py.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & feature catalogue
# =============================================================================
import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from apex_lens.store import PHASES, VIB_COLS, WINDOW_S, Wash, WashStore
from ml.feature_fusion import compute_features
from ml.pipeline import PdmPipeline

# Measurements shown by compare_to_normal: (CSV column, short name, unit)
KEY_FEATURES: Dict[str, List[Tuple[str, str, str]]] = {
    "sound": [
        ("audio_rms", "sound_rms", "fw units"),
        ("audio_hp_rms", "sound_above_2khz_rms", "fw units"),
        ("audio_hp_kurtosis", "sound_above_2khz_kurtosis", "-"),
        ("audio_crest", "sound_crest", "-"),
        ("audio_centroid_hz", "sound_centroid", "Hz"),
        ("audio_band_2k_4k", "sound_band_2_4khz", "fw units"),
        ("audio_band_4k_8k", "sound_band_4_8khz", "fw units"),
    ],
    "vibration": [
        ("vib_mag_std", "vib_level", "m/s2"),
        ("vib_dom_hz", "vib_dominant_freq", "Hz"),
        ("vib_dom_rms", "vib_dominant_rms", "m/s2"),
        ("vib_band_0_5", "vib_band_0_5hz", "m/s2"),
        ("vib_band_5_15", "vib_band_5_15hz", "m/s2"),
        ("vib_band_15_30", "vib_band_15_30hz", "m/s2"),
    ],
    "power": [
        ("power_w", "power_mean", "W"),
        ("power_std", "power_std", "W"),
    ],
}
GROUP_OF = {col: g for g, items in KEY_FEATURES.items() for col, _, _ in items}
SENSOR_GROUPS = ("sound", "vibration", "power", "all")
MIN_PHASE_WINDOWS = 6           # a phase shorter than 30 s is not summarised
SAME_CLASS_MIN = 3              # compare within the inferred wash class if >= 3 such washes exist
MIN_REF_WASHES = 3              # a phase seen in fewer other washes than this is "insufficient data"
MIN_VIB_OK = 0.5                # below this share of usable vibration windows, vibration answers abstain
MAX_TOOL_TOKENS = 1500          # hard output budget per tool answer (approximate tokens)
# short signal name -> (CSV column, unit), for render_plot and similar_washes
SIGNAL_COLS: Dict[str, Tuple[str, str]] = {name: (col, unit) for items in KEY_FEATURES.values()
                                           for col, name, unit in items}


# =============================================================================
# SECTION 2: Formatting helpers
# =============================================================================
def fmt(x) -> str:
    """3 significant figures; whole numbers from 1000 up; '-' for missing."""
    if x is None or isinstance(x, str):
        return "-" if x is None else x
    if isinstance(x, (bool, np.bool_)):
        return str(bool(x)).lower()
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    if not math.isfinite(x):
        return "-"
    if abs(x) >= 1000:
        return str(int(round(x)))
    s = f"{x:.3g}"
    if "e" in s:                                  # tiny values: plain decimal, 3 significant figures
        s = f"{x:.{2 - math.floor(math.log10(abs(x)))}f}"
    return s


def table(columns: Sequence[str], rows: Sequence[Sequence]) -> str:
    """Header-once CSV-style table."""
    lines = [",".join(columns)]
    lines += [",".join(fmt(v) for v in r) for r in rows]
    return "\n".join(lines)


def _phase_spans(w: Wash) -> List[Tuple[str, int, int]]:
    """Contiguous phase blocks: (phase, first_row, windows)."""
    ph = w.df["phase"].to_numpy()
    out, i0 = [], 0
    for i in range(1, len(ph) + 1):
        if i == len(ph) or ph[i] != ph[i0]:
            out.append((ph[i0], i0, i - i0))
            i0 = i
    return out


def _valid(w: Wash, col: str) -> pd.Series:
    """Column values, with bad-accelerometer windows removed for vibration columns."""
    s = w.df[col].astype(float)
    if col.startswith("vib_"):
        s = s.where(w.df["vib_ok"])
    return s


# =============================================================================
# SECTION 3: Tools
# =============================================================================
class ApexLens:
    """Holds the store and caches fitted detectors. One instance per session."""

    def __init__(self, store: Optional[WashStore] = None, show_ids: Optional[Sequence[str]] = None):
        self.store = store or WashStore.from_dir()
        self.show_ids = list(show_ids) if show_ids is not None else None   # ids list_washes may reveal
        self._detectors: Dict[Tuple[Tuple[str, ...], str], PdmPipeline] = {}
        self._scored: Dict[str, pd.DataFrame] = {}      # last detector_score output per wash
        self._n_calls = 0                               # numbers the ref: line of each answer

    # ------------------------------------------------------------- helpers
    def _vib_ok_share(self, w: Wash) -> float:
        """Share of running (non-idle) windows with usable accelerometer data."""
        run = w.df["phase"] != "idle"
        return float(w.df.loc[run, "vib_ok"].mean()) if run.any() else 0.0

    def _ref_washes_with_phase(self, refs: Sequence[str], ph: str) -> int:
        return sum(int((self.store.get(k).df["phase"] == ph).sum() >= MIN_PHASE_WINDOWS) for k in refs)

    # ----------------------------------------------------------- list_washes
    def list_washes(self) -> str:
        ids = self.show_ids if self.show_ids is not None else list(self.store.washes)
        rows = []
        for k in ids:
            w = self.store.get(k)
            vib_ok = 100.0 * w.df["vib_ok"].mean()
            rows.append((k, round(w.duration_min, 1), w.wash_class if w.is_wash else "not a wash",
                         w.n, round(vib_ok)))
        head = (f"{len(rows)} recordings (firmware 07, one row per 5 s window). "
                "class = inferred from power, not the programme the user chose.")
        return head + "\n" + table(["wash_id", "duration_min", "class", "windows", "vib_data_ok_pct"], rows)

    # --------------------------------------------------------- wash_overview
    def wash_overview(self, wash_id: str) -> str:
        w = self.store.get(wash_id)
        p = w.df["power_w"].astype(float)
        energy_kwh = float(np.nansum(p) * WINDOW_S / 3.6e6)
        head = [f"wash {wash_id}: {w.duration_min:.1f} min, class {w.wash_class if w.is_wash else 'not a wash'} "
                f"(inferred from power), energy {energy_kwh:.3f} kWh, peak {fmt(p.max())} W."]
        rows = []
        for ph, i0, n in _phase_spans(w):
            if n < MIN_PHASE_WINDOWS:
                continue
            seg = w.df.iloc[i0:i0 + n]
            vib = seg["vib_mag_std"].where(seg["vib_ok"])
            rows.append((ph, round(i0 * WINDOW_S / 60, 1), round(n * WINDOW_S / 60, 1), seg["power_w"].median(), seg["audio_rms"].median(),
                         vib.median(), seg["vib_dom_hz"].where(seg["vib_ok"]).quantile(0.9)))
        head.append("phases from power: idle, tumble (fill/wash/rinse/drain, not separable by power), "
                    "heat (>1 kW), spin (200-1000 W for >= 100 s). Medians per block:")
        return "\n".join(head) + "\n" + table(
            ["phase", "start_min", "dur_min", "power_W", "sound_rms", "vib_level_m/s2", "vib_freq_p90_Hz"], rows)

    # ----------------------------------------------------- compare_to_normal
    def _reference(self, wash_id: str) -> Tuple[List[str], str]:
        w = self.store.get(wash_id)
        refs = self.store.reference_ids(wash_id)
        same = [k for k in refs if self.store.get(k).wash_class == w.wash_class]
        if w.wash_class not in ("Unclassified", "No power data") and len(same) >= SAME_CLASS_MIN:
            return same, f"the {len(same)} other '{w.wash_class}' washes"
        return refs, f"all {len(refs)} other washes (fewer than {SAME_CLASS_MIN} of the same class)"

    def compare_to_normal(self, wash_id: str, sensor_group: str = "all", phase: Optional[str] = None) -> str:
        """
        Per phase and measurement: this wash's median vs the spread of the
        reference washes' medians. 'all' returns only the rows outside the
        normal range (detail on request); a single group returns every row.
        """
        if sensor_group not in SENSOR_GROUPS:
            raise ValueError(f"sensor_group must be one of {SENSOR_GROUPS}")
        if phase is not None and phase not in PHASES:
            raise ValueError(f"phase must be one of {PHASES}")
        w = self.store.get(wash_id)
        if not w.is_wash:
            return f"abstain: {wash_id} is not a wash (see quality lines), so it has no normal to compare with."
        refs, ref_desc = self._reference(wash_id)
        groups = list(KEY_FEATURES) if sensor_group == "all" else [sensor_group]
        notes = []
        if "vibration" in groups and self._vib_ok_share(w) < MIN_VIB_OK:
            groups.remove("vibration")
            notes.append(f"abstain: vibration not compared, only {round(100 * self._vib_ok_share(w))}% of "
                         "running windows have usable accelerometer data.")
            if not groups:
                return f"wash {wash_id} vs {ref_desc}.\n" + notes[0]
        phases = [phase] if phase else [p for p in PHASES if p != "idle"]
        rows, n_checked = [], 0
        for ph in phases:
            mine = w.df["phase"] == ph
            if mine.sum() < MIN_PHASE_WINDOWS:
                continue
            n_have = self._ref_washes_with_phase(refs, ph)
            if n_have < MIN_REF_WASHES:
                notes.append(f"{ph}: insufficient data (n={n_have} other washes have this phase).")
                continue
            for g in groups:
                for col, name, unit in KEY_FEATURES[g]:
                    if col not in w.df.columns:
                        continue
                    v = _valid(w, col)[mine].median()
                    ref_meds = []
                    for k in refs:
                        r = self.store.get(k)
                        m = r.df["phase"] == ph
                        if m.sum() >= MIN_PHASE_WINDOWS and col in r.df.columns:
                            ref_meds.append(_valid(r, col)[m].median())
                    ref_meds = np.array([x for x in ref_meds if np.isfinite(x)])
                    if len(ref_meds) < MIN_REF_WASHES or not np.isfinite(v):
                        continue
                    n_checked += 1
                    lo, med, hi = np.min(ref_meds), np.median(ref_meds), np.max(ref_meds)
                    diff = 100.0 * (v - med) / abs(med) if med else float("nan")
                    status = "above" if v > hi else "below" if v < lo else "within"
                    if sensor_group == "all" and status == "within":
                        continue
                    rows.append((ph, name, unit, v, med, lo, hi, round(diff), status, len(ref_meds)))
        head = (f"wash {wash_id} vs {ref_desc}. Value = median over the phase; normal range = min..max of "
                f"the other washes' medians for the same phase.")
        if sensor_group == "all":
            head += (f" Showing only measurements outside the normal range: {len(rows)} of {n_checked} checked. "
                     "Ask for one sensor_group to see every row.")
        if notes:
            head += "\n" + "\n".join(notes)
        if not rows:
            return head + "\nnothing outside the normal range."
        return head + "\n" + table(
            ["phase", "measure", "unit", "this_wash", "normal_median", "normal_min", "normal_max",
             "diff_pct", "status", "n_ref"], rows)

    # -------------------------------------------------------- detector_score
    def _vib_fill(self, refs: Sequence[str]) -> Dict[str, Dict[str, float]]:
        """Per phase: median of each raw vibration column over the reference washes' good windows."""
        d = pd.concat([self.store.get(k).df for k in refs], ignore_index=True)
        d = d[d["vib_ok"]]
        cols = [c for c in VIB_COLS if c in d.columns]
        return {ph: g[cols].median().to_dict() for ph, g in d.groupby("phase")}

    def _features(self, ids: Sequence[str], fill: Optional[Dict[str, Dict[str, float]]] = None) -> pd.DataFrame:
        """
        Model features for non-idle windows. Without `fill` (training) windows
        with bad accelerometer data are dropped. With `fill` (scoring) they are
        kept and their vibration columns are set to the reference median for
        that phase, so only their sound and power can raise the score.
        """
        parts = []
        for k in ids:
            w = self.store.get(k)
            d = w.df[w.df["phase"] != "idle"].copy()
            if fill is None:
                d = d[d["vib_ok"]]
            else:
                for ph, med in fill.items():
                    m = (~d["vib_ok"]) & (d["phase"] == ph)
                    for c, v in med.items():
                        d.loc[m, c] = v
            d["session"] = k
            parts.append(d)
        raw = pd.concat(parts, ignore_index=True)
        phase = raw["phase"].to_numpy()
        feats = compute_features(raw.drop(columns=["phase"]), schema="windowed")
        feats["phase_group"] = phase
        feats["phase_source"] = "power"
        return feats

    def _detector(self, refs: Sequence[str], baseline: str) -> PdmPipeline:
        key = (tuple(sorted(refs)), baseline)
        if key not in self._detectors:
            feats = self._features(refs)
            use_power = bool((feats["power_w"].groupby(feats["session"]).quantile(0.95) >= 50).all())
            self._detectors[key] = PdmPipeline("mahalanobis").fit(
                feats, "windowed", use_power, conditioned=(baseline == "per_phase"))
        return self._detectors[key]

    def detector_score(self, wash_id: str, baseline: str = "per_phase") -> str:
        """
        One-class Mahalanobis detector trained on the reference washes only
        (never this wash or its origin). baseline='per_phase' fits one normal
        model per power phase; 'pooled' fits one model for everything.
        """
        if baseline not in ("per_phase", "pooled"):
            raise ValueError("baseline must be 'per_phase' or 'pooled'")
        w = self.store.get(wash_id)
        if not w.is_wash:
            return f"abstain: {wash_id} is not a wash (see quality lines); the detector is not run."
        refs = self.store.reference_ids(wash_id)
        if len(refs) < 3:
            return f"cannot score {wash_id}: need at least 3 other washes, have {len(refs)}."
        det = self._detector(refs, baseline)
        feats = self._features([wash_id], fill=self._vib_fill(refs))
        scored = det.score(feats)
        self._scored[wash_id] = scored          # lets render_plot mark the red windows
        s = det.summarize(scored)
        n_idle = int((w.df["phase"] == "idle").sum())
        n_bad = int(((~w.df["vib_ok"]) & (w.df["phase"] != "idle")).sum())
        head = [
            f"wash {wash_id}, detector trained on {len(refs)} other washes ({baseline} normal model). "
            f"Percentile = how unusual a 5 s window is vs held-out normal windows (99 = more unusual than 99%).",
            f"verdict: {s['cycle_decision']}"
            + (f" (sustained unusualness from minute {s['first_alarm_min']} in: {', '.join(s['triggered_by'])})"
               if s["cycle_decision"] == "ABNORMAL" else " (no sustained unusualness)")
            + f". windows red (>=p99.5): {s['pct_windows_red']}%, amber (p95-99.5): {s['pct_windows_amber']}%.",
            f"scored {len(feats)} non-idle windows ({n_idle} idle left out)"
            + (f"; {n_bad} had bad accelerometer data, so only their sound and power were scored." if n_bad else "."),
        ]
        if s.get("top_features_in_red_windows"):
            head.append("measures driving red windows: " + ", ".join(s["top_features_in_red_windows"]))
        if self._vib_ok_share(w) < MIN_VIB_OK:
            head.append(f"abstain: vibration, only {round(100 * self._vib_ok_share(w))}% of running windows have "
                        "usable accelerometer data, so this verdict rests on sound and power only.")
        if baseline == "per_phase":
            thin = [f"{ph} (n={n})" for ph in PHASES if ph != "idle"
                    and (scored["phase_group"] == ph).sum() >= MIN_PHASE_WINDOWS
                    and (n := self._ref_washes_with_phase(refs, ph)) < MIN_REF_WASHES]
            if thin:
                head.append("insufficient data for a per-phase normal in: " + ", ".join(thin)
                            + " other washes; treat those rows with caution.")
        head.append("ABNORMAL means unusual for this household's washes, not a diagnosed fault.")
        rows = []
        for ph in PHASES:
            g = scored[scored["phase_group"] == ph]
            if len(g) < MIN_PHASE_WINDOWS:
                continue
            row = [ph, len(g), round(100 * (g["band"] == "red").mean(), 1), g["baseline_pct"].median()]
            for ind in ("acoustic", "vibration", "power"):
                c = f"{ind}_indicator_pct"
                row.append(g[c].quantile(0.95) if c in g.columns else None)
            rows.append(row)
        return "\n".join(head) + "\n" + table(
            ["phase", "windows", "red_pct", "median_pct", "sound_p95_pct", "vibration_p95_pct", "power_p95_pct"],
            rows)

    # -------------------------------------------------------- similar_washes
    def _profile(self, wash_id: str) -> pd.Series:
        """Per-phase medians of every key measurement, as one vector ('spin:vib_level', ...)."""
        w = self.store.get(wash_id)
        out = {}
        for ph in ("tumble", "heat", "spin"):
            m = w.df["phase"] == ph
            if m.sum() < MIN_PHASE_WINDOWS:
                continue
            for name, (col, _) in SIGNAL_COLS.items():
                if col in w.df.columns:
                    out[f"{ph}:{name}"] = _valid(w, col)[m].median()
        return pd.Series(out, dtype=float)

    def similar_washes(self, wash_id: str, k: int = 3) -> str:
        """
        The k reference washes closest to this one. Each measurement is
        scaled by the median and IQR of the REFERENCE washes only (no leakage),
        then distance = root-mean-square difference over the measurements both
        washes have. Candidates never include this wash or its origin.
        """
        k = int(k)
        if not 1 <= k <= 5:
            raise ValueError("k must be between 1 and 5")
        w = self.store.get(wash_id)
        if not w.is_wash:
            return f"abstain: {wash_id} is not a wash (see quality lines)."
        refs = self.store.reference_ids(wash_id)
        if not refs:
            return f"no other washes to compare {wash_id} with."
        P = pd.DataFrame({r: self._profile(r) for r in refs}).T
        mine = self._profile(wash_id)
        cols = [c for c in mine.index if c in P.columns]
        med = P[cols].median()
        iqr = (P[cols].quantile(0.75) - P[cols].quantile(0.25)).replace(0, np.nan)
        iqr = iqr.fillna(med.abs() * 0.1 + 1e-9)        # constant measurement: scale by 10% of its level
        zm = (mine[cols] - med) / iqr
        rows = []
        for r in refs:
            zr = (P.loc[r, cols] - med) / iqr
            d = (zm - zr).dropna()
            if len(d) < 3:
                continue
            top = d.abs().sort_values(ascending=False).index[:3]
            diffs = "; ".join(f"{c} {fmt(mine[c])} vs {fmt(P.loc[r, c])}" for c in top)
            rows.append((r, self.store.get(r).wash_class, float(np.sqrt((d ** 2).mean())), len(d), diffs))
        rows.sort(key=lambda x: x[2])
        head = (f"wash {wash_id}: {min(k, len(rows))} most similar of {len(rows)} other washes. "
                "distance = RMS of robust-scaled per-phase medians (0 = identical; about 1 = typical spread "
                "between washes). biggest_differences = this wash vs that wash.")
        return head + "\n" + table(["wash_id", "class", "distance", "n_measures", "biggest_differences"],
                                    [(a, b, c, n, f'"{e}"') for a, b, c, n, e in rows[:k]])

    # ----------------------------------------------------------- render_plot
    def render_plot(self, wash_id: str, kind: str = "trace", signals: Optional[Sequence[str]] = None,
                    phase: Optional[str] = None) -> Tuple[bytes, str]:
        """One fixed-size PNG plus a caption with the numbers it shows (see plots.py)."""
        from apex_lens import plots           # matplotlib is only imported when a plot is asked for
        return plots.render(self, wash_id, kind, signals, phase)

    # ------------------------------------------------------------- dispatch
    def call_full(self, name: str, **kwargs) -> Tuple[str, Optional[bytes]]:
        """
        Run a tool by name. Returns (text, png or None). The text starts with
        `ref: <tool>#<n>` (so an answer can cite where a number came from),
        then any `quality:` lines for the wash, then the tool's answer, cut to
        the output budget. Errors come back as text so an agent can recover.
        """
        fns = {"list_washes": self.list_washes, "wash_overview": self.wash_overview,
               "compare_to_normal": self.compare_to_normal, "detector_score": self.detector_score,
               "similar_washes": self.similar_washes, "render_plot": self.render_plot}
        fn = fns.get(name)
        if fn is None:
            return f"error: unknown tool '{name}'. Tools: {', '.join(fns)}", None
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        try:
            res = fn(**kwargs)
        except (KeyError, ValueError, TypeError) as e:
            return f"error: {str(e).strip(chr(39))}", None
        png = None
        if isinstance(res, tuple):
            png, res = res
        self._n_calls += 1
        lines = [f"ref: {name}#{self._n_calls}"]
        wid = kwargs.get("wash_id")
        if wid in self.store.washes:
            lines += [f"quality: {n}" for n in self.store.get(wid).notes]
        return budget("\n".join(lines + [res])), png

    def call(self, name: str, **kwargs) -> str:
        """Text-only version of call_full (the CLI and the tests use it)."""
        return self.call_full(name, **kwargs)[0]


def budget(text: str, max_tokens: int = MAX_TOOL_TOKENS) -> str:
    """Cut an answer to the output budget, keeping whole lines and saying how much was left out."""
    from apex_lens.experiment import count_tokens
    if count_tokens(text) <= max_tokens:
        return text
    lines = text.split("\n")
    keep = []
    for ln in lines:
        if count_tokens("\n".join(keep + [ln])) > max_tokens - 40:
            break
        keep.append(ln)
    omitted = len(lines) - len(keep)
    return "\n".join(keep + [f"truncated: {omitted} rows omitted; narrow with phase= or sensor_group="])
