"""
Try the Apex Lens tools from the command line on data/real_sessions.

  python -m apex_lens list_washes
  python -m apex_lens wash_overview 2026-10-28_0832
  python -m apex_lens compare_to_normal 2026-10-28_0832 [sound|vibration|power|all] [phase]
  python -m apex_lens detector_score 2026-10-28_0832 [per_phase|pooled]
  python -m apex_lens tokens 2026-10-28_0832        # tool outputs vs raw text, approx tokens
"""
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
                "detector_score": lens.detector_score(wid), "raw window table": raw_window_table(lens.store.get(wid))}
        print("output,approx_tokens")
        for k, v in outs.items():
            print(f"{k},{count_tokens(v)}")
        return 0
    keys = {"wash_overview": ["wash_id"], "compare_to_normal": ["wash_id", "sensor_group", "phase"],
            "detector_score": ["wash_id", "baseline"], "list_washes": []}
    if name not in keys:
        print(__doc__)
        return 1
    print(lens.call(name, **dict(zip(keys[name], args))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
