"""
registry.py
ONE place that defines the six Apex Lens tools the LLM can see: name,
description and input schema (JSON Schema). The MCP server (server.py) and
the experiment runner both read this file, so the LLM sees exactly the same
tools in every condition.

Rules written into every description
------------------------------------
* "Normal" always means THIS washer's other recorded washes.
* The tools report deviations; they never name a failing part.
* Wash classes are inferred from power, not the programme the user chose.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Shared vocabularies (enums)
# =============================================================================
SENSOR_GROUPS = ["all", "sound", "vibration", "power"]
PHASES = ["idle", "tumble", "heat", "spin"]
BASELINES = ["per_phase", "pooled"]
PLOT_KINDS = ["trace", "bands", "overlay"]
# Signals render_plot can draw (short names; the same names compare_to_normal prints)
SIGNALS = ["power_mean", "power_std", "sound_rms", "sound_above_2khz_rms", "sound_above_2khz_kurtosis",
           "sound_crest", "sound_centroid", "vib_level", "vib_dominant_freq", "vib_dominant_rms"]

_WASH_ID = {"type": "string", "description": "A wash id exactly as list_washes prints it."}
_COMMON = ("'Normal' means this washer's other recorded washes, never this wash itself. "
           "Outputs are short CSV-style tables; numbers are rounded to 3 significant figures. "
           "No tool can tell which part is failing (there are no labelled faults).")


# =============================================================================
# SECTION 2: The six tools
# =============================================================================
TOOLS = [
    {
        "name": "list_washes",
        "description": ("List every recorded wash: id, duration, wash class (inferred from power, not the "
                        "programme the user chose), number of 5 s windows and the share of windows with usable "
                        "vibration data. Call this first. " + _COMMON),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "wash_overview",
        "description": ("One wash at a glance: energy (kWh), peak power, data-quality notes, and the wash split "
                        "into phases found from power (idle, tumble, heat, spin) with median power, sound and "
                        "vibration per phase block. " + _COMMON),
        "input_schema": {"type": "object", "properties": {"wash_id": _WASH_ID},
                         "required": ["wash_id"], "additionalProperties": False},
    },
    {
        "name": "compare_to_normal",
        "description": ("Compare one wash with this washer's normal, per phase and measurement: this wash's "
                        "median vs the min..max of the other washes' medians. sensor_group='all' lists only "
                        "measurements outside the normal range; one group lists every row. Phases seen in fewer "
                        "than 3 other washes say 'insufficient data'. " + _COMMON),
        "input_schema": {"type": "object", "properties": {
            "wash_id": _WASH_ID,
            "sensor_group": {"type": "string", "enum": SENSOR_GROUPS, "default": "all"},
            "phase": {"type": "string", "enum": PHASES, "description": "Optional: one phase only."},
        }, "required": ["wash_id"], "additionalProperties": False},
    },
    {
        "name": "detector_score",
        "description": ("Run the one-class anomaly detector (robust Mahalanobis, trained only on the other "
                        "washes) on one wash. Returns NORMAL/ABNORMAL for the whole wash (ABNORMAL needs about "
                        "10 minutes of sustained unusualness), when it started, which sensor group drove it, and "
                        "a per-phase table. ABNORMAL means unusual for this washer, not a diagnosed fault. "
                        + _COMMON),
        "input_schema": {"type": "object", "properties": {
            "wash_id": _WASH_ID,
            "baseline": {"type": "string", "enum": BASELINES, "default": "per_phase",
                         "description": "per_phase = one normal model per phase; pooled = one for everything."},
        }, "required": ["wash_id"], "additionalProperties": False},
    },
    {
        "name": "similar_washes",
        "description": ("Find the k past washes most like this one (per-phase medians of sound, vibration and "
                        "power, scaled with the other washes only) and the measurements where each differs most. "
                        + _COMMON),
        "input_schema": {"type": "object", "properties": {
            "wash_id": _WASH_ID,
            "k": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
        }, "required": ["wash_id"], "additionalProperties": False},
    },
    {
        "name": "render_plot",
        "description": ("Draw one 800x450 chart of a wash with this washer's normal range shaded behind it. "
                        "kind='trace': up to 3 signals over time with phases shaded; kind='bands': sound and "
                        "vibration band energies for one phase vs normal (frequency content as bands, not raw "
                        "waveforms); kind='overlay': one signal's spread per phase, this wash vs normal. A short "
                        "caption with the numbers comes with the image. " + _COMMON),
        "input_schema": {"type": "object", "properties": {
            "wash_id": _WASH_ID,
            "kind": {"type": "string", "enum": PLOT_KINDS, "default": "trace"},
            "signals": {"type": "array", "items": {"type": "string", "enum": SIGNALS}, "minItems": 1,
                        "maxItems": 3, "description": "For trace (1-3) and overlay (first one is used)."},
            "phase": {"type": "string", "enum": PHASES,
                      "description": "trace: zoom to this phase. bands: which phase (default spin)."},
        }, "required": ["wash_id"], "additionalProperties": False},
    },
]

TOOL_NAMES = [t["name"] for t in TOOLS]
