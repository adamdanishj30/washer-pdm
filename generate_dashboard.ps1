$jsPath = if (Test-Path "data/wash_cycle_2026-10-11_1019_embedded.js") { "data/wash_cycle_2026-10-11_1019_embedded.js" } else { "data/wash_1019_embedded.js" }
$embeddedJs = Get-Content $jsPath -Raw

$templatePart1 = @'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Samsung Washer PdM — Machinery Diagnostics</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-body: #1e2229;
      --bg-sidebar: #171a21;
      --bg-card: #252934;
      --bg-card-hover: #2c313e;
      --bg-inner: #1a1d24;
      --border-card: rgba(255, 255, 255, 0.05);
      --border-sub: rgba(255, 255, 255, 0.08);
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --teal-accent: #00f0d2;
      --teal-glow: rgba(0, 240, 210, 0.25);
      --coral-accent: #fb923c;
      --purple-accent: #a78bfa;
      --blue-accent: #38bdf8;
      --green-accent: #34d399;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-body);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Top Navigation Bar */
    .top-nav {
      background: var(--bg-body);
      border-bottom: 1px solid var(--border-card);
      padding: 16px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .nav-left {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-title {
      font-size: 15px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
    }
    .brand-pill {
      background: var(--teal-accent);
      color: #0f172a;
      font-size: 11px;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 6px;
    }

    /* Center Tabs (Dashboard, Analytics, Audience...) */
    .nav-tabs-center {
      display: flex;
      align-items: center;
      gap: 28px;
    }

    .nav-tab-item {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      text-decoration: none;
      transition: color 0.2s;
      position: relative;
    }
    .nav-tab-item:hover {
      color: #fff;
    }
    .nav-tab-item.active {
      color: #fff;
      font-weight: 700;
    }
    .nav-tab-item.active::after {
      content: '';
      position: absolute;
      bottom: -16px;
      left: 0;
      width: 100%;
      height: 2px;
      background: var(--teal-accent);
      border-radius: 999px;
    }

    .nav-right {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      background: rgba(0, 240, 210, 0.1);
      color: var(--teal-accent);
      border: 1px solid rgba(0, 240, 210, 0.2);
    }
    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--teal-accent);
      animation: pulse-dot 2s infinite;
    }
    @keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } }

    .btn-header-action {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      color: var(--text-main);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-header-action:hover {
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.15);
    }

    .hamburger-btn {
      display: none;
      background: none;
      border: none;
      color: #fff;
      font-size: 22px;
      cursor: pointer;
    }

    /* Main App Layout */
    .app-layout {
      display: flex;
      flex: 1;
      max-width: 1560px;
      margin: 0 auto;
      width: 100%;
      padding: 20px 24px;
      gap: 20px;
    }

    /* Sidebar: "My Accounts" / Machines list */
    .sidebar {
      width: 210px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .sidebar-section-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 12px;
    }

    .account-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
      background: transparent;
    }
    .account-item:hover {
      background: rgba(37, 41, 52, 0.6);
    }
    .account-item.active {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
    }

    .account-avatar-ring {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: linear-gradient(135deg, #00f0d2, #38bdf8);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #0f172a;
      font-weight: 800;
      font-size: 13px;
      flex-shrink: 0;
    }
    .avatar-purple { background: linear-gradient(135deg, #a78bfa, #818cf8); color: #fff; }
    .avatar-coral { background: linear-gradient(135deg, #fb923c, #f97316); color: #fff; }

    .account-meta {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .account-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .account-sub {
      font-size: 11px;
      color: var(--text-dim);
    }

    .sidebar-info-card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 14px;
      padding: 16px;
      margin-top: auto;
    }
    .sidebar-info-card h4 {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 4px;
    }
    .sidebar-info-card p {
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.4;
      margin-bottom: 12px;
    }

    /* Main Content Area */
    .main-view {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 16px;
      min-width: 0;
    }

    /* Card Styling */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 16px;
      padding: 18px 20px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
      position: relative;
      transition: border-color 0.2s;
    }
    .card:hover {
      border-color: rgba(255, 255, 255, 0.08);
    }

    .card-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .card-title-text {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .card-dots {
      color: var(--text-dim);
      font-size: 14px;
      cursor: pointer;
    }

    /* Row 1: Top 3 Metric Cards (Matching Image 3) */
    .row-top-three {
      display: grid;
      grid-template-columns: 1.2fr 1.3fr 1.2fr;
      gap: 16px;
    }

    /* Dual-Metric Block (Followers style: 2,535 & 957) */
    .dual-metric-flex {
      display: flex;
      gap: 28px;
      margin-top: 4px;
    }
    .dual-metric-col {
      display: flex;
      flex-direction: column;
    }
    .metric-big-num {
      font-family: 'JetBrains Mono', monospace;
      font-size: 26px;
      font-weight: 700;
      color: #fff;
      line-height: 1.1;
    }
    .metric-sub-lbl {
      font-size: 11px;
      color: var(--text-dim);
      margin-top: 4px;
    }

    /* Overview Stats with % badges (+83.5%) */
    .stat-with-badge {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-top: 2px;
    }
    .badge-percent {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: var(--teal-accent);
    }
    .badge-coral {
      color: var(--coral-accent);
    }

    /* Row 2: Middle Section (Vibration Spline/Bars + Donut Card) */
    .row-middle {
      display: grid;
      grid-template-columns: 1.8fr 1fr;
      gap: 16px;
    }

    /* Legend Pills */
    .chart-legend-row {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 11px;
      color: var(--text-muted);
    }
    .legend-item-dot {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      cursor: pointer;
      user-select: none;
    }
    .dot-teal { width: 7px; height: 7px; border-radius: 50%; background: var(--teal-accent); }
    .dot-coral { width: 7px; height: 7px; border-radius: 50%; background: var(--coral-accent); }
    .dot-purple { width: 7px; height: 7px; border-radius: 50%; background: var(--purple-accent); }
    .dot-blue { width: 7px; height: 7px; border-radius: 50%; background: var(--blue-accent); }

    .canvas-container-mid {
      position: relative;
      width: 100%;
      height: 180px;
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
    }

    /* Circular Donut Ring (Gender card in Image 3) */
    .donut-card-inner {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 10px 0;
    }
    .donut-svg-wrap {
      position: relative;
      width: 130px;
      height: 130px;
    }
    .donut-svg-elem {
      transform: rotate(-90deg);
      width: 100%;
      height: 100%;
    }
    .donut-track-bg {
      fill: none;
      stroke: rgba(255, 255, 255, 0.05);
      stroke-width: 12;
    }
    .donut-arc-teal {
      fill: none;
      stroke: var(--teal-accent);
      stroke-width: 12;
      stroke-linecap: round;
      stroke-dasharray: 326;
      stroke-dashoffset: 80;
      transition: stroke-dashoffset 0.4s;
    }
    .donut-arc-purple {
      fill: none;
      stroke: var(--purple-accent);
      stroke-width: 12;
      stroke-linecap: round;
      stroke-dasharray: 326;
      stroke-dashoffset: 230;
    }
    .donut-inner-num {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .donut-main-stat {
      font-family: 'JetBrains Mono', monospace;
      font-size: 24px;
      font-weight: 800;
      color: #fff;
    }
    .donut-sub-stat {
      font-size: 10px;
      color: var(--text-dim);
      text-transform: uppercase;
      font-weight: 700;
    }

    .donut-split-legend {
      display: flex;
      justify-content: space-around;
      width: 100%;
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid var(--border-sub);
      font-size: 11px;
    }

    /* Row 3: Dedicated Tri-Axial Vibration (Ax, Ay, Az) Card */
    .row-xyz-full {
      display: grid;
      grid-template-columns: 1fr;
    }

    .axis-toggle-clean {
      background: var(--bg-inner);
      border: 1px solid var(--border-card);
      border-radius: 999px;
      padding: 3px 10px;
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      cursor: pointer;
      transition: all 0.2s;
      user-select: none;
    }
    .axis-toggle-clean.dimmed {
      opacity: 0.35;
      text-decoration: line-through;
    }

    /* Row 4: Timeline ("Most Active Times" style) + Phase Breakdown */
    .row-bottom {
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 16px;
    }

    .timeline-scrubber-bar {
      display: flex;
      align-items: center;
      gap: 12px;
      background: var(--bg-inner);
      border: 1px solid var(--border-card);
      border-radius: 10px;
      padding: 8px 14px;
      margin-top: 10px;
    }
    .timeline-scrubber-bar input[type="range"] {
      flex: 1;
      accent-color: var(--teal-accent);
      cursor: pointer;
    }
    .time-badge-mono {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: var(--teal-accent);
      min-width: 50px;
    }

    .action-button-row {
      display: flex;
      gap: 10px;
      margin-top: 12px;
    }
    .btn-dark-primary {
      padding: 8px 16px;
      border-radius: 8px;
      background: var(--teal-accent);
      color: #0f172a;
      border: none;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-dark-primary:hover {
      box-shadow: 0 0 12px var(--teal-glow);
    }
    .btn-dark-secondary {
      padding: 8px 16px;
      border-radius: 8px;
      background: var(--bg-inner);
      color: var(--text-main);
      border: 1px solid var(--border-card);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-dark-secondary:hover {
      background: var(--bg-card-hover);
    }

    /* Phase Progress Bars ("Top Locations" in Image 3) */
    .phase-bars-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-top: 6px;
    }
    .phase-bar-row {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .phase-header-flex {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
    }
    .phase-name-txt {
      color: var(--text-muted);
      font-weight: 500;
    }
    .phase-pct-txt {
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-main);
      font-weight: 600;
    }
    .progress-track-dark {
      width: 100%;
      height: 6px;
      background: var(--bg-inner);
      border-radius: 999px;
      overflow: hidden;
    }
    .progress-fill-teal {
      height: 100%;
      background: var(--teal-accent);
      border-radius: 999px;
    }

    /* Mobile Drawer */
    .mobile-drawer-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(6px);
      z-index: 99;
    }
    .mobile-drawer {
      position: fixed;
      top: 0;
      bottom: 0;
      left: -280px;
      width: 260px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-card);
      z-index: 100;
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .mobile-drawer.open {
      left: 0;
    }

    /* Responsive Breakpoints */
    @media (max-width: 1100px) {
      .row-top-three {
        grid-template-columns: 1fr;
      }
      .row-middle {
        grid-template-columns: 1fr;
      }
      .row-bottom {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 768px) {
      .top-nav {
        padding: 12px 16px;
      }
      .nav-tabs-center {
        display: none;
      }
      .sidebar {
        display: none;
      }
      .hamburger-btn {
        display: block;
      }
      .app-layout {
        padding: 14px;
      }
      .card {
        padding: 14px 16px;
      }
    }
  </style>
</head>
<body>

  <!-- Top Navigation Bar (NO user profile interface) -->
  <header class="top-nav">
    <div class="nav-left">
      <button class="hamburger-btn" onclick="toggleMobileMenu()">☰</button>
      <a href="#" class="brand-title">
        <span class="brand-pill">PDM</span>
        <span>Samsung Washer Monitor</span>
      </a>
    </div>

    <!-- Center Navigation Tabs -->
    <nav class="nav-tabs-center">
      <a class="nav-tab-item active" onclick="setMode('historic')">Dashboard</a>
      <a class="nav-tab-item" onclick="setMode('live')">Real-Time Telemetry</a>
      <a class="nav-tab-item" onclick="toggleDoc()">Acoustic Diagnostics</a>
      <a class="nav-tab-item" onclick="toggleDoc()">ISO 10816 Specs</a>
    </nav>

    <!-- Right Controls: Status & CSV (NO User Profile) -->
    <div class="nav-right">
      <div class="status-badge" id="badge-live-tag">
        <span class="status-dot"></span>
        <span id="lbl-status-text">wash_1019 Active</span>
      </div>
      <button class="btn-header-action" onclick="downloadWashCsv()">
        Export CSV
      </button>
    </div>
  </header>

  <!-- Mobile Drawer -->
  <div class="mobile-drawer-overlay" id="drawer-overlay" onclick="toggleMobileMenu()"></div>
  <aside class="mobile-drawer" id="mobile-drawer">
    <div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <span class="brand-title">
          <span class="brand-pill">PDM</span>
          <span>Washer Monitor</span>
        </span>
        <button onclick="toggleMobileMenu()" style="background:none; border:none; color:#fff; font-size:20px; cursor:pointer;">✕</button>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div class="account-item active" onclick="setMode('historic'); toggleMobileMenu()">
          <div class="account-avatar-ring">W</div>
          <div class="account-meta">
            <span class="account-name">Wash 1019 Run</span>
            <span class="account-sub">35.9 mins archived</span>
          </div>
        </div>
        <div class="account-item" onclick="setMode('live'); toggleMobileMenu()">
          <div class="account-avatar-ring avatar-coral">L</div>
          <div class="account-meta">
            <span class="account-name">Live ESP32 Rig</span>
            <span class="account-sub">50 Hz Firebase stream</span>
          </div>
        </div>
        <div class="account-item" onclick="downloadWashCsv()">
          <div class="account-avatar-ring avatar-purple">D</div>
          <div class="account-meta">
            <span class="account-name">Download Data</span>
            <span class="account-sub">CSV time-series</span>
          </div>
        </div>
      </div>
    </div>
    <div class="sidebar-info-card">
      <h4>Google Firebase</h4>
      <p>Autonomous Asia-SE1 cloud sync active.</p>
      <button class="btn-dark-primary" style="width: 100%;" onclick="downloadWashCsv()">Export CSV</button>
    </div>
  </aside>

  <!-- App Layout -->
  <div class="app-layout">
    
    <!-- Sidebar: Machines / Nodes list ("My Accounts" style from Image 3) -->
    <aside class="sidebar">
      <div>
        <div class="sidebar-section-title">Nodes & Sensors</div>
        
        <div class="account-item active" id="acc-item-1" onclick="setMode('historic')">
          <div class="account-avatar-ring">W</div>
          <div class="account-meta">
            <span class="account-name">Samsung WW10T</span>
            <span class="account-sub">wash_1019 cycle</span>
          </div>
        </div>

        <div class="account-item" id="acc-item-2" onclick="setMode('live')">
          <div class="account-avatar-ring avatar-coral">M</div>
          <div class="account-meta">
            <span class="account-name">MPU-6050 IMU</span>
            <span class="account-sub">I2C 0x68 (±16g)</span>
          </div>
        </div>

        <div class="account-item" onclick="toggleAxis('z')">
          <div class="account-avatar-ring avatar-purple">A</div>
          <div class="account-meta">
            <span class="account-name">INMP441 Audio</span>
            <span class="account-sub">16 kHz I2S DMA</span>
          </div>
        </div>
      </div>

      <div class="sidebar-info-card">
        <h4>Predictive Maintenance</h4>
        <p>10kg Front-Load Anomaly & Vibration Monitor.</p>
        <button class="btn-dark-primary" style="width: 100%;" onclick="downloadWashCsv()">Download CSV</button>
      </div>
    </aside>

    <!-- Main View -->
    <main class="main-view">

      <!-- Row 1: Top 3 Metric Cards (Matching Image 3) -->
      <section class="row-top-three">
        
        <!-- Card 1: Resultant Vibration (Dual numbers: Avg & Peak) -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Vibration Resultant</span>
            <span class="card-dots">•••</span>
          </div>
          <div class="dual-metric-flex">
            <div class="dual-metric-col">
              <span class="metric-big-num" style="color: var(--teal-accent);" id="kpi-avg-vibe">9.58</span>
              <span class="metric-sub-lbl">Avg (m/s²)</span>
            </div>
            <div class="dual-metric-col">
              <span class="metric-big-num" style="color: var(--coral-accent);" id="kpi-peak-vibe">10.14</span>
              <span class="metric-sub-lbl">Peak Spin</span>
            </div>
          </div>
        </div>

        <!-- Card 2: Overview (Acoustic Noise + Percentages) -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Acoustic Energy</span>
            <span class="card-dots">•••</span>
          </div>
          <div>
            <div class="stat-with-badge">
              <span class="metric-big-num" style="font-size: 22px;" id="kpi-avg-rms">146.9</span>
              <span class="badge-percent">+12.4%</span>
            </div>
            <span class="metric-sub-lbl">Average Sound RMS</span>
            <div class="stat-with-badge" style="margin-top: 8px;">
              <span class="metric-big-num" style="font-size: 18px; color: var(--coral-accent);" id="kpi-peak-rms">511.2</span>
              <span class="badge-percent badge-coral">+45.2%</span>
            </div>
            <span class="metric-sub-lbl">Max Peak Extraction Noise</span>
          </div>
        </div>

        <!-- Card 3: Machine Health (Your Audience style) -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Machinery Health</span>
            <span class="card-dots">•••</span>
          </div>
          <div class="stat-with-badge" style="margin-top: 4px;">
            <span class="metric-big-num" style="color: var(--teal-accent);" id="kpi-health-score">94%</span>
            <span class="badge-percent">+9.3%</span>
          </div>
          <span class="metric-sub-lbl">ISO 10816 Class I (Normal)</span>
          <div style="font-size: 11px; color: var(--text-dim); margin-top: 10px;">
            Chassis dynamic equilibrium maintained.
          </div>
        </div>

      </section>

      <!-- Row 2: Middle Section (Vibration Spline + Donut Gender Card) -->
      <section class="row-middle">
        
        <!-- Dual-Modality Waveform (Post Performance style) -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Dual-Modality Telemetry</span>
            <div class="chart-legend-row">
              <span class="legend-item-dot"><span class="dot-teal"></span> Vibration |a|</span>
              <span class="legend-item-dot"><span class="dot-coral"></span> Acoustic RMS</span>
            </div>
          </div>
          <div class="canvas-container-mid">
            <canvas id="spline-canvas"></canvas>
          </div>
        </div>

        <!-- Donut Card (Gender card style in Image 3) -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Machinery Health</span>
            <span class="card-dots">•••</span>
          </div>

          <div class="donut-card-inner">
            <div class="donut-svg-wrap">
              <svg class="donut-svg-elem" viewBox="0 0 130 130">
                <circle class="donut-track-bg" cx="65" cy="65" r="52"></circle>
                <circle class="donut-arc-teal" id="donut-arc-teal" cx="65" cy="65" r="52"></circle>
                <circle class="donut-arc-purple" cx="65" cy="65" r="52"></circle>
              </svg>
              <div class="donut-inner-num">
                <span class="donut-main-stat" id="donut-center-num">94%</span>
                <span class="donut-sub-stat">HEALTH</span>
              </div>
            </div>

            <div class="donut-split-legend">
              <span style="color: var(--teal-accent); font-weight: 600;">● 56.7% Stable</span>
              <span style="color: var(--purple-accent); font-weight: 600;">● 43.3% Dynamic</span>
            </div>
          </div>
        </div>

      </section>

      <!-- Row 3: Dedicated Tri-Axial Vibration (Ax, Ay, Az) Card -->
      <section class="row-xyz-full">
        <div class="card">
          <div class="card-header-row">
            <div>
              <span class="card-title-text">Tri-Axial Vibration (Ax, Ay, Az)</span>
              <span style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">MPU-6050 direct accelerometer register burst</span>
            </div>
            <div style="display: flex; gap: 8px;">
              <span class="axis-toggle-clean" id="pill-tog-x" style="color: var(--teal-accent);" onclick="toggleAxis('x')">
                ● Ax: <strong id="vibe-leg-x">-0.72</strong> m/s²
              </span>
              <span class="axis-toggle-clean" id="pill-tog-y" style="color: var(--coral-accent);" onclick="toggleAxis('y')">
                ● Ay: <strong id="vibe-leg-y">+1.41</strong> m/s²
              </span>
              <span class="axis-toggle-clean" id="pill-tog-z" style="color: var(--purple-accent);" onclick="toggleAxis('z')">
                ● Az: <strong id="vibe-leg-z">-9.44</strong> m/s²
              </span>
            </div>
          </div>
          <div class="canvas-container-mid" style="height: 180px;">
            <canvas id="xyz-canvas"></canvas>
          </div>
        </div>
      </section>

      <!-- Row 4: Timeline ("Most Active Times" style) + Phase Breakdown -->
      <section class="row-bottom">
        
        <!-- Full Wash 1019 Timeline & Playback -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Wash Cycle 1019 Timeline (35.9 Minutes)</span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: var(--teal-accent);" id="lbl-curr-time">
              00:00 / 35:54
            </span>
          </div>

          <div class="canvas-container-mid" style="height: 140px;">
            <canvas id="area-canvas"></canvas>
          </div>

          <!-- Timeline Scrubber -->
          <div class="timeline-scrubber-bar">
            <span style="font-size: 11px; color: var(--text-dim); font-weight: 600;">Scrub:</span>
            <input type="range" id="time-slider" min="0" max="421" value="0" oninput="onScrub(this.value)">
            <span class="time-badge-mono" id="scrub-label">0.0m</span>
          </div>

          <!-- Actions -->
          <div class="action-button-row">
            <button class="btn-dark-primary" onclick="togglePlayPause()" id="btn-play-wash">
              ▶ Replay Wash 1019
            </button>
            <button class="btn-dark-secondary" onclick="downloadWashCsv()">
              📥 Download wash_1019.csv
            </button>
            <button class="btn-dark-secondary" onclick="setMode('live')">
              ⚡ Connect Live Firebase
            </button>
          </div>
        </div>

        <!-- Phase Breakdown ("Top Locations" style in Image 3) -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Cycle Phase Breakdown</span>
            <span class="card-dots">•••</span>
          </div>

          <div class="phase-bars-list">
            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">Drum Fill & Soak (0 - 8m)</span>
                <span class="phase-pct-txt">44.7 RMS</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 20%;"></div>
              </div>
            </div>

            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">Agitation & Tumble (8 - 22m)</span>
                <span class="phase-pct-txt">146.9 RMS</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 48%;"></div>
              </div>
            </div>

            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">Drain & Rinse (22 - 30m)</span>
                <span class="phase-pct-txt">227.0 RMS</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 68%;"></div>
              </div>
            </div>

            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">High-Speed Extraction (30 - 36m)</span>
                <span class="phase-pct-txt" style="color: var(--coral-accent);">511.2 RMS</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 95%; background: var(--coral-accent);"></div>
              </div>
            </div>
          </div>
        </div>

      </section>

    </main>
  </div>

  <!-- Embedded Wash 1019 Dataset & Logic -->
  <script>
'@

$templatePart2 = @'
    // State Variables
    const WASH_DATA = WASH_1019_DATA;
    let currentMode = 'historic'; // 'historic' or 'live'
    let currentIndex = 0;
    let isPlaying = false;
    let playInterval = null;
    let liveTimer = null;

    // Axis visibility
    const axisVisible = { x: true, y: true, z: true };

    // Canvas Elements
    const splineCvs = document.getElementById('spline-canvas');
    const xyzCvs = document.getElementById('xyz-canvas');
    const areaCvs = document.getElementById('area-canvas');
    const splineCtx = splineCvs.getContext('2d');
    const xyzCtx = xyzCvs.getContext('2d');
    const areaCtx = areaCvs.getContext('2d');

    // DOM Controls
    const timeSlider = document.getElementById('time-slider');
    const scrubLabel = document.getElementById('scrub-label');
    const lblCurrTime = document.getElementById('lbl-curr-time');
    const btnPlayWash = document.getElementById('btn-play-wash');
    const lblStatusText = document.getElementById('lbl-status-text');

    // KPI & Legend DOM
    const kpiAvgVibe = document.getElementById('kpi-avg-vibe');
    const kpiPeakVibe = document.getElementById('kpi-peak-vibe');
    const kpiAvgRms = document.getElementById('kpi-avg-rms');
    const kpiHealthScore = document.getElementById('kpi-health-score');
    const donutCenterNum = document.getElementById('donut-center-num');
    const donutArcTeal = document.getElementById('donut-arc-teal');

    const vibeLegX = document.getElementById('vibe-leg-x');
    const vibeLegY = document.getElementById('vibe-leg-y');
    const vibeLegZ = document.getElementById('vibe-leg-z');

    function resizeCanvases() {
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
    }
    window.addEventListener('resize', resizeCanvases);

    function formatMs(ms) {
      const totalSec = Math.floor(ms / 1000);
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    function toggleAxis(axis) {
      axisVisible[axis] = !axisVisible[axis];
      const pill = document.getElementById(`pill-tog-${axis}`);
      if (pill) {
        if (axisVisible[axis]) pill.classList.remove('dimmed');
        else pill.classList.add('dimmed');
      }
      drawXyz();
    }

    function applyRecord(rec) {
      const [t, ax, ay, az, rms] = rec;
      const vibe = Math.sqrt(ax*ax + ay*ay + az*az);
      const dg = Math.abs(vibe - 9.81);

      let health = 100;
      if (dg > 0.5) health -= (dg * 12);
      if (rms > 200) health -= ((rms - 200) * 0.08);
      health = Math.min(100, Math.max(40, Math.round(health)));

      kpiHealthScore.innerText = `${health}%`;
      donutCenterNum.innerText = `${health}%`;

      // Circumference = 2 * PI * 52 ~= 326
      const offset = 326 - (326 * (health / 100));
      donutArcTeal.style.strokeDashoffset = offset;

      const strX = (ax >= 0 ? '+' : '') + ax.toFixed(2);
      const strY = (ay >= 0 ? '+' : '') + ay.toFixed(2);
      const strZ = (az >= 0 ? '+' : '') + az.toFixed(2);

      vibeLegX.innerText = strX;
      vibeLegY.innerText = strY;
      vibeLegZ.innerText = strZ;

      const maxT = WASH_DATA[WASH_DATA.length - 1][0];
      lblCurrTime.innerText = `${formatMs(t)} / ${formatMs(maxT)}`;
    }

    // DRAW DEDICATED TRI-AXIAL VIBRATION (AX, AY, AZ)
    function drawXyz() {
      const w = xyzCvs.width;
      const h = xyzCvs.height;
      const dpr = window.devicePixelRatio || 1;
      xyzCtx.clearRect(0, 0, w, h);

      // Subtle grid lines
      xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      xyzCtx.lineWidth = 1;
      for (let i = 1; i <= 3; i++) {
        const y = (h / 4) * i;
        xyzCtx.beginPath();
        xyzCtx.moveTo(0, y);
        xyzCtx.lineTo(w, y);
        xyzCtx.stroke();
      }

      // Zero baseline (Ax & Ay) at 35% height
      const yZero = h * 0.35;
      xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      xyzCtx.setLineDash([4, 4]);
      xyzCtx.beginPath();
      xyzCtx.moveTo(0, yZero);
      xyzCtx.lineTo(w, yZero);
      xyzCtx.stroke();

      // Gravity baseline (Az at -9.81) at 78% height
      const yGravity = h * 0.78;
      xyzCtx.strokeStyle = 'rgba(167, 139, 250, 0.2)';
      xyzCtx.beginPath();
      xyzCtx.moveTo(0, yGravity);
      xyzCtx.lineTo(w, yGravity);
      xyzCtx.stroke();
      xyzCtx.setLineDash([]);

      // Baseline labels
      xyzCtx.fillStyle = 'rgba(255, 255, 255, 0.25)';
      xyzCtx.font = `600 ${9 * dpr}px 'JetBrains Mono', monospace`;
      xyzCtx.fillText('0.0 (X/Y)', 6 * dpr, yZero - (4 * dpr));
      xyzCtx.fillStyle = 'rgba(167, 139, 250, 0.4)';
      xyzCtx.fillText('-9.81g (Z)', 6 * dpr, yGravity - (4 * dpr));

      const winSize = 40;
      const startIdx = Math.max(0, currentIndex - (winSize / 2));
      const endIdx = Math.min(WASH_DATA.length - 1, startIdx + winSize);
      const points = WASH_DATA.slice(startIdx, endIdx + 1);

      if (points.length < 2) return;

      const scaleXY = 14 * dpr;
      const scaleZ = 16 * dpr;

      // 1. Plot Az (Purple)
      if (axisVisible.z) {
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#a78bfa';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {
          const x = (i / (points.length - 1)) * w;
          const az = points[i][3];
          const y = yGravity - ((az + 9.81) * scaleZ);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }
        xyzCtx.stroke();
      }

      // 2. Plot Ay (Coral)
      if (axisVisible.y) {
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#fb923c';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {
          const x = (i / (points.length - 1)) * w;
          const ay = points[i][2];
          const y = yZero - (ay * scaleXY);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }
        xyzCtx.stroke();
      }

      // 3. Plot Ax (Teal)
      if (axisVisible.x) {
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#00f0d2';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {
          const x = (i / (points.length - 1)) * w;
          const ax = points[i][1];
          const y = yZero - (ax * scaleXY);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }
        xyzCtx.stroke();
      }

      // Current point dots
      const curRel = currentIndex - startIdx;
      if (curRel >= 0 && curRel < points.length) {
        const cx = (curRel / (points.length - 1)) * w;
        if (axisVisible.x) {
          const cyX = yZero - (points[curRel][1] * scaleXY);
          xyzCtx.fillStyle = '#00f0d2';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyX, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }
        if (axisVisible.y) {
          const cyY = yZero - (points[curRel][2] * scaleXY);
          xyzCtx.fillStyle = '#fb923c';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyY, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }
        if (axisVisible.z) {
          const cyZ = yGravity - ((points[curRel][3] + 9.81) * scaleZ);
          xyzCtx.fillStyle = '#a78bfa';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyZ, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }
      }
    }

    // DRAW DUAL-MODALITY SPLINE WAVEFORM (Post Performance style)
    function drawSpline() {
      const w = splineCvs.width;
      const h = splineCvs.height;
      const dpr = window.devicePixelRatio || 1;
      splineCtx.clearRect(0, 0, w, h);

      // Subtle horizontal grid
      splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      splineCtx.lineWidth = 1;
      for (let i = 1; i <= 3; i++) {
        const y = (h / 4) * i;
        splineCtx.beginPath();
        splineCtx.moveTo(0, y);
        splineCtx.lineTo(w, y);
        splineCtx.stroke();
      }

      const winSize = 40;
      const startIdx = Math.max(0, currentIndex - (winSize / 2));
      const endIdx = Math.min(WASH_DATA.length - 1, startIdx + winSize);
      const points = WASH_DATA.slice(startIdx, endIdx + 1);

      if (points.length < 2) return;

      // 1. Draw Acoustic Wave (Coral with Translucent Fill)
      const gradCoral = splineCtx.createLinearGradient(0, 0, 0, h);
      gradCoral.addColorStop(0, 'rgba(251, 146, 60, 0.15)');
      gradCoral.addColorStop(1, 'rgba(251, 146, 60, 0.0)');

      splineCtx.beginPath();
      splineCtx.moveTo(0, h);
      for (let i = 0; i < points.length; i++) {
        const x = (i / (points.length - 1)) * w;
        const normRms = points[i][4] / 520.0;
        const y = h - (normRms * h * 0.75) - 10;
        splineCtx.lineTo(x, y);
      }
      splineCtx.lineTo(w, h);
      splineCtx.closePath();
      splineCtx.fillStyle = gradCoral;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#fb923c';
      splineCtx.lineWidth = 2.2 * dpr;
      for (let i = 0; i < points.length; i++) {
        const x = (i / (points.length - 1)) * w;
        const normRms = points[i][4] / 520.0;
        const y = h - (normRms * h * 0.75) - 10;
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }
      splineCtx.stroke();

      // 2. Draw Vibration Wave (Teal with Translucent Fill)
      const gradTeal = splineCtx.createLinearGradient(0, 0, 0, h);
      gradTeal.addColorStop(0, 'rgba(0, 240, 210, 0.2)');
      gradTeal.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

      splineCtx.beginPath();
      splineCtx.moveTo(0, h);
      for (let i = 0; i < points.length; i++) {
        const x = (i / (points.length - 1)) * w;
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = (h * 0.45) - ((v - 9.81) * 25 * dpr);
        splineCtx.lineTo(x, y);
      }
      splineCtx.lineTo(w, h);
      splineCtx.closePath();
      splineCtx.fillStyle = gradTeal;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#00f0d2';
      splineCtx.lineWidth = 2.2 * dpr;
      for (let i = 0; i < points.length; i++) {
        const x = (i / (points.length - 1)) * w;
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = (h * 0.45) - ((v - 9.81) * 25 * dpr);
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }
      splineCtx.stroke();

      // Current point dot
      const curRel = currentIndex - startIdx;
      if (curRel >= 0 && curRel < points.length) {
        const cx = (curRel / (points.length - 1)) * w;
        const normRms = points[curRel][4] / 520.0;
        const cyRms = h - (normRms * h * 0.75) - 10;
        splineCtx.fillStyle = '#fb923c';
        splineCtx.beginPath();
        splineCtx.arc(cx, cyRms, 4 * dpr, 0, Math.PI * 2);
        splineCtx.fill();
      }
    }

    // DRAW FULL AREA & TIMELINE (Most Active Times style in Image 3)
    function drawArea() {
      const w = areaCvs.width;
      const h = areaCvs.height;
      const dpr = window.devicePixelRatio || 1;
      areaCtx.clearRect(0, 0, w, h);

      // Grid
      areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      areaCtx.lineWidth = 1;
      for (let i = 1; i <= 3; i++) {
        const y = (h / 4) * i;
        areaCtx.beginPath();
        areaCtx.moveTo(0, y);
        areaCtx.lineTo(w, y);
        areaCtx.stroke();
      }

      const total = WASH_DATA.length;
      if (total < 2) return;

      // Area gradient in glowing teal
      const grad = areaCtx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, 'rgba(0, 240, 210, 0.25)');
      grad.addColorStop(0.8, 'rgba(0, 240, 210, 0.04)');
      grad.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

      areaCtx.beginPath();
      areaCtx.moveTo(0, h);
      for (let i = 0; i < total; i++) {
        const x = (i / (total - 1)) * w;
        const rms = WASH_DATA[i][4];
        const y = h - ((rms / 520.0) * (h - 20)) - 8;
        areaCtx.lineTo(x, y);
      }
      areaCtx.lineTo(w, h);
      areaCtx.closePath();
      areaCtx.fillStyle = grad;
      areaCtx.fill();

      // Top curve stroke
      areaCtx.beginPath();
      areaCtx.strokeStyle = '#00f0d2';
      areaCtx.lineWidth = 2 * dpr;
      for (let i = 0; i < total; i++) {
        const x = (i / (total - 1)) * w;
        const rms = WASH_DATA[i][4];
        const y = h - ((rms / 520.0) * (h - 20)) - 8;
        if (i === 0) areaCtx.moveTo(x, y); else areaCtx.lineTo(x, y);
      }
      areaCtx.stroke();

      // Scrubber cursor line
      const curX = (currentIndex / (total - 1)) * w;
      areaCtx.strokeStyle = '#00f0d2';
      areaCtx.lineWidth = 2;
      areaCtx.beginPath();
      areaCtx.moveTo(curX, 0);
      areaCtx.lineTo(curX, h);
      areaCtx.stroke();

      // Scrubber point
      const curRms = WASH_DATA[currentIndex][4];
      const curY = h - ((curRms / 520.0) * (h - 20)) - 8;
      areaCtx.fillStyle = '#00f0d2';
      areaCtx.beginPath();
      areaCtx.arc(curX, curY, 5 * dpr, 0, Math.PI * 2);
      areaCtx.fill();
    }

    function onScrub(val) {
      currentIndex = parseInt(val, 10);
      const minutes = ((WASH_DATA[currentIndex][0] / 60000)).toFixed(1);
      scrubLabel.innerText = `${minutes}m`;
      applyRecord(WASH_DATA[currentIndex]);
      drawSpline();
      drawXyz();
      drawArea();
    }

    function togglePlayPause() {
      isPlaying = !isPlaying;
      if (isPlaying) {
        btnPlayWash.innerText = '⏸ Pause Playback';
        playInterval = setInterval(() => {
          currentIndex++;
          if (currentIndex >= WASH_DATA.length) currentIndex = 0;
          timeSlider.value = currentIndex;
          onScrub(currentIndex);
        }, 80);
      } else {
        btnPlayWash.innerText = '▶ Replay Wash 1019';
        if (playInterval) clearInterval(playInterval);
      }
    }

    function setMode(mode) {
      currentMode = mode;
      if (mode === 'live') {
        if (isPlaying) togglePlayPause();
        lblStatusText.innerText = 'Live Streaming (50 Hz)';
        document.getElementById('acc-item-1').classList.remove('active');
        document.getElementById('acc-item-2').classList.add('active');
        startLivePolling();
      } else {
        if (liveTimer) clearInterval(liveTimer);
        lblStatusText.innerText = 'wash_1019 Active';
        document.getElementById('acc-item-2').classList.remove('active');
        document.getElementById('acc-item-1').classList.add('active');
        applyRecord(WASH_DATA[currentIndex]);
        drawSpline();
        drawXyz();
        drawArea();
      }
    }

    async function startLivePolling() {
      const fetchLive = async () => {
        try {
          const res = await fetch('https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app/live.json');
          const d = await res.json();
          if (d) {
            applyRecord([d.uptime * 1000, d.ax, d.ay, d.az, d.rms]);
            drawXyz();
            drawSpline();
          }
        } catch (e) {}
      };
      fetchLive();
      liveTimer = setInterval(fetchLive, 2000);
    }

    function downloadWashCsv() {
      let csv = 'timestamp_ms,accel_x,accel_y,accel_z,audio_rms\n';
      WASH_DATA.forEach(r => {
        csv += `${r[0]},${r[1]},${r[2]},${r[3]},${r[4]}\n`;
      });
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'wash_1019.csv';
      a.click();
    }

    function toggleMobileMenu() {
      const drawer = document.getElementById('mobile-drawer');
      const overlay = document.getElementById('drawer-overlay');
      drawer.classList.toggle('open');
      overlay.style.display = drawer.classList.contains('open') ? 'block' : 'none';
    }

    function toggleDoc() {
      window.open('hardware_bom_and_setup_guide.pdf', '_blank');
    }

    // Initialize
    setTimeout(() => {
      resizeCanvases();
      applyRecord(WASH_DATA[0]);
    }, 100);
  </script>
</body>
</html>
'@

$fullHtml = $templatePart1 + "`n" + $embeddedJs + "`n" + $templatePart2

[System.IO.File]::WriteAllText("g:\My Drive\PdM SideProject\dashboard.html", $fullHtml, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText("g:\My Drive\PdM SideProject\index.html", $fullHtml, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText("g:\My Drive\PdM SideProject\cloud_dashboard.html", $fullHtml, [System.Text.Encoding]::UTF8)

$brainArtifact = "C:\Users\adamd\.gemini\antigravity\brain\eaf1a310-7f2a-46d6-b3a7-72b474df813e\dashboard.html"
[System.IO.File]::WriteAllText($brainArtifact, $fullHtml, [System.Text.Encoding]::UTF8)

Write-Output "Complete! Sleek dark slate dashboard generated and written to all targets."
