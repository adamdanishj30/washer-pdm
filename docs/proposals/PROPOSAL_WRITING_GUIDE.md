# Apex PdM: Proposal Writing Guide

**Read this before writing or editing any proposal, brief, pitch deck or Q&A answer.**
Last updated: 2026-10-21 (facts updated to 21 Oct: 13 sessions, 4 fw-07 cycles, inferred wash types, no load guess). Owner: Adam.

This guide covers what our proposal must say, in what order, in what tone, and which numbers we are allowed to use. It applies to people and to AI agents (Claude, Antigravity/Gemini).

---

## 1. The Story in One Paragraph

Townships are full of machines that spin: AC compressors in mosques, malls and temples, water pumps, fans. They usually get fixed only after they break, which is expensive and disruptive. We built a **real, working sensor rig** that feels, hears and measures a machine, sends the data to the internet, and shows it live on a website. We proved it on a washing machine, a hard test because it shakes, sloshes and changes speed all the time. With this data we are training an **unsupervised machine-learning model** to spot unusual vibration early. Next, we test on AC compressors and water pumps. At township scale, the same rig can watch every AC unit from one dashboard, cutting energy waste and expensive repairs.

---

## Track

Our one track is **PLANET · 03 Energy Efficiency**. Circular economy (longer machine life, fewer replacements) is a supporting benefit only; do not present it as our track.

---

## 2. Section Order

Use this order for the master proposal and the pitch deck. For the official 2-page form, keep the form's headings (1. Title … 7. Impact) and fit this content inside them (see Section 7).

| # | Section | Goal | Must include |
|---|---|---|---|
| 1 | **Intro** | Hook the judge in 30 seconds | 2 lines on the township problem first, then "we built a working rig to solve it" + live link |
| 2 | **Problem** | Make the pain real | Machines fixed only after they break; worn parts make machines shake more and use more power; small part → big repair bill; mosques/malls lose cooling |
| 3 | **Our Solution** | What it is, in plain words | Sensor pod on the outside of a machine; 3 sensors together (vibration, sound, power), machine state planned; ML model learns "normal"; alerts when something looks wrong |
| 4 | **Our Prototype** | Prove it's real | Working rig in a splash-resistant (untested) box, sends data to the internet, live website; **real rig photo** |
| 5 | **Our Hardware** | Show it's buildable and cheap | Parts table: Part / What it does / Cost; simple flow diagram |
| 6 | **Testing Results** | Show real data | Numbers from our own cycles only (Section 4 of this guide) |
| 7 | **Machine-Learning Model (Plan)** | Show the next step is solid | Unsupervised anomaly detection, feature fusion, how we test it (Section 5) |
| 8 | **Next Machines** | Show it travels | AC compressor, water pump, fans (machines with real vibration) |
| 9 | **Township Vision** | Tie back to the theme | Many AC units per mosque/mall/temple, mass-produced pods, one dashboard, energy + repair savings |
| 10 | **Impact & Cost** | Make the value concrete | Three ways it saves money; a clearly labelled estimate example |

**Rule:** the township must appear in the **first 2 lines** of the intro, not only at the end. Impact (25%) and Strategic Fit (15%) are 40% of the score.

---

## 3. Tone Rules

**Confident, simple, true.**

- Write like a student pitching to a panel: short sentences, everyday words.
  - ✅ "The pod feels shaking, hears grinding and measures power."
  - ❌ "Multimodal kinematic-acoustic-electrical edge telemetry fusion."
- Be confident about what we **built and measured**. Be clear about what is **next**.
- Never apologise for the washer. ❌ "Because we lacked resources…" ✅ "We started with a washer because it's easy to access and a hard test."
- No number without a source. If we can't point to it in our data or a cited source, it's an **estimate** (and says so) or it doesn't go in.
- One key number per section is better than five.
- Say "machine learning", never bare "AI", for our model.

### Say / Plan / Don't say

| ✅ Say confidently (we have proof) | 🟡 Say as the plan (not done yet) | ❌ Don't say |
|---|---|---|
| We built a working rig that streams live data | Health score / remaining-life prediction ("once we record real faults") | "Zero false alarms", "100% accurate" |
| 13 wash sessions recorded, 9,114 data rows | False-alarm rate on the new firmware ("measuring over the next 20+ cycles") | "TRL 6" (we are TRL 4–5) |
| Vibration up 20×+ from idle to spin | Ringgit energy savings ("our estimate; the pilot will confirm") | "Predicts exactly when it will break" |
| Drum frequency climbs to ~20 Hz (~1,200 rpm), confirmed across all 4 new-firmware washes | Phase badge on the website (wash / rinse / spin; planned once machine state is saved with the data, distinct from the wash-type badge) | "Dust-proof" (IP55 = dust-*protected*) |
| The website labels each wash type, inferred from power | Township map, phone alerts, resident app | "Triples savings" or any multiplier we didn't measure |
| Washer sound 36–90× louder than room noise in high bands | Tests on AC compressor / water pump | Force power back ON when switched off (safety problem on real equipment) |
| Live dashboard you can open now | Machine-learning model on the new-firmware data (needs 3+ cycles first) | "1,400 rpm" as measured (that's the rated max) |
| Shows electricity use live | | "Zero false alarms" as a general claim, "predicts failures", or the test result presented as a real fault |
| A heated wash used about 5× the energy of a cold wash on our rig (measured) | | Energy savings presented as a township or AC saving |
| Leave-one-wash-out test on 8 earlier washes: 0 falsely flagged; a simulated sound fault caught in 7 of 8 (always say "simulated" and "eight earlier washes") | | "4 sensors" or "knows what the machine is doing" (no phase labels are saved yet) |

---

## 4. Approved Facts and Numbers

Use only these. If you need a new number, add it here first **with its source**.

| Fact | Value | Source |
|---|---|---|
| Wash sessions recorded | 13 (as of 21 Oct): 8 healthy older-firmware cycles form the evaluation set; 4 complete firmware-07 cycles (19 Oct 09:11, 20 Oct 07:44, 21 Oct 05:14, 21 Oct 06:31); 1 short older-firmware session (19 Oct 00:22, 167 rows, not evaluated) | `data/real_sessions/`, `ml/models/loco_report.md` |
| Firmware-07 cycles | 4 complete (786, 965, 387, 348 windows; 2,486 total). The evaluated model in `ml/models/loco_report.md` is evaluated on the 8 legacy cycles and has not been retrained on firmware-07 data yet | `data/real_sessions/`, `ml/models/loco_report.md` |
| Machine state (phase labels) | None saved yet: every row across all 4 firmware-07 cycles has `phase = none`, `phase_source = fallback`. Say "planned", never "knows what the machine is doing" | `data/real_sessions/` (the four firmware-07 CSVs) |
| Wash type | Classes inferred from power: Long cold (4 cycles: 16 Oct 08:57, 17 Oct 07:18, 18 Oct 05:16, 19 Oct 09:11), Long hot (1 cycle: 20 Oct 07:44), Quick (2 cycles: 21 Oct 05:14, 21 Oct 06:31), No power data (6 unmetered cycles). Rule: always say "inferred from power"; programme names are not logged | `ml/models/cycle_signature_report.md` |
| Load weight | Not recorded (`load_kg` is blank in `data/session_context.csv` across all cycles until a physical weighed load is entered) | `data/session_context.csv` |
| Energy per wash (measured) | Quick: 0.03–0.04 kWh per wash (peak 302–373 W); Long cold: 0.10–0.11 kWh per wash (peak 401–774 W); Long hot: 0.55 kWh per wash (peak 2,290 W). Heated wash used about 5× the energy of a cold wash. Rule: one household washer, measured by the smart plug; never present as an AC, township or fault saving | `ml/models/cycle_signature_report.md` |
| Evaluation result (nested leave-one-cycle-out) | 0 of 8 healthy cycles falsely flagged (95% upper bound 31%); simulated +100% sound caught in 7 of 8 cycles; added vibration not detected. **Always say it was run on the 8 earlier snapshot-format (5 s snapshot) cycles, not on the 32-feature firmware-07 windows** | `ml/models/loco_report.md` |
| Training-ready rows | 9,114 (as of 21 Oct; was 8,379 before the two 21 Oct quick washes) | `data/pdm_ml_standardized_training_dataset.csv` (`session_source` counts) |
| Window record | 45-column row every 5.024 s, of which 32 are signal features (audio 15, vibration 13, power 4) | `firmware/session_export.py` (`V3_KEY_MAP`). Not the feature dictionary: that is the legacy 31-field contract |
| Vibration sensor | MPU-6050, 200 Hz, ±16 g | `INVARIANTS_DO_NOT_CHANGE.md` §2 |
| Microphone | INMP441, 16 kHz | same |
| Power | Tapo P110 smart plug, 1 Hz | same |
| Controller | ESP32 dual-core (one core sensors, one core Wi-Fi/cloud) | firmware 07 |
| Offline buffer | ~4 min of data kept during Wi-Fi drops | INVARIANTS §2 (outbox 48 windows) |
| Vibration jump idle → spin | over 20× (σ 0.03 → 0.72 m/s²) | `wash_cycle_2026-10-19_0911.csv` |
| Drum frequency in final spin | ≈ 20 Hz (19.9–20.0 Hz ≈ 1,200 rpm), confirmed across all 4 firmware-07 cycles (19.9 Hz on 19 and 20 Oct; 20.0 Hz p90 on 21 Oct 05:14 and 06:31) | `vib_dom_hz` in the four firmware-07 CSVs, `ml/models/cycle_signature_report.md` §3 |
| Local fail-safe (firmware 07) | HTTP on the home network serving the latest feature window (`/window.json`), the last 2.56 s of raw 200 Hz vibration (`/accel.csv`), and a short audio clip (`/clip.wav`) that never goes to the cloud; reachability [UNVERIFIED] | `firmware/07_feature_streamer/07_feature_streamer.ino`, `INVARIANTS_DO_NOT_CHANGE.md` §2 |
| Washer sound vs room noise (spin, 250 Hz–4 kHz bands) | 36–90× louder | same file (audio bands vs washer-off rows) |
| Washer rated max spin | 1,400 rpm | Samsung WW10TP44DSX spec |
| Enclosure and mount | ABS project box 158×90×60 mm (sold as dustproof/waterproof), 3M VHB tape mount. Drilled ports mean no IP claim: say "splash-resistant, untested" | `Hackathon/HARDWARE_BOM_AND_COST_BREAKDOWN.md`, `docs/hardware_guides/hardware_bom_and_setup_guide.md` |
| Sensor node cost (no smart plug) | RM 131.07 net paid (three boards alone: RM 82.88 at list prices) | `Hackathon/HARDWARE_BOM_AND_COST_BREAKDOWN.md` (receipts) |
| Pilot kit cost (with smart plug) | RM 169.68 net paid across 7 Shopee orders (say "about RM 170") | `Hackathon/HARDWARE_BOM_AND_COST_BREAKDOWN.md` |
| Phase conditioning | Implemented in code; the evaluated model is pooled (0% of evaluated windows have phase labels). Describe as planned | `ml/models/loco_report.md` |
| Stage | TRL 4–5 | working prototype on a representative machine |
| Live site | https://washer-pdm.pages.dev | Cloudflare Pages |
| Reactive maintenance share (external, problem framing) | Over 55% of an average facility's maintenance resources and activities are still reactive ("run it till it breaks") | US DOE FEMP, *O&M Best Practices Guide*, Release 2.0 (PNNL-14788, July 2004), §5.2. Added 20 Oct 2026 |
| Predictive maintenance benefit (external, problem/impact framing) | Surveys cited by the guide: predictive maintenance eliminated 70–75% of breakdowns (also 25–30% lower maintenance costs, 35–45% less downtime) | Same guide, §5.4. Added 20 Oct 2026 |
| Malaysian commercial AC energy share (external, problem framing) | Air-conditioning ≈ 57% of energy in Malaysian office buildings | Saidur 2009, *Energy Policy* 37(10):4104–4113, doi:10.1016/j.enpol.2009.04.052 |
| Wear-related fault energy waste (external, problem framing) | Wear-related faults raise building energy use; US faults ≈ 103–500 TWh/yr (citing Roth et al. 2004) | Melgaard et al. 2022, *Energies* 15(12):4366, doi:10.3390/en15124366 |
| O&M energy savings potential (external, impact framing) | 5–20% energy savings from proper O&M (a range from the literature, not our measurement) | US DOE FEMP O&M Best Practices Guide §2.4 |

**Rules for external statistics:** they are figures from published literature (US DOE FEMP guide, Saidur 2009, Melgaard et al. 2022), not Malaysian township measurements by us. Always show the source and year next to them, say "surveys cited by a US Department of Energy guide" or cite the published paper, and never present them as our own result or as what Apex PdM will achieve. Source: https://www.pnnl.gov/main/publications/external/technical_reports/pnnl-14788.pdf

**Estimate example (always labelled as an estimate):**
One 5 kW commercial AC × 10 h/day ≈ 18,250 kWh/yr. A worn part adding 10% ≈ 1,825 kWh ≈ **about RM 900/yr** (estimate) at ~RM 0.50/kWh. A ~RM 170 pod catching one such problem pays back within a few months.

**Not allowed (corrected 2026-10-21):** "under RM 50 in parts" (unvalidated volume target only), "magnetic mount" (mount is VHB tape), "45 features" (use "45-column record, 32 signal features"), "phase-conditioned model works", "IP55/IP65 pod", "UDP broadcast" and "50 Hz vibration" (firmware-05 era; firmware 07 has no UDP and samples at 200 Hz).

**Not allowed until confirmed:** equipment counts for Masjid Elmina / Elmina Lakeside Mall (old drafts said "8 chillers", "11 compressors", which are unverified), CO₂ tonnes, scrap tonnes, "15–35% excess power", "5–10 years longer life".

---

## 5. How to Describe the Machine-Learning Model

Before writing this section, **check the ML code in the repo** so the description matches what's built (features used, model type, how it's validated). Don't invent a model name.

Plain-language template:

> We train the machine-learning model only on normal runs, so it learns what "healthy" looks like for this machine. This is called **unsupervised** learning: it doesn't need examples of broken machines. When a new run looks different from normal, it raises an **anomaly score**.
>
> It uses **feature fusion**: it combines vibration features (how much it shakes, on each axis, and the main shaking frequency), sound features (loudness in different pitch bands) and power use, and, once phase labels are recorded, will compare them **within the same phase** (wash vs rinse vs spin) so a normal fast spin isn't mistaken for a fault. (Today's evaluated model is pooled; say this as the plan.)
>
> We test it fairly by **leaving out one whole wash cycle at a time** and checking whether the model still treats it as normal. That way it's never tested on data it has already seen.

Say **"detect early signs"**, not "predict when it will break". Predicting a failure date needs real fault data, which comes after the pilot.

---

## 6. Hardware Section Template

| Part | What it does | Cost (RM) |
|---|---|---|
| ESP32 dev board | The brain: reads sensors, sends data over Wi-Fi | RM 32.90 |
| MPU-6050 | Feels vibration (3 axes) | RM 21.99 |
| INMP441 microphone | Hears machine sounds | RM 27.99 |
| Tapo P110 smart plug | Measures electricity use | RM 42.90 |
| ABS project box 158×90×60 mm | Houses and protects the electronics from splashes (untested; no IP claim) | RM 16.30 |
| 3M VHB tape (5 m roll) | Rigid vibration coupling to the machine (one roll, many mounts) | RM 20.68 |
| ESP32 screw-terminal board | Vibration-proof wiring | RM 8.46 |
| **Total** | | **RM 169.68** net paid for all 7 orders (the rows above are list prices of the main parts and do not sum to it: they exclude Dupont wires, glands, ferrules and voucher discounts) |

Add one simple flow diagram:

```
Sensors → ESP32 → Wi-Fi / Internet → Cloud database → Live website
                                                    ↘ ML model → Alert
```

Include **1–2 real photos of the rig** (from `hardware/photos/`), with no personal items or addresses visible.

---

## 7. Fitting This Into the Official 2-Page Form

| Form heading | Put in it |
|---|---|
| 1. Title | Title + one-line plain description + live link + stage (TRL 4–5) |
| 2. Problem Statement | Intro hook (township) + Problem |
| 3. Proposed Solution | Solution + 3 sensors (machine state planned) + ML model plan (short) |
| 4. Target Market | Mosques, suraus, kuils, malls, clubhouses, FM contractors, residents |
| 5. Uniqueness | Low cost, 3 sensors together, sees energy waste, easy to fit |
| 6. Prototype & Evidence | Prototype + hardware (short) + photo + testing results + next machines |
| 7. Impact & ROI | Township vision + three ways it saves + labelled estimate |

The 2-page PDF is generated by `docs/proposals/generate_2page_pdf.py`, and **the text lives inside that script**, not the `.md`. Edit both. The page boxes have a fixed height and hide overflow, so "Total Pages: 2" does **not** prove nothing was cut off. **Open the PDF and check the bottom of each page by eye.**

---

## 8. Formatting Rules

- 3–5 short bullets per section; no paragraph longer than 4 lines.
- One bold key number per section.
- Tables for parts and comparisons; one flow diagram; 1–2 real photos.
- No LaTeX formulas or heavy jargon in the body.
- Same numbers everywhere: brief, master proposal, Q&A pack, slides, website. If one changes, change all.

---

## 9. Open Items (fill before final submission)

- [ ] Which document: 2-page form, master proposal or pitch deck?
- [ ] Pick 1–2 rig photos.
- [x] Real parts list with prices: done, `Hackathon/HARDWARE_BOM_AND_COST_BREAKDOWN.md` (receipts).
- [ ] Check the ML code and write the machine-learning section from it.
- [ ] Decide: build a phase badge on the website before submission, or describe it as "coming next".
- [ ] Next test machine confirmed (house water pump / air compressor).
- [ ] Rewrite the master proposal (`PROPOSAL_Apex_PdM_Township_of_Tomorrow.md` + `generate_proposal_pdf.py`) to this guide.

---

## 10. Final Checklist Before Submitting

- [ ] Township appears in the first 2 lines.
- [ ] Every number appears in Section 4 (or is labelled as an estimate).
- [ ] Nothing from the "Don't say" column.
- [ ] Machine-learning model described as "detect early signs", trained on normal data, tested one cycle out at a time.
- [ ] Washer framed as "accessible + hard test", never "lack of resources".
- [ ] Real rig photo included.
- [ ] Live link works.
- [ ] 2-page PDF checked by eye; nothing cut off.
- [ ] Brief, master proposal, Q&A pack and slides all use the same numbers.
