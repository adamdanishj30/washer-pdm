# MSME IDEA HACKATHON / SIME DARBY PROPERTY HACKATHON
## IDEA SUBMISSION PROPOSAL (2-PAGE EXECUTIVE BRIEF)

---

### 1. Title of the Idea
**AcuVibe PdM: Township-Scale Asset Health & Air-Conditioning Predictive Maintenance Platform**  
*Subtitle: Eliminating Parasitic Energy Waste & Premature Landfill Scrap from Scaled Testbed to Commercial Infrastructure*  
**Live Working Prototype & Telemetry Dashboard:** [https://washer-pdm.pages.dev](https://washer-pdm.pages.dev)  
**Track Alignment:** **PLANET** (Energy Optimization & Circular Economy) with **PEOPLE** (Digital Living) synergy.

---

### 2. Problem Statement

* **What is the issue?**  
  Mechanical rotating equipment (commercial central air-conditioning chillers, water pumps, large appliances) operates reactively on "run-to-failure." When consumable wear components (bearings, dampers, mechanical seals) degrade, friction forces modern inverter-driven motors to draw **15% to 35% excess electrical power ($W$)** to sustain speed—undetected by circuit breakers for months. Eventually, unchecked friction causes catastrophic seizure (motor burnout, compressor seizure), transforming an **RM 25–50 component fix** into an **RM 800–RM 1,800+ replacement** for appliances, or **RM 15,000–RM 30,000+** for commercial HVAC chillers.
* **Who is affected?**  
  1. **Township Communal & Commercial Spaces:** Community **mosques, suraus, kuils (temples), clubhouses, and retail shopping malls** that operate 20 to 50+ commercial AC compressors daily. Breakdown leaves congregations and weekend shoppers in unbearable heat.
  2. **Township Facility Management (FM) Teams:** Technicians waste hundreds of hours on manual 1-by-1 physical walk-throughs, unable to detect internal mechanical degradation before catastrophic breakdown occurs.
  3. **Township Residents:** Urban households facing costly appliance replacements, structural vibration noise, and inflated utility bills.
* **Why is it important to solve this problem now?**  
  Rising electricity tariffs (TNB Commercial Tariff B @ RM 0.509/kWh) and national ESG circular economy goals mandate an end to preventable waste. Eliminating unmonitored mechanical friction saves gigawatt-hours across township utility grids, while catching faults early along the **P-F Interval** extends machinery operating lifespan by 5 to 10 years, diverting metric tons of heavy scrap metal and appliance e-waste from landfills.

---

### 3. Proposed Solution

* **How does your solution address the problem?**  
  AcuVibe PdM provides low-cost, non-intrusive edge-IoT sensor pods that clip onto rotating machinery housings. It continuously tracks a **Machine Health Index (0%–100%)** and **Remaining Useful Life (RUL)**, detecting mechanical friction weeks in advance (at Point P) before catastrophic failure occurs (at Point F).
* **What makes it innovative? (4-Modality Synchronous Fusion):**  
  Traditional vibration alarms trigger frequent false alarms during normal high-speed operation. AcuVibe integrates four synchronized physical dimensions:
  1. *Kinematics (MPU-6050 @ 50 Hz):* Tri-axial acceleration ($\pm 16\text{g}$) measuring chassis rocking, unbalance, and damper shock.
  2. *Acoustics (INMP441 @ 16 kHz):* 24-bit digital I2S DMA capturing high-frequency bearing squeal and pump cavitation.
  3. *Electrical Power (Tapo P110 @ 1 Hz):* Active wattage ($W$), voltage, and current measuring motor load and parasitic friction drag.
  4. *Operational Context:* Conditions anomaly detection against machine states, eliminating spin-cycle false alarms.
* **What technology/product is involved?**  
  * **Dual-Core ESP32 Edge Firmware:** Strict FreeRTOS isolation—Core 1 handles real-time sensor DSP; Core 0 manages Wi-Fi, encrypted local KLAP power queries, and Google Firebase RTDB cloud sync.
  * **Automated Force-ON Safety Guard:** Watchdog daemon detects accidental power switch-off within 1,000ms and immediately forces power back ON.
  * **Centralized Township Interface:** Cloud-based facility management dashboard providing automated health triage maps and mobile repair alerts.

---

### 4. Target Market / Beneficiaries

* **Specific Industry or Sector:** Commercial Facility Management (FM), Communal Places of Worship, Retail Real Estate, and Smart Sustainable Townships (e.g., Sime Darby Property's City of Elmina, Bandar Bukit Raja).
* **MSME & Communal Segment:**  
  * **Places of Worship:** Mosques, Suraus, and Kuils (temples) relying on central air-conditioning split units.  
  * **Commercial Centers & Clubhouses:** Community gyms, function halls, and retail malls (e.g., Elmina Lakeside Mall).  
  * **Local Maintenance Contractors (MSMEs):** Local service technicians empowered with automated, predictive repair dispatching rather than reactive crisis calls.
* **Urban/Rural Focus:** High-density master-planned urban townships and commercial property clusters.

---

### 5. Uniqueness and Innovation

* **Ultra-Low Cost (< RM 50 Production BOM):** Existing industrial predictive maintenance systems cost upwards of RM 2,000–RM 5,000 per sensor, limiting them to oil-and-gas refineries. AcuVibe brings industrial-grade prognostics to everyday township assets.
* **Solves the False Alarm Paradox:** By conditioning vibration and sound against ground-truth operational states, AcuVibe prevents false emergency alarms during normal high-speed extractions.
* **Quantifies Parasitic Energy Drag in Ringgit:** Rather than reporting raw acceleration, AcuVibe correlates vibration harmonics with active wattage to compute excess power loss ($W_{\text{excess}}$) and monthly electricity bill inflation.
* **Zero-Intrusive 5-Minute Retrofit:** Requires zero rewiring or warranty-voiding alterations; mounts with 3M VHB viscoelastic acrylic coupling and smart inline metering.

---

### 6. Prototype Feasibility, Empirical Evidence & The Expansion Plan

* **The Accessible Home Testbed (Proven Foundation):**  
  Because commercial 50 kW rooftop chillers are costly and inaccessible for early student bench testing, we built and validated our prototype on an accessible, highly dynamic residential front-load washing machine. Mechanically, a 1,400 RPM washing machine is one of the most violent rotating electromechanical environments in existence. By proving clean, synchronized dual-core telemetry here, we successfully de-risked the hardest technical hurdle.
* **Empirical Datasets in Hand:**  
  * Over **3,980 standardized operational telemetry records** captured across 5 genuine full wash cycles.  
  * Documented 31-feature machine learning prognostic contract (`pdm_feature_dictionary.json`).
* **Live Global Web Dashboard:** Fully deployed and verifiable worldwide at [**https://washer-pdm.pages.dev**](https://washer-pdm.pages.dev).
* **The Bigger Expandable Plan:**  
  Because rotating electromechanical failure physics ($\text{Vibration} \rightarrow \text{Acoustic Friction} \rightarrow \text{Electrical Drag} \rightarrow \text{Seizure}$) is universal, our roadmap mass-produces these sub-RM 50 pods into clip-on hardware. We will deploy them across **20 to 50 commercial AC compressors in township mosques, kuils, community halls, and shopping malls**, training a specialized compressor ML model and providing facility managers with a centralized asset health dashboard.

---

### 7. Expected Impact, Scalability & Commercial ROI

* **Commercial Cluster Economics (20 Commercial AC Units):**  
  * **Electricity Saved:** Eliminating 15% parasitic friction saves **~87,600 kWh annually** (**> RM 44,500/year** under TNB Commercial Tariff B).  
  * **Capital Payback Period:** **Under 1 month** against a sensor pod deployment cost of ~RM 3,400 (20 pods &times; RM 170 pilot kit).  
  * **Catastrophic Replacement Avoided:** Saves RM 15,000–RM 30,000 per prevented commercial compressor burnout.
* **Township Quality of Life & ESG Impact:**  
  * **Zero Community Disruption:** Guarantees uninterrupted climate comfort during Friday prayers, temple festivals, and weekend retail crowds.  
  * **Circular Economy:** Extends equipment operating lifespan by **5 to 10 years**, preventing **25 to 40 metric tons of compressor scrap metal** and **66 metric tons of $\text{CO}_2$ emissions** per commercial cluster annually.
