"""
test_pipeline_synthetic.py
End-to-end mechanics test of the firmware-07 (windowed) ML path on SYNTHETIC
cycles. It checks the code runs and behaves sensibly (phase conditioning,
power features, calibration, injected-fault detection). Synthetic numbers
say NOTHING about the real washer.

Run:  py ml/tests/test_pipeline_synthetic.py
"""
# =============================================================================
# SECTION 1: Synthetic firmware-07 cycles
# =============================================================================
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from firmware.session_export import V3_COLUMNS  # noqa: E402

PHASES = [("weightSensing", 24, 150, 0.03, 3.0), ("wash", 360, 90, 0.06, 6.0),
          ("rinse", 240, 120, 0.08, 10.0), ("spin", 120, 450, 0.6, 20.0), ("finish", 12, 3, 0.01, 0.0)]


def make_cycle(seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    load = rng.uniform(0.8, 1.2)                     # benign cycle-to-cycle variation
    rows, t = [], 0
    for phase, n, pw, vib, dom in PHASES:
        for _ in range(n):
            t += 5024
            rms = 150 * load * np.exp(0.15 * rng.standard_normal()) * (2.5 if phase == "spin" else 1)
            hp = 0.4 * rms * np.exp(0.1 * rng.standard_normal())
            v = vib * load * np.exp(0.2 * rng.standard_normal())
            r = dict(timestamp_ms=t, accel_x=-0.6, accel_y=2.1, accel_z=-9.25, audio_rms=rms,
                     power_w=pw * load * np.exp(0.1 * rng.standard_normal()), phase=phase, load_class="MEDIUM",
                     epoch_ms=1.79e12 + t, n_audio=80384, n_accel=1005, n_power=5, fifo_overflows=0,
                     accel_clip_samples=0, audio_peak=rms * 12, audio_crest=12 * np.exp(0.1 * rng.standard_normal()),
                     audio_kurtosis=3.5 * np.exp(0.1 * rng.standard_normal()), audio_hp_rms=hp,
                     audio_hp_kurtosis=3.2 * np.exp(0.1 * rng.standard_normal()), audio_block_rms_max=rms * 1.6,
                     audio_block_rms_p90=rms * 1.2, audio_centroid_hz=2500 + 200 * rng.standard_normal(),
                     audio_band_0_250=0.3 * rms, audio_band_250_500=0.3 * rms, audio_band_500_1k=0.35 * rms,
                     audio_band_1k_2k=0.4 * rms, audio_band_2k_4k=0.4 * rms, audio_band_4k_8k=0.35 * rms,
                     vib_std_x=v, vib_std_y=v, vib_std_z=0.4 * v, vib_ptp_x=3 * v, vib_ptp_y=3 * v,
                     vib_ptp_z=1.2 * v, vib_mag_std=0.5 * v, vib_dom_hz=dom + rng.standard_normal() * 0.3,
                     vib_dom_rms=0.8 * v, vib_band_0_5=0.2 * v, vib_band_5_15=0.3 * v,
                     vib_band_15_30=(0.8 if phase == "spin" else 0.1) * v, vib_band_30_60=0.05 * v,
                     power_min=pw * 0.9, power_max=pw * 1.1, power_std=pw * 0.05 + 0.1, phase_source="smartthings")
            rows.append(r)
    return pd.DataFrame(rows)[V3_COLUMNS]


# =============================================================================
# SECTION 2: Run training + evaluation on them, check the report
# =============================================================================
def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        for i in range(6):
            make_cycle(100 + i).to_csv(d / f"wash_cycle_2026-11-0{i + 1}_0800.csv", index=False)
        models = d / "models"
        res = subprocess.run([sys.executable, str(ROOT / "ml" / "train_unsupervised_pdm.py"),
                              "--data-dir", str(d), "--models-dir", str(models),
                              "--eval-models", "mahalanobis"],
                             capture_output=True, text=True, cwd=str(ROOT))
        print(res.stdout[-4000:])
        assert res.returncode == 0, res.stderr[-3000:]
        import json
        rep = json.loads((models / "loco_report.json").read_text())
        r = rep["results"][0]
        assert rep["schema"] == "windowed"
        assert r["uses_power"] is True
        meta = json.loads((models / "pdm_detector_meta.json").read_text())
        assert meta["phase_conditioned"] is True, "SmartThings-labelled data must be phase-conditioned"
        assert r["false_alarm_cycles"] <= 1, r["false_alarm_cycles"]
        big = {k: v["levels"][-1]["clean_detect_rate"] for k, v in r["faults"].items()}
        print("largest-severity clean detection:", big)
        assert big["bearing_impulsive"] >= 0.8 and big["suspension_rocking"] >= 0.8, big
        assert "power_drag" in big, "power faults must be evaluated when every cycle has power"
    print("[PASS] windowed pipeline mechanics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
