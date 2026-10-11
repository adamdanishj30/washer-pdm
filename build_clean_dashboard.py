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

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Samsung Washer PdM - Vibration &amp; Acoustic Spike Monitor</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
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

    /* Top Navigation Bar */
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

    /* Center Tabs */
    .nav-tabs-center {{
      display: flex;
      align-items: center;
      gap: 24px;
    }}
    .nav-tab-item {{
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      text-decoration: none;
      transition: color 0.2s;
      position: relative;
      padding: 6px 0;
    }}
    .nav-tab-item:hover {{
      color: #fff;
    }}
    .nav-tab-item.active {{
      color: #fff;
    }}
    .nav-tab-item.active::after {{
      content: '';
      position: absolute;
      bottom: -16px;
      left: 0;
      right: 0;
      height: 2px;
      background: var(--teal-accent);
      border-radius: 2px;
    }}

    /* Right Controls: Status & CSV (NO User Profile) */
    .nav-right {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .status-badge {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 240, 210, 0.08);
      border: 1px solid rgba(0, 240, 210, 0.2);
      padding: 5px 12px;
      border-radius: 20px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      color: var(--teal-accent);
    }}
    .status-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--teal-accent);
      box-shadow: 0 0 8px var(--teal-accent);
      animation: pulse-glow 2s infinite;
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

    .hamburger-btn {{
      display: none;
      background: none;
      border: none;
      color: var(--text-main);
      cursor: pointer;
      padding: 4px;
    }}

    /* Main Container with Sidebar */
    .app-layout {{
      display: grid;
      grid-template-columns: 240px 1fr;
      flex: 1;
      min-height: calc(100vh - 65px);
    }}

    /* Left Sidebar */
    .sidebar {{
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-card);
      padding: 24px 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .sidebar-section-title {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-dim);
      margin-bottom: 14px;
      padding-left: 6px;
    }}

    .account-item {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 10px;
      cursor: pointer;
      transition: background 0.2s;
      margin-bottom: 6px;
    }}
    .account-item:hover {{
      background: rgba(255, 255, 255, 0.03);
    }}
    .account-item.active {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
    }}
    .account-avatar-ring {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: rgba(0, 240, 210, 0.15);
      border: 1px solid var(--teal-accent);
      color: var(--teal-accent);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 13px;
    }}
    .account-avatar-ring.avatar-coral {{
      background: rgba(251, 146, 60, 0.15);
      border-color: var(--coral-accent);
      color: var(--coral-accent);
    }}
    .account-avatar-ring.avatar-purple {{
      background: rgba(167, 139, 250, 0.15);
      border-color: var(--purple-accent);
      color: var(--purple-accent);
    }}
    .account-meta {{
      display: flex;
      flex-direction: column;
    }}
    .account-name {{
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
    }}
    .account-sub {{
      font-size: 11px;
      color: var(--text-dim);
    }}

    .sidebar-info-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 12px;
      padding: 16px;
    }}
    .sidebar-info-card h4 {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 6px;
    }}
    .sidebar-info-card p {{
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.5;
      margin-bottom: 12px;
    }}

    /* Main View Area */
    .main-view {{
      padding: 24px 32px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      max-width: 1440px;
    }}

    /* Cards */
    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 14px;
      padding: 20px;
      position: relative;
    }}

    .card-header-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }}
    .card-title-text {{
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .card-menu-dots {{
      display: flex;
      align-items: center;
      gap: 3px;
      opacity: 0.4;
      cursor: pointer;
    }}
    .card-menu-dots:hover {{
      opacity: 1;
    }}
    .mini-dot {{
      width: 3.5px;
      height: 3.5px;
      background: #fff;
      border-radius: 50%;
      display: inline-block;
    }}

    /* Row 1: Top 3 Metric Cards */
    .row-top-three {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}

    .dual-metric-flex {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
    }}
    .dual-metric-col {{
      display: flex;
      flex-direction: column;
    }}
    .metric-big-num {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 26px;
      font-weight: 700;
      color: #fff;
      line-height: 1.1;
    }}
    .metric-sub-lbl {{
      font-size: 11px;
      color: var(--text-dim);
      margin-top: 4px;
    }}

    .stat-with-badge {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-top: 2px;
    }}
    .badge-percent {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: var(--teal-accent);
    }}
    .badge-coral {{
      color: var(--coral-accent);
    }}

    /* Row 2: Middle Section */
    .row-middle {{
      display: grid;
      grid-template-columns: 1.8fr 1fr;
      gap: 16px;
    }}

    .chart-legend-row {{
      display: flex;
      align-items: center;
      gap: 14px;
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

    .canvas-container-mid {{
      position: relative;
      width: 100%;
      height: 180px;
    }}
    canvas {{
      width: 100%;
      height: 100%;
      display: block;
    }}

    /* Live Spike & Intensity Box (replaces donut) */
    .spike-monitor-box {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      height: 100%;
      padding-top: 2px;
    }}
    .spike-primary-readout {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .spike-pill-badge {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px solid currentColor;
      transition: all 0.2s ease;
    }}
    .spike-bar-wrap {{
      margin: 14px 0 10px 0;
    }}
    .spike-bar-track {{
      position: relative;
      width: 100%;
      height: 10px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 6px;
    }}
    .spike-bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, #00f0d2 0%, #38bdf8 45%, #fb923c 85%);
      border-radius: 6px;
      transition: width 0.12s ease;
    }}
    .spike-bar-pin {{
      position: absolute;
      top: -4px;
      width: 4px;
      height: 18px;
      background: #ffffff;
      border-radius: 2px;
      box-shadow: 0 0 8px rgba(255, 255, 255, 0.9);
      transition: left 0.12s ease;
      transform: translateX(-50%);
    }}
    .spike-bar-scale {{
      display: flex;
      justify-content: space-between;
      font-size: 9.5px;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-dim);
      margin-top: 6px;
    }}
    .spike-stat-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      padding-top: 10px;
      border-top: 1px solid var(--border-sub);
    }}
    .spike-stat-cell {{
      background: var(--bg-inner);
      padding: 7px 10px;
      border-radius: 6px;
      border: 1px solid var(--border-card);
      display: flex;
      flex-direction: column;
    }}
    .spike-stat-lbl {{
      font-size: 10px;
      color: var(--text-dim);
      font-weight: 600;
    }}
    .spike-stat-val {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
      margin-top: 2px;
    }}

    /* Row 3: Dedicated Tri-Axial Vibration (Ax, Ay, Az) */
    .row-xyz-full {{
      display: grid;
      grid-template-columns: 1fr;
    }}

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

    /* Row 4: Bottom Section (Timeline & Phase breakdown) */
    .row-bottom {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
    }}

    /* Horizontal Phase Bars */
    .phase-bars-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-top: 4px;
    }}
    .phase-bar-row {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .phase-header-flex {{
      display: flex;
      justify-content: space-between;
      font-size: 11.5px;
      font-weight: 600;
    }}
    .phase-name-txt {{
      color: var(--text-muted);
    }}
    .phase-pct-txt {{
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-main);
    }}
    .progress-track-dark {{
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 4px;
      overflow: hidden;
    }}
    .progress-fill-teal {{
      height: 100%;
      background: var(--teal-accent);
      border-radius: 4px;
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

    /* Mobile Drawer */
    .mobile-drawer {{
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      width: 260px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-card);
      z-index: 100;
      transform: translateX(-100%);
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      padding: 24px 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .mobile-drawer.open {{
      transform: translateX(0);
    }}
    .mobile-drawer-overlay {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(4px);
      z-index: 99;
      display: none;
    }}

    @media (max-width: 1024px) {{
      .app-layout {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        display: none;
      }}
      .hamburger-btn {{
        display: block;
      }}
      .row-middle {{
        grid-template-columns: 1fr;
      }}
      .row-bottom {{
        grid-template-columns: 1fr;
      }}
      .main-view {{
        padding: 16px;
      }}
      .top-nav {{
        padding: 12px 16px;
      }}
      .nav-tabs-center {{
        display: none;
      }}
    }}

    @media (max-width: 768px) {{
      .row-top-three {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>

  <!-- Top Sticky Header -->
  <header class="top-nav">
    <div class="nav-left">
      <button class="hamburger-btn" onclick="toggleMobileMenu()">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="5" x2="17" y2="5"></line>
          <line x1="3" y1="10" x2="17" y2="10"></line>
          <line x1="3" y1="15" x2="17" y2="15"></line>
        </svg>
      </button>
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
        <button onclick="toggleMobileMenu()" style="background:none; border:none; color:#fff; font-size:20px; cursor:pointer;">&times;</button>
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
    
    <!-- Sidebar: Nodes list -->
    <aside class="sidebar">
      <div>
        <div class="sidebar-section-title">Nodes &amp; Sensors</div>
        
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
            <span class="account-sub">I2C 0x68 (&plusmn;16g)</span>
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
        <p>10kg Front-Load Anomaly &amp; Vibration Monitor.</p>
        <button class="btn-dark-primary" style="width: 100%;" onclick="downloadWashCsv()">Download CSV</button>
      </div>
    </aside>

    <!-- Main View -->
    <main class="main-view">

      <!-- Row 1: Top 3 Metric Cards -->
      <section class="row-top-three">
        
        <!-- Card 1: Resultant Vibration -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Vibration Resultant</span>
            <div class="card-menu-dots">
              <span class="mini-dot"></span><span class="mini-dot"></span><span class="mini-dot"></span>
            </div>
          </div>
          <div class="dual-metric-flex">
            <div class="dual-metric-col">
              <span class="metric-big-num" style="color: var(--teal-accent);" id="kpi-avg-vibe">9.58</span>
              <span class="metric-sub-lbl">Avg (m/s&sup2;)</span>
            </div>
            <div class="dual-metric-col">
              <span class="metric-big-num" style="color: var(--coral-accent);" id="kpi-peak-vibe">10.14</span>
              <span class="metric-sub-lbl">Peak Spin (m/s&sup2;)</span>
            </div>
          </div>
        </div>

        <!-- Card 2: Acoustic Sound Level -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Acoustic Sound Level</span>
            <div class="card-menu-dots">
              <span class="mini-dot"></span><span class="mini-dot"></span><span class="mini-dot"></span>
            </div>
          </div>
          <div>
            <div class="stat-with-badge">
              <span class="metric-big-num" style="font-size: 24px; color: var(--teal-accent);" id="kpi-curr-rms">44.7</span>
              <span class="badge-percent" id="kpi-rms-badge">BASELINE</span>
            </div>
            <span class="metric-sub-lbl">Instantaneous Acoustic RMS</span>
            <div class="stat-with-badge" style="margin-top: 8px;">
              <span class="metric-big-num" style="font-size: 18px; color: var(--coral-accent);" id="kpi-peak-rms">511.2</span>
              <span class="badge-percent badge-coral">+326% Peak</span>
            </div>
            <span class="metric-sub-lbl">Wash Cycle Max Extraction Spike</span>
          </div>
        </div>

        <!-- Card 3: Instantaneous Spike Ratio -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Instantaneous Spike Ratio</span>
            <div class="card-menu-dots">
              <span class="mini-dot"></span><span class="mini-dot"></span><span class="mini-dot"></span>
            </div>
          </div>
          <div class="stat-with-badge" style="margin-top: 4px;">
            <span class="metric-big-num" style="color: var(--coral-accent);" id="kpi-spike-factor">1.0x</span>
            <span class="badge-percent" id="kpi-spike-badge" style="color: var(--teal-accent);">BASELINE</span>
          </div>
          <span class="metric-sub-lbl" id="kpi-spike-detail">Current: 44.7 RMS (Normal: 120 RMS)</span>
          <div style="font-size: 11px; color: var(--text-dim); margin-top: 10px; display: flex; justify-content: space-between;">
            <span>Cycle Max Spike: <strong style="color: #fff;" id="kpi-max-spike">511.2 RMS</strong></span>
            <span style="color: var(--coral-accent); font-weight: 700;">+326% Peak</span>
          </div>
        </div>

      </section>

      <!-- Row 2: Middle Section -->
      <section class="row-middle">
        
        <!-- Dual-Modality Waveform -->
        <div class="card">
          <div class="card-header-row">
            <div>
              <span class="card-title-text">Dual-Modality Telemetry</span>
              <span style="font-size: 11px; color: var(--text-dim); display: block; margin-top: 2px;">Vibration resultant &amp; sound RMS with numeric rulers</span>
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
          <div class="canvas-container-mid">
            <canvas id="spline-canvas"></canvas>
          </div>
        </div>

        <!-- Card: Signal Spike & Amplitude Monitor -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Signal Spike &amp; Amplitude</span>
            <div class="card-menu-dots">
              <span class="mini-dot"></span><span class="mini-dot"></span><span class="mini-dot"></span>
            </div>
          </div>

          <div class="spike-monitor-box">
            <div class="spike-primary-readout">
              <div style="display: flex; align-items: baseline; gap: 6px;">
                <span class="metric-big-num" style="font-size: 32px; color: var(--teal-accent);" id="gauge-curr-rms">44.7</span>
                <span style="font-size: 13px; font-weight: 700; color: var(--text-dim); font-family: 'JetBrains Mono', monospace;">RMS</span>
              </div>
              <div class="spike-pill-badge" id="gauge-spike-pill" style="background: rgba(0,240,210,0.12); color: var(--teal-accent);">
                Baseline 1.0x
              </div>
            </div>
            <span class="metric-sub-lbl">Real-time acoustic intensity at scrub cursor</span>

            <!-- Spike Level Meter Bar -->
            <div class="spike-bar-wrap">
              <div class="spike-bar-track">
                <div class="spike-bar-fill" id="gauge-bar-fill" style="width: 8.7%;"></div>
                <div class="spike-bar-pin" id="gauge-bar-pin" style="left: 8.7%;"></div>
              </div>
              <div class="spike-bar-scale">
                <span>0</span>
                <span>120 (Normal)</span>
                <span>250 (Agitation)</span>
                <span>511.2 (Peak Spike)</span>
              </div>
            </div>

            <!-- 4-Stat Live Breakdown Grid -->
            <div class="spike-stat-grid">
              <div class="spike-stat-cell">
                <span class="spike-stat-lbl">Spike Delta:</span>
                <span class="spike-stat-val" id="cell-spike-delta" style="color: var(--teal-accent);">0% (Baseline)</span>
              </div>
              <div class="spike-stat-cell">
                <span class="spike-stat-lbl">Total Accel |a|:</span>
                <span class="spike-stat-val" id="cell-total-accel">9.58 m/s&sup2;</span>
              </div>
              <div class="spike-stat-cell">
                <span class="spike-stat-lbl">Dynamic Shock:</span>
                <span class="spike-stat-val" id="cell-dyn-shock" style="color: var(--coral-accent);">&plusmn;0.23 m/s&sup2;</span>
              </div>
              <div class="spike-stat-cell">
                <span class="spike-stat-lbl">Cycle Peak Spike:</span>
                <span class="spike-stat-val" style="color: #fff;">511.2 RMS (24.2m)</span>
              </div>
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
              <span style="font-size: 11px; color: var(--text-dim); display: block; margin-top: 2px;">MPU-6050 direct register burst with explicit Y-axis scale (+10 to -15 m/s&sup2;)</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              <span class="axis-toggle-clean" id="pill-tog-x" style="color: var(--teal-accent);" onclick="toggleAxis('x')">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--teal-accent);"></span>
                Ax: <strong id="vibe-leg-x">-0.77</strong> m/s&sup2;
              </span>
              <span class="axis-toggle-clean" id="pill-tog-y" style="color: var(--coral-accent);" onclick="toggleAxis('y')">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--coral-accent);"></span>
                Ay: <strong id="vibe-leg-y">+1.36</strong> m/s&sup2;
              </span>
              <span class="axis-toggle-clean" id="pill-tog-z" style="color: var(--purple-accent);" onclick="toggleAxis('z')">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--purple-accent);"></span>
                Az: <strong id="vibe-leg-z">-9.40</strong> m/s&sup2;
              </span>
              <span class="axis-toggle-clean" style="color: #fff;">
                |a|: <strong id="head-vibe-mag">9.58</strong> m/s&sup2;
              </span>
            </div>
          </div>
          <div class="canvas-container-mid" style="height: 190px;">
            <canvas id="xyz-canvas"></canvas>
          </div>
        </div>
      </section>

      <!-- Row 4: Timeline + Phase Breakdown -->
      <section class="row-bottom">
        
        <!-- Full Wash 1019 Timeline & Playback -->
        <div class="card">
          <div class="card-header-row">
            <div>
              <span class="card-title-text">Wash Cycle 1019 Timeline (35.9 Minutes)</span>
              <span style="font-size: 11px; color: var(--text-dim); display: block; margin-top: 2px;">Continuous acoustic waveform with Y-axis numbers &amp; spike peak markers</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <span class="axis-toggle-clean" style="color: var(--teal-accent);">
                Current: <strong id="timeline-head-rms">44.7</strong> RMS
              </span>
              <span class="axis-toggle-clean" style="color: var(--coral-accent);">
                Spike: <strong id="timeline-head-spike">1.0x</strong>
              </span>
              <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: #fff;" id="lbl-curr-time">
                00:00 / 35:54
              </span>
            </div>
          </div>

          <div class="canvas-container-mid" style="height: 155px;">
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
              Replay Wash 1019
            </button>
            <button class="btn-dark-secondary" onclick="downloadWashCsv()">
              Download wash_1019.csv
            </button>
            <button class="btn-dark-secondary" onclick="setMode('live')">
              Connect Live Firebase
            </button>
          </div>
        </div>

        <!-- Phase Breakdown -->
        <div class="card">
          <div class="card-header-row">
            <span class="card-title-text">Cycle Phase Breakdown</span>
            <div class="card-menu-dots">
              <span class="mini-dot"></span><span class="mini-dot"></span><span class="mini-dot"></span>
            </div>
          </div>

          <div class="phase-bars-list">
            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">Drum Fill &amp; Soak (0 - 8m)</span>
                <span class="phase-pct-txt">44.7 RMS</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 20%;"></div>
              </div>
            </div>

            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">Agitation &amp; Tumble (8 - 22m)</span>
                <span class="phase-pct-txt">146.9 RMS</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 48%;"></div>
              </div>
            </div>

            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">High-Spin Extraction (22 - 28m)</span>
                <span class="phase-pct-txt" style="color: var(--coral-accent);">511.2 RMS (Peak)</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 100%; background: var(--coral-accent);"></div>
              </div>
            </div>

            <div class="phase-bar-row">
              <div class="phase-header-flex">
                <span class="phase-name-txt">Final Drain &amp; Rinse (28 - 36m)</span>
                <span class="phase-pct-txt">98.3 RMS</span>
              </div>
              <div class="progress-track-dark">
                <div class="progress-fill-teal" style="width: 32%;"></div>
              </div>
            </div>
          </div>

          <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-sub); font-size: 11px; color: var(--text-dim); line-height: 1.5;">
            Dynamic shock triggers during spin transition when drum speed crosses natural chassis resonant frequency (14 Hz).
          </div>
        </div>

      </section>

    </main>
  </div>

  <script>
    const WASH_DATA = {embedded_json};
    let currentMode = 'historic';
    let currentIndex = 0;
    let isPlaying = false;
    let playInterval = null;
    let liveTimer = null;

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
    const btnPlayWash = document.getElementById('btn-play-wash');
    const lblStatusText = document.getElementById('lbl-status-text');

    const kpiAvgVibe = document.getElementById('kpi-avg-vibe');
    const kpiPeakVibe = document.getElementById('kpi-peak-vibe');
    const kpiCurrRms = document.getElementById('kpi-curr-rms');
    const kpiRmsBadge = document.getElementById('kpi-rms-badge');
    const kpiSpikeFactor = document.getElementById('kpi-spike-factor');
    const kpiSpikeBadge = document.getElementById('kpi-spike-badge');
    const kpiSpikeDetail = document.getElementById('kpi-spike-detail');

    const gaugeCurrRms = document.getElementById('gauge-curr-rms');
    const gaugeSpikePill = document.getElementById('gauge-spike-pill');
    const gaugeBarFill = document.getElementById('gauge-bar-fill');
    const gaugeBarPin = document.getElementById('gauge-bar-pin');
    const cellSpikeDelta = document.getElementById('cell-spike-delta');
    const cellTotalAccel = document.getElementById('cell-total-accel');
    const cellDynShock = document.getElementById('cell-dyn-shock');

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

    function applyRecord(rec) {{
      const [t, ax, ay, az, rms] = rec;
      const vibe = Math.sqrt(ax*ax + ay*ay + az*az);
      const dg = Math.abs(vibe - 9.81);

      // Normal baseline is 120 RMS during wash tumble
      const baselineRms = 120.0;
      const spikeRatio = Math.max(1.0, (rms / baselineRms)).toFixed(1);
      const spikePct = Math.round(((rms - baselineRms) / baselineRms) * 100);

      // 1. Top Card 2: Acoustic Sound Level
      if (kpiCurrRms) kpiCurrRms.innerText = rms.toFixed(1);
      if (kpiRmsBadge) {{
        if (rms > 300) {{
          kpiRmsBadge.innerText = 'HIGH SPIKE';
          kpiRmsBadge.style.color = 'var(--coral-accent)';
        }} else if (rms > 160) {{
          kpiRmsBadge.innerText = 'AGITATION';
          kpiRmsBadge.style.color = 'var(--blue-accent)';
        }} else {{
          kpiRmsBadge.innerText = 'BASELINE';
          kpiRmsBadge.style.color = 'var(--teal-accent)';
        }}
      }}

      // 2. Top Card 3: Instantaneous Spike Ratio
      if (kpiSpikeFactor) kpiSpikeFactor.innerText = `${{spikeRatio}}x`;
      if (kpiSpikeBadge) {{
        if (rms > 300) {{
          kpiSpikeBadge.innerText = `+${{spikePct}}% SPIKE`;
          kpiSpikeBadge.style.color = 'var(--coral-accent)';
        }} else if (rms > 160) {{
          kpiSpikeBadge.innerText = `+${{spikePct}}% TUMBLE`;
          kpiSpikeBadge.style.color = 'var(--blue-accent)';
        }} else {{
          kpiSpikeBadge.innerText = 'BASELINE 1.0x';
          kpiSpikeBadge.style.color = 'var(--teal-accent)';
        }}
      }}
      if (kpiSpikeDetail) {{
        kpiSpikeDetail.innerText = `Current: ${{rms.toFixed(1)}} RMS (Baseline: 120 RMS)`;
      }}

      // 3. Middle Card: Signal Spike & Amplitude (Replaces Donut)
      if (gaugeCurrRms) gaugeCurrRms.innerText = rms.toFixed(1);
      if (gaugeSpikePill) {{
        if (rms > 300) {{
          gaugeSpikePill.innerText = `Spike ${{spikeRatio}}x (+${{spikePct}}%)`;
          gaugeSpikePill.style.background = 'rgba(251, 146, 60, 0.15)';
          gaugeSpikePill.style.color = 'var(--coral-accent)';
        }} else if (rms > 160) {{
          gaugeSpikePill.innerText = `Agitation ${{spikeRatio}}x (+${{spikePct}}%)`;
          gaugeSpikePill.style.background = 'rgba(56, 189, 248, 0.15)';
          gaugeSpikePill.style.color = 'var(--blue-accent)';
        }} else {{
          gaugeSpikePill.innerText = `Baseline 1.0x (${{rms <= 50 ? 'Drum Fill' : 'Normal'}})`;
          gaugeSpikePill.style.background = 'rgba(0, 240, 210, 0.12)';
          gaugeSpikePill.style.color = 'var(--teal-accent)';
        }}
      }}

      const pctWidth = Math.min(100, Math.max(0, (rms / 511.2) * 100));
      if (gaugeBarFill) gaugeBarFill.style.width = `${{pctWidth}}%`;
      if (gaugeBarPin) gaugeBarPin.style.left = `${{pctWidth}}%`;

      if (cellSpikeDelta) {{
        cellSpikeDelta.innerText = spikePct > 0 ? `+${{spikePct}}%` : '0% (Baseline)';
        cellSpikeDelta.style.color = spikePct > 80 ? 'var(--coral-accent)' : 'var(--teal-accent)';
      }}
      if (cellTotalAccel) cellTotalAccel.innerText = `${{vibe.toFixed(2)}} m/s\u00B2`;
      if (cellDynShock) cellDynShock.innerText = `\u00B1${{dg.toFixed(2)}} m/s\u00B2`;

      // 4. Header Badges
      if (timelineHeadRms) timelineHeadRms.innerText = rms.toFixed(1);
      if (timelineHeadSpike) timelineHeadSpike.innerText = `${{spikeRatio}}x`;
      if (headVibeMag) headVibeMag.innerText = vibe.toFixed(2);

      // 5. Ax, Ay, Az text updates
      const strX = (ax >= 0 ? '+' : '') + ax.toFixed(2);
      const strY = (ay >= 0 ? '+' : '') + ay.toFixed(2);
      const strZ = (az >= 0 ? '+' : '') + az.toFixed(2);

      vibeLegX.innerText = strX;
      vibeLegY.innerText = strY;
      vibeLegZ.innerText = strZ;

      const maxT = WASH_DATA[WASH_DATA.length - 1][0];
      lblCurrTime.innerText = `${{formatMs(t)}} / ${{formatMs(maxT)}}`;
    }}

    // Canvas 1: Dedicated Tri-Axial Vibration with Explicit Y-Axis Scale
    function drawXyz() {{
      const w = xyzCvs.width;
      const h = xyzCvs.height;
      const dpr = window.devicePixelRatio || 1;
      xyzCtx.clearRect(0, 0, w, h);

      const yZero = h * 0.35;
      const scaleXY = 14 * dpr;
      const yGravity = h * 0.78;
      const scaleZ = 16 * dpr;

      // 1. Grid & Numerical Ticks for Ax, Ay
      const xyTicks = [
        {{ val: 5.0, label: '+5.0 m/s\u00B2' }},
        {{ val: 0.0, label: '0.0 m/s\u00B2 (X/Y Baseline)' }},
        {{ val: -5.0, label: '-5.0 m/s\u00B2' }}
      ];
      xyTicks.forEach(t => {{
        const y = yZero - (t.val * scaleXY);
        xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        xyzCtx.lineWidth = 1;
        xyzCtx.beginPath();
        xyzCtx.moveTo(0, y);
        xyzCtx.lineTo(w, y);
        xyzCtx.stroke();

        xyzCtx.fillStyle = t.val === 0.0 ? 'rgba(255, 255, 255, 0.38)' : 'rgba(255, 255, 255, 0.2)';
        xyzCtx.font = `600 ${{8.5 * dpr}}px 'JetBrains Mono', monospace`;
        xyzCtx.fillText(t.label, 8 * dpr, y - (3 * dpr));
      }});

      // 2. Grid & Numerical Ticks for Az
      const zTicks = [
        {{ val: -5.0, label: '-5.0 m/s\u00B2' }},
        {{ val: -9.81, label: '-9.81 m/s\u00B2 (Az 1g Gravity Baseline)' }},
        {{ val: -15.0, label: '-15.0 m/s\u00B2' }}
      ];
      zTicks.forEach(t => {{
        const y = yGravity - ((t.val + 9.81) * scaleZ);
        xyzCtx.strokeStyle = 'rgba(167, 139, 250, 0.08)';
        xyzCtx.lineWidth = 1;
        xyzCtx.beginPath();
        xyzCtx.moveTo(0, y);
        xyzCtx.lineTo(w, y);
        xyzCtx.stroke();

        xyzCtx.fillStyle = t.val === -9.81 ? 'rgba(167, 139, 250, 0.5)' : 'rgba(167, 139, 250, 0.25)';
        xyzCtx.font = `600 ${{8.5 * dpr}}px 'JetBrains Mono', monospace`;
        xyzCtx.fillText(t.label, 8 * dpr, y - (3 * dpr));
      }});

      const winSize = 40;
      const startIdx = Math.max(0, currentIndex - (winSize / 2));
      const endIdx = Math.min(WASH_DATA.length - 1, startIdx + winSize);
      const points = WASH_DATA.slice(startIdx, endIdx + 1);

      if (points.length < 2) return;

      // Plot Az (Purple)
      if (axisVisible.z) {{
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#a78bfa';
        xyzCtx.lineWidth = 2.2 * dpr;
        for (let i = 0; i < points.length; i++) {{
          const x = (i / (points.length - 1)) * w;
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
          const x = (i / (points.length - 1)) * w;
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
          const x = (i / (points.length - 1)) * w;
          const ax = points[i][1];
          const y = yZero - (ax * scaleXY);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }}
        xyzCtx.stroke();
      }}

      // Active cursor points & numeric tags
      const curRel = currentIndex - startIdx;
      if (curRel >= 0 && curRel < points.length) {{
        const cx = (curRel / (points.length - 1)) * w;
        if (axisVisible.x) {{
          const cyX = yZero - (points[curRel][1] * scaleXY);
          xyzCtx.fillStyle = '#00f0d2';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyX, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }}
        if (axisVisible.y) {{
          const cyY = yZero - (points[curRel][2] * scaleXY);
          xyzCtx.fillStyle = '#fb923c';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyY, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }}
        if (axisVisible.z) {{
          const cyZ = yGravity - ((points[curRel][3] + 9.81) * scaleZ);
          xyzCtx.fillStyle = '#a78bfa';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyZ, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
        }}
      }}
    }}

    // Canvas 2: Dual-Modality Waveform with Dual Numeric Rulers
    function drawSpline() {{
      const w = splineCvs.width;
      const h = splineCvs.height;
      const dpr = window.devicePixelRatio || 1;
      splineCtx.clearRect(0, 0, w, h);

      // Dual Y-axis ticks
      const soundTicks = [500, 375, 250, 125, 0];
      soundTicks.forEach(val => {{
        const y = h - ((val / 520.0) * h * 0.75) - 10;
        splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        splineCtx.lineWidth = 1;
        splineCtx.beginPath();
        splineCtx.moveTo(0, y);
        splineCtx.lineTo(w, y);
        splineCtx.stroke();

        // Right side: Sound RMS labels
        splineCtx.fillStyle = 'rgba(251, 146, 60, 0.45)';
        splineCtx.font = `600 ${{8 * dpr}}px 'JetBrains Mono', monospace`;
        splineCtx.textAlign = 'right';
        splineCtx.fillText(`${{val}} RMS`, w - (8 * dpr), y - (3 * dpr));
        splineCtx.textAlign = 'left';
      }});

      // Left side: Vibration labels
      const vibeTicks = [
        {{ val: 12.0, lbl: '12.0 m/s\u00B2' }},
        {{ val: 9.81, lbl: '9.81 m/s\u00B2 (1g)' }},
        {{ val: 8.0, lbl: '8.0 m/s\u00B2' }}
      ];
      vibeTicks.forEach(t => {{
        const y = (h * 0.45) - ((t.val - 9.81) * 25 * dpr);
        splineCtx.fillStyle = 'rgba(0, 240, 210, 0.45)';
        splineCtx.font = `600 ${{8 * dpr}}px 'JetBrains Mono', monospace`;
        splineCtx.fillText(t.lbl, 8 * dpr, y - (3 * dpr));
      }});

      const winSize = 40;
      const startIdx = Math.max(0, currentIndex - (winSize / 2));
      const endIdx = Math.min(WASH_DATA.length - 1, startIdx + winSize);
      const points = WASH_DATA.slice(startIdx, endIdx + 1);

      if (points.length < 2) return;

      // 1. Draw Sound Wave (Coral)
      const gradCoral = splineCtx.createLinearGradient(0, 0, 0, h);
      gradCoral.addColorStop(0, 'rgba(251, 146, 60, 0.15)');
      gradCoral.addColorStop(1, 'rgba(251, 146, 60, 0.0)');

      splineCtx.beginPath();
      splineCtx.moveTo(0, h);
      for (let i = 0; i < points.length; i++) {{
        const x = (i / (points.length - 1)) * w;
        const normRms = points[i][4] / 520.0;
        const y = h - (normRms * h * 0.75) - 10;
        splineCtx.lineTo(x, y);
      }}
      splineCtx.lineTo(w, h);
      splineCtx.closePath();
      splineCtx.fillStyle = gradCoral;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#fb923c';
      splineCtx.lineWidth = 2.2 * dpr;
      for (let i = 0; i < points.length; i++) {{
        const x = (i / (points.length - 1)) * w;
        const normRms = points[i][4] / 520.0;
        const y = h - (normRms * h * 0.75) - 10;
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }}
      splineCtx.stroke();

      // 2. Draw Vibration Wave (Teal)
      const gradTeal = splineCtx.createLinearGradient(0, 0, 0, h);
      gradTeal.addColorStop(0, 'rgba(0, 240, 210, 0.2)');
      gradTeal.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

      splineCtx.beginPath();
      splineCtx.moveTo(0, h);
      for (let i = 0; i < points.length; i++) {{
        const x = (i / (points.length - 1)) * w;
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = (h * 0.45) - ((v - 9.81) * 25 * dpr);
        splineCtx.lineTo(x, y);
      }}
      splineCtx.lineTo(w, h);
      splineCtx.closePath();
      splineCtx.fillStyle = gradTeal;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#00f0d2';
      splineCtx.lineWidth = 2.2 * dpr;
      for (let i = 0; i < points.length; i++) {{
        const x = (i / (points.length - 1)) * w;
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = (h * 0.45) - ((v - 9.81) * 25 * dpr);
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }}
      splineCtx.stroke();

      // Active point dot
      const curRel = currentIndex - startIdx;
      if (curRel >= 0 && curRel < points.length) {{
        const cx = (curRel / (points.length - 1)) * w;
        const normRms = points[curRel][4] / 520.0;
        const cyRms = h - (normRms * h * 0.75) - 10;
        splineCtx.fillStyle = '#fb923c';
        splineCtx.beginPath();
        splineCtx.arc(cx, cyRms, 4 * dpr, 0, Math.PI * 2);
        splineCtx.fill();
      }}
    }}

    // Canvas 3: Full Wash 1019 Timeline with Numbers, Max Peak Spike & Live Floating Cursor Badge
    function drawArea() {{
      const w = areaCvs.width;
      const h = areaCvs.height;
      const dpr = window.devicePixelRatio || 1;
      areaCtx.clearRect(0, 0, w, h);

      const padBottom = 16 * dpr;
      const padTop = 18 * dpr;
      const plotH = h - padBottom - padTop;

      // 1. Horizontal Y-Axis Numeric Rulers
      const yTicks = [500, 375, 250, 125, 0];
      yTicks.forEach(val => {{
        const yVal = h - padBottom - ((val / 520.0) * plotH);
        areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        areaCtx.lineWidth = 1;
        areaCtx.beginPath();
        areaCtx.moveTo(0, yVal);
        areaCtx.lineTo(w, yVal);
        areaCtx.stroke();

        areaCtx.fillStyle = 'rgba(255, 255, 255, 0.38)';
        areaCtx.font = `600 ${{8.5 * dpr}}px 'JetBrains Mono', monospace`;
        areaCtx.fillText(`${{val}} RMS`, 8 * dpr, yVal - (3 * dpr));
      }});

      // 2. Horizontal Reference Line: Max Peak Spike (511.2 RMS)
      const yPeak = h - padBottom - ((511.2 / 520.0) * plotH);
      areaCtx.strokeStyle = 'rgba(251, 146, 60, 0.5)';
      areaCtx.lineWidth = 1.2 * dpr;
      areaCtx.setLineDash([4 * dpr, 4 * dpr]);
      areaCtx.beginPath();
      areaCtx.moveTo(0, yPeak);
      areaCtx.lineTo(w, yPeak);
      areaCtx.stroke();
      areaCtx.setLineDash([]);
      areaCtx.fillStyle = 'rgba(251, 146, 60, 0.85)';
      areaCtx.font = `700 ${{8.5 * dpr}}px 'JetBrains Mono', monospace`;
      areaCtx.textAlign = 'right';
      areaCtx.fillText('PEAK SPIKE: 511.2 RMS (24.2m)', w - (8 * dpr), yPeak - (3 * dpr));
      areaCtx.textAlign = 'left';

      // 3. Horizontal Reference Line: Normal Baseline (120 RMS)
      const yBase = h - padBottom - ((120.0 / 520.0) * plotH);
      areaCtx.strokeStyle = 'rgba(0, 240, 210, 0.28)';
      areaCtx.lineWidth = 1 * dpr;
      areaCtx.setLineDash([3 * dpr, 3 * dpr]);
      areaCtx.beginPath();
      areaCtx.moveTo(0, yBase);
      areaCtx.lineTo(w, yBase);
      areaCtx.stroke();
      areaCtx.setLineDash([]);
      areaCtx.fillStyle = 'rgba(0, 240, 210, 0.6)';
      areaCtx.font = `600 ${{8 * dpr}}px 'JetBrains Mono', monospace`;
      areaCtx.textAlign = 'right';
      areaCtx.fillText('NORMAL BASELINE: 120 RMS', w - (8 * dpr), yBase - (3 * dpr));
      areaCtx.textAlign = 'left';

      const total = WASH_DATA.length;
      if (total < 2) return;

      // Area gradient
      const grad = areaCtx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, 'rgba(0, 240, 210, 0.25)');
      grad.addColorStop(0.8, 'rgba(0, 240, 210, 0.04)');
      grad.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

      areaCtx.beginPath();
      areaCtx.moveTo(0, h);
      for (let i = 0; i < total; i++) {{
        const x = (i / (total - 1)) * w;
        const rms = WASH_DATA[i][4];
        const y = h - padBottom - ((rms / 520.0) * plotH);
        areaCtx.lineTo(x, y);
      }}
      areaCtx.lineTo(w, h);
      areaCtx.closePath();
      areaCtx.fillStyle = grad;
      areaCtx.fill();

      // Top stroke
      areaCtx.beginPath();
      areaCtx.strokeStyle = '#00f0d2';
      areaCtx.lineWidth = 2 * dpr;
      for (let i = 0; i < total; i++) {{
        const x = (i / (total - 1)) * w;
        const rms = WASH_DATA[i][4];
        const y = h - padBottom - ((rms / 520.0) * plotH);
        if (i === 0) areaCtx.moveTo(x, y); else areaCtx.lineTo(x, y);
      }}
      areaCtx.stroke();

      // Cursor vertical scrubber line
      const curX = (currentIndex / (total - 1)) * w;
      areaCtx.strokeStyle = '#00f0d2';
      areaCtx.lineWidth = 2 * dpr;
      areaCtx.beginPath();
      areaCtx.moveTo(curX, 0);
      areaCtx.lineTo(curX, h);
      areaCtx.stroke();

      const curRms = WASH_DATA[currentIndex][4];
      const curY = h - padBottom - ((curRms / 520.0) * plotH);

      // Cursor dot
      areaCtx.fillStyle = '#00f0d2';
      areaCtx.beginPath();
      areaCtx.arc(curX, curY, 5 * dpr, 0, Math.PI * 2);
      areaCtx.fill();

      // Floating cursor value badge (clearly shows the live number & spike)
      const spikeMult = Math.max(1.0, curRms / 120.0).toFixed(1);
      const spikePctVal = Math.round(((curRms - 120.0) / 120.0) * 100);
      const badgeText = `${{curRms.toFixed(1)}} RMS (${{spikeMult}}x ${{spikePctVal > 0 ? '+' + spikePctVal + '%' : 'base'}})`;

      areaCtx.font = `700 ${{9 * dpr}}px 'JetBrains Mono', monospace`;
      const tw = areaCtx.measureText(badgeText).width;
      const bw = tw + (12 * dpr);
      const bh = 18 * dpr;

      let bx = curX - (bw / 2);
      if (bx < 6 * dpr) bx = 6 * dpr;
      if (bx + bw > w - (6 * dpr)) bx = w - bw - (6 * dpr);

      let by = curY - (22 * dpr);
      if (by < 4 * dpr) by = curY + (10 * dpr);

      areaCtx.fillStyle = curRms > 250 ? 'rgba(251, 146, 60, 0.95)' : 'rgba(0, 240, 210, 0.95)';
      areaCtx.beginPath();
      if (areaCtx.roundRect) {{
        areaCtx.roundRect(bx, by, bw, bh, 3 * dpr);
      }} else {{
        areaCtx.rect(bx, by, bw, bh);
      }}
      areaCtx.fill();

      areaCtx.fillStyle = '#0f172a';
      areaCtx.textAlign = 'center';
      areaCtx.fillText(badgeText, bx + (bw / 2), by + (12.5 * dpr));
      areaCtx.textAlign = 'left';
    }}

    function onScrub(val) {{
      currentIndex = parseInt(val, 10);
      const minutes = ((WASH_DATA[currentIndex][0] / 60000)).toFixed(1);
      scrubLabel.innerText = `${{minutes}}m`;
      applyRecord(WASH_DATA[currentIndex]);
      drawSpline();
      drawXyz();
      drawArea();
    }}

    function togglePlayPause() {{
      isPlaying = !isPlaying;
      if (isPlaying) {{
        btnPlayWash.innerText = 'Pause Playback';
        playInterval = setInterval(() => {{
          currentIndex++;
          if (currentIndex >= WASH_DATA.length) currentIndex = 0;
          timeSlider.value = currentIndex;
          onScrub(currentIndex);
        }}, 80);
      }} else {{
        btnPlayWash.innerText = 'Replay Wash 1019';
        if (playInterval) clearInterval(playInterval);
      }}
    }}

    function setMode(mode) {{
      currentMode = mode;
      if (mode === 'live') {{
        if (isPlaying) togglePlayPause();
        lblStatusText.innerText = 'Live Streaming (50 Hz)';
        document.getElementById('acc-item-1').classList.remove('active');
        document.getElementById('acc-item-2').classList.add('active');
        startLivePolling();
      }} else {{
        if (liveTimer) clearInterval(liveTimer);
        lblStatusText.innerText = 'wash_1019 Active';
        document.getElementById('acc-item-2').classList.remove('active');
        document.getElementById('acc-item-1').classList.add('active');
        applyRecord(WASH_DATA[currentIndex]);
        drawSpline();
        drawXyz();
        drawArea();
      }}
    }}

    async function startLivePolling() {{
      const fetchLive = async () => {{
        try {{
          const res = await fetch('https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app/live.json');
          const d = await res.json();
          if (d) {{
            applyRecord([d.uptime * 1000, d.ax, d.ay, d.az, d.rms]);
            drawXyz();
            drawSpline();
          }}
        }} catch (e) {{}}
      }};
      fetchLive();
      liveTimer = setInterval(fetchLive, 2000);
    }}

    function downloadWashCsv() {{
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

    function toggleMobileMenu() {{
      const drawer = document.getElementById('mobile-drawer');
      const overlay = document.getElementById('drawer-overlay');
      drawer.classList.toggle('open');
      overlay.style.display = drawer.classList.contains('open') ? 'block' : 'none';
    }}

    function toggleDoc() {{
      window.open('hardware_bom_and_setup_guide.pdf', '_blank');
    }}

    setTimeout(() => {{
      resizeCanvases();
      applyRecord(WASH_DATA[0]);
    }}, 100);
  </script>
</body>
</html>
'''

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

with open('cloud_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

brain_path = r'C:\Users\adamd\.gemini\antigravity\brain\eaf1a310-7f2a-46d6-b3a7-72b474df813e\dashboard.html'
try:
    with open(brain_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
except Exception as e:
    print('Brain artifact write note:', e)

print('Successfully built UTF-8 clean dashboard with ZERO mojibake!')
