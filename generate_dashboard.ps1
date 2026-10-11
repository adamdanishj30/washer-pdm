$embeddedJs = Get-Content "data/wash_1019_embedded.js" -Raw

$templatePart1 = @'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Samsung Washer PdM — Multimodal Cloud Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-body: #f4f7fc;
      --bg-card: #ffffff;
      --bg-card-sub: #f8fafc;
      --border-card: #e8edf5;
      --border-sub: #f1f5f9;
      --text-main: #1e293b;
      --text-muted: #64748b;
      --text-dim: #94a3b8;
      --primary-blue: #2563eb;
      --primary-blue-light: #eff6ff;
      --primary-blue-border: #dbeafe;
      --accent-coral: #f97316;
      --accent-coral-light: #fff7ed;
      --accent-emerald: #10b981;
      --accent-emerald-light: #ecfdf5;
      --accent-purple: #8b5cf6;
      --accent-purple-light: #f5f3ff;
      --shadow-sm: 0 1px 3px rgba(0,0,0,0.03), 0 1px 2px rgba(0,0,0,0.02);
      --shadow-card: 0 4px 20px -2px rgba(50, 60, 90, 0.05), 0 2px 6px -1px rgba(50, 60, 90, 0.03);
      --shadow-card-hover: 0 10px 25px -4px rgba(50, 60, 90, 0.08), 0 4px 10px -2px rgba(50, 60, 90, 0.04);
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
      background: #ffffff;
      border-bottom: 1px solid var(--border-card);
      padding: 12px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
      box-shadow: 0 1px 4px rgba(0,0,0,0.02);
    }

    .nav-left {
      display: flex;
      align-items: center;
      gap: 20px;
    }

    .brand-logo {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
    }

    .brand-name {
      font-size: 20px;
      font-weight: 800;
      color: var(--primary-blue);
      letter-spacing: -0.5px;
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #f1f5f9;
      border: 1px solid transparent;
      border-radius: 999px;
      padding: 8px 16px;
      width: 280px;
      transition: all 0.2s;
    }
    .search-box:focus-within {
      background: #ffffff;
      border-color: var(--primary-blue-border);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    .search-box input {
      border: none;
      background: transparent;
      outline: none;
      font-size: 13px;
      color: var(--text-main);
      width: 100%;
      font-family: inherit;
    }
    .search-box input::placeholder {
      color: var(--text-dim);
    }

    .nav-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .badge-live-tag {
      background: var(--accent-emerald-light);
      color: #059669;
      border: 1px solid #bbf7d0;
      border-radius: 999px;
      padding: 4px 12px;
      font-size: 11px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .badge-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
      animation: pulse-dot 2s infinite;
    }
    @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

    .btn-icon-light {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #f8fafc;
      border: 1px solid var(--border-card);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 14px;
      position: relative;
      transition: all 0.2s;
    }
    .btn-icon-light:hover {
      background: #f1f5f9;
      color: var(--text-main);
    }

    .notif-bubble {
      position: absolute;
      top: -2px;
      right: -2px;
      background: var(--accent-coral);
      color: #fff;
      font-size: 9px;
      font-weight: 800;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid #ffffff;
    }

    .user-profile {
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
    }
    .user-avatar-circle {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: linear-gradient(135deg, #2563eb, #3b82f6);
      color: #ffffff;
      font-weight: 700;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .user-profile-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
    }

    .hamburger-btn {
      display: none;
      background: none;
      border: none;
      color: var(--text-main);
      font-size: 22px;
      cursor: pointer;
    }

    /* App Layout */
    .app-layout {
      display: flex;
      flex: 1;
      max-width: 1560px;
      margin: 0 auto;
      width: 100%;
      padding: 24px;
      gap: 24px;
    }

    /* Clean White Sidebar */
    .sidebar {
      width: 220px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .sidebar-menu {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .sidebar-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-radius: 10px;
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      transition: all 0.2s;
      cursor: pointer;
    }
    .sidebar-item:hover {
      background: #f1f5f9;
      color: var(--text-main);
    }
    .sidebar-item.active {
      background: var(--primary-blue-light);
      color: var(--primary-blue);
      font-weight: 700;
    }

    .sidebar-card {
      background: #ffffff;
      border: 1px solid var(--border-card);
      border-radius: 16px;
      padding: 18px;
      box-shadow: var(--shadow-sm);
    }
    .sidebar-card h4 {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 4px;
    }
    .sidebar-card p {
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.4;
      margin-bottom: 14px;
    }
    .btn-side-action {
      width: 100%;
      padding: 9px 12px;
      border-radius: 8px;
      background: var(--primary-blue);
      color: #ffffff;
      border: none;
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-side-action:hover {
      background: #1d4ed8;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }

    /* Main Dashboard View */
    .main-view {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 20px;
      min-width: 0;
    }

    /* Section Title */
    .dashboard-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: -4px;
    }
    .page-title {
      font-size: 18px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.3px;
    }
    .page-subtitle {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
    }

    /* Card Styling */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 16px;
      padding: 20px;
      box-shadow: var(--shadow-card);
      transition: all 0.2s ease;
    }
    .card:hover {
      box-shadow: var(--shadow-card-hover);
    }

    /* Row 1: 4 Metric Cards (Matching tdlr style) */
    .row-metrics {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }

    .kpi-card {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 20px;
    }
    .kpi-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .kpi-label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      font-weight: 700;
    }
    .kpi-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 22px;
      font-weight: 800;
      color: var(--text-main);
      display: flex;
      align-items: baseline;
      gap: 4px;
    }
    .kpi-sub {
      font-size: 11px;
      color: var(--text-muted);
      font-weight: 500;
    }

    .kpi-icon-circle {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }
    .icon-blue { background: var(--primary-blue-light); color: var(--primary-blue); }
    .icon-coral { background: var(--accent-coral-light); color: var(--accent-coral); }
    .icon-purple { background: var(--accent-purple-light); color: var(--accent-purple); }
    .icon-emerald { background: var(--accent-emerald-light); color: var(--accent-emerald); }

    /* Row 2: Dual Waveform Spline & Multi-Segment Donut Ring */
    .row-charts-mid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
    }

    .card-header-clean {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .card-title-clean {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .legend-clean-row {
      display: flex;
      gap: 14px;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
    }
    .legend-dot-item {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .dot-blue { width: 8px; height: 8px; border-radius: 50%; background: var(--primary-blue); }
    .dot-coral { width: 8px; height: 8px; border-radius: 50%; background: var(--accent-coral); }
    .dot-emerald { width: 8px; height: 8px; border-radius: 50%; background: var(--accent-emerald); }

    .canvas-box-mid {
      position: relative;
      width: 100%;
      height: 190px;
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
    }

    /* Donut Ring Card (Right Column) */
    .card-donut-clean {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .donut-ring-wrap {
      position: relative;
      width: 130px;
      height: 130px;
      margin: 6px auto;
    }
    .donut-svg-clean {
      transform: rotate(-90deg);
      width: 100%;
      height: 100%;
    }
    .donut-bg-clean {
      fill: none;
      stroke: #f1f5f9;
      stroke-width: 12;
    }
    .donut-seg-blue {
      fill: none;
      stroke: var(--primary-blue);
      stroke-width: 12;
      stroke-linecap: round;
      stroke-dasharray: 326;
      stroke-dashoffset: 70;
      transition: stroke-dashoffset 0.4s;
    }
    .donut-seg-coral {
      fill: none;
      stroke: var(--accent-coral);
      stroke-width: 12;
      stroke-linecap: round;
      stroke-dasharray: 326;
      stroke-dashoffset: 240;
    }
    .donut-center-text {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
    }
    .donut-big-num {
      font-size: 24px;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-main);
    }
    .donut-sub-lbl {
      font-size: 10px;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-dim);
    }

    .donut-legend-list {
      display: flex;
      justify-content: space-around;
      padding-top: 10px;
      border-top: 1px solid var(--border-sub);
      font-size: 11px;
      color: var(--text-muted);
      font-weight: 600;
    }

    /* Row 3: Dedicated Tri-Axial Vibration (Ax, Ay, Az) Card */
    .row-xyz-dedicated {
      display: grid;
      grid-template-columns: 1fr;
    }

    .axis-pill-toggle {
      background: #f8fafc;
      border: 1px solid var(--border-card);
      border-radius: 999px;
      padding: 4px 12px;
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .axis-pill-toggle:hover {
      background: #f1f5f9;
    }
    .axis-pill-toggle.dimmed {
      opacity: 0.35;
      text-decoration: line-through;
    }

    /* Row 4: Timeline Scrubber (Sales Bar Chart style) & Phase Breakdown */
    .row-bottom-split {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 16px;
    }

    /* Scrubber Slider */
    .timeline-clean-box {
      display: flex;
      align-items: center;
      gap: 14px;
      background: var(--bg-card-sub);
      border: 1px solid var(--border-card);
      border-radius: 12px;
      padding: 10px 16px;
      margin-top: 12px;
    }
    .timeline-clean-box input[type="range"] {
      flex: 1;
      accent-color: var(--primary-blue);
      cursor: pointer;
    }
    .timeline-tag-time {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      color: var(--primary-blue);
      min-width: 60px;
    }

    /* Action Control Row */
    .actions-clean-row {
      display: flex;
      gap: 10px;
      margin-top: 14px;
    }
    .btn-clean-primary {
      padding: 10px 18px;
      border-radius: 10px;
      background: var(--primary-blue);
      color: #ffffff;
      border: none;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .btn-clean-primary:hover {
      background: #1d4ed8;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    .btn-clean-secondary {
      padding: 10px 18px;
      border-radius: 10px;
      background: #ffffff;
      color: var(--text-main);
      border: 1px solid var(--border-card);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .btn-clean-secondary:hover {
      background: #f8fafc;
      border-color: #cbd5e1;
    }

    /* Phase List Items ("Projects" list style) */
    .phase-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .phase-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-radius: 10px;
      background: var(--bg-card-sub);
      border: 1px solid var(--border-sub);
      transition: all 0.2s;
    }
    .phase-item:hover {
      border-color: var(--primary-blue-border);
      background: #ffffff;
    }
    .phase-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .phase-badge-num {
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: var(--primary-blue-light);
      color: var(--primary-blue);
      font-weight: 700;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .phase-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
    }
    .phase-desc {
      font-size: 11px;
      color: var(--text-muted);
    }
    .phase-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
    }

    /* Mobile Drawer Overlay */
    .mobile-drawer-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.4);
      backdrop-filter: blur(4px);
      z-index: 99;
    }
    .mobile-drawer {
      position: fixed;
      top: 0;
      bottom: 0;
      left: -280px;
      width: 260px;
      background: #ffffff;
      border-right: 1px solid var(--border-card);
      z-index: 100;
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .mobile-drawer.open {
      left: 0;
    }

    /* Responsive Breakpoints */
    @media (max-width: 1200px) {
      .row-metrics {
        grid-template-columns: repeat(2, 1fr);
      }
      .row-charts-mid {
        grid-template-columns: 1fr;
      }
      .row-bottom-split {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 768px) {
      .top-nav {
        padding: 10px 16px;
      }
      .search-box {
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
      .row-metrics {
        grid-template-columns: 1fr;
      }
      .card {
        padding: 16px;
      }
    }
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <header class="top-nav">
    <div class="nav-left">
      <button class="hamburger-btn" onclick="toggleMobileMenu()">☰</button>
      <a href="#" class="brand-logo">
        <span class="brand-name">tdlr<span style="color: var(--primary-blue);">.</span></span>
      </a>
      <div class="search-box">
        <span style="color: var(--text-dim); font-size: 14px;">🔍</span>
        <input type="text" placeholder="Search machine telemetry, ISO 10816...">
      </div>
    </div>

    <div class="nav-right">
      <div class="badge-live-tag" id="badge-live">
        <span class="badge-dot"></span>
        <span id="lbl-live-text">wash_1019 Active</span>
      </div>

      <div class="btn-icon-light" onclick="downloadWashCsv()" title="Download CSV">
        📥
      </div>
      <div class="btn-icon-light" title="Notifications">
        🔔
        <span class="notif-bubble">1</span>
      </div>

      <div class="user-profile">
        <div class="user-avatar-circle">AD</div>
        <span class="user-profile-name">Adam D.</span>
      </div>
    </div>
  </header>

  <!-- Mobile Drawer -->
  <div class="mobile-drawer-overlay" id="drawer-overlay" onclick="toggleMobileMenu()"></div>
  <aside class="mobile-drawer" id="mobile-drawer">
    <div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <span class="brand-name">tdlr<span style="color: var(--primary-blue);">.</span></span>
        <button onclick="toggleMobileMenu()" style="background:none; border:none; font-size:20px; cursor:pointer;">✕</button>
      </div>
      <div class="sidebar-menu">
        <a class="sidebar-item active" onclick="setMode('historic'); toggleMobileMenu()">📊 Wash 1019 Run</a>
        <a class="sidebar-item" onclick="setMode('live'); toggleMobileMenu()">📡 Live ESP32 Stream</a>
        <a class="sidebar-item" onclick="downloadWashCsv()">💾 Download wash_1019.csv</a>
        <a class="sidebar-item" onclick="toggleMobileMenu()">🛡️ ISO 10816 Standards</a>
      </div>
    </div>
    <div class="sidebar-card">
      <h4>Firebase Cloud</h4>
      <p>422 multimodal records synced over Asia-SE1.</p>
      <button class="btn-side-action" onclick="downloadWashCsv()">📥 Export CSV</button>
    </div>
  </aside>

  <!-- App Layout -->
  <div class="app-layout">
    
    <!-- Clean Minimalist Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-menu">
        <div class="sidebar-item active" id="side-item-1" onclick="setMode('historic')">
          <span>📊</span> Dashboard
        </div>
        <div class="sidebar-item" id="side-item-2" onclick="setMode('live')">
          <span>📡</span> Live Telemetry
        </div>
        <div class="sidebar-item" onclick="toggleAxis('x')">
          <span>📳</span> Tri-Axial IMU
        </div>
        <div class="sidebar-item" onclick="openPdfDoc()">
          <span>📑</span> Setup Guide
        </div>
        <div class="sidebar-item" onclick="openPdfDoc()">
          <span>⚙️</span> Settings
        </div>
      </div>

      <div class="sidebar-card">
        <h4>Samsung Washer PdM</h4>
        <p>WW10TP44DSX/FQ front-load rotating machine diagnostics.</p>
        <button class="btn-side-action" onclick="downloadWashCsv()">📥 Export CSV</button>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="main-view">

      <!-- Header Title Row -->
      <div class="dashboard-header-row">
        <div>
          <h2 class="page-title">Dashboard</h2>
          <p class="page-subtitle">Multimodal Machine Learning PdM • ESP32 DevKit V1 (MPU-6050 + INMP441)</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn-clean-secondary" style="padding: 6px 14px; font-size: 12px;" onclick="setMode(currentMode === 'live' ? 'historic' : 'live')">
            <span id="btn-mode-toggle-text">Mode: Wash 1019 Cycle</span> ⇄
          </button>
        </div>
      </div>

      <!-- Row 1: 4 Clean KPI Cards -->
      <section class="row-metrics">
        
        <!-- Card 1: Resultant Vibration -->
        <div class="card kpi-card">
          <div class="kpi-info">
            <span class="kpi-label">Avg Vibration</span>
            <div class="kpi-val" style="color: var(--primary-blue);" id="kpi-avg-vibe">
              9.58 <span class="kpi-sub">m/s²</span>
            </div>
            <span class="kpi-sub">Static Gravity: 1.0g</span>
          </div>
          <div class="kpi-icon-circle icon-blue">📳</div>
        </div>

        <!-- Card 2: Peak Vibration -->
        <div class="card kpi-card">
          <div class="kpi-info">
            <span class="kpi-label">Peak Vibration</span>
            <div class="kpi-val" style="color: var(--accent-coral);" id="kpi-peak-vibe">
              10.14 <span class="kpi-sub">m/s²</span>
            </div>
            <span class="kpi-sub" style="color: #ea580c;">Spin Extraction</span>
          </div>
          <div class="kpi-icon-circle icon-coral">📈</div>
        </div>

        <!-- Card 3: Acoustic Noise -->
        <div class="card kpi-card">
          <div class="kpi-info">
            <span class="kpi-label">Acoustic Energy</span>
            <div class="kpi-val" style="color: var(--accent-purple);" id="kpi-avg-rms">
              146.9 <span class="kpi-sub">RMS</span>
            </div>
            <span class="kpi-sub">Peak: 511.2 RMS</span>
          </div>
          <div class="kpi-icon-circle icon-purple">🎙️</div>
        </div>

        <!-- Card 4: Machine Health -->
        <div class="card kpi-card">
          <div class="kpi-info">
            <span class="kpi-label">Health Score</span>
            <div class="kpi-val" style="color: var(--accent-emerald);" id="kpi-health-score">
              94%
            </div>
            <span class="kpi-sub" style="color: #059669;">ISO 10816 Class I</span>
          </div>
          <div class="kpi-icon-circle icon-emerald">🛡️</div>
        </div>

      </section>

      <!-- Row 2: Conversions Spline Waveform & Traffic Channels Donut -->
      <section class="row-charts-mid">
        
        <!-- Spline Dual-Modality Waveform (Conversions Style) -->
        <div class="card">
          <div class="card-header-clean">
            <div>
              <h3 class="card-title-clean">Dual-Modality Spline Waveform</h3>
              <p style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">Synchronized vibration acceleration vs. acoustic sound pressure</p>
            </div>
            <div class="legend-clean-row">
              <span class="legend-dot-item"><span class="dot-blue"></span> Vibration |a|</span>
              <span class="legend-dot-item"><span class="dot-coral"></span> Acoustic RMS</span>
            </div>
          </div>

          <div class="canvas-box-mid">
            <canvas id="spline-canvas"></canvas>
          </div>
        </div>

        <!-- Clean Donut Multi-Segment Ring (Traffic Channels Style) -->
        <div class="card card-donut-clean">
          <div class="card-header-clean" style="margin-bottom: 0;">
            <h3 class="card-title-clean">Machinery Status</h3>
            <span style="font-size: 11px; color: var(--text-dim);">Real-Time</span>
          </div>

          <div class="donut-ring-wrap">
            <svg class="donut-svg-clean" viewBox="0 0 130 130">
              <circle class="donut-bg-clean" cx="65" cy="65" r="52"></circle>
              <circle class="donut-seg-blue" id="donut-fill-seg" cx="65" cy="65" r="52"></circle>
              <circle class="donut-seg-coral" cx="65" cy="65" r="52"></circle>
            </svg>
            <div class="donut-center-text">
              <span class="donut-big-num" id="donut-center-num">94%</span>
              <span class="donut-sub-lbl">Health</span>
            </div>
          </div>

          <div class="donut-legend-list">
            <span class="legend-dot-item"><span class="dot-blue"></span> Normal</span>
            <span class="legend-dot-item"><span class="dot-coral"></span> Dynamic</span>
            <span class="legend-dot-item"><span class="dot-emerald"></span> Stable</span>
          </div>
        </div>

      </section>

      <!-- Row 3: DEDICATED Tri-Axial Vibration (Ax, Ay, Az) Graph -->
      <section class="row-xyz-dedicated">
        <div class="card">
          <div class="card-header-clean">
            <div>
              <h3 class="card-title-clean">Tri-Axial Vibration (Ax, Ay, Az)</h3>
              <p style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">MPU-6050 direct ±16g accelerometer register burst reading</p>
            </div>
            <div style="display: flex; gap: 8px;">
              <span class="axis-pill-toggle" id="pill-tog-x" style="color: var(--primary-blue);" onclick="toggleAxis('x')">
                <span style="width: 7px; height: 7px; border-radius: 50%; background: var(--primary-blue);"></span>
                Ax: <strong id="vibe-leg-x">-0.72</strong> m/s²
              </span>
              <span class="axis-pill-toggle" id="pill-tog-y" style="color: var(--accent-coral);" onclick="toggleAxis('y')">
                <span style="width: 7px; height: 7px; border-radius: 50%; background: var(--accent-coral);"></span>
                Ay: <strong id="vibe-leg-y">+1.41</strong> m/s²
              </span>
              <span class="axis-pill-toggle" id="pill-tog-z" style="color: var(--accent-emerald);" onclick="toggleAxis('z')">
                <span style="width: 7px; height: 7px; border-radius: 50%; background: var(--accent-emerald);"></span>
                Az: <strong id="vibe-leg-z">-9.44</strong> m/s²
              </span>
            </div>
          </div>

          <div class="canvas-box-mid" style="height: 180px;">
            <canvas id="xyz-canvas"></canvas>
          </div>
        </div>
      </section>

      <!-- Row 4: Full 35.9-min Timeline Scrubber (Sales Bar Chart style) & Phase Breakdown -->
      <section class="row-bottom-split">
        
        <!-- Full Timeline & Controls -->
        <div class="card">
          <div class="card-header-clean">
            <div>
              <h3 class="card-title-clean">Wash Cycle 1019 Full Timeline (35.9 Minutes)</h3>
              <p style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">422 real recorded time-series frames from Samsung front-load washer</p>
            </div>
            <span style="font-size: 13px; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--primary-blue);" id="lbl-curr-time">
              00:00 / 35:54
            </span>
          </div>

          <div class="canvas-box-mid" style="height: 160px;">
            <canvas id="area-canvas"></canvas>
          </div>

          <!-- Timeline Scrubber -->
          <div class="timeline-clean-box">
            <span style="font-size: 12px; font-weight: 600; color: var(--text-muted);">Scrub Timeline:</span>
            <input type="range" id="time-slider" min="0" max="421" value="0" oninput="onScrub(this.value)">
            <span class="timeline-tag-time" id="scrub-label">0.0m</span>
          </div>

          <!-- Action Buttons -->
          <div class="actions-clean-row">
            <button class="btn-clean-primary" onclick="togglePlayPause()" id="btn-play-wash">
              ▶ Replay Wash 1019
            </button>
            <button class="btn-clean-secondary" onclick="downloadWashCsv()">
              📥 Download wash_1019.csv
            </button>
            <button class="btn-clean-secondary" onclick="setMode('live')">
              ⚡ Connect Live Firebase
            </button>
          </div>
        </div>

        <!-- Phase List ("Projects" style list from reference image) -->
        <div class="card">
          <div class="card-header-clean">
            <h3 class="card-title-clean">Wash Phases & Cycle Breakdown</h3>
            <span style="font-size: 12px; color: var(--primary-blue); font-weight: 600; cursor: pointer;">Samsung WW10T</span>
          </div>

          <div class="phase-list">
            <div class="phase-item">
              <div class="phase-left">
                <div class="phase-badge-num">1</div>
                <div>
                  <div class="phase-title">Drum Fill & Soak</div>
                  <div class="phase-desc">0 - 8 mins • Water inlet valve</div>
                </div>
              </div>
              <span class="phase-val" style="color: var(--primary-blue);">44.7 RMS</span>
            </div>

            <div class="phase-item">
              <div class="phase-left">
                <div class="phase-badge-num">2</div>
                <div>
                  <div class="phase-title">Agitation & Wash Tumble</div>
                  <div class="phase-desc">8 - 22 mins • Direct drive motor 50 RPM</div>
                </div>
              </div>
              <span class="phase-val" style="color: var(--primary-blue);">146.9 RMS</span>
            </div>

            <div class="phase-item">
              <div class="phase-left">
                <div class="phase-badge-num">3</div>
                <div>
                  <div class="phase-title">Intermediate Drain & Rinse</div>
                  <div class="phase-desc">22 - 30 mins • Drain pump active</div>
                </div>
              </div>
              <span class="phase-val" style="color: var(--accent-coral);">227.0 RMS</span>
            </div>

            <div class="phase-item">
              <div class="phase-left">
                <div class="phase-badge-num">4</div>
                <div>
                  <div class="phase-title">High-Speed Spin Extraction</div>
                  <div class="phase-desc">30 - 35.9 mins • 1400 RPM spin</div>
                </div>
              </div>
              <span class="phase-val" style="color: #dc2626;">511.2 RMS</span>
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
    const btnModeToggleText = document.getElementById('btn-mode-toggle-text');
    const lblLiveText = document.getElementById('lbl-live-text');

    // KPI & Legend DOM
    const kpiAvgVibe = document.getElementById('kpi-avg-vibe');
    const kpiPeakVibe = document.getElementById('kpi-peak-vibe');
    const kpiAvgRms = document.getElementById('kpi-avg-rms');
    const kpiHealthScore = document.getElementById('kpi-health-score');
    const donutCenterNum = document.getElementById('donut-center-num');
    const donutFillSeg = document.getElementById('donut-fill-seg');

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
      donutFillSeg.style.strokeDashoffset = offset;

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

      // Light grid lines
      xyzCtx.strokeStyle = '#f1f5f9';
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
      xyzCtx.strokeStyle = '#e2e8f0';
      xyzCtx.setLineDash([4, 4]);
      xyzCtx.beginPath();
      xyzCtx.moveTo(0, yZero);
      xyzCtx.lineTo(w, yZero);
      xyzCtx.stroke();

      // Gravity baseline (Az at -9.81) at 78% height
      const yGravity = h * 0.78;
      xyzCtx.strokeStyle = '#bbf7d0';
      xyzCtx.beginPath();
      xyzCtx.moveTo(0, yGravity);
      xyzCtx.lineTo(w, yGravity);
      xyzCtx.stroke();
      xyzCtx.setLineDash([]);

      // Baseline labels
      xyzCtx.fillStyle = '#94a3b8';
      xyzCtx.font = `600 ${9 * dpr}px 'JetBrains Mono', monospace`;
      xyzCtx.fillText('0.0 (X/Y)', 6 * dpr, yZero - (4 * dpr));
      xyzCtx.fillStyle = '#10b981';
      xyzCtx.fillText('-9.81g (Z)', 6 * dpr, yGravity - (4 * dpr));

      const winSize = 40;
      const startIdx = Math.max(0, currentIndex - (winSize / 2));
      const endIdx = Math.min(WASH_DATA.length - 1, startIdx + winSize);
      const points = WASH_DATA.slice(startIdx, endIdx + 1);

      if (points.length < 2) return;

      const scaleXY = 14 * dpr;
      const scaleZ = 16 * dpr;

      // 1. Plot Az (Emerald)
      if (axisVisible.z) {
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#10b981';
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
        xyzCtx.strokeStyle = '#f97316';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {
          const x = (i / (points.length - 1)) * w;
          const ay = points[i][2];
          const y = yZero - (ay * scaleXY);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }
        xyzCtx.stroke();
      }

      // 3. Plot Ax (Royal Blue)
      if (axisVisible.x) {
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#2563eb';
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
          xyzCtx.fillStyle = '#2563eb';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyX, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }
        if (axisVisible.y) {
          const cyY = yZero - (points[curRel][2] * scaleXY);
          xyzCtx.fillStyle = '#f97316';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyY, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }
        if (axisVisible.z) {
          const cyZ = yGravity - ((points[curRel][3] + 9.81) * scaleZ);
          xyzCtx.fillStyle = '#10b981';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyZ, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }
      }
    }

    // DRAW DUAL-MODALITY SPLINE WAVEFORM (Conversions Style)
    function drawSpline() {
      const w = splineCvs.width;
      const h = splineCvs.height;
      const dpr = window.devicePixelRatio || 1;
      splineCtx.clearRect(0, 0, w, h);

      // Light horizontal grid
      splineCtx.strokeStyle = '#f1f5f9';
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

      // 1. Draw Acoustic Wave (Coral with Soft Gradient Fill)
      const gradCoral = splineCtx.createLinearGradient(0, 0, 0, h);
      gradCoral.addColorStop(0, 'rgba(249, 115, 22, 0.18)');
      gradCoral.addColorStop(1, 'rgba(249, 115, 22, 0.0)');

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
      splineCtx.strokeStyle = '#f97316';
      splineCtx.lineWidth = 2.5 * dpr;
      for (let i = 0; i < points.length; i++) {
        const x = (i / (points.length - 1)) * w;
        const normRms = points[i][4] / 520.0;
        const y = h - (normRms * h * 0.75) - 10;
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }
      splineCtx.stroke();

      // 2. Draw Vibration Wave (Royal Blue with Soft Gradient Fill)
      const gradBlue = splineCtx.createLinearGradient(0, 0, 0, h);
      gradBlue.addColorStop(0, 'rgba(37, 99, 235, 0.2)');
      gradBlue.addColorStop(1, 'rgba(37, 99, 235, 0.0)');

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
      splineCtx.fillStyle = gradBlue;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#2563eb';
      splineCtx.lineWidth = 2.5 * dpr;
      for (let i = 0; i < points.length; i++) {
        const x = (i / (points.length - 1)) * w;
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = (h * 0.45) - ((v - 9.81) * 25 * dpr);
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }
      splineCtx.stroke();

      // Current dot marker
      const curRel = currentIndex - startIdx;
      if (curRel >= 0 && curRel < points.length) {
        const cx = (curRel / (points.length - 1)) * w;
        const normRms = points[curRel][4] / 520.0;
        const cyRms = h - (normRms * h * 0.75) - 10;
        splineCtx.fillStyle = '#f97316';
        splineCtx.beginPath();
        splineCtx.arc(cx, cyRms, 4 * dpr, 0, Math.PI * 2);
        splineCtx.fill();
      }
    }

    // DRAW FULL AREA & TIMELINE BARS (Sales Style)
    function drawArea() {
      const w = areaCvs.width;
      const h = areaCvs.height;
      const dpr = window.devicePixelRatio || 1;
      areaCtx.clearRect(0, 0, w, h);

      // Light grid
      areaCtx.strokeStyle = '#f1f5f9';
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

      // Area gradient in light royal blue
      const grad = areaCtx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, 'rgba(37, 99, 235, 0.25)');
      grad.addColorStop(0.8, 'rgba(37, 99, 235, 0.04)');
      grad.addColorStop(1, 'rgba(37, 99, 235, 0.0)');

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
      areaCtx.strokeStyle = '#2563eb';
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
      areaCtx.strokeStyle = '#2563eb';
      areaCtx.lineWidth = 2;
      areaCtx.beginPath();
      areaCtx.moveTo(curX, 0);
      areaCtx.lineTo(curX, h);
      areaCtx.stroke();

      // Scrubber circle
      const curRms = WASH_DATA[currentIndex][4];
      const curY = h - ((curRms / 520.0) * (h - 20)) - 8;
      areaCtx.fillStyle = '#2563eb';
      areaCtx.beginPath();
      areaCtx.arc(curX, curY, 5 * dpr, 0, Math.PI * 2);
      areaCtx.fill();
      areaCtx.strokeStyle = '#ffffff';
      areaCtx.lineWidth = 2 * dpr;
      areaCtx.stroke();
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
        btnModeToggleText.innerText = 'Mode: Live Firebase Rig';
        lblLiveText.innerText = 'Live Streaming (50 Hz)';
        document.getElementById('side-item-1').classList.remove('active');
        document.getElementById('side-item-2').classList.add('active');
        startLivePolling();
      } else {
        if (liveTimer) clearInterval(liveTimer);
        btnModeToggleText.innerText = 'Mode: Wash 1019 Cycle';
        lblLiveText.innerText = 'wash_1019 Active';
        document.getElementById('side-item-2').classList.remove('active');
        document.getElementById('side-item-1').classList.add('active');
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

    function openPdfDoc() {
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

Write-Output "Complete! Light aesthetic dashboard generated and written to all targets."
