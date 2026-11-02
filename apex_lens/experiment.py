"""
experiment.py
Helpers for the Apex Lens pilot and experiment: fault-injected "virtual"
washes under neutral ids, the raw-text baseline (condition C1), and token
counting.

Token counts use tiktoken's cl100k_base encoding as a stand-in. Claude's
tokenizer differs, so treat counts as approximate and use the provider's
token-count endpoint (or the usage field of real API calls) for reported
results.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports
# =============================================================================
from typing import Optional

import numpy as np
import pandas as pd

from apex_lens.store import Wash, WashStore
from apex_lens.tools import fmt
from ml.fault_injection import FAULTS, inject

# power phase -> group name ml/fault_injection.py understands (drum turns in tumble and heat)
_PHASE_TO_GROUP = {"idle": "idle", "tumble": "wash", "heat": "wash", "spin": "spin"}
RAW_COLUMNS_SKIP = ("timestamp_ms", "epoch_ms", "phase", "load_class", "phase_source", "row", "vib_ok",
                    "n_audio", "n_accel", "n_power", "fifo_overflows")


# =============================================================================
# SECTION 2: Fault-injected virtual washes
# =============================================================================
def add_faulty_copy(store: WashStore, origin_id: str, kind: str, severity: float, new_id: str,
                    onset_frac: float = 0.5, seed: int = 0) -> Wash:
    """
    Copy recording `origin_id`, inject `kind` at `severity` (units in
    ml/fault_injection.FAULTS) from `onset_frac` of the wash, and register it
    as `new_id`. The copy never joins the reference set, and its origin is
    left out of its own reference set.
    """
    if kind not in FAULTS or FAULTS[kind]["schema"] not in ("windowed", "both"):
        raise ValueError(f"'{kind}' is not a firmware-07 fault")
    src = store.get(origin_id).df.copy()
    src["phase_group"] = src["phase"].map(_PHASE_TO_GROUP)
    faulty = inject(src, kind, severity, onset_frac=onset_frac, seed=seed)
    w = store.register(new_id, faulty, source=f"{origin_id} + {kind} @ {severity}", origin=origin_id)
    w.df["fault_active"] = faulty["fault_active"].to_numpy()      # ground truth, never shown to the LLM
    return w


# =============================================================================
# SECTION 3: Condition C1 (raw text) and token counting
# =============================================================================
def raw_window_table(w: Wash, max_rows: Optional[int] = None) -> str:
    """Every firmware measurement of every window as CSV text (what 'give the LLM the raw data' means)."""
    cols = [c for c in w.df.columns if c not in RAW_COLUMNS_SKIP and c != "fault_active"]
    d = w.df[cols] if max_rows is None else w.df[cols].head(max_rows)
    lines = [",".join(cols)]
    for row in d.itertuples(index=False):
        lines.append(",".join(fmt(v) for v in row))
    return "\n".join(lines)


_ENC = None


def count_tokens(text: str) -> int:
    """Approximate token count (cl100k_base); falls back to chars/4 if tiktoken is missing."""
    global _ENC
    try:
        if _ENC is None:
            import tiktoken
            _ENC = tiktoken.get_encoding("cl100k_base")
        return len(_ENC.encode(text))
    except ImportError:
        return int(np.ceil(len(text) / 4))
