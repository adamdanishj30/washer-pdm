"""
ml/tests/test_cycle_signature_energy.py
Unit tests for energy integration (kWh) and peak power (W) metrics in cycle signatures.

Verifies:
1. Constant 1,000 W for 720 windows at 5.0 s yields exactly 1.000 kWh and 1,000 W peak.
2. Low-power session (< 50 W) yields None for both energy and peak power (No power data).
3. Firmware-07 windowed session (dt = 5.024 s) correctly scales energy by 5.024 s.
4. Variable power profile correctly extracts peak power and integrates kWh.

Constraints:
- Operates strictly on synthetic files in tempfile.TemporaryDirectory().
- Never writes to data/ or ml/models/.
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
from typing import List

# =============================================================================
# SECTION 1: Path Setup & Module Import
# =============================================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.cycle_signature_report import analyze_session_csv  # noqa: E402


# =============================================================================
# SECTION 2: Synthetic CSV Generator Helpers
# =============================================================================
def write_synthetic_legacy_csv(
    csv_path: Path,
    powers: List[float],
    dt_ms: int = 5000,
) -> None:
    """
    Write a synthetic legacy CSV session file with specified power profile.
    Uses legacy columns: timestamp_ms, power_w, accel_x, accel_y, accel_z, audio_rms.
    """
    fieldnames = ["timestamp_ms", "power_w", "accel_x", "accel_y", "accel_z", "audio_rms"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        t = 0
        for p in powers:
            writer.writerow({
                "timestamp_ms": t,
                "power_w": f"{p:.2f}",
                "accel_x": "-0.66",
                "accel_y": "2.88",
                "accel_z": "-9.00",
                "audio_rms": "120.0",
            })
            t += dt_ms


def write_synthetic_fw07_csv(
    csv_path: Path,
    powers: List[float],
    dt_ms: int = 5024,
) -> None:
    """
    Write a synthetic firmware-07 CSV session file with specified power profile.
    Contains epoch_ms and vib_mag_std to trigger schema_label == 'fw07'.
    """
    fieldnames = [
        "timestamp_ms", "epoch_ms", "power_w", "accel_x", "accel_y", "accel_z",
        "audio_rms", "vib_mag_std", "vib_dom_hz", "n_accel", "fifo_overflows",
        "accel_clip_samples",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        t = 100000  # Start well above 30s to avoid boot_at_start
        epoch = 1729000000000
        for p in powers:
            writer.writerow({
                "timestamp_ms": t,
                "epoch_ms": epoch,
                "power_w": f"{p:.2f}",
                "accel_x": "-0.66",
                "accel_y": "2.88",
                "accel_z": "-9.00",
                "audio_rms": "150.0",
                "vib_mag_std": "0.032",
                "vib_dom_hz": "19.9",
                "n_accel": "1005",
                "fifo_overflows": "0",
                "accel_clip_samples": "0",
            })
            t += dt_ms
            epoch += dt_ms


# =============================================================================
# SECTION 3: Test Cases
# =============================================================================
def test_constant_1000w_720_windows() -> None:
    """
    Test 1: Constant 1,000 W for 720 windows at 5.0 s.
    Duration: 720 * 5.0 s = 3,600 s = 1.0 hour.
    Energy: 1,000 W * 3,600 s / 3,600,000 = 1.000 kWh.
    Peak power: 1,000 W.
    """
    with tempfile.TemporaryDirectory() as td:
        session_path = Path(td) / "wash_cycle_2026-11-01_1000.csv"
        powers = [1000.0] * 720
        write_synthetic_legacy_csv(session_path, powers, dt_ms=5000)

        res = analyze_session_csv(session_path, {})
        assert res["energy_kwh"] is not None, "energy_kwh should not be None for 1000 W session"
        assert res["peak_power_w"] is not None, "peak_power_w should not be None for 1000 W session"

        # Check exact expected numbers
        assert res["energy_kwh"] == 1.000, f"Expected 1.000 kWh, got {res['energy_kwh']}"
        assert res["peak_power_w"] == 1000, f"Expected peak 1000 W, got {res['peak_power_w']}"
        print("  [PASS] test_constant_1000w_720_windows (1.000 kWh, 1000 W peak)")


def test_unmetered_low_power_yields_none() -> None:
    """
    Test 2: Low-power session (< 50 W maximum power).
    Must result in energy_kwh = None and peak_power_w = None.
    Signature class must be 'No power data'.
    """
    with tempfile.TemporaryDirectory() as td:
        session_path = Path(td) / "wash_cycle_2026-11-01_1001.csv"
        # Constant 25 W (well below 50 W threshold)
        powers = [25.0] * 120
        write_synthetic_legacy_csv(session_path, powers, dt_ms=5000)

        res = analyze_session_csv(session_path, {})
        assert res["energy_kwh"] is None, f"Expected energy_kwh=None, got {res['energy_kwh']}"
        assert res["peak_power_w"] is None, f"Expected peak_power_w=None, got {res['peak_power_w']}"
        assert res["signature_class"] == "No power data", f"Expected 'No power data', got {res['signature_class']}"
        print("  [PASS] test_unmetered_low_power_yields_none (None, None, 'No power data')")


def test_firmware_07_dt_scaling() -> None:
    """
    Test 3: Firmware-07 windowed session with dt = 5.024 s.
    720 windows at 1,000 W:
    Energy: 720 * 1,000 * 5.024 / 3,600,000 = 1.0048 kWh -> rounded to 3 dp = 1.005 kWh.
    Peak power: 1,000 W.
    """
    with tempfile.TemporaryDirectory() as td:
        session_path = Path(td) / "wash_cycle_2026-11-01_1002.csv"
        powers = [1000.0] * 720
        write_synthetic_fw07_csv(session_path, powers, dt_ms=5024)

        res = analyze_session_csv(session_path, {})
        assert res["schema"] == "fw07", f"Expected schema fw07, got {res['schema']}"
        assert res["energy_kwh"] == 1.005, f"Expected 1.005 kWh, got {res['energy_kwh']}"
        assert res["peak_power_w"] == 1000, f"Expected peak 1000 W, got {res['peak_power_w']}"
        print("  [PASS] test_firmware_07_dt_scaling (1.005 kWh at dt=5.024s)")


def test_variable_power_profile() -> None:
    """
    Test 4: Variable power profile with distinct peak and active intervals.
    100 windows at 10 W, 50 windows at 2,290 W, 100 windows at 300 W (dt = 5.0 s).
    Total energy: (100*10 + 50*2290 + 100*300) * 5.0 / 3,600,000
                = (1,000 + 114,500 + 30,000) * 5.0 / 3,600,000
                = 145,500 * 5.0 / 3,600,000 = 0.202083... kWh -> 0.202 kWh.
    Peak power: 2,290 W.
    """
    with tempfile.TemporaryDirectory() as td:
        session_path = Path(td) / "wash_cycle_2026-11-01_1003.csv"
        powers = [10.0] * 100 + [2290.0] * 50 + [300.0] * 100
        write_synthetic_legacy_csv(session_path, powers, dt_ms=5000)

        res = analyze_session_csv(session_path, {})
        assert res["energy_kwh"] == 0.202, f"Expected 0.202 kWh, got {res['energy_kwh']}"
        assert res["peak_power_w"] == 2290, f"Expected peak 2290 W, got {res['peak_power_w']}"
        print("  [PASS] test_variable_power_profile (0.202 kWh, 2290 W peak)")


# =============================================================================
# SECTION 4: Test Suite Runner
# =============================================================================
def main() -> int:
    print("[RUN] Running cycle signature energy calculation tests...")
    test_constant_1000w_720_windows()
    test_unmetered_low_power_yields_none()
    test_firmware_07_dt_scaling()
    test_variable_power_profile()
    print("[PASS] All cycle signature energy tests passed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
