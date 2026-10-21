# Hackathon Info & Pitch Summary

> **Context:** Hackathon facts below come from the official announcements and portal briefs for the **Sime Darby Property University Hackathon ("Township of Tomorrow")** with **Kolaxus Innovation Platform**. Event facts: `Hackathon/SDP_HACKATHON_BRIEFING_SUMMARY.md` is the official source and takes precedence. Project numbers follow `docs/proposals/PROPOSAL_WRITING_GUIDE.md` §4 (single source, synced 2026-10-20). If either changes, update this file too.

---

## 1. Quick Facts Sheet

| Parameter | Official Detail |
| :--- | :--- |
| **Competition Name** | Sime Darby Property University Hackathon 2026 ("Township of Tomorrow") |
| **Organizers** | Sime Darby Property Berhad in partnership with Kolaxus Innovation Platform |
| **Overarching Theme** | *"How might we reimagine the Township of Tomorrow where people, businesses and nature thrive together through innovation, technology and sustainable living?"* |
| **Core Tracks** | **1. Planet** (Sustainability, circular economy, resource efficiency, emissions reduction)<br>**2. People** (Healthier, safer, friction-free digital living, community connectivity) |
| **Total Prize Pool** | **RM 14,000** (Champion: RM 6,000; 1st Runner-Up: RM 3,000; 2nd Runner-Up: RM 1,500; 4th–10th: RM 500 each) + internship priority & PoC incubation support |
| **Key Milestones** | • Registration closes 21 Oct; submission 23 Oct, 11:59 PM<br>• Top 10 announced 28 Oct; mentoring sprint 2–6 Nov<br>• Top 10 physical pitch 14 Nov (10 min + 5 min Q&A)<br>• Final and award ceremony 3 Dec (Elmina) |
| **Evaluation Framework** | 1. **Impact & Sustainability (25%)**<br>2. **Innovation & Differentiation (20%)**<br>3. **Feasibility & Deliverability (20%)**<br>4. **Strategic Fit & Theme Relevance (15%)**<br>5. **Commercial Viability & Value Multiplication (10%)**<br>6. **Team, Pitch & Empirical Evidence (10%)** |

---

## 2. Our Story in One Picture

```
┌──────────────────────────────────────────┬─────────────────────────────────────────┐
│ WHAT WE BUILT (working today)            │ WHERE IT GOES NEXT (township)           │
│ • Sensor pod on a front-load washer      │ • AC units, chillers and pumps in       │
│   (rated 1,400 rpm; measured spin        │   mosques, malls and clubhouses         │
│   ~1,200 rpm)                            │ • One FM dashboard for all machines     │
│ • 3 sensors: vibration, sound, power     │ • Alerts in a resident app (planned)    │
│   (machine state planned)                │                                         │
│ • 11 wash sessions, 8,379 data rows      │                                         │
│ • Live dashboard: washer-pdm.pages.dev   │                                         │
└──────────────────────────────────────────┴─────────────────────────────────────────┘
```

### Why the washer story works
* **It's a hard test.** A washer shakes hard, the load moves, water sloshes and the speed changes all the time. If the pod gives clean data here, a steady AC compressor or pump is an easier job.
* **Machines wear out the same way.** Worn parts cause more shaking, then more noise, then more power use, then a breakdown. That's true for a washer drum, an AC fan or a water pump, so the same pod and software can move across.

---

## 3. Rubric → Our Evidence

| Rubric Axis (Weight) | What Judges Look For | What We Say | Proof We Can Show |
| :--- | :--- | :--- | :--- |
| **1. Impact & Sustainability (25%)** | Energy savings, less waste, longer machine life. | Catch wear early → cheap part swap instead of a new compressor, lower bills, less scrap. Example estimate: one 5 kW AC using 10% extra power wastes ~RM 900/yr. | Our power data (Tapo P110, 1 Hz) on every cycle. Savings are an **estimate** until the pilot. |
| **2. Innovation & Differentiation (20%)** | Something new, not just another sensor. | 3 sensors checked together (vibration 200 Hz, sound 16 kHz, power 1 Hz). Machine-state context from SmartThings is planned (no phase labels are saved yet); phase conditioning, so a normal fast spin isn't mistaken for a fault, is planned; today's evaluated model is pooled. | 45-column window record with 32 signal features (`firmware/session_export.py`); live dashboard. |
| **3. Feasibility & Deliverability (20%)** | Can it really be built and fitted? | It's already built and running. Pilot kit about RM 170 net paid (node about RM 131 + RM 39 smart plug). Fits outside, no rewiring. | Working rig, firmware in `firmware/`, 11 wash sessions in `data/real_sessions/`. |
| **4. Strategic Fit & Relevance (15%)** | Fits Sime Darby Property townships. | Targets AC units and pumps in places like Masjid Elmina, Elmina Lakeside Mall and clubhouses. | Exact asset counts **to be confirmed with SDP / FM team**. Don't quote numbers we haven't checked. |
| **5. Commercial Viability (10%)** | Business model and payback. | FM dashboard subscription (B2B) + resident alerts (B2C). A RM 170 pod pays back within months on one caught fault. | Worked example in Section 4, Q4. |
| **6. Pitch & Evidence (10%)** | Real prototype, real data. | Real rig, real data, live link, first model test. | Vibration up **over 20×** idle → spin; main frequency climbs to **19.9 Hz (~1,200 rpm)** in both new-firmware washes; washer sound **36–90×** louder than room noise in the high bands; leave-one-wash-out test on 8 earlier washes: 0 falsely flagged (95% upper bound 31%), simulated sound fault caught in 7 of 8. |

---

## 4. Submission Q&A Pack (copy-paste ready)

### Q1: Problem Statement (≤160 words)
Townships depend on machines that spin: air-conditioners and chillers in mosques and malls, water pumps, and appliances at home. Most of them are only fixed after they break. Before a breakdown, a worn bearing, damper or seal slowly makes the machine shake more, sound different and work harder, using more electricity. No one notices, because technicians check machines one by one by hand and cannot see wear happening inside. When the machine finally fails, a small part worth tens of ringgit becomes a new motor or compressor worth thousands. The community loses cooling during prayers or busy weekends, the electricity bill was higher for months, and a whole unit ends up as scrap. Townships need a cheap way to watch every machine all the time and catch problems while they are still small and cheap to fix.

### Q2: Proposed Solution & Innovation (≤180 words)
Apex PdM is a small, low-cost sensor pod (about RM 131 in parts, RM 170 with the smart plug) that fits on the outside of a machine with no rewiring. It records three things at the same time:
1. **Vibration** (MPU-6050, 200 Hz): shaking, unbalance and loose or worn parts.
2. **Sound** (INMP441 microphone, 16 kHz): grinding, squealing and rattling.
3. **Power** (Tapo P110 smart plug, 1 Hz): how hard the motor is working.
Next, it will also save the machine state (wash, rinse, spin), so a normal fast spin is compared only with other spins.

A dual-core ESP32 does the work: one core reads the sensors in real time, the other uploads to the cloud. Every 5 seconds it turns raw signals into 32 signal features. Our model learns what normal looks like for each machine and gives an anomaly score and a simple verdict for every run. Everything is visible live at washer-pdm.pages.dev. What makes it new: three sensors checked together, at a price that works for every AC unit, not just factories.

### Q3: Implementation Feasibility & Evidence (≤180 words)
We built a working prototype on a front-load washing machine, one of the hardest machines to monitor: it shakes, sloshes and changes speed constantly. If the pod gives clean data here, a steady AC compressor or pump is an easier job.

What we have today:
* **11 wash sessions** recorded and **8,379 rows** of training-ready data (32 signal features per 5-second window).
* **Clear signals:** vibration rose over 20× from idle to spin, and the main vibration frequency climbed to 19.9 Hz (about 1,200 rpm) in both washes on our latest firmware.
* **First model test:** leaving one of 8 earlier washes out at a time, none was falsely flagged, and a simulated sound fault was caught in 7 of 8.
* **Works in a noisy room:** the washer's sound was 36–90× louder than the background noise in the higher bands, even with a compressor and water pump running nearby.
* **Live public dashboard** at washer-pdm.pages.dev.
* **Pilot kit cost** of about RM 170 including the smart plug.

Next: record 20+ more cycles to measure our false-alarm rate, then pilot on real township equipment.

### Q4: Target Market & Scaling Roadmap (≤175 words)
1. **Facility management (B2B):** AC units, chillers and pumps in places like Masjid Elmina, Elmina Lakeside Mall and community clubhouses. One dashboard shows which machines look abnormal, so technicians go only where they are needed.
2. **Residents (B2C):** a simple alert in a resident app, for example: *"Your washer is shaking more than its normal. Book a check before it gets worse."*

**Roadmap:**
* **Months 1–3:** finish 20+ test cycles and measure our false-alarm rate, then pilot pods on a small set of communal assets in City of Elmina.
* **Months 4–6:** connect alerts to the FM team's repair tickets and the resident app.
* **Months 7–12:** grow to more buildings and offer pods as an optional add-on for new homes.

**Why it pays:** for one 5 kW AC running 10 hours a day, a worn part that adds just 10% to its power use costs about RM 900 a year in electricity. A RM 170 pod that catches it pays for itself within a few months, before counting the cost of a compressor that never had to be replaced.

---

## 5. Pitch Q&A Cheat Sheet (for the live 5-minute pitch)

**Say confidently (we have the data):**
* "11 wash sessions, 8,379 rows of data, live dashboard you can open right now."
* "Vibration goes up over 20× from idle to spin, and we can see the drum speed up to about 1,200 rpm in the vibration frequency."
* "Our mic picks out the washer clearly even with a compressor and pump running in the same room."
* "Three sensors together, about RM 170 for a full kit."
* "We tested the model fairly: hide one of 8 earlier washes, learn from the rest. None was falsely flagged, and a simulated sound fault was caught in 7 of 8. It's a small sample, so we say so."

**Say as the plan (not done yet):**
* Health score and remaining-life prediction → "once we have recorded real faults."
* False-alarm rate → "we're measuring it over the next 20+ cycles."
* Energy savings in ringgit → "our estimate; the pilot will confirm it."
* Township map, phone alerts, resident app → "next build."

**If a judge asks "why a washing machine?"**
"Because it's a hard test. It shakes, sloshes and changes speed all the time. If we get clean data there, a steady AC compressor is easier. And all these machines wear out the same way: more shaking, more noise, more power, then a breakdown."

**If a judge asks "have you caught a real fault?"**
"Not yet on a real failing machine. That's exactly what the pilot is for. What we've proven is that the pod captures clean, clear signals in a hard environment, and in a fair test on 8 earlier washes the model flagged none of the healthy ones and caught a simulated sound fault in 7 of 8."

**If a judge asks "did it catch extra vibration too?"**
"Not in that test. The earlier washes were recorded as 5-second snapshots, which can't show fast vibration detail. Our new firmware measures vibration 200 times a second and works out the features on the chip, so testing that is the next step."

**If a judge asks "why do two healthy washes look different?"**
"Healthy doesn't mean identical. One wash used the water heater and the other didn't, so power and spin strength differ; the programme and load weren't logged, which we now fix. That's why the model learns normal per machine and, next, per programme."

**Don't say:**
* "Zero false alarms" as a general claim, or "100% accurate". Our test is 0 of 8 earlier washes, a small sample (95% upper bound 31%).
* "Four sensors" or that it "knows what the machine is doing". Machine state is planned; no phase labels are saved yet.
* "TRL 6". We're TRL 4–5: a working prototype on a representative machine.
* "Under RM 50 in parts" (node is about RM 131, kit about RM 170; sub-RM 50 is an unvalidated volume target) or "magnetic mount" (the mount is VHB tape).
* "45 features" (it is a 45-column record with 32 signal features).
* That the deployed model is phase-conditioned (not yet: phase labels were absent in the evaluated cycles).
* That the system forces power back on when someone switches it off. On real equipment that's a safety problem (technicians need machines to stay off while they repair them).
