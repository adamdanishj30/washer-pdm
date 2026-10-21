"""
test_session_export.py - offline tests for firmware/session_export.py
(no network: Firebase + SmartThings are not touched because the phase
timeline is read from a temporary local file).

Run:  py firmware/tests/test_session_export.py
"""
# =============================================================================
# SECTION 1: Setup
# =============================================================================
import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import firmware.smartthings_client as stc  # noqa: E402
from firmware import session_export as se  # noqa: E402


def v3_window(i: int, epoch0: int):
    """A record exactly as firmware 07 serialises it (compact keys)."""
    return {"t": 5024 * i, "e": epoch0 + 5024 * i, "na": 80384, "nv": 1005, "np": 5, "ov": 0, "vc": 0,
            "rms": 210.5, "apk": 3100.0, "acr": 14.7, "aku": 9.8, "ahr": 120.2, "ahk": 7.1, "abm": 300.0,
            "ab9": 250.0, "acn": 2900.0, "ab0": 60.0, "ab1": 30.0, "ab2": 40.0, "ab3": 70.0, "ab4": 90.0,
            "ab5": 110.0, "ax": -0.62, "ay": 2.14, "az": -9.25, "sx": 0.05, "sy": 0.04, "sz": 0.02,
            "px": 0.3, "py": 0.25, "pz": 0.1, "sm": 0.03, "vdf": 17.9, "vdr": 0.2, "vb0": 0.01, "vb1": 0.02,
            "vb2": 0.2, "vb3": 0.01, "pwr": 80.0 + i, "pmn": 75.0, "pmx": 90.0, "psd": 3.0}


# =============================================================================
# SECTION 2: Tests
# =============================================================================
def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stc.PHASE_DIR = td / "phases"                 # local timeline -> no Firebase fallback needed
        epoch0 = 1_792_300_000_000
        sid = "wash_2026-10-20_081500"
        stc.PHASE_DIR.mkdir()
        with open(stc._local_timeline_path(sid), "w") as f:
            f.write(json.dumps({"ts": epoch0 - 1000, "phase": "weightSensing"}) + "\n")
            f.write(json.dumps({"ts": epoch0 + 5024 * 100, "phase": "wash"}) + "\n")

        # --- v3 session: keys "w000001".. (dict, unordered on purpose) ---
        batches = {f"w{i:06d}": v3_window(i, epoch0) for i in range(200, 0, -1)}
        out = se.export_session_to_csv(sid, batches, out_path=td / "v3.csv")
        rows = list(csv.DictReader(open(out)))
        assert len(rows) == 200
        assert list(rows[0].keys())[:8] == se.LEGACY_COLUMNS, "first 8 columns must stay dashboard-compatible"
        assert int(rows[0]["timestamp_ms"]) < int(rows[1]["timestamp_ms"]), "rows must be chronological"
        assert rows[0]["phase"] == "weightSensing" and rows[150]["phase"] == "wash", "phase matching"
        assert rows[0]["phase_source"] == "smartthings"
        assert float(rows[0]["audio_kurtosis"]) == 9.8 and rows[0]["vib_dom_hz"] == "17.9"
        assert all(r["load_class"] == "unknown" for r in rows), "all v3 rows must have load_class == unknown"
        print("[ok] v3 export:", len(rows), "rows,", len(rows[0]), "columns")

        # --- legacy session: integer keys, amplified RMS gets rectified ---
        legacy = {str(i): {"t": 5000 * i, "ts": epoch0 + 5000 * i, "ax": -0.7, "ay": 1.4, "az": -9.4,
                           "rms": 3000.0, "pwr": 60.0} for i in range(1, 20)}
        out2 = se.export_session_to_csv("wash_offline_ABCD", legacy, out_path=td / "legacy.csv")
        lrows = list(csv.DictReader(open(out2)))
        assert list(lrows[0].keys()) == se.LEGACY_COLUMNS, "legacy schema must be unchanged"
        assert abs(float(lrows[0]["audio_rms"]) - 3000 / se.LEGACY_RMS_RATIO) < 0.1
        assert all(r["load_class"] == "unknown" for r in lrows), "all legacy rows must have load_class == unknown"
        print("[ok] legacy export unchanged (8 columns, RMS rectified)")

        # --- routing: short sessions go to testing_data ---
        assert se.target_path("wash_2026-10-20_081500", se.batches_to_rows(batches)).parent.name == "real_sessions"
        assert se.target_path("wash_x", se.batches_to_rows(legacy)).parent.name == "testing_data"
        assert se.format_session_filename(sid) == "wash_cycle_2026-10-20_0815.csv"
        print("[ok] routing + file naming")
    print("[PASS] session_export")
    return 0


if __name__ == "__main__":
    sys.exit(main())
