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


# =============================================================================
# L1 additions: six tools, output budget, quality/abstain, thin phases
# =============================================================================
from apex_lens.registry import TOOL_NAMES, TOOLS  # noqa: E402
from apex_lens.tools import budget  # noqa: E402

BLOCKED = ("bearing", "damper", "shock absorber", "imbalance", "unbalance", "motor fault", "pump fault",
           "worn", "failing", "failure", "remaining life", "ringgit")


def _real_ids(lens):
    return sorted(k for k, w in lens.store.washes.items() if w.reference)


def test_registry_matches_dispatch(lens):
    assert TOOL_NAMES == ["list_washes", "wash_overview", "compare_to_normal", "detector_score",
                          "similar_washes", "render_plot"]
    for t in TOOLS:
        assert t["input_schema"]["type"] == "object" and len(t["description"]) > 80
        assert not lens.call(t["name"], **({} if t["name"] == "list_washes"
                                           else {"wash_id": _real_ids(lens)[0]})).startswith("error:")


def test_all_six_tools_short_with_ref_line(lens):
    wid = _real_ids(lens)[0]
    for name in TOOL_NAMES:
        out = lens.call(name, **({} if name == "list_washes" else {"wash_id": wid}))
        assert out.startswith(f"ref: {name}#"), out[:80]
        assert count_tokens(out) < MAX_TOOL_TOKENS
        low = out.lower()
        assert not any(b in low for b in BLOCKED), out


def test_similar_washes_never_returns_self_or_origin(lens):
    ids = _real_ids(lens)
    add_faulty_copy(lens.store, ids[2], "bearing_impulsive", 1.0, "X3")
    out = lens.similar_washes("X3", k=5)
    listed = [ln.split(",")[0] for ln in out.split("\n")[2:]]
    assert "X3" not in listed and ids[2] not in listed and len(listed) == 5
    assert "X3" not in lens.store.reference_ids(ids[3])          # fault copies never become candidates


def test_render_plot_png_fixed_size(lens):
    import struct
    wid = _real_ids(lens)[0]
    for kind in ("trace", "bands", "overlay"):
        text, png = lens.call_full("render_plot", wash_id=wid, kind=kind)
        assert png[:8] == b"\x89PNG\r\n\x1a\n", text
        w, h = struct.unpack(">II", png[16:24])
        assert (w, h) == (800, 450)
        assert "chart:" in text
    assert lens.call("render_plot", wash_id=wid, signals=["nope"]).startswith("error:")


def test_thin_phase_says_insufficient_data(lens):
    ids = _real_ids(lens)
    d = lens.store.get(ids[0]).df.copy()
    d.loc[100:140, "power_w"] = 1500.0                 # a heater block no reference wash has
    lens.store.register("X4", d, origin=ids[0])
    assert "heat" in set(lens.store.get("X4").df["phase"])
    out = lens.compare_to_normal("X4", "power")
    assert "heat: insufficient data (n=0" in out


def test_not_a_wash_abstains(lens):
    d = lens.store.get(_real_ids(lens)[0]).df.copy()
    d["power_w"] = 1.0
    lens.store.register("X5", d)
    for name in ("compare_to_normal", "detector_score", "similar_washes"):
        out = lens.call(name, wash_id="X5")
        assert "abstain:" in out and "quality: not a wash" in out


def test_budget_truncates_whole_lines():
    long = "\n".join(f"row{i},{i * 1.5},{'x' * 40}" for i in range(2000))
    out = budget(long)
    assert count_tokens(out) <= MAX_TOOL_TOKENS
    assert out.split("\n")[-1].startswith("truncated: ") and "rows omitted" in out
