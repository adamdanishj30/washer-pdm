import os
import subprocess
import re
import base64

def get_base64_image(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            ext = os.path.splitext(path)[1].lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            return f"data:image/{ext};base64," + base64.b64encode(f.read()).decode('utf-8')
    return None

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "proposal_2page_presentation.html")
    pdf_path = os.path.join(base_dir, "PROPOSAL_2PAGE_AcuVibe_PdM_Township_of_Tomorrow.pdf")

    # Load images if available
    img_layout = get_base64_image(os.path.join(base_dir, "washer_electronics_layout_diagram.jpg"))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AcuVibe PdM - 2-Page Executive Proposal</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

  @page {{
    size: A4;
    margin: 8mm 11mm 8mm 11mm;
  }}

  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  body {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.36;
    font-size: 8pt;
    margin: 0;
    padding: 0;
  }}

  .page-container {{
    height: 279mm;
    max-height: 279mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
    position: relative;
  }}

  .page-break {{
    page-break-before: always;
  }}

  /* Header Bar */
  .doc-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #0f172a;
    padding-bottom: 4px;
    margin-bottom: 6px;
  }}

  .header-tag {{
    font-size: 7pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #0369a1;
  }}

  .header-track {{
    font-size: 6.8pt;
    font-weight: 700;
    background: #dcfce7;
    color: #166534;
    padding: 2px 7px;
    border-radius: 12px;
    border: 1px solid #86efac;
    text-transform: uppercase;
  }}

  /* Section Styling */
  .section {{
    margin-bottom: 6px;
  }}

  .section-title {{
    font-size: 8.8pt;
    font-weight: 800;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-left: 3px solid #0284c7;
    padding-left: 6px;
    margin: 4px 0 3px 0;
    background: #f8fafc;
    padding-top: 1px;
    padding-bottom: 1px;
    border-radius: 0 4px 4px 0;
  }}

  .title-hero {{
    font-size: 13.5pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.15;
    margin: 2px 0;
  }}

  .subtitle-hero {{
    font-size: 8.2pt;
    font-weight: 600;
    color: #0284c7;
    margin-bottom: 4px;
  }}

  .live-bar {{
    display: inline-block;
    background: #0f172a;
    color: #ffffff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 7.2pt;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 5px;
  }}
  .live-bar span {{ color: #38bdf8; font-weight: 700; }}

  p {{
    margin: 0 0 4px 0;
    text-align: justify;
  }}

  ul {{
    margin: 2px 0 4px 14px;
    padding: 0;
  }}

  li {{
    margin-bottom: 2px;
  }}

  strong {{
    color: #0f172a;
  }}

  /* Callout Highlights */
  .callout {{
    border-left: 3px solid #059669;
    background: #f0fdf4;
    padding: 4px 8px;
    margin: 4px 0;
    border-radius: 0 4px 4px 0;
    font-size: 7.6pt;
    line-height: 1.3;
  }}

  .callout-amber {{
    border-left: 3px solid #d97706;
    background: #fffbeb;
    padding: 4px 8px;
    margin: 4px 0;
    border-radius: 0 4px 4px 0;
    font-size: 7.6pt;
    line-height: 1.3;
  }}

  /* Metric Grid */
  .metrics-strip {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin: 4px 0 6px 0;
  }}

  .metric-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 4px 6px;
    text-align: center;
  }}

  .metric-card .num {{
    font-size: 11pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.1;
  }}

  .metric-card .lbl {{
    font-size: 6.2pt;
    font-weight: 700;
    color: #059669;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}

  /* 2-Column Layout for Modalities */
  .two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }}

  .modality-box {{
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 4px 6px;
    margin-bottom: 3px;
  }}

  .modality-box strong {{
    color: #0284c7;
    font-size: 7.6pt;
  }}

  /* Image banner */
  .image-row {{
    display: flex;
    gap: 8px;
    align-items: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px 6px;
    margin: 4px 0;
  }}

  .image-row img {{
    height: 38mm;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
  }}

  .image-desc {{
    font-size: 7pt;
    color: #334155;
    line-height: 1.3;
  }}

  /* Footer */
  .doc-footer {{
    border-top: 1px solid #cbd5e1;
    padding-top: 3px;
    display: flex;
    justify-content: space-between;
    font-size: 6.8pt;
    color: #64748b;
  }}

</style>
</head>
<body>

<!-- ================= PAGE 1 ================= -->
<div class="page-container">
  <div>
    <!-- Document Header -->
    <div class="doc-header">
      <span class="header-tag">MSME IDEA HACKATHON 5.0 / SIME DARBY PROPERTY HACKATHON &bull; IDEA SUBMISSION BRIEF</span>
      <div>
        <span class="header-track">Track: PLANET (Circular Energy)</span>
        <span class="header-track" style="background:#e0f2fe; color:#0369a1; border-color:#7dd3fc; margin-left:3px;">Synergy: PEOPLE (Digital Living)</span>
      </div>
    </div>

    <!-- Section 1: Title -->
    <div class="section" style="margin-bottom: 4px;">
      <div style="font-size:7.5pt; font-weight:800; color:#64748b; text-transform:uppercase;">1. Title of the Idea</div>
      <div class="title-hero">AcuVibe PdM: Township-Scale Asset Health &amp; Air-Conditioning Predictive Maintenance Platform</div>
      <div class="subtitle-hero">Eliminating Parasitic Energy Waste &amp; Premature Landfill Scrap from Scaled Testbed to Commercial Infrastructure</div>
      <div>
        <span class="live-bar">LIVE WORKING RIG: <span>https://washer-pdm.pages.dev</span></span>
        <span style="font-size:7pt; color:#64748b; margin-left:6px;"><strong>TRL Level:</strong> TRL 5/6 (Functional Hardware Rig &amp; Live Cloud)</span>
      </div>
    </div>

    <!-- Metric Strip -->
    <div class="metrics-strip">
      <div class="metric-card">
        <div class="num">15%–35%</div>
        <div class="lbl">Parasitic Friction Cut</div>
      </div>
      <div class="metric-card">
        <div class="num">&lt; 1 Month</div>
        <div class="lbl">Commercial Payback</div>
      </div>
      <div class="metric-card">
        <div class="num">+5–10 Yrs</div>
        <div class="lbl">Lifespan Extension</div>
      </div>
      <div class="metric-card">
        <div class="num">&lt; RM 50</div>
        <div class="lbl">Edge Pod Cost</div>
      </div>
    </div>

    <!-- Section 2: Problem Statement -->
    <div class="section">
      <div class="section-title">2. Problem Statement</div>
      <p><strong>What is the issue?</strong> Mechanical rotating equipment (commercial central air-conditioning chillers, water pumps, large appliances) is managed reactively through "run-to-failure." When consumable wear parts (bearings, dampers, mechanical seals) degrade, internal friction forces inverter motors to draw <strong>15% to 35% excess electrical power ($W$)</strong> to maintain operational speed—undetected by circuit breakers for months. Eventually, unchecked friction causes catastrophic seizure (motor burnout, compressor seizure), turning an <strong>RM 25–50 component fix</strong> into an <strong>RM 800–RM 1,800+ replacement</strong> for appliances, or <strong>RM 15,000–RM 30,000+</strong> for commercial HVAC chillers.</p>
      
      <p><strong>Who is affected?</strong></p>
      <ul>
        <li><strong>Township Communal &amp; Commercial Spaces:</strong> Community <strong>mosques, suraus, kuils (temples), clubhouses, and retail shopping malls</strong> operating 20 to 50+ commercial AC compressors daily. Sudden breakdown leaves congregations and shoppers in unbearable tropical heat.</li>
        <li><strong>Township Facility Management (FM) Teams:</strong> Technicians waste hundreds of hours on manual 1-by-1 physical walk-throughs, unable to detect internal mechanical degradation before catastrophic breakdown occurs.</li>
        <li><strong>Township Residents:</strong> Urban households facing expensive appliance repairs, structural noise, and inflated utility bills.</li>
      </ul>

      <p><strong>Why is it important to solve this problem now?</strong> Rising commercial electricity tariffs (TNB Tariff B @ RM 0.509/kWh) and national ESG circular economy mandates demand an end to preventable waste. Eliminating unmonitored mechanical friction saves gigawatt-hours across township utility grids, while intervening early at <strong>Point P on the P-F Interval</strong> extends machinery lifespan by 5 to 10 years, diverting metric tons of heavy scrap metal and appliance e-waste from landfills.</p>
    </div>

    <!-- Section 3: Proposed Solution -->
    <div class="section">
      <div class="section-title">3. Proposed Solution</div>
      <p><strong>How does your solution address the problem?</strong> AcuVibe PdM provides low-cost, non-intrusive edge-IoT sensor pods that clip onto rotating machinery housings. It continuously tracks a <strong>Machine Health Index (0%–100%)</strong> and <strong>Remaining Useful Life (RUL)</strong>, detecting mechanical friction weeks in advance (Point P) before catastrophic failure (Point F).</p>

      <div class="two-col" style="margin-top:3px;">
        <div class="modality-box">
          <strong>1. Kinematics (MPU-6050 @ 50 Hz):</strong> Tri-axial digital acceleration (&plusmn;16g) capturing structural unbalance, rocking, and damper fatigue.
        </div>
        <div class="modality-box">
          <strong>2. Acoustics (INMP441 @ 16 kHz):</strong> 24-bit digital I2S DMA sound pressure detecting high-frequency bearing squeal and pump cavitation.
        </div>
        <div class="modality-box">
          <strong>3. Electrical Power (Tapo P110 @ 1 Hz):</strong> Active wattage ($W$), voltage, current, and parasitic motor drag.
        </div>
        <div class="modality-box">
          <strong>4. Operational Context:</strong> Conditions anomaly detection against machine states, eliminating spin false alarms.
        </div>
      </div>

      <p style="margin-top:4px;"><strong>What technology / product is involved?</strong></p>
      <ul>
        <li><strong>Dual-Core ESP32 Edge Firmware:</strong> FreeRTOS task affinity—Core 1 executes real-time sensor DSP; Core 0 handles Wi-Fi, encrypted local KLAP power queries, and Google Firebase RTDB cloud streaming.</li>
        <li><strong>Automated Force-ON Safety Guard:</strong> Watchdog daemon detects accidental power switch-off within 1,000ms and immediately forces power back ON.</li>
        <li><strong>Centralized Township Interface:</strong> Cloud-based facility management dashboard providing automated health triage maps and mobile repair alerts.</li>
      </ul>
    </div>
  </div>

  <!-- Page 1 Footer -->
  <div class="doc-footer">
    <span>AcuVibe PdM &bull; Sime Darby Property "Township of Tomorrow" Hackathon</span>
    <span>Page 1 of 2</span>
  </div>
</div>

<div class="page-break"></div>

<!-- ================= PAGE 2 ================= -->
<div class="page-container">
  <div>
    <!-- Document Header -->
    <div class="doc-header">
      <span class="header-tag">MSME IDEA HACKATHON 5.0 / SIME DARBY PROPERTY HACKATHON &bull; IDEA SUBMISSION BRIEF</span>
      <div>
        <span class="header-track">Target Pilot: City of Elmina</span>
        <span class="header-track" style="background:#f1f5f9; color:#334155; border-color:#cbd5e1; margin-left:3px;">Hardware BOM &lt; RM 50</span>
      </div>
    </div>

    <!-- Section 4: Target Market / Beneficiaries -->
    <div class="section">
      <div class="section-title">4. Target Market / Beneficiaries</div>
      <p><strong>Specific Industry or Sector:</strong> Commercial Facility Management (FM), Communal Places of Worship, Retail Real Estate, and Smart Sustainable Townships (e.g., Sime Darby Property's City of Elmina, Bandar Bukit Raja).</p>
      <ul>
        <li><strong>Communal Places of Worship:</strong> Mosques, Suraus, and Kuils (temples) relying on central air-conditioning split units.</li>
        <li><strong>Commercial Centers &amp; Clubhouses:</strong> Community gyms, function halls, and retail malls (e.g., Elmina Lakeside Mall).</li>
        <li><strong>Local Maintenance Contractors (MSMEs):</strong> Service technicians empowered with automated, predictive repair dispatching rather than reactive emergency calls.</li>
      </ul>
      <p><strong>Urban/Rural Focus:</strong> High-density master-planned urban townships and commercial property clusters.</p>
    </div>

    <!-- Section 5: Uniqueness and Innovation -->
    <div class="section">
      <div class="section-title">5. Uniqueness and Innovation</div>
      <ul>
        <li><strong>Ultra-Low Cost (&lt; RM 50 Production BOM):</strong> Industrial predictive systems cost RM 2,000–RM 5,000 per sensor. AcuVibe brings industrial-grade prognostics to everyday township communal infrastructure at 1/40th the cost.</li>
        <li><strong>Solves the False Alarm Paradox:</strong> By conditioning vibration and sound against ground-truth operational states, AcuVibe prevents false emergency alarms during normal high-speed extractions.</li>
        <li><strong>Quantifies Parasitic Energy Drag in Ringgit:</strong> Correlates vibration harmonics with active wattage to compute excess power loss ($W_{{excess}}$) and monthly electricity bill inflation.</li>
        <li><strong>Zero-Intrusive 5-Minute Retrofit:</strong> Mounts externally with 3M VHB viscoelastic acrylic coupling and smart inline metering—zero rewiring or warranty-voiding alterations.</li>
      </ul>
    </div>

    <!-- Section 6: Prototype Status & Expansion Plan -->
    <div class="section">
      <div class="section-title">6. Prototype Feasibility, Empirical Evidence &amp; The Expansion Plan</div>
      <p><strong>The Accessible Home Testbed (Proven Foundation):</strong> Because commercial 50 kW rooftop chillers are costly and inaccessible for early student bench testing, we built and validated our prototype on an accessible, highly dynamic residential front-load washing machine. Mechanically, a 1,400 RPM washing machine is one of the most violent rotating electromechanical environments in existence. By proving clean, synchronized dual-core telemetry here, we successfully de-risked the hardest technical hurdle.</p>

      <!-- Embedded Visual Proof Banner -->
      <div class="image-row">
        {f'<img src="{img_layout}" alt="Hardware Layout">' if img_layout else '<div style="width:70px; height:70px; background:#e2e8f0; display:flex; align-items:center; justify-content:center; font-size:6pt;">Rig Photo</div>'}
        <div class="image-desc">
          <strong>Figure 1: Field-Deployed Multimodal Edge Pod &amp; Live Cloud Dashboard</strong><br>
          &bull; <strong>Hardware Core:</strong> ESP32 Dual-Core + MPU-6050 (&plusmn;16g) + INMP441 I2S DMA + Tapo P110 (1 Hz KLAP).<br>
          &bull; <strong>Empirical Data in Hand:</strong> Over <strong>3,980 standardized active telemetry points</strong> archived across 5 full wash cycles.<br>
          &bull; <strong>Live Global Dashboard:</strong> Operational worldwide at <a href="https://washer-pdm.pages.dev" style="color:#0284c7; text-decoration:none; font-weight:700;">https://washer-pdm.pages.dev</a>.
        </div>
      </div>

      <p style="margin-top:4px;"><strong>The Bigger Expandable Plan:</strong> Because rotating electromechanical failure physics ($\text{{Vibration}} \rightarrow \text{{Acoustic Friction}} \rightarrow \text{{Electrical Drag}} \rightarrow \text{{Seizure}}$) is universal, our roadmap mass-produces these sub-RM 50 pods into clip-on hardware. We will deploy them across <strong>20 to 50 commercial AC compressors in township mosques, kuils, community halls, and shopping malls</strong>, training a specialized compressor ML model and providing facility managers with a centralized asset health dashboard.</p>
    </div>

    <!-- Section 7: Impact & ROI -->
    <div class="section">
      <div class="section-title">7. Expected Impact, Scalability &amp; Commercial ROI</div>
      <div class="callout">
        <strong>Commercial Cluster Economics (20 Commercial AC Units):</strong><br>
        &bull; <strong>Electricity Saved:</strong> Eliminating 15% parasitic friction saves <strong>~87,600 kWh annually (&gt; RM 44,500/year</strong> under TNB Tariff B).<br>
        &bull; <strong>Capital Payback Period:</strong> <strong>Under 1 month</strong> against a sensor deployment cost of ~RM 3,400 (20 pods &times; RM 170 pilot kit).<br>
        &bull; <strong>Catastrophic Replacement Avoided:</strong> Saves RM 15,000–RM 30,000 per prevented commercial compressor burnout.
      </div>
      <p style="margin-top:3px;"><strong>Township Quality of Life &amp; ESG Impact:</strong></p>
      <ul>
        <li><strong>Zero Community Disruption:</strong> Guarantees uninterrupted climate comfort during Friday prayers, temple festivals, and weekend retail crowds.</li>
        <li><strong>Circular Economy &amp; ESG:</strong> Extends equipment operating lifespan by <strong>5 to 10 years</strong>, preventing <strong>25 to 40 metric tons of compressor scrap metal</strong> and <strong>66 metric tons of CO&sub2; emissions</strong> per commercial cluster annually.</li>
      </ul>
    </div>
  </div>

  <!-- Page 2 Footer -->
  <div class="doc-footer">
    <span>AcuVibe PdM &bull; Confidential &bull; Designed for Sime Darby Property Innovation Challenge</span>
    <span>Page 2 of 2</span>
  </div>
</div>

</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML presentation written to: {html_path}")

    # Convert to PDF using Edge headless
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    if os.path.exists(edge_path):
        cmd = [
            edge_path,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path
        ]
        print("Invoking Edge headless to generate 2-page PDF...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(res.stdout)
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            pages = len(re.findall(rb'/Type\s*/Page\b', pdf_bytes))
            size_kb = len(pdf_bytes) / 1024.0
            print(f"SUCCESS: Generated PDF at {pdf_path} ({size_kb:.1f} KB, Total Pages: {pages})")
        else:
            print("ERROR: PDF was not generated by Edge headless.")
    else:
        print("Microsoft Edge executable not found.")

if __name__ == "__main__":
    main()
