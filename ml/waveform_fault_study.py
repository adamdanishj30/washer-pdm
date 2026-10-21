"""
waveform_fault_study.py
Raw-signal (waveform-level) bearing-spall injection study.

Question it answers
-------------------
"If the tub bearing had an outer-race spall of a given size, how much would
each firmware-07 audio feature move, compared with the normal clip-to-clip
spread of a healthy machine?"

How
---
1. Take REAL healthy audio clips recorded by the rig
   (data/audio_clips/<session>/*.wav, collected by firmware/collect_audio_clips.py).
   Without clips, it falls back to a synthetic washer-like noise so the
   script can be tried - those numbers are illustrative only.
2. Add a spall impulse train (standard bearing-fault signal model):
     * impacts at BPFO = order x drum speed (default 4.3 x 20 Hz = 86 Hz
       during spin; give the real drum speed / bearing geometry if known),
     * each impact excites a structural resonance: a decaying sinusoid
       (default 3 kHz, 0.6 ms decay),
     * small timing jitter (1%) and amplitude modulation at 1x drum speed
       (load zone),
     * impact energy set relative to the clip's own 2 kHz-high-pass RMS
       (ratio 0.1 ... 1.0), i.e. the same severity scale as
       ml/fault_injection.py 'bearing_impulsive'.
3. Run ml/dsp_features.py (bit-for-bit the firmware DSP) on clean and
   injected clips and report, per feature, the shift in units of the
   healthy clip-to-clip standard deviation (|shift| > 3 = clearly visible).

Usage
-----
  py ml/waveform_fault_study.py                         # all clips found
  py ml/waveform_fault_study.py --drum-hz 18 --order 4.3 --resonance-hz 3500
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & paths
# =============================================================================
import argparse
import sys
import wave
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.dsp_features import AUDIO_FS, audio_clip_features  # noqa: E402

CLIP_DIR = BASE_DIR / "data" / "audio_clips"
OUT = BASE_DIR / "ml" / "outputs" / "waveform_fault_study.csv"
FEATURES = ["audio_rms", "audio_crest", "audio_kurtosis", "audio_hp_rms", "audio_hp_kurtosis",
            "audio_block_rms_max", "audio_centroid_hz", "audio_band_2k_4k", "audio_band_4k_8k"]


# =============================================================================
# SECTION 2: Clip loading (WAV from the rig is int16 = top 16 bits of int24)
# =============================================================================
def load_clips(limit: int) -> List[np.ndarray]:
    clips = []
    for p in sorted(CLIP_DIR.glob("*/*.wav"))[:limit]:
        with wave.open(str(p), "rb") as w:
            if w.getframerate() != AUDIO_FS or w.getsampwidth() != 2:
                continue
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64)
        clips.append(x * 256.0)                      # back to int24 units used by the firmware
    return clips


def synthetic_clips(n: int, seconds: float = 2.0, seed: int = 1) -> List[np.ndarray]:
    """Illustrative stand-in: pink-ish noise + motor hum + drum slosh modulation."""
    rng = np.random.default_rng(seed)
    out = []
    t = np.arange(int(seconds * AUDIO_FS)) / AUDIO_FS
    for _ in range(n):
        white = rng.standard_normal(len(t))
        pink = np.cumsum(white)
        pink = pink - np.convolve(pink, np.ones(400) / 400, mode="same")
        x = 6e4 * pink / pink.std() + 3e4 * white + 2e4 * np.sin(2 * np.pi * 100 * t)
        x *= 1 + 0.2 * np.sin(2 * np.pi * rng.uniform(0.5, 2) * t)
        out.append(x * rng.uniform(0.8, 1.2))
    return out


# =============================================================================
# SECTION 3: Spall impulse train
# =============================================================================
def spall_train(n: int, drum_hz: float, order: float, f_res: float, tau_s: float,
                jitter: float, seed: int) -> np.ndarray:
    """Unit-RMS impulse train: resonant ringing at each defect impact."""
    rng = np.random.default_rng(seed)
    bpfo = order * drum_hz
    sig = np.zeros(n)
    k = np.arange(int(8 * tau_s * AUDIO_FS))
    ring = np.exp(-k / (tau_s * AUDIO_FS)) * np.sin(2 * np.pi * f_res * k / AUDIO_FS)
    t = rng.uniform(0, 1 / bpfo)
    while t * AUDIO_FS < n:
        i0 = int(t * AUDIO_FS)
        amp = 1.0 + 0.5 * np.cos(2 * np.pi * drum_hz * t)          # load-zone modulation
        seg = ring[: max(0, min(len(ring), n - i0))]
        sig[i0:i0 + len(seg)] += amp * seg
        t += (1 / bpfo) * (1 + jitter * rng.standard_normal())
    return sig / max(sig.std(), 1e-12)


def hp_rms(x: np.ndarray) -> float:
    from ml.dsp_features import _hp_biquad_coeffs
    from scipy.signal import lfilter
    b, a = _hp_biquad_coeffs()
    return float(np.std(lfilter(b, a, x - x.mean())))


# =============================================================================
# SECTION 4: Study
# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="Waveform-level spall injection study")
    ap.add_argument("--drum-hz", type=float, default=20.0, help="drum speed (Hz); 1200 rpm = 20 Hz")
    ap.add_argument("--order", type=float, default=4.3, help="BPFO / shaft-speed ratio (bearing geometry)")
    ap.add_argument("--resonance-hz", type=float, default=3000.0)
    ap.add_argument("--decay-ms", type=float, default=0.6)
    ap.add_argument("--ratios", default="0.1,0.25,0.5,1.0", help="impact RMS / healthy hp RMS")
    ap.add_argument("--max-clips", type=int, default=200)
    a = ap.parse_args()

    clips = load_clips(a.max_clips)
    source = "recorded rig clips"
    if len(clips) < 5:
        clips = synthetic_clips(30)
        source = "SYNTHETIC stand-in noise (no recorded clips yet - numbers are illustrative only)"
    print(f"[STUDY] {len(clips)} clips from {source}")

    base = pd.DataFrame([audio_clip_features(c)[0] for c in clips])[FEATURES]
    logf = lambda d: np.log(np.clip(d.astype(float), 1e-9, None))      # noqa: E731
    spread = logf(base).std(ddof=1).replace(0, np.nan)

    rows = []
    for ratio in [float(r) for r in a.ratios.split(",")]:
        inj = []
        for i, c in enumerate(clips):
            s = spall_train(len(c), a.drum_hz, a.order, a.resonance_hz, a.decay_ms / 1000, 0.01, seed=i)
            inj.append(audio_clip_features(c + ratio * hp_rms(c) * s)[0])
        inj = pd.DataFrame(inj)[FEATURES]
        shift = (logf(inj) - logf(base)).mean() / spread       # in healthy-spread units (log scale)
        rows.append({"impact_ratio": ratio, **{f: round(float(v), 2) for f, v in shift.items()}})
    res = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    print("\nMean feature shift caused by the spall, in units of healthy clip-to-clip std "
          "(log scale; |value| > 3 = clearly separable per clip):\n")
    print(res.to_string(index=False))
    print(f"\n[SAVE] {OUT.relative_to(BASE_DIR)}")
    print("Use this to sanity-check ml/fault_injection.py 'bearing_impulsive': the features that move "
          "here should be the ones the injector moves, by a similar amount.")


if __name__ == "__main__":
    main()
