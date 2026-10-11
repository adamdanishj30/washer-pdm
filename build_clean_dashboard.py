import json
import os

with open('data/wash_1019.csv', 'r', encoding='utf-8') as f:
    lines = f.readlines()[1:]

data = []
for line in lines:
    parts = line.strip().split(',')
    if len(parts) >= 5:
        data.append([
            int(parts[0]),
            float(parts[1]),
            float(parts[2]),
            float(parts[3]),
            float(parts[4])
        ])

embedded_json = json.dumps(data)

def generate_html(default_view='live'):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Samsung Washer PdM - Live Rig &amp; Historical Diagnostics</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-body: #1e2229;
      --bg-card: #252934;
      --bg-card-hover: #2c313e;
      --bg-inner: #1a1d24;
      --border-card: rgba(255, 255, 255, 0.06);
      --border-sub: rgba(255, 255, 255, 0.08);
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --teal-accent: #00f0d2;
      --teal-glow: rgba(0, 240, 210, 0.25);
      --coral-accent: #fb923c;
      --purple-accent: #a78bfa;
      --blue-accent: #38bdf8;
      --red-accent: #ef4444;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}

    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-body);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }}

    /* Top Sticky Header */
    .top-nav {{
      background: var(--bg-body);
      border-bottom: 1px solid var(--border-card);
      padding: 16px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .nav-left {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .brand-title {{
      font-size: 15px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
    }}
    .brand-pill {{
      background: var(--teal-accent);
      color: #0f172a;
      font-size: 11px;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 6px;
    }}

    /* Right Controls */
    .nav-right {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .btn-mode-toggle {{
      background: rgba(0, 240, 210, 0.12);
      border: 1px solid var(--teal-accent);
      color: var(--teal-accent);
      padding: 7px 16px;
      border-radius: 8px;
      font-size: 12.5px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }}
    .btn-mode-toggle:hover {{
      background: var(--teal-accent);
      color: #0f172a;
      box-shadow: 0 0 14px var(--teal-glow);
    }}

    .status-badge {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 240, 210, 0.08);
      border: 1px solid rgba(0, 240, 210, 0.2);
      padding: 6px 14px;
      border-radius: 20px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      color: var(--teal-accent);
      transition: all 0.25s ease;
    }}
    .status-badge.offline-badge {{
      background: rgba(239, 68, 68, 0.1);
      border-color: rgba(239, 68, 68, 0.3);
      color: #f87171;
    }}

    .status-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--teal-accent);
      box-shadow: 0 0 8px var(--teal-accent);
      animation: pulse-glow 2s infinite;
      transition: all 0.25s ease;
    }}
    .status-dot.dot-offline {{
      background: #ef4444;
      box-shadow: 0 0 6px rgba(239, 68, 68, 0.6);
      animation: none;
    }}
    @keyframes pulse-glow {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}

    .btn-header-action {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      color: var(--text-main);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }}
    .btn-header-action:hover {{
      background: var(--bg-card-hover);
      border-color: var(--border-sub);
    }}

    /* Main Container (Centered, clean full-width cards) */
    .main-container {{
      max-width: 1320px;
      margin: 0 auto;
      width: 100%;
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      flex: 1;
    }}

    /* Live Offline Alert Banner */
    .live-offline-banner {{
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.28);
      border-radius: 10px;
      padding: 10px 18px;
      color: #fca5a5;
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      animation: fadeIn 0.3s ease;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(-4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Clean Dark Cards */
    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 14px;
      padding: 22px 24px;
      position: relative;
    }}

    .card-header-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .card-title-text {{
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .card-sub-txt {{
      font-size: 11px;
      color: var(--text-dim);
      display: block;
      margin-top: 3px;
    }}

    .chart-legend-row {{
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 11px;
      color: var(--text-muted);
    }}
    .legend-item-dot {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      user-select: none;
    }}
    .dot-indicator {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
    }}

    .canvas-container-box {{
      position: relative;
      width: 100%;
      height: 180px;
    }}
    canvas {{
      width: 100%;
      height: 100%;
      display: block;
    }}

    /* Axis Toggle Badges */
    .axis-toggle-clean {{
      background: var(--bg-inner);
      border: 1px solid var(--border-card);
      border-radius: 8px;
      padding: 4px 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      user-select: none;
      transition: opacity 0.2s;
    }}
    .axis-toggle-clean.dimmed {{
      opacity: 0.35;
      text-decoration: line-through;
    }}

    /* Timeline Scrubber Bar */
    .timeline-scrubber-bar {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid var(--border-sub);
    }}
    .timeline-scrubber-bar input[type="range"] {{
      flex: 1;
      height: 4px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 2px;
      outline: none;
      accent-color: var(--teal-accent);
      cursor: pointer;
    }}
    .time-badge-mono {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--teal-accent);
      min-width: 48px;
      text-align: right;
    }}

    .action-button-row {{
      display: flex;
      gap: 10px;
      margin-top: 14px;
      flex-wrap: wrap;
    }}
    .btn-dark-primary {{
      background: var(--teal-accent);
      color: #0f172a;
      border: none;
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.2s;
    }}
    .btn-dark-primary:hover {{
      opacity: 0.9;
    }}
    .btn-dark-secondary {{
      background: var(--bg-inner);
      color: var(--text-main);
      border: 1px solid var(--border-card);
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .btn-dark-secondary:hover {{
      background: var(--bg-card-hover);
    }}

    @media (max-width: 768px) {{
      .main-container {{
        padding: 16px;
        gap: 16px;
      }}
      .top-nav {{
        padding: 12px 16px;
      }}
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <header class="top-nav">
    <div class="nav-left">
      <a href="#" class="brand-title">
        <span class="brand-pill">PDM</span>
        <span>Samsung Washer Monitor</span>
      </a>
    </div>

    <!-- Center/Right Controls: View Toggle Button, Status Badge, Export -->
    <div class="nav-right">
      <button class="btn-mode-toggle" id="btn-toggle-view" onclick="toggleViewMode()">
        <span id="btn-mode-icon">📊</span>
        <span id="btn-mode-text">Historical Data (wash_1019)</span>
      </button>

      <div class="status-badge offline-badge" id="badge-live-tag">
        <span class="status-dot dot-offline" id="status-dot-indicator"></span>
        <span id="lbl-status-text">Live Rig Offline (No Input)</span>
      </div>

      <button class="btn-header-action" onclick="exportActiveCsv()">
        Export CSV
      </button>
    </div>
  </header>

  <!-- Main View Container: ONLY the 3 Cards from Screenshot -->
  <main class="main-container">

    <!-- Live Offline Alert Banner (shown only when in Live mode and rig has no input) -->
    <div id="live-offline-banner" class="live-offline-banner" style="display: none;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ef4444;"></span>
        <span><strong>Live Rig Offline:</strong> No active sensor input detected from ESP32. Displaying last cached packet.</span>
      </div>
      <button class="btn-dark-secondary" style="padding: 4px 12px; font-size: 11px;" onclick="setViewMode('historic')">Switch to Historical Data</button>
    </div>

    <!-- Card 1: Dual-Modality Telemetry (Screenshot 3) -->
    <div class="card">
      <div class="card-header-row">
        <div>
          <span class="card-title-text" id="title-spline">Dual-Modality Telemetry</span>
          <span class="card-sub-txt" id="sub-spline">Vibration resultant &bull; Acoustic sound amplitude</span>
        </div>
        <div class="chart-legend-row">
          <span class="legend-item-dot">
            <span class="dot-indicator" style="background: var(--teal-accent);"></span> Vibration |a| (m/s&sup2;)
          </span>
          <span class="legend-item-dot">
            <span class="dot-indicator" style="background: var(--coral-accent);"></span> Sound (RMS)
          </span>
        </div>
      </div>
      <div class="canvas-container-box" style="height: 190px;">
        <canvas id="spline-canvas"></canvas>
      </div>
    </div>

    <!-- Card 2: Tri-Axial Vibration (Ax, Ay, Az) (Screenshot 2) -->
    <div class="card">
      <div class="card-header-row">
        <div>
          <span class="card-title-text">Tri-Axial Vibration (Ax, Ay, Az)</span>
          <span class="card-sub-txt">MPU-6050 Accelerometer &bull; Isolated X/Y &amp; Z oscilloscope lanes</span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
          <span class="axis-toggle-clean" id="pill-tog-x" style="color: var(--teal-accent);" onclick="toggleAxis('x')">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--teal-accent);"></span>
            Ax: <strong id="vibe-leg-x">-0.74</strong> m/s&sup2;
          </span>
          <span class="axis-toggle-clean" id="pill-tog-y" style="color: var(--coral-accent);" onclick="toggleAxis('y')">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--coral-accent);"></span>
            Ay: <strong id="vibe-leg-y">+1.40</strong> m/s&sup2;
          </span>
          <span class="axis-toggle-clean" id="pill-tog-z" style="color: var(--purple-accent);" onclick="toggleAxis('z')">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--purple-accent);"></span>
            Az: <strong id="vibe-leg-z">-9.40</strong> m/s&sup2;
          </span>
          <span class="axis-toggle-clean" style="color: #fff;">
            |a|: <strong id="head-vibe-mag">9.53</strong> m/s&sup2;
          </span>
        </div>
      </div>
      <div class="canvas-container-box" style="height: 200px;">
        <canvas id="xyz-canvas"></canvas>
      </div>
    </div>

    <!-- Card 3: Timeline & Controls (Screenshot 1) -->
    <div class="card">
      <div class="card-header-row">
        <div>
          <span class="card-title-text" id="title-timeline">Live Rig Telemetry Stream</span>
          <span class="card-sub-txt" id="sub-timeline">Real-time incoming telemetry stream from ESP32</span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <span class="axis-toggle-clean" style="color: var(--teal-accent);">
            Current: <strong id="timeline-head-rms">105.6</strong> RMS
          </span>
          <span class="axis-toggle-clean" style="color: var(--coral-accent);">
            Spike: <strong id="timeline-head-spike">1.0x</strong>
          </span>
          <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: #fff;" id="lbl-curr-time">
            00:00 / 35:54
          </span>
        </div>
      </div>

      <div class="canvas-container-box" style="height: 165px;">
        <canvas id="area-canvas"></canvas>
      </div>

      <!-- Timeline Scrubber (Active in Historical mode) -->
      <div class="timeline-scrubber-bar" id="wrap-scrubber" style="display: none;">
        <span style="font-size: 11px; color: var(--text-dim); font-weight: 600;">Scrub:</span>
        <input type="range" id="time-slider" min="0" max="421" value="0" oninput="onScrub(this.value)">
        <span class="time-badge-mono" id="scrub-label">0.0m</span>
      </div>

      <!-- Action Buttons Row -->
      <div class="action-button-row">
        <button class="btn-dark-primary" id="btn-primary-action" onclick="onPrimaryAction()">
          Pause Live Stream
        </button>
        <button class="btn-dark-secondary" id="btn-secondary-switch" onclick="toggleViewMode()">
          Switch to Historical Data (wash_1019)
        </button>
        <button class="btn-dark-secondary" onclick="exportActiveCsv()">
          Download CSV
        </button>
      </div>
    </div>

  </main>

  <script>
    const WASH_DATA = {embedded_json};
    let currentMode = '{default_view}'; // 'live' or 'historic'
    let currentIndex = 0;
    let isPlaying = false;
    let playInterval = null;
    let isLivePaused = false;

    // Rolling buffer for Live telemetry
    let LIVE_BUFFER = [];
    let lastLivePacketCnt = null;
    let lastLivePacketUptime = null;
    let lastPacketArrivedAt = 0;
    let isRigOnline = false;

    const axisVisible = {{ x: true, y: true, z: true }};

    const splineCvs = document.getElementById('spline-canvas');
    const xyzCvs = document.getElementById('xyz-canvas');
    const areaCvs = document.getElementById('area-canvas');
    const splineCtx = splineCvs.getContext('2d');
    const xyzCtx = xyzCvs.getContext('2d');
    const areaCtx = areaCvs.getContext('2d');

    const timeSlider = document.getElementById('time-slider');
    const scrubLabel = document.getElementById('scrub-label');
    const lblCurrTime = document.getElementById('lbl-curr-time');
    const lblStatusText = document.getElementById('lbl-status-text');
    const statusDot = document.getElementById('status-dot-indicator');
    const statusBadge = document.getElementById('badge-live-tag');
    const offlineBanner = document.getElementById('live-offline-banner');

    const btnToggleView = document.getElementById('btn-toggle-view');
    const btnModeText = document.getElementById('btn-mode-text');
    const btnModeIcon = document.getElementById('btn-mode-icon');
    const wrapScrubber = document.getElementById('wrap-scrubber');
    const btnPrimaryAction = document.getElementById('btn-primary-action');
    const btnSecondarySwitch = document.getElementById('btn-secondary-switch');

    const titleTimeline = document.getElementById('title-timeline');
    const subTimeline = document.getElementById('sub-timeline');
    const timelineHeadRms = document.getElementById('timeline-head-rms');
    const timelineHeadSpike = document.getElementById('timeline-head-spike');
    const headVibeMag = document.getElementById('head-vibe-mag');

    const vibeLegX = document.getElementById('vibe-leg-x');
    const vibeLegY = document.getElementById('vibe-leg-y');
    const vibeLegZ = document.getElementById('vibe-leg-z');

    function resizeCanvases() {{
      const dpr = window.devicePixelRatio || 1;

      const sRect = splineCvs.parentElement.getBoundingClientRect();
      splineCvs.width = sRect.width * dpr;
      splineCvs.height = sRect.height * dpr;

      const xRect = xyzCvs.parentElement.getBoundingClientRect();
      xyzCvs.width = xRect.width * dpr;
      xyzCvs.height = xRect.height * dpr;

      const aRect = areaCvs.parentElement.getBoundingClientRect();
      areaCvs.width = aRect.width * dpr;
      areaCvs.height = aRect.height * dpr;

      drawSpline();
      drawXyz();
      drawArea();
    }}
    window.addEventListener('resize', resizeCanvases);

    function formatMs(ms) {{
      const totalSec = Math.floor(ms / 1000);
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      return `${{String(m).padStart(2, '0')}}:${{String(s).padStart(2, '0')}}`;
    }}

    function toggleAxis(axis) {{
      axisVisible[axis] = !axisVisible[axis];
      const pill = document.getElementById(`pill-tog-${{axis}}`);
      if (pill) {{
        if (axisVisible[axis]) pill.classList.remove('dimmed');
        else pill.classList.add('dimmed');
      }}
      drawXyz();
    }}

    function drawPillBadge(ctx, x, y, text, color, align, dpr) {{
      ctx.font = `700 ${{8.5 * dpr}}px 'JetBrains Mono', monospace`;
      const tw = ctx.measureText(text).width;
      const pw = tw + (12 * dpr);
      const ph = 17 * dpr;
      const px = align === 'right' ? x - pw : (align === 'center' ? x - (pw / 2) : x);
      const py = y - (ph / 2);

      ctx.fillStyle = 'rgba(26, 29, 36, 0.94)';
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(px, py, pw, ph, 4 * dpr);
      else ctx.rect(px, py, pw, ph);
      ctx.fill();

      ctx.strokeStyle = color;
      ctx.lineWidth = 1 * dpr;
      ctx.stroke();

      ctx.fillStyle = color;
      ctx.textAlign = 'left';
      ctx.fillText(text, px + (6 * dpr), py + (12 * dpr));
    }}

    // Toggle between Live Rig page and Historical Data page
    function toggleViewMode() {{
      const newMode = (currentMode === 'live') ? 'historic' : 'live';
      setViewMode(newMode);
    }}

    function setViewMode(mode) {{
      currentMode = mode;
      if (currentMode === 'live') {{
        btnModeIcon.innerText = '📊';
        btnModeText.innerText = 'Historical Data (wash_1019)';
        wrapScrubber.style.display = 'none';
        btnPrimaryAction.innerText = isLivePaused ? 'Resume Live Stream' : 'Pause Live Stream';
        btnSecondarySwitch.innerText = 'Switch to Historical Data (wash_1019)';
        titleTimeline.innerText = 'Live Rig Telemetry Stream';
        subTimeline.innerText = 'Real-time incoming telemetry stream from ESP32';
        lblCurrTime.innerText = 'LIVE (50 Hz)';
        updateRigStatusUI(isRigOnline);
        checkRigHeartbeat();
      }} else {{
        if (isPlaying) togglePlayPause();
        btnModeIcon.innerText = '📡';
        btnModeText.innerText = 'Live Rig (Real-Time)';
        wrapScrubber.style.display = 'flex';
        btnPrimaryAction.innerText = 'Replay Wash 1019';
        btnSecondarySwitch.innerText = 'Switch to Live Rig (Real-Time)';
        titleTimeline.innerText = 'Wash Cycle 1019 Timeline (35.9 Minutes)';
        subTimeline.innerText = '35.9-min continuous acoustic waveform \u2022 Scrubber with peak spike rulers';
        statusBadge.className = 'status-badge';
        statusDot.className = 'status-dot';
        lblStatusText.innerText = 'wash_1019 Archive (35.9m)';
        offlineBanner.style.display = 'none';
        applyRecord(WASH_DATA[currentIndex], false);
        drawSpline();
        drawXyz();
        drawArea();
      }}
    }}

    function onPrimaryAction() {{
      if (currentMode === 'live') {{
        isLivePaused = !isLivePaused;
        btnPrimaryAction.innerText = isLivePaused ? 'Resume Live Stream' : 'Pause Live Stream';
      }} else {{
        togglePlayPause();
      }}
    }}

    function updateRigStatusUI(online) {{
      if (currentMode === 'live') {{
        if (online) {{
          statusBadge.className = 'status-badge';
          statusDot.className = 'status-dot';
          lblStatusText.innerText = 'Live Rig Active (50 Hz)';
          offlineBanner.style.display = 'none';
        }} else {{
          statusBadge.className = 'status-badge offline-badge';
          statusDot.className = 'status-dot dot-offline';
          lblStatusText.innerText = 'Live Rig Offline (No Input)';
          offlineBanner.style.display = 'flex';
        }}
      }}
    }}

    async function checkRigHeartbeat() {{
      try {{
        const res = await fetch('https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app/live.json');
        const d = await res.json();
        if (d && (d.cnt !== undefined || d.uptime !== undefined)) {{
          const hasIncremented = (lastLivePacketCnt !== null && d.cnt !== undefined && d.cnt !== lastLivePacketCnt) ||
                                 (lastLivePacketUptime !== null && d.uptime !== undefined && d.uptime !== lastLivePacketUptime);

          if (hasIncremented) {{
            lastPacketArrivedAt = Date.now();
            isRigOnline = true;
          }} else {{
            if (lastPacketArrivedAt === 0) {{
              isRigOnline = false;
            }} else if (Date.now() - lastPacketArrivedAt > 4500) {{
              isRigOnline = false;
            }}
          }}

          lastLivePacketCnt = d.cnt;
          lastLivePacketUptime = d.uptime;

          // Push into Live rolling buffer
          if (!isLivePaused) {{
            const newRec = [d.uptime * 1000, d.ax, d.ay, d.az, d.rms];
            LIVE_BUFFER.push(newRec);
            if (LIVE_BUFFER.length > 80) LIVE_BUFFER.shift();

            if (currentMode === 'live') {{
              applyRecord(newRec, true);
              drawSpline();
              drawXyz();
              drawArea();
            }}
          }}
        }} else {{
          isRigOnline = false;
        }}
      }} catch (e) {{
        isRigOnline = false;
      }}
      updateRigStatusUI(isRigOnline);
    }}

    function applyRecord(rec, isFromLive = false) {{
      const [t, ax, ay, az, rms] = rec;
      const vibe = Math.sqrt(ax*ax + ay*ay + az*az);
      const baselineRms = 120.0;
      const spikeRatio = Math.max(1.0, (rms / baselineRms)).toFixed(1);

      if (timelineHeadRms) timelineHeadRms.innerText = rms.toFixed(1);
      if (timelineHeadSpike) timelineHeadSpike.innerText = `${{spikeRatio}}x`;
      if (headVibeMag) headVibeMag.innerText = vibe.toFixed(2);

      const strX = (ax >= 0 ? '+' : '') + ax.toFixed(2);
      const strY = (ay >= 0 ? '+' : '') + ay.toFixed(2);
      const strZ = (az >= 0 ? '+' : '') + az.toFixed(2);
      vibeLegX.innerText = strX;
      vibeLegY.innerText = strY;
      vibeLegZ.innerText = strZ;

      if (!isFromLive) {{
        const maxT = WASH_DATA[WASH_DATA.length - 1][0];
        lblCurrTime.innerText = `${{formatMs(t)}} / ${{formatMs(maxT)}}`;
      }}
    }}

    // Canvas 1: Dual-Modality Waveform (Screenshot 3)
    function drawSpline() {{
      const w = splineCvs.width;
      const h = splineCvs.height;
      const dpr = window.devicePixelRatio || 1;
      splineCtx.clearRect(0, 0, w, h);

      const marginLeft = 58 * dpr;
      const marginRight = 58 * dpr;
      const marginTop = 18 * dpr;
      const marginBottom = 18 * dpr;
      const plotW = w - marginLeft - marginRight;
      const plotH = h - marginTop - marginBottom;

      // Vertical separator lines
      splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      splineCtx.lineWidth = 1 * dpr;
      splineCtx.beginPath();
      splineCtx.moveTo(marginLeft, marginTop);
      splineCtx.lineTo(marginLeft, h - marginBottom);
      splineCtx.moveTo(w - marginRight, marginTop);
      splineCtx.lineTo(w - marginRight, h - marginBottom);
      splineCtx.stroke();

      // Right side: Sound RMS ticks
      const soundTicks = [500, 375, 250, 125, 0];
      soundTicks.forEach(val => {{
        const y = marginTop + plotH - ((val / 520.0) * plotH);
        splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        splineCtx.beginPath();
        splineCtx.moveTo(marginLeft, y);
        splineCtx.lineTo(w - marginRight, y);
        splineCtx.stroke();

        splineCtx.fillStyle = 'rgba(251, 146, 60, 0.6)';
        splineCtx.font = `600 ${{8 * dpr}}px 'JetBrains Mono', monospace`;
        splineCtx.textAlign = 'left';
        splineCtx.fillText(`${{val}}`, w - marginRight + (8 * dpr), y + (3 * dpr));
      }});
      splineCtx.fillText('RMS', w - marginRight + (8 * dpr), marginTop - (4 * dpr));

      // Left side: Vibration m/s^2 ticks
      const vibeTicks = [
        {{ val: 12.0, lbl: '12.0' }},
        {{ val: 9.81, lbl: '9.81 (1g)' }},
        {{ val: 8.0, lbl: '8.0' }}
      ];
      vibeTicks.forEach(t => {{
        const y = marginTop + (plotH * 0.45) - ((t.val - 9.81) * 25 * dpr);
        splineCtx.fillStyle = 'rgba(0, 240, 210, 0.6)';
        splineCtx.font = `600 ${{8 * dpr}}px 'JetBrains Mono', monospace`;
        splineCtx.textAlign = 'right';
        splineCtx.fillText(t.lbl, marginLeft - (8 * dpr), y + (3 * dpr));
      }});
      splineCtx.fillText('m/s\u00B2', marginLeft - (8 * dpr), marginTop - (4 * dpr));
      splineCtx.textAlign = 'left';

      // Select data source based on active mode
      let points;
      let curRelIdx = 0;
      if (currentMode === 'live') {{
        points = LIVE_BUFFER.length > 1 ? LIVE_BUFFER : [
          [0, -0.74, 1.40, -9.40, 105.6],
          [2000, -0.74, 1.40, -9.40, 105.6]
        ];
        curRelIdx = points.length - 1;
      }} else {{
        const winSize = 40;
        const startIdx = Math.max(0, currentIndex - (winSize / 2));
        const endIdx = Math.min(WASH_DATA.length - 1, startIdx + winSize);
        points = WASH_DATA.slice(startIdx, endIdx + 1);
        curRelIdx = currentIndex - startIdx;
      }}

      if (points.length < 2) return;

      // 1. Draw Sound Wave (Coral) strictly within [marginLeft, w - marginRight]
      const gradCoral = splineCtx.createLinearGradient(0, marginTop, 0, marginTop + plotH);
      gradCoral.addColorStop(0, 'rgba(251, 146, 60, 0.15)');
      gradCoral.addColorStop(1, 'rgba(251, 146, 60, 0.0)');

      splineCtx.beginPath();
      splineCtx.moveTo(marginLeft, marginTop + plotH);
      for (let i = 0; i < points.length; i++) {{
        const x = marginLeft + ((i / (points.length - 1)) * plotW);
        const normRms = points[i][4] / 520.0;
        const y = marginTop + plotH - (normRms * plotH);
        splineCtx.lineTo(x, y);
      }}
      splineCtx.lineTo(w - marginRight, marginTop + plotH);
      splineCtx.closePath();
      splineCtx.fillStyle = gradCoral;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#fb923c';
      splineCtx.lineWidth = 2.2 * dpr;
      for (let i = 0; i < points.length; i++) {{
        const x = marginLeft + ((i / (points.length - 1)) * plotW);
        const normRms = points[i][4] / 520.0;
        const y = marginTop + plotH - (normRms * plotH);
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }}
      splineCtx.stroke();

      // 2. Draw Vibration Wave (Teal) strictly within [marginLeft, w - marginRight]
      const gradTeal = splineCtx.createLinearGradient(0, marginTop, 0, marginTop + plotH);
      gradTeal.addColorStop(0, 'rgba(0, 240, 210, 0.2)');
      gradTeal.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

      splineCtx.beginPath();
      splineCtx.moveTo(marginLeft, marginTop + plotH);
      for (let i = 0; i < points.length; i++) {{
        const x = marginLeft + ((i / (points.length - 1)) * plotW);
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = marginTop + (plotH * 0.45) - ((v - 9.81) * 25 * dpr);
        splineCtx.lineTo(x, y);
      }}
      splineCtx.lineTo(w - marginRight, marginTop + plotH);
      splineCtx.closePath();
      splineCtx.fillStyle = gradTeal;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#00f0d2';
      splineCtx.lineWidth = 2.2 * dpr;
      for (let i = 0; i < points.length; i++) {{
        const x = marginLeft + ((i / (points.length - 1)) * plotW);
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = marginTop + (plotH * 0.45) - ((v - 9.81) * 25 * dpr);
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }}
      splineCtx.stroke();

      // Active point dot
      if (curRelIdx >= 0 && curRelIdx < points.length) {{
        const cx = marginLeft + ((curRelIdx / (points.length - 1)) * plotW);
        const normRms = points[curRelIdx][4] / 520.0;
        const cyRms = marginTop + plotH - (normRms * plotH);
        splineCtx.fillStyle = '#fb923c';
        splineCtx.beginPath();
        splineCtx.arc(cx, cyRms, 4 * dpr, 0, Math.PI * 2);
        splineCtx.fill();
      }}
    }}

    // Canvas 2: Tri-Axial Vibration (Ax, Ay, Az) (Screenshot 2)
    function drawXyz() {{
      const w = xyzCvs.width;
      const h = xyzCvs.height;
      const dpr = window.devicePixelRatio || 1;
      xyzCtx.clearRect(0, 0, w, h);

      const marginLeft = 68 * dpr;
      const marginRight = 16 * dpr;
      const marginTop = 16 * dpr;
      const marginBottom = 16 * dpr;
      const plotW = w - marginLeft - marginRight;
      const plotH = h - marginTop - marginBottom;

      const yZero = marginTop + (plotH * 0.32);
      const scaleXY = 12 * dpr;
      const yGravity = marginTop + (plotH * 0.78);
      const scaleZ = 12 * dpr;

      // Vertical separator line
      xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      xyzCtx.lineWidth = 1 * dpr;
      xyzCtx.beginPath();
      xyzCtx.moveTo(marginLeft, marginTop);
      xyzCtx.lineTo(marginLeft, h - marginBottom);
      xyzCtx.stroke();

      // Baseline grid lines
      const hLines = [
        {{ y: yZero - (4.0 * scaleXY), lbl: '+4.0 m/s\u00B2', col: 'rgba(255, 255, 255, 0.25)' }},
        {{ y: yZero, lbl: '0.0 (X/Y)', col: 'rgba(255, 255, 255, 0.45)' }},
        {{ y: yZero + (4.0 * scaleXY), lbl: '-4.0 m/s\u00B2', col: 'rgba(255, 255, 255, 0.25)' }},
        {{ y: yGravity - ((-7.0 + 9.81) * scaleZ), lbl: '-7.0 m/s\u00B2', col: 'rgba(167, 139, 250, 0.3)' }},
        {{ y: yGravity, lbl: '-9.81 (Z)', col: 'rgba(167, 139, 250, 0.6)' }},
        {{ y: yGravity - ((-13.0 + 9.81) * scaleZ), lbl: '-13.0 m/s\u00B2', col: 'rgba(167, 139, 250, 0.3)' }}
      ];

      hLines.forEach(l => {{
        xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        xyzCtx.beginPath();
        xyzCtx.moveTo(marginLeft, l.y);
        xyzCtx.lineTo(w - marginRight, l.y);
        xyzCtx.stroke();

        xyzCtx.fillStyle = l.col;
        xyzCtx.font = `600 ${{8 * dpr}}px 'JetBrains Mono', monospace`;
        xyzCtx.textAlign = 'right';
        xyzCtx.fillText(l.lbl, marginLeft - (8 * dpr), l.y + (3 * dpr));
      }});
      xyzCtx.textAlign = 'left';

      // Dashed Zero Baseline
      xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      xyzCtx.setLineDash([4 * dpr, 4 * dpr]);
      xyzCtx.beginPath();
      xyzCtx.moveTo(marginLeft, yZero);
      xyzCtx.lineTo(w - marginRight, yZero);
      xyzCtx.stroke();

      // Dashed Gravity Baseline
      xyzCtx.strokeStyle = 'rgba(167, 139, 250, 0.2)';
      xyzCtx.beginPath();
      xyzCtx.moveTo(marginLeft, yGravity);
      xyzCtx.lineTo(w - marginRight, yGravity);
      xyzCtx.stroke();
      xyzCtx.setLineDash([]);

      drawPillBadge(xyzCtx, w - marginRight, yZero, 'X/Y Zero Baseline', 'rgba(255,255,255,0.4)', 'right', dpr);
      drawPillBadge(xyzCtx, w - marginRight, yGravity, 'Z 1g Gravity (-9.81 m/s\u00B2)', '#a78bfa', 'right', dpr);

      let points;
      let curRelIdx = 0;
      if (currentMode === 'live') {{
        points = LIVE_BUFFER.length > 1 ? LIVE_BUFFER.slice(-40) : [
          [0, -0.74, 1.40, -9.40, 105.6],
          [2000, -0.74, 1.40, -9.40, 105.6]
        ];
        curRelIdx = points.length - 1;
      }} else {{
        const winSize = 40;
        const startIdx = Math.max(0, currentIndex - (winSize / 2));
        const endIdx = Math.min(WASH_DATA.length - 1, startIdx + winSize);
        points = WASH_DATA.slice(startIdx, endIdx + 1);
        curRelIdx = currentIndex - startIdx;
      }}

      if (points.length < 2) return;

      // Plot Az (Purple)
      if (axisVisible.z) {{
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#a78bfa';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {{
          const x = marginLeft + ((i / (points.length - 1)) * plotW);
          const az = points[i][3];
          const y = yGravity - ((az + 9.81) * scaleZ);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }}
        xyzCtx.stroke();
      }}

      // Plot Ay (Coral)
      if (axisVisible.y) {{
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#fb923c';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {{
          const x = marginLeft + ((i / (points.length - 1)) * plotW);
          const ay = points[i][2];
          const y = yZero - (ay * scaleXY);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }}
        xyzCtx.stroke();
      }}

      // Plot Ax (Teal)
      if (axisVisible.x) {{
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#00f0d2';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {{
          const x = marginLeft + ((i / (points.length - 1)) * plotW);
          const ax = points[i][1];
          const y = yZero - (ax * scaleXY);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }}
        xyzCtx.stroke();
      }}

      // Active cursor dots
      if (curRelIdx >= 0 && curRelIdx < points.length) {{
        const cx = marginLeft + ((curRelIdx / (points.length - 1)) * plotW);
        if (axisVisible.x) {{
          const cyX = yZero - (points[curRelIdx][1] * scaleXY);
          xyzCtx.fillStyle = '#00f0d2';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyX, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }}
        if (axisVisible.y) {{
          const cyY = yZero - (points[curRelIdx][2] * scaleXY);
          xyzCtx.fillStyle = '#fb923c';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyY, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }}
        if (axisVisible.z) {{
          const cyZ = yGravity - ((points[curRelIdx][3] + 9.81) * scaleZ);
          xyzCtx.fillStyle = '#a78bfa';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyZ, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }}
      }}
    }}

    // Canvas 3: Timeline & Controls (Screenshot 1)
    function drawArea() {{
      const w = areaCvs.width;
      const h = areaCvs.height;
      const dpr = window.devicePixelRatio || 1;
      areaCtx.clearRect(0, 0, w, h);

      const marginLeft = 60 * dpr;
      const marginRight = 16 * dpr;
      const marginTop = 20 * dpr;
      const marginBottom = 18 * dpr;
      const plotW = w - marginLeft - marginRight;
      const plotH = h - marginTop - marginBottom;

      const getY = (rms) => marginTop + plotH - ((rms / 520.0) * plotH);

      // Vertical separator line
      areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      areaCtx.lineWidth = 1 * dpr;
      areaCtx.beginPath();
      areaCtx.moveTo(marginLeft, marginTop);
      areaCtx.lineTo(marginLeft, h - marginBottom);
      areaCtx.stroke();

      // Horizontal Y-Axis Numeric Rulers in Left Gutter
      const yTicks = [500, 375, 250, 125, 0];
      yTicks.forEach(val => {{
        const yVal = getY(val);
        areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        areaCtx.beginPath();
        areaCtx.moveTo(marginLeft, yVal);
        areaCtx.lineTo(w - marginRight, yVal);
        areaCtx.stroke();

        areaCtx.fillStyle = 'rgba(255, 255, 255, 0.45)';
        areaCtx.font = `600 ${{8.5 * dpr}}px 'JetBrains Mono', monospace`;
        areaCtx.textAlign = 'right';
        areaCtx.fillText(`${{val}}`, marginLeft - (8 * dpr), yVal + (3 * dpr));
      }});
      areaCtx.fillText('RMS', marginLeft - (8 * dpr), marginTop - (6 * dpr));
      areaCtx.textAlign = 'left';

      // Peak & Baseline Markers
      const yPeak = getY(511.2);
      areaCtx.strokeStyle = 'rgba(251, 146, 60, 0.4)';
      areaCtx.lineWidth = 1.2 * dpr;
      areaCtx.setLineDash([4 * dpr, 4 * dpr]);
      areaCtx.beginPath();
      areaCtx.moveTo(marginLeft, yPeak);
      areaCtx.lineTo(w - marginRight, yPeak);
      areaCtx.stroke();
      areaCtx.setLineDash([]);
      drawPillBadge(areaCtx, w - marginRight, yPeak, 'PEAK SPIKE: 511.2 RMS (24.2m)', '#fb923c', 'right', dpr);

      const yBase = getY(120.0);
      areaCtx.strokeStyle = 'rgba(0, 240, 210, 0.25)';
      areaCtx.lineWidth = 1 * dpr;
      areaCtx.setLineDash([3 * dpr, 3 * dpr]);
      areaCtx.beginPath();
      areaCtx.moveTo(marginLeft, yBase);
      areaCtx.lineTo(w - marginRight, yBase);
      areaCtx.stroke();
      areaCtx.setLineDash([]);
      drawPillBadge(areaCtx, w - marginRight, yBase, 'NORMAL BASELINE: 120 RMS', '#00f0d2', 'right', dpr);

      // Data source based on mode
      let dataSeries;
      let curPointIdx = 0;
      if (currentMode === 'live') {{
        dataSeries = LIVE_BUFFER.length > 1 ? LIVE_BUFFER : [
          [0, -0.74, 1.40, -9.40, 105.6],
          [2000, -0.74, 1.40, -9.40, 105.6]
        ];
        curPointIdx = dataSeries.length - 1;
      }} else {{
        dataSeries = WASH_DATA;
        curPointIdx = currentIndex;
      }}

      const total = dataSeries.length;
      if (total < 2) return;

      const getX = (idx) => marginLeft + ((idx / (total - 1)) * plotW);

      // Area gradient
      const grad = areaCtx.createLinearGradient(0, marginTop, 0, marginTop + plotH);
      grad.addColorStop(0, 'rgba(0, 240, 210, 0.25)');
      grad.addColorStop(0.8, 'rgba(0, 240, 210, 0.04)');
      grad.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

      areaCtx.beginPath();
      areaCtx.moveTo(marginLeft, marginTop + plotH);
      for (let i = 0; i < total; i++) {{
        const x = getX(i);
        const y = getY(dataSeries[i][4]);
        areaCtx.lineTo(x, y);
      }}
      areaCtx.lineTo(w - marginRight, marginTop + plotH);
      areaCtx.closePath();
      areaCtx.fillStyle = grad;
      areaCtx.fill();

      // Top curve stroke
      areaCtx.beginPath();
      areaCtx.strokeStyle = '#00f0d2';
      areaCtx.lineWidth = 2 * dpr;
      for (let i = 0; i < total; i++) {{
        const x = getX(i);
        const y = getY(dataSeries[i][4]);
        if (i === 0) areaCtx.moveTo(x, y); else areaCtx.lineTo(x, y);
      }}
      areaCtx.stroke();

      // Cursor scrubber line
      const curX = getX(curPointIdx);
      areaCtx.strokeStyle = 'rgba(0, 240, 210, 0.8)';
      areaCtx.lineWidth = 1.5 * dpr;
      areaCtx.beginPath();
      areaCtx.moveTo(curX, marginTop);
      areaCtx.lineTo(curX, marginTop + plotH);
      areaCtx.stroke();

      const curRms = dataSeries[curPointIdx][4];
      const curY = getY(curRms);

      // Cursor dot
      areaCtx.fillStyle = '#00f0d2';
      areaCtx.beginPath();
      areaCtx.arc(curX, curY, 5 * dpr, 0, Math.PI * 2);
      areaCtx.fill();

      // Floating cursor badge
      const spikeMult = Math.max(1.0, curRms / 120.0).toFixed(1);
      const spikePctVal = Math.round(((curRms - 120.0) / 120.0) * 100);
      const badgeText = `${{curRms.toFixed(1)}} RMS (${{spikeMult}}x ${{spikePctVal > 0 ? '+' + spikePctVal + '%' : 'base'}})`;

      areaCtx.font = `700 ${{8.5 * dpr}}px 'JetBrains Mono', monospace`;
      const tw = areaCtx.measureText(badgeText).width;
      const bw = tw + (14 * dpr);
      const bh = 20 * dpr;

      let bx = curX - (bw / 2);
      if (bx < marginLeft + (4 * dpr)) bx = marginLeft + (4 * dpr);
      if (bx + bw > w - marginRight - (4 * dpr)) bx = w - marginRight - bw - (4 * dpr);

      let by = curY - (26 * dpr);
      if (by < marginTop + (4 * dpr)) by = curY + (12 * dpr);

      const badgeCol = curRms > 250 ? '#fb923c' : '#00f0d2';
      areaCtx.fillStyle = 'rgba(20, 24, 33, 0.94)';
      areaCtx.beginPath();
      if (areaCtx.roundRect) areaCtx.roundRect(bx, by, bw, bh, 4 * dpr);
      else areaCtx.rect(bx, by, bw, bh);
      areaCtx.fill();

      areaCtx.strokeStyle = badgeCol;
      areaCtx.lineWidth = 1.2 * dpr;
      areaCtx.stroke();

      areaCtx.fillStyle = badgeCol;
      areaCtx.textAlign = 'center';
      areaCtx.fillText(badgeText, bx + (bw / 2), by + (13.5 * dpr));
      areaCtx.textAlign = 'left';
    }}

    function onScrub(val) {{
      currentIndex = parseInt(val, 10);
      const curRec = WASH_DATA[currentIndex];
      const minutes = ((curRec[0] / 60000)).toFixed(1);
      scrubLabel.innerText = `${{minutes}}m`;
      applyRecord(curRec, false);
      drawSpline();
      drawXyz();
      drawArea();
    }}

    function togglePlayPause() {{
      isPlaying = !isPlaying;
      if (isPlaying) {{
        btnPrimaryAction.innerText = 'Pause Replay';
        playInterval = setInterval(() => {{
          currentIndex++;
          if (currentIndex >= WASH_DATA.length) currentIndex = 0;
          timeSlider.value = currentIndex;
          onScrub(currentIndex);
        }}, 80);
      }} else {{
        btnPrimaryAction.innerText = 'Replay Wash 1019';
        if (playInterval) clearInterval(playInterval);
      }}
    }}

    function exportActiveCsv() {{
      if (currentMode === 'live') {{
        let csv = 'timestamp_ms,accel_x,accel_y,accel_z,audio_rms\\n';
        const src = LIVE_BUFFER.length > 0 ? LIVE_BUFFER : [[Date.now(), -0.74, 1.40, -9.40, 105.6]];
        src.forEach(r => {{
          csv += `${{r[0]}},${{r[1]}},${{r[2]}},${{r[3]}},${{r[4]}}\\n`;
        }});
        const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'live_rig_stream.csv';
        a.click();
      }} else {{
        let csv = 'timestamp_ms,accel_x,accel_y,accel_z,audio_rms\\n';
        WASH_DATA.forEach(r => {{
          csv += `${{r[0]}},${{r[1]}},${{r[2]}},${{r[3]}},${{r[4]}}\\n`;
        }});
        const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'wash_1019.csv';
        a.click();
      }}
    }}

    // Initialize: default to requested view
    setTimeout(() => {{
      resizeCanvases();
      // Check query parameter or hash if user navigated directly
      const urlParams = new URLSearchParams(window.location.search);
      const isHistoricalUrl = window.location.pathname.includes('historical') || window.location.hash.includes('historical') || urlParams.get('mode') === 'historical';
      if (isHistoricalUrl) {{
        setViewMode('historic');
      }} else {{
        setViewMode('{default_view}');
      }}
      checkRigHeartbeat();
      setInterval(checkRigHeartbeat, 2500);
    }}, 100);
  </script>
</body>
</html>
'''

# Generate default Live Rig view for index.html
html_live = generate_html(default_view='live')
# Generate default Historical Data view for historical.html
html_historical = generate_html(default_view='historic')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_live)

with open('historical.html', 'w', encoding='utf-8') as f:
    f.write(html_historical)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_live)

with open('cloud_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_live)

brain_path = r'C:\Users\adamd\.gemini\antigravity\brain\eaf1a310-7f2a-46d6-b3a7-72b474df813e\dashboard.html'
try:
    with open(brain_path, 'w', encoding='utf-8') as f:
        f.write(html_live)
except Exception as e:
    print('Brain artifact write note:', e)

print('Successfully generated streamlined website with ONLY the 3 cards, Live Rig default, and Historical toggle!')
