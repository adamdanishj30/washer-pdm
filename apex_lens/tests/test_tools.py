"""
test_tools.py
Mechanics tests for the Apex Lens tools on SYNTHETIC firmware-07 washes
(ml/tests/test_pipeline_synthetic.make_cycle). They check the tools run, keep
their outputs short, never compare a wash with itself or its origin, and
react to a large injected fault. Synthetic numbers say nothing about the
real washer.

Run:  python -m pytest apex_lens/tests -q
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apex_lens.experiment import add_faulty_copy, count_tokens, raw_window_table  # noqa: E402
from apex_lens.store import WashStore, power_phases, vib_bad_mask  # noqa: E402
from apex_lens.tools import ApexLens, fmt, table  # noqa: E402
from ml.tests.test_pipeline_synthetic import make_cycle  # noqa: E402

MAX_TOOL_TOKENS = 1500


@pytest.fixture(scope="module")
def lens(tmp_path_factory):
    d = tmp_path_factory.mktemp("washes")
    for i in range(6):
        make_cycle(200 + i).to_csv(d / f"wash_cycle_2026-12-0{i + 1}_0800.csv", index=False)
    return ApexLens(WashStore.from_dir(d))


def test_power_phases():
    p = np.array([1] * 5 + [60] * 30 + [1500] * 25 + [80] * 10 + [400] * 25 + [2] * 5, float)
    ph = power_phases(p)
    assert list(ph[:5]) == ["idle"] * 5 and list(ph[-5:]) == ["idle"] * 5
    assert set(ph[35:60]) == {"heat"} and set(ph[70:95]) == {"spin"}
    assert set(ph[5:35]) == {"tumble"} and set(ph[60:70]) == {"tumble"}


def test_vib_bad_mask_flags_rotated_axes():
    df = make_cycle(1)
    df.loc[400:, ["accel_x", "accel_y", "accel_z"]] = [9.0, 0.5, 1.0]     # axes rotated (FIFO desync)
    bad = vib_bad_mask(df)
    assert not bad[:400].any() and bad[400:].all()


def test_format_helpers():
    assert fmt(0.04701) == "0.047" and fmt(1234.6) == "1235" and fmt(None) == "-" and fmt(float("nan")) == "-"
    assert table(["a", "b"], [(1, 0.5)]) == "a,b\n1,0.5"


def test_tools_run_and_stay_short(lens):
    wid = sorted(lens.store.washes)[0]
    outs = [lens.list_washes(), lens.wash_overview(wid), lens.compare_to_normal(wid),
            lens.compare_to_normal(wid, "sound"), lens.detector_score(wid, "per_phase"),
            lens.detector_score(wid, "pooled")]
    for o in outs:
        assert count_tokens(o) < MAX_TOOL_TOKENS, o
    assert count_tokens(raw_window_table(lens.store.get(wid))) > 10 * max(count_tokens(o) for o in outs)


def test_reference_never_includes_self_or_origin(lens):
    ids = sorted(lens.store.washes)
    add_faulty_copy(lens.store, ids[0], "suspension_rocking", 0.10, "X1")
    refs = lens.store.reference_ids("X1")
    assert "X1" not in refs and ids[0] not in refs and len(refs) == len(ids) - 1
    assert "X1" not in lens.store.reference_ids(ids[1])          # virtual washes never define normal


def test_large_fault_is_flagged(lens):
    ids = sorted(k for k in lens.store.washes if k != "X1")
    add_faulty_copy(lens.store, ids[1], "suspension_rocking", 0.10, "X2")
    assert "ABNORMAL" in lens.detector_score("X2", "per_phase")
    assert "above" in lens.compare_to_normal("X2", "vibration")


def test_errors_come_back_as_text(lens):
    assert lens.call("wash_overview", wash_id="nope").startswith("error:")
    assert lens.call("compare_to_normal", wash_id=sorted(lens.store.washes)[0], sensor_group="x").startswith("error:")
    assert lens.call("no_such_tool").startswith("error:")
