"""
dsp_features.py
Python reference implementation of the firmware-07 window features.

WHY THIS FILE EXISTS
--------------------
1. Parity testing: `firmware/07_feature_streamer/pdm_dsp.h` (C++, runs on the
   ESP32) and this file implement the SAME maths. `ml/tests/test_dsp_parity.py`
   compiles the C++ on a PC and checks both give the same numbers. If they
   ever disagree, the firmware is wrong (or this file is) - never silently.
2. Waveform-level fault injection: the honest way to test "would the system
   notice a bearing spall?" is to add a physically-modelled spall impulse
   train to a REAL recorded audio clip and push the result through the exact
   same feature extractor the firmware uses. That is what
   `ml/waveform_fault_study.py` does with this module.

UNITS (identical to the firmware)
---------------------------------
* audio input  : raw 32-bit I2S words (INMP441 24-bit, left-justified) OR
                 int24 sample values (pass `already_int24=True`).
* audio output : "legacy units" = int24 / 1000 (same scale as old audio_rms).
* vibration    : m/s^2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.signal import lfilter

# =============================================================================
# SECTION 1: Constants - MUST match pdm_dsp.h SECTION 1
# =============================================================================

AUDIO_FS = 16000
AUDIO_BLOCK = 512
AUDIO_MAX_BLOCKS = 200
AUDIO_DC_POLE = 0.995
AUDIO_HP_HZ = 2000.0
AUDIO_LEGACY_DIV = 1000.0
AUDIO_BAND_EDGES = [0.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0]
AUDIO_BAND_NAMES = ["0_250", "250_500", "500_1k", "1k_2k", "2k_4k", "4k_8k"]

VIB_FS = 200
VIB_FFT = 512
VIB_DOM_LO_HZ = 0.5
VIB_DOM_HI_HZ = 45.0
VIB_BAND_EDGES = [0.5, 5.0, 15.0, 30.0, 60.0]
VIB_BAND_NAMES = ["0_5", "5_15", "15_30", "30_60"]

# Window length used by the firmware: 157 audio blocks = 80,384 samples (5.024 s)
WINDOW_BLOCKS = 157


def periodic_hann(n: int) -> np.ndarray:
    """Periodic Hann window, identical to pdm_dsp.h FFT::init()."""
    k = np.arange(n)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * k / n)


def band_rms(P: np.ndarray, n: int, fs: float, hann_s2: float,
             f_lo: float, f_hi: float, include_top: bool) -> float:
    """
    RMS of the content in [f_lo, f_hi) from a one-sided power spectrum
    P[k] = |X_k|^2 of a Hann-windowed n-point frame (Parseval + window
    energy correction). Mirrors pdm::bandRms().
    """
    k = np.arange(1, n // 2)
    f = k * (fs / n)
    mask = (f >= f_lo) & ((f < f_hi) | (include_top & (f <= f_hi)))
    acc = float(np.sum(2.0 * P[1:n // 2][mask]))
    return float(np.sqrt(acc / (n * hann_s2)))


# =============================================================================
# SECTION 2: Audio window features
# =============================================================================

def _hp_biquad_coeffs(fs: float = AUDIO_FS, fc: float = AUDIO_HP_HZ):
    """RBJ 2nd-order Butterworth high-pass, same formula as the firmware."""
    w0 = 2.0 * np.pi * fc / fs
    alpha = np.sin(w0) / (2.0 * 0.70710678)
    c = np.cos(w0)
    a0 = 1.0 + alpha
    b = np.array([(1.0 + c) / 2.0, -(1.0 + c), (1.0 + c) / 2.0]) / a0
    a = np.array([1.0, -2.0 * c / a0, (1.0 - alpha) / a0])
    return b, a


class AudioWindowRef:
    """
    Stateful audio feature extractor. Like the firmware, the DC-blocker and
    high-pass filter states persist between windows; only the accumulators
    are reset when a window is finished.
    """

    def __init__(self) -> None:
        self.hp_b, self.hp_a = _hp_biquad_coeffs()
        self.hann = periodic_hann(AUDIO_BLOCK)
        self.hann_s2 = float(np.sum(self.hann ** 2))
        # filter states (scipy lfilter "zi" form)
        self.dc_zi = np.zeros(1)
        self.hp_zi = np.zeros(2)
        self._reset()

    def _reset(self) -> None:
        self.n = 0
        self.s2 = self.s4 = self.hs2 = self.hs4 = 0.0
        self.peak = self.hpeak = 0.0
        self.blk_rms: List[float] = []
        self.psd = np.zeros(AUDIO_BLOCK // 2 + 1)
        self.n_fft = 0

    def process_block(self, samples: np.ndarray, already_int24: bool = False) -> None:
        """Feed one block (<= 512 samples)."""
        s = np.asarray(samples)
        x = (s.astype(np.float64) if already_int24 else (s.astype(np.int64) >> 8).astype(np.float64))
        # DC blocker: y = x - x[-1] + R*y[-1]  ->  b=[1,-1], a=[1,-R]
        y, self.dc_zi = lfilter([1.0, -1.0], [1.0, -AUDIO_DC_POLE], x, zi=self.dc_zi)
        h, self.hp_zi = lfilter(self.hp_b, self.hp_a, y, zi=self.hp_zi)
        y2 = y * y
        h2 = h * h
        self.s2 += float(y2.sum()); self.s4 += float((y2 * y2).sum())
        self.hs2 += float(h2.sum()); self.hs4 += float((h2 * h2).sum())
        if len(y):
            self.peak = max(self.peak, float(np.abs(y).max()))
            self.hpeak = max(self.hpeak, float(np.abs(h).max()))
        self.n += len(y)
        if len(y) > 0 and len(self.blk_rms) < AUDIO_MAX_BLOCKS:
            self.blk_rms.append(float(np.sqrt(y2.mean())))
        if len(y) == AUDIO_BLOCK:
            X = np.fft.rfft(y * self.hann)
            self.psd += np.abs(X) ** 2
            self.n_fft += 1

    def finish(self) -> Dict[str, float]:
        """Return the feature dict for the window and reset accumulators."""
        n = self.n if self.n > 0 else 1
        m2, m4 = self.s2 / n, self.s4 / n
        hm2, hm4 = self.hs2 / n, self.hs4 / n
        rms, hrms = np.sqrt(m2), np.sqrt(hm2)
        out: Dict[str, float] = {
            "audio_rms": rms / AUDIO_LEGACY_DIV,
            "audio_peak": self.peak / AUDIO_LEGACY_DIV,
            "audio_crest": self.peak / rms if rms > 0 else np.nan,
            "audio_kurtosis": m4 / (m2 * m2) if m2 > 0 else np.nan,
            "audio_hp_rms": hrms / AUDIO_LEGACY_DIV,
            "audio_hp_kurtosis": hm4 / (hm2 * hm2) if hm2 > 0 else np.nan,
        }
        if self.blk_rms:
            b = np.sort(np.array(self.blk_rms))
            out["audio_block_rms_max"] = b[-1] / AUDIO_LEGACY_DIV
            out["audio_block_rms_p90"] = b[int(np.floor(0.9 * (len(b) - 1)))] / AUDIO_LEGACY_DIV
        else:
            out["audio_block_rms_max"] = out["audio_block_rms_p90"] = np.nan
        if self.n_fft > 0:
            P = self.psd / self.n_fft
            df = AUDIO_FS / AUDIO_BLOCK
            k = np.arange(1, AUDIO_BLOCK // 2)
            den = P[k].sum()
            out["audio_centroid_hz"] = float((k * df * P[k]).sum() / den) if den > 0 else np.nan
            for i, name in enumerate(AUDIO_BAND_NAMES):
                out[f"audio_band_{name}"] = band_rms(
                    P, AUDIO_BLOCK, AUDIO_FS, self.hann_s2,
                    AUDIO_BAND_EDGES[i], AUDIO_BAND_EDGES[i + 1],
                    i == len(AUDIO_BAND_NAMES) - 1) / AUDIO_LEGACY_DIV
        else:
            out["audio_centroid_hz"] = np.nan
            for name in AUDIO_BAND_NAMES:
                out[f"audio_band_{name}"] = np.nan
        out["n_audio"] = float(self.n)
        self._reset()
        return {k_: float(v) for k_, v in out.items()}


# =============================================================================
# SECTION 3: Vibration window features
# =============================================================================

class VibWindowRef:
    """Stateful vibration feature extractor (512-sample ring spans windows)."""

    def __init__(self) -> None:
        self.hann = periodic_hann(VIB_FFT)
        self.hann_s2 = float(np.sum(self.hann ** 2))
        self.ring: List[np.ndarray] = []      # chronological samples (kept <= VIB_FFT)
        self._reset()

    def _reset(self) -> None:
        self.buf: List[np.ndarray] = []

    def add_samples(self, xyz: np.ndarray) -> None:
        """xyz: (n, 3) array in m/s^2."""
        xyz = np.asarray(xyz, dtype=np.float64).reshape(-1, 3)
        self.buf.append(xyz)
        self.ring.append(xyz)
        allr = np.concatenate(self.ring)
        self.ring = [allr[-VIB_FFT:]]

    def finish(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        data = np.concatenate(self.buf) if self.buf else np.zeros((0, 3))
        axes = ["x", "y", "z"]
        if len(data):
            mu = data.mean(axis=0)
            sd = data.std(axis=0)
            ptp = data.max(axis=0) - data.min(axis=0)
            mag = np.sqrt((data ** 2).sum(axis=1))
            mag_std = float(mag.std())
        else:
            mu = sd = ptp = np.full(3, np.nan)
            mag_std = np.nan
        for i, a in enumerate(axes):
            out[f"accel_{a}"] = float(mu[i])          # window mean (gravity / tilt)
            out[f"vib_std_{a}"] = float(sd[i])
            out[f"vib_ptp_{a}"] = float(ptp[i])
        out["vib_mag_std"] = mag_std

        ring = self.ring[0] if self.ring else np.zeros((0, 3))
        if len(ring) == VIB_FFT:
            P = np.zeros(VIB_FFT // 2 + 1)
            for i in range(3):
                seg = ring[:, i] - ring[:, i].mean()
                P += np.abs(np.fft.rfft(seg * self.hann)) ** 2
            df = VIB_FS / VIB_FFT
            k = np.arange(1, VIB_FFT // 2)
            f = k * df
            valid = (f >= VIB_DOM_LO_HZ) & (f <= VIB_DOM_HI_HZ)
            kb = int(k[valid][np.argmax(P[k[valid]])])
            if 1 < kb < VIB_FFT // 2 - 1:
                pl, pc, pr = P[kb - 1], P[kb], P[kb + 1]
                den = pl - 2 * pc + pr
                delta = 0.5 * (pl - pr) / den if den != 0 else 0.0
                out["vib_dom_hz"] = float((kb + delta) * df)
                kk = [j for j in range(kb - 2, kb + 3) if 1 <= j < VIB_FFT // 2]
                out["vib_dom_rms"] = float(np.sqrt(np.sum(2 * P[kk]) / (VIB_FFT * self.hann_s2)))
            else:
                out["vib_dom_hz"] = out["vib_dom_rms"] = np.nan
            for i, name in enumerate(VIB_BAND_NAMES):
                out[f"vib_band_{name}"] = band_rms(P, VIB_FFT, VIB_FS, self.hann_s2,
                                                   VIB_BAND_EDGES[i], VIB_BAND_EDGES[i + 1], False)
        else:
            out["vib_dom_hz"] = out["vib_dom_rms"] = np.nan
            for name in VIB_BAND_NAMES:
                out[f"vib_band_{name}"] = np.nan
        out["n_accel"] = float(len(data))
        self._reset()
        return out


# =============================================================================
# SECTION 4: Convenience - features for a whole clip
# =============================================================================

def audio_clip_features(int24_samples: np.ndarray, window_blocks: int = WINDOW_BLOCKS) -> List[Dict[str, float]]:
    """
    Split an int24 audio clip into firmware-sized windows and return one
    feature dict per window. A clip shorter than one window yields one
    (short) window, which is what the /clip.wav study needs.
    """
    ext = AudioWindowRef()
    x = np.asarray(int24_samples)
    out: List[Dict[str, float]] = []
    blocks_in_window = 0
    for start in range(0, len(x), AUDIO_BLOCK):
        ext.process_block(x[start:start + AUDIO_BLOCK], already_int24=True)
        blocks_in_window += 1
        if blocks_in_window == window_blocks:
            out.append(ext.finish())
            blocks_in_window = 0
    if blocks_in_window > 0:
        out.append(ext.finish())
    return out
