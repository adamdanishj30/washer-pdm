# MSME IDEA HACKATHON / SIME DARBY PROPERTY HACKATHON
## IDEA SUBMISSION PROPOSAL (2-PAGE EXECUTIVE BRIEF)

---

### 1. Title of the Idea
**Apex PdM: Township-Scale Asset Health & Air-Conditioning Predictive Maintenance Platform**  
*A low-cost sensor pod that feels, hears and measures machines, so township teams fix small problems before they become big breakdowns.*  
**Live Working Prototype & Dashboard:** [https://washer-pdm.pages.dev](https://washer-pdm.pages.dev)  
**Stage:** Working prototype (TRL 4–5) with live data online  
**Track Alignment:** **PLANET: 02 Circular Economy** (with Energy Efficiency in the narrative) with **PEOPLE** (Digital Living) synergy.

| 10 | 4 | 20×+ | ~RM 170 |
|---|---|---|---|
| Real wash sessions archived | Sensors working in sync | Vibration jump, idle → spin | Pilot kit cost, off the shelf |

---

### 2. Problem Statement

* **What is the issue?**  
  Air-conditioners, chillers, water pumps and big appliances are usually fixed only **after they break**. Before that, a worn bearing, damper or seal slowly makes the machine shake more, sound different and **work harder, using more electricity**. Nobody notices until the machine stops. By then, a **small part worth tens of ringgit** has turned into a **new motor or compressor worth thousands**, plus days without cooling.
* **Who is affected?**  
  1. **Township Communal & Commercial Spaces:** Community **mosques, suraus, kuils (temples), clubhouses and shopping malls** running many AC units every day. A sudden breakdown leaves congregations and shoppers in the heat.
  2. **Township Facility Management (FM) Teams:** Technicians check machines one by one, by hand, and still cannot see wear happening inside until something fails.
  3. **Township Residents:** Households facing surprise repair bills, noisy machines and higher electricity bills.
* **Why is it important to solve this problem now?**  
  Electricity keeps getting more expensive, and townships are aiming for lower emissions and less waste. A machine that is wearing out uses more power and gets thrown away sooner. Catching the problem early means **a cheap repair instead of a full replacement**, lower bills and less scrap going to landfill.

---

### 3. Proposed Solution

* **How does your solution address the problem?**  
  Apex PdM is a small sensor pod that sits on the outside of a machine. It records **vibration, sound and power together**, learns what *normal* looks like for that machine, and gives an **anomaly score and a simple verdict for every run** (normal / check it). A full health score and remaining-life estimate are our next step, once we have recorded real faults.
* **What makes it innovative? (4 sensors working together)**  
  1. *Vibration (MPU-6050 @ 200 Hz):* 3-axis sensor that feels shaking, unbalance and loose or worn parts.
  2. *Sound (INMP441 @ 16 kHz):* Digital microphone that hears grinding, squealing and rattling.
  3. *Power (Tapo P110 @ 1 Hz):* Smart plug that measures how hard the motor is working, in watts.
  4. *Machine State:* Context from SmartThings (wash, rinse, spin); comparing vibration and sound within the same phase is planned.
* **What technology / product is involved?**  
  * **Dual-Core ESP32:** One core reads the sensors in real time, the other handles Wi-Fi and cloud upload, so neither slows the other down. Every 5 seconds the pod turns raw signals into **32 signal features**.
  * **Keeps Logging Through Wi-Fi Drops:** The pod stores about 4 minutes of data and sends it once the connection is back.
  * **Live Web Dashboard:** Anyone can watch the rig live today. A township map and phone alerts are the next build.

---

### 4. Target Market / Beneficiaries

* **Specific Industry or Sector:** Commercial Facility Management (FM), places of worship, retail property and smart sustainable townships (e.g. Sime Darby Property's City of Elmina, Bandar Bukit Raja).
* **MSME & Communal Segment:**  
  * **Places of Worship:** Mosques, suraus and kuils (temples) that rely on air-conditioning.  
  * **Commercial Centres & Clubhouses:** Community gyms, function halls and malls (e.g. Elmina Lakeside Mall).  
  * **Local Maintenance Contractors (MSMEs):** Technicians who get told which machine needs a look, instead of rushing to emergency calls.
* **Urban/Rural Focus:** Master-planned urban townships and commercial property clusters.

---

### 5. Uniqueness and Innovation

* **Low Cost:** Industrial vibration sensors cost thousands of ringgit each, so only big factories use them. We spent **about RM 131 in parts for the sensor node** (about RM 170 for a full pilot kit with smart plug) — cheap enough for every AC unit in a mosque or mall.
* **Fewer False Alarms by Design:** One sensor alone gets fooled — a normal fast spin looks like a fault. We check vibration, sound and power **together**, and plan to check against what the machine is doing, before raising an alert.
* **Sees Energy Waste Too:** Because we measure power directly, the system can compare each run's power use against that machine's own normal and show when it starts working harder.
* **Easy to Fit:** Mounts on the outside and plugs in — no rewiring and nothing opened up.

---

### 6. Prototype Feasibility, Evidence & Expansion Plan

* **Why we tested on a washing machine:**  
  A front-load washer is one of the toughest machines to monitor. It shakes hard, the load moves around, water sloshes, and the speed keeps changing from slow tumbling to a fast spin. If our pod gets clean, clear data here, a steady-running AC compressor or pump is an easier job.
* **What we measured** (latest 66-minute cycle):  
  * Vibration jumped **over 20×** from idle to spin.  
  * The main vibration frequency climbed smoothly to **19.9 Hz (about 1,200 rpm)** as the drum sped up.  
  * The washer's sound in the higher bands was **36–90× louder** than the room's background noise, even with a compressor and water pump running nearby.
* **Data in hand:** **10 real wash sessions archived** and **7,414 rows** of training-ready data, with 32 signal features per 5-second window (firmware-07 window record).
* **Model validation:** Leave-one-cycle-out test on 8 healthy cycles: 0 falsely flagged (95% upper bound 31%); a simulated doubling of sound was caught in 7 of 8.
* **Hardware:** ESP32 dual-core + MPU-6050 (200 Hz) + INMP441 mic (16 kHz) + Tapo P110 smart plug (1 Hz).
* **Live dashboard:** [https://washer-pdm.pages.dev](https://washer-pdm.pages.dev).
* **From washer to township:**  
  Fans, pumps and compressors wear out the same way — worn parts cause more shaking, then more noise, then more power use, then a breakdown. The same pod and software can move onto **AC units and pumps in township mosques, kuils, community halls and malls**.
* **Next steps:** record 20+ more cycles to measure our false-alarm rate, then pilot on real township equipment.

---

### 7. Expected Impact, Scalability & Commercial ROI

* **Example (our estimate, to be confirmed in the pilot):**  
  * One 5 kW commercial AC running 10 hours a day uses about 18,250 kWh a year. If a worn part makes it use just **10% more**, that is ~1,825 kWh — **about RM 900 a year** at ~RM 0.50/kWh.  
  * A pilot kit costs about **RM 170**, so catching one problem like this **pays for the pod within a few months**.  
  * Catching a failing part early can also **avoid replacing a whole compressor**, which costs thousands of ringgit.
* **Township Quality of Life & ESG Impact:**  
  * **Less Disruption:** Repairs can be planned ahead, so cooling stays on during Friday prayers, festivals and busy weekends.  
  * **Less Waste & Lower Emissions:** Fixing one small part instead of replacing a whole unit keeps machines running longer, cuts scrap metal and saves electricity.
