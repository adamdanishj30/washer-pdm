"""
Try the Apex Lens tools from the command line on data/real_sessions.

  python -m apex_lens list_washes
  python -m apex_lens wash_overview 2026-10-28_0832
  python -m apex_lens compare_to_normal 2026-10-28_0832 [sound|vibration|power|all] [phase]
  python -m apex_lens detector_score 2026-10-28_0832 [per_phase|pooled]
  python -m apex_lens similar_washes 2026-10-28_0832 [k]
  python -m apex_lens render_plot 2026-10-28_0832 [trace|bands|overlay] [signal,signal] [phase]
                                    # saves the PNG to ml/outputs/apex_lens_smoke/ and prints the caption
  python -m apex_lens tokens 2026-10-28_0832        # tool outputs vs raw text, approx tokens
"""
from pathlib import Path
import sys

from apex_lens.experiment import count_tokens, raw_window_table
from apex_lens.tools import ApexLens


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 1
    lens = ApexLens()
    name, args = argv[0], argv[1:]
    if name == "tokens":
        wid = args[0]
        outs = {"wash_overview": lens.wash_overview(wid), "compare_to_normal(all)": lens.compare_to_normal(wid),
                "compare_to_normal(sound)": lens.compare_to_normal(wid, "sound"),
                "detector_score": lens.detector_score(wid), "similar_washes": lens.similar_washes(wid),
                "render_plot caption": lens.render_plot(wid)[1], "raw window table": raw_window_table(lens.store.get(wid))}
        print("output,approx_tokens")
        for k, v in outs.items():
            print(f"{k},{count_tokens(v)}")
        return 0
    keys = {"wash_overview": ["wash_id"], "compare_to_normal": ["wash_id", "sensor_group", "phase"],
            "detector_score": ["wash_id", "baseline"], "list_washes": [], "similar_washes": ["wash_id", "k"],
            "render_plot": ["wash_id", "kind", "signals", "phase"]}
    if name not in keys:
        print(__doc__)
        return 1
    kw = dict(zip(keys[name], args))
    if "signals" in kw:
        kw["signals"] = kw["signals"].split(",")
    text, png = lens.call_full(name, **kw)
    print(text)
    if png:
        # the CLI (not the tool) writes the smoke-test image, so the tools stay read-only
        out = Path(__file__).resolve().parent.parent / "ml" / "outputs" / "apex_lens_smoke"
        out.mkdir(parents=True, exist_ok=True)
        f = out / f"{kw['wash_id']}_{kw.get('kind', 'trace')}.png"
        f.write_bytes(png)
        print(f"saved {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
