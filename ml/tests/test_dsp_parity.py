"""
test_dsp_parity.py
Checks that the ESP32 feature code (firmware/07_feature_streamer/pdm_dsp.h)
and the Python reference (ml/dsp_features.py) produce the same numbers.

Run from the project root:   py ml/tests/test_dsp_parity.py
Needs a C++ compiler (g++ or clang++) on PATH. Exit code 0 = pass.
"""

# =============================================================================
# SECTION 1: Imports & paths
# =============================================================================
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ml.dsp_features import (AUDIO_BLOCK, AUDIO_FS, VIB_FS, WINDOW_BLOCKS,  # noqa: E402
                             AudioWindowRef, VibWindowRef)

HARNESS_SRC = ROOT / "ml" / "tests" / "dsp_host_harness.cpp"

# Column order printed by the harness
COLS = (["n_audio", "audio_rms", "audio_peak", "audio_crest", "audio_kurtosis", "audio_hp_rms",
         "audio_hp_kurtosis", "audio_block_rms_max", "audio_block_rms_p90", "audio_centroid_hz"]
        + [f"audio_band_{n}" for n in ["0_250", "250_500", "500_1k", "1k_2k", "2k_4k", "4k_8k"]]
        + ["n_accel"]
        + [f"{k}_{a}" for a in "xyz" for k in ("accel", "vib_std", "vib_ptp")]
        + ["vib_mag_std", "vib_dom_hz", "vib_dom_rms"]
        + [f"vib_band_{n}" for n in ["0_5", "5_15", "15_30", "30_60"]])


# =============================================================================
# SECTION 2: Synthetic washer-like test signals (deterministic)
# =============================================================================
def make_signals(seconds: float = 16.0, seed: int = 7):
    """Noise + motor hum + sparse impacts (audio) and gravity + 1x drum order (accel)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * AUDIO_FS) // AUDIO_BLOCK * AUDIO_BLOCK
    t = np.arange(n) / AUDIO_FS
    audio = 2e5 * rng.standard_normal(n) + 8e4 * np.sin(2 * np.pi * 100 * t) + 3e4   # int24 units + DC
    impacts = rng.random(n) < 0.0005
    audio[impacts] += 3e6 * rng.choice([-1, 1], impacts.sum())
    raw = (np.clip(audio, -8e6, 8e6).astype(np.int64) << 8).astype(np.int32)       # 24-bit left-justified

    nv = int(seconds * VIB_FS)
    tv = np.arange(nv) / VIB_FS
    f_drum = 18.0
    accel = np.stack([
        -0.6 + 0.30 * np.sin(2 * np.pi * f_drum * tv) + 0.02 * rng.standard_normal(nv),
        2.1 + 0.20 * np.sin(2 * np.pi * f_drum * tv + 1.0) + 0.02 * rng.standard_normal(nv),
        -9.25 + 0.05 * np.sin(2 * np.pi * 2.0 * tv) + 0.02 * rng.standard_normal(nv),
    ], axis=1).astype(np.float32)
    return raw, accel


# =============================================================================
# SECTION 3: Python reference run (same feeding rule as the harness)
# =============================================================================
def run_python(raw, accel):
    aw, vw = AudioWindowRef(), VibWindowRef()
    rows, blocks, v_fed = [], 0, 0
    for start in range(0, len(raw) - AUDIO_BLOCK + 1, AUDIO_BLOCK):
        aw.process_block(raw[start:start + AUDIO_BLOCK])
        blocks += 1
        target = (start + AUDIO_BLOCK) * VIB_FS // AUDIO_FS
        if target > v_fed:
            vw.add_samples(accel[v_fed:min(target, len(accel))].astype(np.float64))
            v_fed = min(target, len(accel))
        if blocks % WINDOW_BLOCKS == 0:
            d = aw.finish(); d.update(vw.finish())
            rows.append([d[c] for c in COLS])
    return np.array(rows)


# =============================================================================
# SECTION 4: Compile + run the C++ harness, compare
# =============================================================================
def main() -> int:
    cxx = shutil.which("g++") or shutil.which("clang++")
    if not cxx:
        print("[SKIP] no C++ compiler found on PATH")
        return 0
    raw, accel = make_signals()
    with tempfile.TemporaryDirectory() as td:
        exe = Path(td) / "harness"
        subprocess.run([cxx, "-O2", "-std=c++11", str(HARNESS_SRC), "-o", str(exe)], check=True)
        binf = Path(td) / "in.bin"
        with open(binf, "wb") as f:
            f.write(struct.pack("<ii", len(raw), len(accel)))
            f.write(raw.astype("<i4").tobytes())
            f.write(accel.astype("<f4").tobytes())
        out = subprocess.run([str(exe), str(binf)], capture_output=True, text=True, check=True).stdout
    cpp = np.array([[float(v) for v in line.split(",")] for line in out.strip().splitlines()])
    py = run_python(raw, accel)
    assert cpp.shape == py.shape, f"shape mismatch {cpp.shape} vs {py.shape}"

    worst = 0.0
    failed = []
    for j, name in enumerate(COLS):
        a, b = cpp[:, j], py[:, j]
        both_nan = np.isnan(a) & np.isnan(b)
        rel = np.abs(a - b) / np.maximum(np.abs(b), 1e-6)
        rel[both_nan] = 0.0
        r = float(np.nanmax(rel))
        worst = max(worst, r)
        # float32 signal path in C++ vs float64 in Python: allow 0.5 % (1e-2 for kurtosis/peaks)
        tol = 1e-2 if ("kurt" in name or "peak" in name or "crest" in name) else 5e-3
        status = "ok " if r <= tol else "BAD"
        if r > tol:
            failed.append(name)
        print(f"  [{status}] {name:<22} max rel err {r:.2e}   (cpp {a[-1]:.5g} | py {b[-1]:.5g})")
    print(f"\nwindows compared: {len(py)}   worst relative error: {worst:.2e}")
    if failed:
        print("[FAIL] mismatched features:", failed)
        return 1
    print("[PASS] firmware DSP and Python reference agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
