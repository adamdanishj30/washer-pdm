# Apex Lens: tools that let an LLM read the washer data

Apex Lens is the "bridge" part of Apex PdM 2.0. An LLM (Claude) does not read the raw sensor table. It calls these tools, which do the computing and return short text answers. The LLM chooses what to look at and explains; it never diagnoses a fault, because there are no fault labels to learn that from.

This folder is plain Python for now. The MCP server wrapper comes next, and it will expose these same functions unchanged. Design notes and literature: `Papers\mcp\RESEARCH_SYNTHESIS.md` and `MCP_RESEARCH_NOTES.md` on the project Drive.

## Tools

| Tool | What it returns |
|---|---|
| `list_washes()` | Every firmware-07 recording: id, duration, wash class inferred from power, share of windows with usable vibration data |
| `wash_overview(wash_id)` | Energy, peak power, data-quality notes, and the wash split into phases (idle / tumble / heat / spin) with median power, sound and vibration per block |
| `compare_to_normal(wash_id, sensor_group="all", phase=None)` | This wash's median per phase and measurement against the range of the other washes' medians. `all` lists only what is outside the normal range; one group (`sound`, `vibration`, `power`) lists every row |
| `detector_score(wash_id, baseline="per_phase")` | The one-class Mahalanobis detector from `ml/` trained on the *other* washes, with a NORMAL/ABNORMAL verdict, when it started, which sensor group drove it, and a per-phase table. `baseline="pooled"` uses one normal model for the whole wash, `"per_phase"` one per power phase |

Every answer is a header line plus a header-once CSV table with numbers rounded to 3 significant figures. Errors come back as text (`error: ...`) so an agent can recover.

Try them:

```
python -m apex_lens list_washes
python -m apex_lens wash_overview 2026-10-28_0832
python -m apex_lens compare_to_normal 2026-10-28_0832 vibration
python -m apex_lens detector_score 2026-10-28_0832 pooled
python -m apex_lens tokens 2026-10-28_0832
```

The tools read `data/real_sessions/wash_cycle_*.csv` (firmware-07 files only). Those CSVs are not in git yet, so copy them from the Drive folder first.

## What the tools do to the data

* **Phases from power** (there are no SmartThings phase labels on any firmware-07 wash): `idle` before the first and after the last window at 20 W or more; `heat` for 20 or more windows above 1 kW; `spin` for 20 or more windows at 200–1000 W; `tumble` for everything in between. Fill, wash, rinse and drain cannot be told apart from power alone, so they share `tumble`.
* **Wash class** (Quick / Long cold / Long hot) from the rules in `ml/cycle_signature_report.py`. It is an inference, not the programme the user picked. `compare_to_normal` compares within the class when 3 or more other washes share it, otherwise against all washes.
* **Bad accelerometer windows.** The MPU-6050 FIFO desyncs during some washes and corrupts the vibration data from that point to the end. A window is marked bad if `| |a| - 9.81 | > 1.5`, any accelerometer sample clipped, or the gravity vector is more than 30° from the first 60 windows. Bad windows are left out of vibration statistics and of detector training. When scoring a wash, their vibration columns are replaced with the normal median so only their sound and power count.
* **No leakage.** "Normal" for a wash is always the *other* recorded washes. A fault-injected copy (`experiment.add_faulty_copy`) never joins the normal set, and its original recording is left out of its own normal set.

## Experiment helpers (`experiment.py`)

* `add_faulty_copy(store, origin_id, kind, severity, new_id)` injects a fault from `ml/fault_injection.py` (`bearing_impulsive`, `suspension_rocking`, `imbalance_1x`, `power_drag`) and stores it under a neutral id, so the LLM cannot tell from the name.
* `raw_window_table(wash)` is condition C1: every measurement of every window as CSV text.
* `count_tokens(text)` gives an approximate count using tiktoken `cl100k_base`. Claude's tokenizer differs, so reported results must use the API's own token counts.

## First numbers (2 Nov 2026, 12 recorded washes, approximate tokens)

| Input to the LLM | Tokens |
|---|---|
| Raw window table, one wash (C1) | 49,000–165,000 (median about 140,000) |
| `wash_overview` | about 300 |
| `compare_to_normal("all")` | about 250 |
| `compare_to_normal("sound")` | about 500 |
| `detector_score` | about 200 |

Sanity check on one recording only (28 Oct, faults injected from mid-wash), **not a result**:

| Fault injected | per_phase | pooled |
|---|---|---|
| none | NORMAL | NORMAL |
| bearing_impulsive 0.5 × | ABNORMAL (sound, from spin at 59.7 min) | NORMAL |
| suspension_rocking 0.05 m/s² | ABNORMAL (vibration) | ABNORMAL (vibration) |
| imbalance_1x 0.10 m/s² | NORMAL | NORMAL |
| power_drag 20 W | NORMAL | NORMAL |

One wash proves nothing, but it shows the per-phase vs pooled comparison can be measured with these tools.

## Known limits

* Accelerometer FIFO desync: 24 Oct (from 69.5 min), 27 Oct 06:24 (from 35.4 min), 1 Nov (from 58.7 min) and 2 Nov 06:37 (from 77.0 min). In each case it runs from that point to the end of the recording. `2026-11-02_0851` is not a wash (no power draw, accelerometer bad throughout).
* 12 usable washes. Claims about false-alarm rates need about 30.
* `audio_*` values are in firmware units, not calibrated sound pressure.

## Tests

```
python -m pytest apex_lens/tests -q
```

The tests use synthetic washes and check mechanics only: outputs stay under 1,500 tokens, the raw table is at least 10× larger, no wash is ever compared with itself or its origin, and a large injected fault is flagged.
