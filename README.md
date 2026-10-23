# Apex PdM: Hear It Before It Breaks

> A low-cost sensor pod that feels, hears and meters township machines, so wear and wasted power are caught before a breakdown.
> Built for the Sime Darby Property *Township of Tomorrow* Hackathon, track **PLANET · 03 Energy Efficiency**.
>
> 🌐 **Live dashboard:** [https://washer-pdm.pages.dev](https://washer-pdm.pages.dev)
> 📄 **Proposal:** [submission/Apex_PdM_Proposal.pdf](submission/Apex_PdM_Proposal.pdf)
> 📊 **Pitch deck:** [submission/Apex_PdM_Pitch_Deck.pdf](submission/Apex_PdM_Pitch_Deck.pdf)
> 📊 **Model evaluation:** [ml/models/loco_report.md](ml/models/loco_report.md)

**Team:** ADAM DANISH BIN JAMALUDIN, CHIK AMIR ASHRAF BIN AHMAD ADLAN (UiTM) · AITHISHWARAN A/L SHANKAR GANESH (UMPSA) · MANIKKAVASAGAN A/L SOMAIAH DEIVARAJAN (UKM) · MUHAMAD TOWA BIN MUHAMAD BUHARI (UPM)

---

## 1. The problem

Mosques, suraus, kuils, malls and clubhouses run many machines that spin: air-conditioning compressors, water pumps and fans. They are usually fixed only after they break. Over 55% of an average facility's maintenance is still reactive, "run it till it breaks" (US DOE FEMP *O&M Best Practices Guide*, Release 2.0, 2004, §5.2; US figures, not Malaysian data).

Before a machine fails, a worn bearing, damper or seal slowly makes it shake more, sound different and work harder. A part worth tens of ringgit turns into a new motor or compressor worth thousands, and a worn machine uses more electricity along the way. Industrial vibration sensors cost thousands of ringgit each, so only big factories use them.

## 2. The solution

A small pod on the **outside** of a machine (3M VHB tape, nothing inside opened) plus a smart plug (no rewiring):

| Sense | Hardware | What it catches |
|---|---|---|
| Feel | MPU-6050 accelerometer, 200 Hz via FIFO, 44 Hz anti-alias filter | Shaking, drum speed, suspension rocking |
| Hear | INMP441 MEMS microphone, 16 kHz (I2S DMA) | Grinding and rubbing; sound becomes numbers on the chip and is never uploaded as a recording |
| Meter | TP-Link Tapo P110 smart plug, 1 s (local KLAP) | How hard the motor is working |

A one-class (unsupervised) model learns each machine's own normal from healthy runs only, so it needs no broken-machine examples. A live web dashboard shows every run.

It is proven first on a Samsung WW10TP44DSX front-load washer: a hard test machine that shakes, sloshes and keeps changing speed.

## 3. How it works

```
Sensors ──► ESP32 (dual core) ──► Firebase RTDB ──► Live dashboard (washer-pdm.pages.dev)
                                          └──────► One-class anomaly model ──► flag the machine
```

- **Core 1:** continuous I2S audio, 200 Hz MPU FIFO and window DSP. **Core 0:** Tapo KLAP, session gating, batched Firebase upload, web server, OTA.
- Every **5.024 s** the pod sends one **45-column record with 32 signal features** (audio 15, vibration 13, power 4). About 4 minutes of data are kept during Wi-Fi drops.
- PC scripts and dashboard viewers never poll the cloud faster than every 30 s (Firebase Spark quota).

## 4. Evidence so far (TRL 4–5)

| What | Result | Source |
|---|---|---|
| Pilot kit cost | RM 169.68 net paid (sensor node RM 131.07 + smart plug) | Shopee receipts (7 orders) |
| Data | 13 wash sessions, 9,114 training-ready rows (as of 21 Oct), 4 complete firmware-07 cycles | `data/real_sessions/` |
| Vibration idle → spin | over 20× | firmware-07 cycles |
| Drum frequency in final spin | ≈ 20 Hz (≈ 1,200 rpm) in all 4 firmware-07 cycles | `ml/models/cycle_signature_report.md` |
| Nested leave-one-wash-out test | 0 of 8 healthy washes falsely flagged (95% upper bound 31%); simulated doubling of sound caught in 7 of 8; added vibration **not** detected | `ml/models/loco_report.md` |

**Limits, stated plainly:** the model test ran on 8 earlier washes in the older snapshot format (one 5 s snapshot, no phase labels), not on the 32-feature firmware-07 windows. Faults were simulated, not real. There is one test machine so far. The firmware-07 model needs at least 3 cycles of each wash type first.

## 5. Impact: Planet · Energy Efficiency

- **Energy (our estimate, to be confirmed in the pilot):** one machine with a 5 kW power draw running 10 h a day uses about 18,250 kWh a year. If a worn part makes it use 10% more, that is about 1,825 kWh, or **about RM 900 a year** at about RM 0.50/kWh. The 10% is an assumption; it sits inside the 5–20% energy savings the US DOE guide gives for O&M programmes (§2.4). A ~RM 170 pod that catches one such problem pays for itself within months (estimate).
- **Context:** air-conditioning is about 57% of energy use in Malaysian office buildings (Saidur, 2009). Surveys cited by the US DOE guide found predictive maintenance eliminated 70–75% of breakdowns (§5.4, US figures).
- **Second benefit:** fixing a small part early means machines last longer and less is scrapped.

No kWh, ringgit, carbon or scrap savings have been measured yet.

## 6. Roadmap

1. **Next:** 20+ more firmware-07 cycles, train and test the new model, noise baselines, then an air compressor and a water pump.
2. **Pilot:** about ten AC units at one township site (e.g. City of Elmina), measuring real kWh and false-alarm rates.
3. **Scale:** custom board, industrial accelerometer, one fleet dashboard for the township.

## 7. Repository map

| Path | What |
|---|---|
| `firmware/07_feature_streamer/` | Current ESP32 firmware (FreeRTOS dual core, Tapo, Firebase); see its README |
| `firmware/firebase_rest.py`, `firmware/auto_drive_sync_daemon.py`, `firmware/cloud_downloader.py` | Quota-aware cloud access, archiver and session downloader |
| `firmware/session_export.py` | Firmware-07 window schema (`V3_KEY_MAP`) |
| `ml/` | Feature fusion, detectors, calibration, leave-one-cycle-out evaluation ([ml/README.md](ml/README.md)) |
| `data/` | Session CSVs, session context, legacy feature dictionary |
| `index.html`, `historical.html`, `build_clean_dashboard.py` | Live and historical dashboards |
| `docs/hardware_guides/` | Hardware wiring schematics, assembly pinout, and sensor mounting instructions |
| `submission/` | Final hackathon proposal and pitch deck (PDF) |

## 8. Run it

```powershell
# Flash firmware 07 (credentials come from .env only)
py -3.12 firmware/07_feature_streamer/flash_firmware.py --compile --port COM3
# Download new sessions (incremental) and rebuild the dashboards
py firmware/cloud_downloader.py
py build_clean_dashboard.py
# Train + nested leave-one-cycle-out evaluation -> ml/models/loco_report.md
py ml/train_unsupervised_pdm.py
# Score one cycle
py ml/predict_pdm.py --file data/real_sessions/<cycle>.csv
```

Tests: `py ml/tests/test_dsp_parity.py`, `py ml/tests/test_pipeline_synthetic.py`, `py firmware/tests/test_session_export.py`, `py firmware/tests/test_daemon_offline.py`.
