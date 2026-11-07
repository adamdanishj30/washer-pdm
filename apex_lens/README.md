# Apex Lens: tools that let an LLM read the washer data

Apex Lens is the "bridge" part of Apex PdM 2.0. An LLM (Claude) does not read the raw sensor table. It calls these tools, which do the computing and return short text answers. The LLM chooses what to look at and explains; it never diagnoses a fault, because there are no fault labels to learn that from.

The six tools are plain Python (`tools.py`, `plots.py`) and are served unchanged by a read-only MCP server (`server.py`). Names, descriptions and input schemas live in one file, `registry.py`, so the MCP server and the experiment runner show the LLM exactly the same tools. Design notes and literature: `Papers\mcp\RESEARCH_SYNTHESIS.md` and `MCP_RESEARCH_NOTES.md` on the project Drive. Build plan: `docs/handoffs/PLAN_QUEUE_apex_lens.md` on Drive (L0-L2 done by Claude on 7 Nov 2026).

## Tools

| Tool | What it returns |
|---|---|
| `list_washes()` | Every firmware-07 recording: id, duration, wash class inferred from power, share of windows with usable vibration data |
| `wash_overview(wash_id)` | Energy, peak power, data-quality notes, and the wash split into phases (idle / tumble / heat / spin) with median power, sound and vibration per block |
| `compare_to_normal(wash_id, sensor_group="all", phase=None)` | This wash's median per phase and measurement against the range of the other washes' medians. `all` lists only what is outside the normal range; one group (`sound`, `vibration`, `power`) lists every row |
| `detector_score(wash_id, baseline="per_phase")` | The one-class Mahalanobis detector from `ml/` trained on the *other* washes, with a NORMAL/ABNORMAL verdict, when it started, which sensor group drove it, and a per-phase table. `baseline="pooled"` uses one normal model for the whole wash, `"per_phase"` one per power phase |
| `similar_washes(wash_id, k=3)` | The k other washes closest to this one (per-phase medians, scaled with the other washes only) and the 3 measurements where each differs most |
| `render_plot(wash_id, kind="trace", signals=None, phase=None)` | One 800×450 PNG with this washer's normal range behind it, plus a caption holding the numbers it shows. `trace`: up to 3 signals over time, phases shaded, bad-accelerometer windows hatched, detector red windows ticked; `bands`: sound and vibration band energies for one phase vs normal; `overlay`: one signal's spread per phase, this wash vs normal |

Every answer is a header line plus a header-once CSV table with numbers rounded to 3 significant figures. Errors come back as text (`error: ...`) so an agent can recover.

Through `ApexLens.call` / `call_full` (what the MCP server uses) every answer also:
* starts with `ref: <tool>#<n>`, so an LLM answer can cite where each number came from;
* carries a `quality:` line for each data problem of the wash (bad accelerometer windows, not a wash);
* is cut to **1,500 approximate tokens**, ending with `truncated: N rows omitted; narrow with phase= or sensor_group=` if it had to be cut.

Honesty rules built into the answers:
* **Abstain.** A recording that is not a wash gets `abstain:` from `compare_to_normal`, `detector_score` and `similar_washes`. If under 50% of a wash's running windows have usable accelerometer data, vibration is not compared and the detector says its verdict rests on sound and power only.
* **Thin phases.** A phase that fewer than 3 other washes contain (for example `heat`, which only the one Long hot wash has) says `insufficient data (n=k ...)` instead of a comparison.
* No tool output names a part (bearing, damper, pump...). "Unusual for this washer" is the strongest claim.

Try them:

```
python -m apex_lens list_washes
python -m apex_lens wash_overview 2026-10-28_0832
python -m apex_lens compare_to_normal 2026-10-28_0832 vibration
python -m apex_lens detector_score 2026-10-28_0832 pooled
python -m apex_lens similar_washes 2026-10-28_0832
python -m apex_lens render_plot 2026-10-28_0832 bands       # PNG saved to ml/outputs/apex_lens_smoke/
python -m apex_lens tokens 2026-10-28_0832
```

## MCP server

Install once: `py -m pip install -r apex_lens/requirements.txt`.

The server speaks MCP over stdio and is read-only: it loads `data/real_sessions/*.csv` at start-up and never writes files, opens network connections, reads `.env` or touches Firebase, SmartThings or Tapo, so it needs no key and the Firebase polling rule is untouched. Only recorded washes are visible (fault-injected copies exist only in the experiment).

* **Claude Code** (run in the project folder):
  `claude mcp add apex-lens -- py "G:\My Drive\Projects\PdM SideProject\apex_lens\server.py"`
* **Claude Desktop**: Settings → Developer → Edit Config, then add to `claude_desktop_config.json`:
  ```json
  {"mcpServers": {"apex-lens": {"command": "py",
    "args": ["G:\\My Drive\\Projects\\PdM SideProject\\apex_lens\\server.py"]}}}
  ```
  Restart Claude Desktop; the six tools appear under the tools icon.
* **Antigravity / other MCP clients**: same command and argument (`py <repo>\apex_lens\server.py`), stdio transport.
* Another data folder: add `--data-dir <folder>` to the arguments.

Then ask, for example: "Was the 28 Oct wash normal for this washer? Which phase and sensor stand out?" Expect start-up in a few seconds and about 1 s per detector call. Answers in chat are a demo, not an experiment result.

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
* Only one wash (20 Oct, Long hot) has a heater phase, so `heat` always says "insufficient data" until 3 or more hot washes are recorded.
* `audio_*` values are in firmware units, not calibrated sound pressure.

## Tests

```
python -m pytest apex_lens/tests -q
```

The tests use synthetic washes and check mechanics only: all six tools stay under 1,500 tokens and start with a `ref:` line, the raw table is at least 10× larger, no wash is ever compared with itself or its origin (also in `similar_washes`), a large injected fault is flagged, plots are 800×450 PNGs, thin phases say "insufficient data", non-washes abstain, and the MCP server lists exactly the six registry tools as read-only and returns text and images (`test_server.py`). `ml/tests/test_pipeline_default_unchanged.py` proves the `conditioned=` switch in `ml/pipeline.py` leaves the deployed model's behaviour unchanged.
