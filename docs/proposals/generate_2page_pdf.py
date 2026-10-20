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
    root_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))
    html_path = os.path.join(base_dir, "proposal_2page_presentation.html")
    pdf_path = os.path.join(base_dir, "PROPOSAL_2PAGE_Apex_PdM_Township_of_Tomorrow.pdf")

    # Load images if available
    img_layout = get_base64_image(os.path.join(root_dir, "docs", "hardware_guides", "diagrams", "washer_electronics_layout_diagram.jpg"))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Apex PdM - 2-Page Executive Proposal</title>
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
    white-space: nowrap;
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
        <span class="header-track">Track: PLANET (02 Circular Economy)</span>
        <span class="header-track" style="background:#e0f2fe; color:#0369a1; border-color:#7dd3fc; margin-left:3px;">Synergy: PEOPLE (Digital Living)</span>
      </div>
    </div>

    <!-- Section 1: Title -->
    <div class="section" style="margin-bottom: 4px;">
      <div style="font-size:7.5pt; font-weight:800; color:#64748b; text-transform:uppercase;">1. Title of the Idea</div>
      <div class="title-hero">Apex PdM: Township-Scale Asset Health &amp; Air-Conditioning Predictive Maintenance Platform</div>
      <div class="subtitle-hero">A low-cost sensor pod that feels, hears and measures machines, so township teams fix small problems before they become big breakdowns</div>
      <div>
        <span class="live-bar">LIVE WORKING RIG: <span>https://washer-pdm.pages.dev</span></span>
        <span style="font-size:7pt; color:#64748b; margin-left:6px;"><strong>Stage:</strong> Working prototype (TRL 4&ndash;5) with live data online</span>
      </div>
    </div>

    <!-- Metric Strip -->
    <div class="metrics-strip">
      <div class="metric-card">
        <div class="num">10</div>
        <div class="lbl">Real Wash Sessions Archived</div>
      </div>
      <div class="metric-card">
        <div class="num">4</div>
        <div class="lbl">Sensors Working in Sync</div>
      </div>
      <div class="metric-card">
        <div class="num">20&times;+</div>
        <div class="lbl">Vibration Jump, Idle &rarr; Spin</div>
      </div>
      <div class="metric-card">
        <div class="num">~RM 170</div>
        <div class="lbl">Pilot Kit Cost, Off the Shelf</div>
      </div>
    </div>

    <!-- Section 2: Problem Statement -->
    <div class="section">
      <div class="section-title">2. Problem Statement</div>
      <p><strong>What is the issue?</strong> Air-conditioners, chillers, water pumps and big appliances are usually fixed only <strong>after they break</strong>. Before that, a worn bearing, damper or seal slowly makes the machine shake more, sound different and <strong>work harder, using more electricity</strong>. Nobody notices until the machine stops. By then, a <strong>small part worth tens of ringgit</strong> has turned into a <strong>new motor or compressor worth thousands</strong>, plus days without cooling.</p>
      
      <p><strong>Who is affected?</strong></p>
      <ul>
        <li><strong>Township Communal &amp; Commercial Spaces:</strong> Community <strong>mosques, suraus, kuils (temples), clubhouses, and retail shopping malls</strong> operating many commercial AC compressors daily. Sudden breakdown leaves congregations and shoppers in unbearable tropical heat.</li>
        <li><strong>Township Facility Management (FM) Teams:</strong> Technicians check machines one by one, by hand, and still cannot see wear happening inside until something fails.</li>
        <li><strong>Township Residents:</strong> Households facing surprise repair bills, noisy machines and higher electricity bills.</li>
      </ul>

      <p><strong>Why is it important to solve this problem now?</strong> Electricity keeps getting more expensive, and townships are aiming for lower emissions and less waste. A machine that is wearing out uses more power and gets thrown away sooner. Catching the problem early means <strong>a cheap repair instead of a full replacement</strong>, lower bills and less scrap going to landfill.</p>
    </div>

    <!-- Section 3: Proposed Solution -->
    <div class="section">
      <div class="section-title">3. Proposed Solution</div>
      <p><strong>How does your solution address the problem?</strong> Apex PdM is a small sensor pod that sits on the outside of a machine. It records <strong>vibration, sound and power together</strong>, learns what <em>normal</em> looks like for that machine, and gives an <strong>anomaly score and a simple verdict for every run</strong> (normal / check it). A full health score and remaining-life estimate are our next step, once we have recorded real faults.</p>

      <div class="two-col" style="margin-top:3px;">
        <div class="modality-box">
          <strong>1. Vibration (MPU-6050 @ 200 Hz):</strong> 3-axis sensor that feels shaking, unbalance and loose or worn parts.
        </div>
        <div class="modality-box">
          <strong>2. Sound (INMP441 @ 16 kHz):</strong> Digital microphone that hears grinding, squealing and rattling.
        </div>
        <div class="modality-box">
          <strong>3. Power (Tapo P110 @ 1 Hz):</strong> Smart plug that measures how hard the motor is working, in watts.
        </div>
        <div class="modality-box">
          <strong>4. Machine State:</strong> Context from SmartThings (wash, rinse, spin); comparing vibration and sound within the same phase is planned.
        </div>
      </div>

      <p style="margin-top:4px;"><strong>What technology / product is involved?</strong></p>
      <ul>
        <li><strong>Dual-Core ESP32:</strong> One core reads the sensors in real time, the other handles Wi-Fi and cloud upload, so neither slows the other down. Every 5 seconds the pod turns raw signals into <strong>32 signal features</strong>.</li>
        <li><strong>Keeps Logging Through Wi-Fi Drops:</strong> The pod stores about 4 minutes of data and sends it once the connection is back.</li>
        <li><strong>Live Web Dashboard:</strong> Anyone can watch the rig live today. A township map and phone alerts are the next build.</li>
      </ul>
    </div>
  </div>

  <!-- Page 1 Footer -->
  <div class="doc-footer">
    <span>Apex PdM &bull; Sime Darby Property "Township of Tomorrow" Hackathon</span>
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
        <span class="header-track" style="background:#f1f5f9; color:#334155; border-color:#cbd5e1; margin-left:3px;">Pilot kit about RM 170</span>
      </div>
    </div>

    <!-- Section 4: Target Market / Beneficiaries -->
    <div class="section">
      <div class="section-title">4. Target Market / Beneficiaries</div>
      <p><strong>Specific Industry or Sector:</strong> Commercial Facility Management (FM), Communal Places of Worship, Retail Real Estate, and Smart Sustainable Townships (e.g., Sime Darby Property's City of Elmina, Bandar Bukit Raja).</p>
      <ul>
        <li><strong>Communal Places of Worship:</strong> Mosques, Suraus, and Kuils (temples) relying on central air-conditioning split units.</li>
        <li><strong>Commercial Centers &amp; Clubhouses:</strong> Community gyms, function halls, and retail malls (e.g., Elmina Lakeside Mall).</li>
        <li><strong>Local Maintenance Contractors (MSMEs):</strong> Technicians who get told which machine needs a look, instead of rushing to emergency calls.</li>
      </ul>
      <p><strong>Urban/Rural Focus:</strong> High-density master-planned urban townships and commercial property clusters.</p>
    </div>

    <!-- Section 5: Uniqueness and Innovation -->
    <div class="section">
      <div class="section-title">5. Uniqueness and Innovation</div>
      <ul>
        <li><strong>Low Cost:</strong> Industrial vibration sensors cost thousands of ringgit each, so only big factories use them. We spent <strong>about RM 131 in parts for the sensor node</strong> (about RM 170 for a full pilot kit with smart plug) &mdash; cheap enough for every AC unit in a mosque or mall.</li>
        <li><strong>Fewer False Alarms by Design:</strong> One sensor alone gets fooled &mdash; a normal fast spin looks like a fault. We check vibration, sound and power <strong>together</strong>, and plan to check against what the machine is doing, before raising an alert.</li>
        <li><strong>Sees Energy Waste Too:</strong> Because we measure power directly, the system can compare each run's power use against that machine's own normal and show when it starts working harder.</li>
        <li><strong>Easy to Fit:</strong> Mounts on the outside and plugs in &mdash; no rewiring and nothing opened up.</li>
      </ul>
    </div>

    <!-- Section 6: Prototype Status & Expansion Plan -->
    <div class="section">
      <div class="section-title">6. Prototype Feasibility, Empirical Evidence &amp; The Expansion Plan</div>
      <p><strong>Why we tested on a washing machine:</strong> A front-load washer is one of the toughest machines to monitor. It shakes hard, the load moves around, water sloshes, and the speed keeps changing from slow tumbling to a fast spin. If our pod gets clean, clear data here, a steady-running AC compressor or pump is an easier job. <strong>What we measured</strong> in our latest 66-minute cycle: vibration jumped <strong>over 20&times;</strong> from idle to spin; the main vibration frequency climbed smoothly to <strong>19.9 Hz (about 1,200 rpm)</strong> as the drum sped up; and the washer's sound in the higher bands was <strong>36&ndash;90&times; louder</strong> than the room's background noise, even with a compressor and water pump running nearby.</p>

      <!-- Embedded Visual Proof Banner -->
      <div class="image-row">
        {f'<img src="{img_layout}" alt="Hardware Layout">' if img_layout else '<div style="width:70px; height:70px; background:#e2e8f0; display:flex; align-items:center; justify-content:center; font-size:6pt;">Rig Photo</div>'}
        <div class="image-desc">
          <strong>Figure 1: Sensor pod layout</strong><br>
          &bull; <strong>Hardware:</strong> ESP32 dual-core + MPU-6050 (200 Hz) + INMP441 mic (16 kHz) + Tapo P110 smart plug (1 Hz).<br>
          &bull; <strong>Data in Hand:</strong> <strong>10 real wash sessions archived</strong> and <strong>7,414 rows</strong> of training-ready data, 32 signal features per 5-second window (firmware-07 window record).<br>
          &bull; <strong>Model Validation:</strong> Leave-one-cycle-out test on 8 healthy cycles: 0 falsely flagged (95% upper bound 31%); a simulated doubling of sound was caught in 7 of 8.<br>
          &bull; <strong>Live Global Dashboard:</strong> Operational worldwide at <a href="https://washer-pdm.pages.dev" style="color:#0284c7; text-decoration:none; font-weight:700;">https://washer-pdm.pages.dev</a>.
        </div>
      </div>

      <p style="margin-top:4px;"><strong>From washer to township:</strong> Fans, pumps and compressors wear out the same way &mdash; worn parts cause more shaking, then more noise, then more power use, then a breakdown. The same pod and software can move onto <strong>AC units and pumps in township mosques, kuils, community halls and malls</strong>. <strong>Next steps:</strong> record 20+ more cycles to measure our false-alarm rate, then pilot on real township equipment.</p>
    </div>

    <!-- Section 7: Impact & ROI -->
    <div class="section">
      <div class="section-title">7. Expected Impact, Scalability &amp; Commercial ROI</div>
      <div class="callout">
        <strong>Example (our estimate, to be confirmed in the pilot):</strong><br>
        &bull; One 5 kW commercial AC running 10 hours a day uses about 18,250 kWh a year. If a worn part makes it use just <strong>10% more</strong>, that is ~1,825 kWh &mdash; <strong>about RM 900 a year</strong> at ~RM 0.50/kWh.<br>
        &bull; A pilot kit costs about <strong>RM 170</strong>, so catching one problem like this <strong>pays for the pod within a few months</strong>.<br>
        &bull; Catching a failing part early can also <strong>avoid replacing a whole compressor</strong>, which costs thousands of ringgit.
      </div>
      <p style="margin-top:3px;"><strong>Township Quality of Life &amp; ESG Impact:</strong></p>
      <ul>
        <li><strong>Less Disruption:</strong> Repairs can be planned ahead, so cooling stays on during Friday prayers, festivals and busy weekends.</li>
        <li><strong>Less Waste &amp; Lower Emissions:</strong> Fixing one small part instead of replacing a whole unit keeps machines running longer, cuts scrap metal and saves electricity.</li>
      </ul>
    </div>
  </div>

  <!-- Page 2 Footer -->
  <div class="doc-footer">
    <span>Apex PdM &bull; Confidential &bull; Designed for Sime Darby Property Innovation Challenge</span>
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
