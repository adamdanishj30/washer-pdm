import json
import os

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[1:]
    rows = []
    for l in lines:
        parts = l.strip().split(',')
        if len(parts) >= 5:
            try:
                t = int(float(parts[0]))
                ax = float(parts[1])
                ay = float(parts[2])
                az = float(parts[3])
                rms = float(parts[4])
                pwr = float(parts[5]) if len(parts) >= 6 and parts[5] != '' else None
                rec = [t, ax, ay, az, rms]
                if pwr is not None:
                    rec.append(pwr)
                rows.append(rec)
            except ValueError:
                pass
    return rows

def discover_all_sessions():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    real_dir = os.path.join(data_dir, 'real_sessions')
    test_dir = os.path.join(data_dir, 'testing_data')
    sessions = {}
    options = []
    
    # 1. Real Wash Sessions (from data/real_sessions)
    real_options = []
    if os.path.exists(real_dir):
        files = sorted(os.listdir(real_dir), reverse=True)
        for fname in files:
            if fname.endswith('.csv') and not fname.startswith('.'):
                fpath = os.path.join(real_dir, fname)
                rows = load_csv(fpath)
                if not rows or len(rows) < 3:
                    continue
                s_key = 'preset_real_' + fname.replace('.csv', '').replace('-', '_').replace('.', '_')
                pts_cnt = len(rows)
                duration_m = round((rows[-1][0] - rows[0][0]) / 60000.0) if pts_cnt > 1 else 0
                
                if 'morning' in fname:
                    disp = f"🧺 15 Oct 2026 Morning Wash ({duration_m}m, {pts_cnt} pts)"
                elif '2026-10-15_1020' in fname:
                    disp = f"🧺 15 Oct 2026, 12:41 AM ({duration_m}m Live Wash, {pts_cnt} pts)"
                elif '2026-10-12_0800' in fname:
                    disp = f"🧺 12 Oct 2026, 08:00 AM (103m Full Wash, {pts_cnt} pts)"
                elif '2026-10-12_1019' in fname:
                    disp = f"🧺 12 Oct 2026, 10:19 AM (101m Wash, {pts_cnt} pts)"
                elif '2026-10-11_1019' in fname:
                    disp = f"🧺 11 Oct 2026, 10:19 AM (24m Wash, {pts_cnt} pts)"
                else:
                    disp = f"🧺 Wash: {fname} ({duration_m}m, {pts_cnt} pts)"

                sessions[s_key] = {
                    'name': fname.replace('.csv', ''),
                    'displayName': disp,
                    'data': rows,
                    'category': 'real'
                }
                real_options.append(f'<option value="{s_key}">{disp}</option>')
                
    if real_options:
        options.append('<optgroup label="🧺 Real Wash Sessions">')
        options.extend(real_options)
        options.append('</optgroup>')

    # 2. Testing & Calibration Data (from data/testing_data)
    test_options = []
    if os.path.exists(test_dir):
        for fname in sorted(os.listdir(test_dir), reverse=True):
            if fname.endswith('.csv') and not fname.startswith('.'):
                fpath = os.path.join(test_dir, fname)
                rows = load_csv(fpath)
                if rows:
                    s_key = 'preset_test_' + fname.replace('.csv', '').replace('-', '_').replace('.', '_')
                    pts_cnt = len(rows)
                    if 'wifi_test' in fname:
                        disp = f"🧪 Wi-Fi Telemetry Stream Test ({pts_cnt} pts)"
                    elif '0123' in fname or '0127' in fname:
                        disp = f"🧪 Boot Offline Dump Test ({pts_cnt} pts)"
                    elif 'snapshot' in fname:
                        disp = f"🧪 Live Snapshot Test ({pts_cnt} pts)"
                    elif '1009' in fname:
                        disp = f"🧪 Bench Pre-Wash Test ({pts_cnt} pts)"
                    elif '1020' in fname:
                        disp = f"🧪 Bench Spin Test ({pts_cnt} pts)"
                    else:
                        disp = f"🧪 Test: {fname} ({pts_cnt} pts)"

                    sessions[s_key] = {
                        'name': fname.replace('.csv', ''),
                        'displayName': disp,
                        'data': rows,
                        'category': 'test'
                    }
                    test_options.append(f'<option value="{s_key}">{disp}</option>')
                    
    if test_options:
        options.append('<optgroup label="🧪 Testing & Bench Calibration">')
        options.extend(test_options)
        options.append('</optgroup>')

    return sessions, '\n            '.join(options)

PRESET_SESSIONS_DICT, PRESET_OPTIONS_HTML = discover_all_sessions()
PRESET_SESSIONS_JSON = json.dumps(PRESET_SESSIONS_DICT)
FIRST_SESSION_KEY = next(iter(PRESET_SESSIONS_DICT.keys())) if PRESET_SESSIONS_DICT else 'preset_wash_0800'
FIRST_SESSION_NAME = PRESET_SESSIONS_DICT[FIRST_SESSION_KEY]['name'] if PRESET_SESSIONS_DICT else 'Wash Session'


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
      background: var(--bg-card);
      border-bottom: 1px solid var(--border-card);
      padding: 14px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
      gap: 16px;
    }}

    .nav-brand-row {{
      display: flex;
      align-items: center;
      gap: 12px;
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

    .nav-controls-row {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .mobile-status-tag {{
      display: none;
    }}
    .desktop-status-tag {{
      display: flex;
    }}

    /* Session Picker in Top Nav */
    .session-picker-box {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .session-select-dropdown {{
      background: rgba(0, 240, 210, 0.12);
      border: 1px solid var(--teal-accent);
      color: var(--teal-accent);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 700;
      font-family: inherit;
      cursor: pointer;
      outline: none;
      transition: all 0.2s;
      max-width: 270px;
    }}
    .session-select-dropdown:hover, .session-select-dropdown:focus {{
      box-shadow: 0 0 12px var(--teal-glow);
    }}
    .session-select-dropdown option, .session-select-dropdown optgroup {{
      background: var(--bg-card);
      color: var(--text-main);
      font-weight: 600;
    }}

    .btn-load-csv {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .btn-load-csv:hover {{
      background: var(--bg-card-hover);
      border-color: var(--teal-accent);
      color: var(--teal-accent);
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
      white-space: nowrap;
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
      flex-shrink: 0;
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
      white-space: nowrap;
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
    }}
    .box-spline {{ height: 185px; }}
    .box-xyz {{ height: 195px; }}
    .box-timeline {{ height: 165px; }}
    .box-energy {{ height: 175px; }}

    .view-toggle-pill {{
      display: inline-flex;
      background: var(--bg-inner);
      border: 1px solid var(--border-card);
      border-radius: 8px;
      padding: 2px;
      gap: 2px;
    }}
    .span-btn {{
      background: transparent;
      border: none;
      color: var(--text-dim);
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
      white-space: nowrap;
    }}
    .span-btn:hover {{
      color: var(--text-main);
    }}
    .span-btn.active {{
      background: rgba(0, 240, 210, 0.15);
      color: var(--teal-accent);
      box-shadow: 0 0 8px rgba(0, 240, 210, 0.2);
    }}

    canvas {{
      width: 100%;
      height: 100%;
      display: block;
      cursor: crosshair;
    }}

    /* Axis Toggle Badges */
    .vibe-badges-container {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
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

    .timeline-stats-container {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .time-readout-pill {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      color: #fff;
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
    .secondary-btn-group {{
      display: flex;
      gap: 10px;
      flex: 1;
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
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .btn-dark-primary:hover {{
      box-shadow: 0 0 12px var(--teal-glow);
      filter: brightness(1.05);
    }}
    .btn-dark-secondary {{
      background: var(--bg-inner);
      border: 1px solid var(--border-card);
      color: var(--text-main);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .btn-dark-secondary:hover {{
      background: var(--bg-card-hover);
      border-color: var(--border-sub);
    }}

    /* Toast Notification */
    .toast-notification {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: rgba(26, 29, 36, 0.95);
      border: 1px solid var(--teal-accent);
      color: var(--text-main);
      padding: 10px 18px;
      border-radius: 10px;
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      z-index: 9999;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.3s ease;
      pointer-events: none;
    }}
    .toast-notification.show {{
      opacity: 1;
      transform: translateY(0);
    }}

    /* Mobile Responsive Optimizations */
    @media (max-width: 640px) {{
      .top-nav {{
        padding: 10px 12px;
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
      }}
      .nav-brand-row {{
        justify-content: space-between;
        width: 100%;
      }}
      .mobile-status-tag {{
        display: flex;
        padding: 4px 10px;
        font-size: 10.5px;
      }}
      .desktop-status-tag {{
        display: none;
      }}
      .nav-controls-row {{
        width: 100%;
        gap: 8px;
      }}
      .session-picker-box {{
        flex: 1;
        width: 100%;
        display: flex;
        gap: 6px;
      }}
      .session-select-dropdown {{
        flex: 1;
        min-width: 0;
        font-size: 11px;
        padding: 6px 8px;
        max-width: none;
      }}
      .btn-load-csv {{
        padding: 6px 8px;
        font-size: 11px;
      }}
      .nav-controls-row .btn-header-action {{
        padding: 6px 10px;
        font-size: 11px;
      }}

      .main-container {{
        padding: 10px 8px;
        gap: 10px;
      }}
      .live-offline-banner {{
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        padding: 8px 10px;
        font-size: 11px;
      }}
      .live-offline-banner button {{
        width: 100%;
        padding: 6px 10px !important;
        text-align: center;
      }}

      .card {{
        padding: 12px 10px;
        border-radius: 10px;
      }}
      .card-header-row {{
        margin-bottom: 8px;
        gap: 6px;
      }}
      .card-title-text {{
        font-size: 13px;
      }}
      .card-sub-txt {{
        font-size: 10px;
      }}
      .chart-legend-row {{
        font-size: 10px;
        gap: 10px;
      }}

      .box-spline {{ height: 145px; }}
      .box-xyz {{ height: 155px; }}
      .box-timeline {{ height: 140px; }}

      .vibe-badges-container {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        width: 100%;
        gap: 5px;
      }}
      .vibe-badges-container .axis-toggle-clean {{
        justify-content: center;
        padding: 4px 6px;
        font-size: 10px;
      }}

      .timeline-stats-container {{
        width: 100%;
        justify-content: space-between;
        gap: 4px;
      }}
      .timeline-stats-container .axis-toggle-clean,
      .timeline-stats-container .time-readout-pill {{
        font-size: 10px;
        padding: 3px 6px;
      }}

      .action-button-row {{
        flex-direction: column;
        gap: 8px;
        margin-top: 10px;
      }}
      .action-button-row .btn-dark-primary {{
        width: 100%;
        padding: 9px 12px;
        font-size: 12px;
        text-align: center;
      }}
      .secondary-btn-group {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 6px;
        width: 100%;
      }}
      .secondary-btn-group .btn-dark-secondary {{
        width: 100%;
        padding: 7px 6px;
        font-size: 10px;
        text-align: center;
        justify-content: center;
        display: flex;
        align-items: center;
      }}
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <header class="top-nav">
    <div class="nav-brand-row">
      <a href="#" class="brand-title">
        <span class="brand-pill">PDM</span>
        <span>Samsung Washer Monitor</span>
      </a>
      <div class="status-badge offline-badge mobile-status-tag" id="badge-live-tag-mobile">
        <span class="status-dot dot-offline" id="status-dot-indicator-mobile"></span>
        <span id="lbl-status-text-mobile">Offline</span>
      </div>
    </div>

    <!-- Center/Right Controls: Session Chooser, Load CSV, Status Badge, Export -->
    <div class="nav-controls-row">
      <div class="session-picker-box">
        <select class="session-select-dropdown" id="sel-session" onchange="onSessionDropdownChange(this.value)">
          <optgroup label="Real-Time Telemetry">
            <option value="live">📡 Live Rig Telemetry (50 Hz)</option>
          </optgroup>
          {PRESET_OPTIONS_HTML}
          <optgroup label="Custom Loaded Files" id="group-custom-sessions" style="display: none;"></optgroup>
          <optgroup label="Cloud Firebase Sessions" id="group-cloud-sessions" style="display: none;"></optgroup>
        </select>

        <button class="btn-load-csv" title="Open any local CSV file" onclick="document.getElementById('input-file-csv').click()">
          📁 Load CSV
        </button>
        <input type="file" id="input-file-csv" accept=".csv" style="display: none;" onchange="handleCsvFileSelected(event)">
      </div>

      <div class="status-badge offline-badge desktop-status-tag" id="badge-live-tag">
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
        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ef4444; flex-shrink: 0;"></span>
        <span><strong>Live Rig Offline:</strong> No active ESP32 sensor input. Displaying cached data.</span>
      </div>
      <button class="btn-dark-secondary" style="padding: 4px 12px; font-size: 11px;" onclick="switchToSession(activeSessionKey)">Switch to Historical Data</button>
    </div>

    <!-- Card 1: Dual-Modality Telemetry -->
    <div class="card">
      <div class="card-header-row">
        <div>
          <span class="card-title-text" id="title-spline">Dual-Modality Telemetry</span>
          <span class="card-sub-txt" id="sub-spline">Vibration resultant &bull; Acoustic sound amplitude</span>
        </div>
        <div class="chart-legend-row">
          <div class="view-toggle-pill" id="tog-spline-mode" style="display: none;">
            <button class="span-btn active" id="btn-spline-full" onclick="setChartSpan('spline', 'full')">Full Run</button>
            <button class="span-btn" id="btn-spline-win" onclick="setChartSpan('spline', 'win')">40s Window</button>
          </div>
          <span class="legend-item-dot">
            <span class="dot-indicator" style="background: var(--teal-accent);"></span> |a|: <strong id="spline-cur-vibe" style="color: var(--teal-accent); font-family: 'JetBrains Mono', monospace;">9.54</strong> m/s&sup2;
          </span>
          <span class="legend-item-dot">
            <span class="dot-indicator" style="background: var(--coral-accent);"></span> Sound: <strong id="spline-cur-rms" style="color: var(--coral-accent); font-family: 'JetBrains Mono', monospace;">75.3</strong> RMS
          </span>
        </div>
      </div>
      <div class="canvas-container-box box-spline">
        <canvas id="spline-canvas"></canvas>
      </div>
    </div>

    <!-- Card 2: Tri-Axial Vibration (Ax, Ay, Az) -->
    <div class="card">
      <div class="card-header-row">
        <div>
          <span class="card-title-text" id="title-xyz">Tri-Axial Vibration (Ax, Ay, Az)</span>
          <span class="card-sub-txt" id="sub-xyz">MPU-6050 Accelerometer &bull; Isolated X/Y &amp; Z oscilloscope lanes</span>
        </div>
        <div class="vibe-badges-container">
          <div class="view-toggle-pill" id="tog-xyz-mode" style="display: none;">
            <button class="span-btn active" id="btn-xyz-full" onclick="setChartSpan('xyz', 'full')">Full Run</button>
            <button class="span-btn" id="btn-xyz-win" onclick="setChartSpan('xyz', 'win')">40s Window</button>
          </div>
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
      <div class="canvas-container-box box-xyz">
        <canvas id="xyz-canvas"></canvas>
      </div>
    </div>

    <!-- Card 3: Timeline & Controls -->
    <div class="card">
      <div class="card-header-row">
        <div>
          <span class="card-title-text" id="title-timeline">Live Rig Telemetry Stream</span>
          <span class="card-sub-txt" id="sub-timeline">Real-time incoming telemetry stream from ESP32</span>
        </div>
        <div class="timeline-stats-container">
          <span class="axis-toggle-clean" style="color: var(--teal-accent);">
            Current: <strong id="timeline-head-rms">105.6</strong> RMS
          </span>
          <span class="axis-toggle-clean" style="color: var(--coral-accent);">
            Spike: <strong id="timeline-head-spike">1.0x</strong>
          </span>
          <span class="time-readout-pill" id="lbl-curr-time">
            LIVE (50 Hz)
          </span>
        </div>
      </div>

      <div class="canvas-container-box box-timeline">
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
        <div class="secondary-btn-group">
          <button class="btn-dark-secondary" id="btn-secondary-switch" onclick="toggleViewMode()">
            Switch to Historical Data
          </button>
          <button class="btn-dark-secondary" onclick="document.getElementById('input-file-csv').click()" title="Open local CSV file">
            📁 Load CSV
          </button>
          <button class="btn-dark-secondary" onclick="exportActiveCsv()">
            Download CSV
          </button>
        </div>
      </div>
    </div>

    <!-- Card 4: Electrical Power & Energy Consumption (TP-Link Tapo P110) -->
    <div class="card" id="card-energy-diagnostics">
      <div class="card-header-row">
        <div>
          <span class="card-title-text" id="title-energy">⚡ Electrical Power &amp; Energy Consumption</span>
          <span class="card-sub-txt" id="sub-energy">TP-Link Tapo P110 (1 Hz KLAP) &bull; Active motor load, cycle energy, and parasitic friction</span>
        </div>
        <div class="vibe-badges-container">
          <span class="axis-toggle-clean" style="color: #facc15;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: #facc15;"></span>
            Active: <strong id="energy-head-watts">0.0</strong> W
          </span>
          <span class="axis-toggle-clean" style="color: var(--teal-accent);">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--teal-accent);"></span>
            Energy: <strong id="energy-head-kwh">0.00</strong> kWh
          </span>
          <span class="axis-toggle-clean" style="color: var(--coral-accent);">
            Load: <strong id="energy-head-load">-- kg</strong> (<span id="energy-head-class">Auto</span>)
          </span>
          <span class="axis-toggle-clean" style="color: #4ade80;">
            Motor Drag: <strong id="energy-head-drag">0% (Normal)</strong>
          </span>
        </div>
      </div>
      <div class="canvas-container-box box-energy">
        <canvas id="energy-canvas"></canvas>
      </div>
      <div class="energy-metrics-bar" style="display: flex; gap: 12px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-sub); font-size: 11px; color: var(--text-dim); flex-wrap: wrap; justify-content: space-between;">
        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
          <span>Peak Power: <strong id="energy-stat-peak" style="color: var(--text-main); font-family: 'JetBrains Mono', monospace;">0 W</strong></span>
          <span>Avg Active: <strong id="energy-stat-avg" style="color: var(--text-main); font-family: 'JetBrains Mono', monospace;">0 W</strong></span>
          <span>Cycle Est. Cost: <strong id="energy-stat-cost" style="color: var(--teal-accent); font-family: 'JetBrains Mono', monospace;">RM 0.00</strong></span>
        </div>
        <div style="display: flex; gap: 12px;">
          <span>P-F Health: <strong id="energy-stat-pf" style="color: #4ade80; font-family: 'JetBrains Mono', monospace;">100% [Point P: Optimal]</strong></span>
        </div>
      </div>
    </div>

  </main>

  <div id="toast" class="toast-notification">Notification</div>

  <script>
    const PRESET_SESSIONS = {PRESET_SESSIONS_JSON};

    let LOADED_SESSIONS = Object.assign({{}}, PRESET_SESSIONS);
    let activeSessionKey = '{FIRST_SESSION_KEY}';
    let activeSessionName = '{FIRST_SESSION_NAME}';
    let ACTIVE_DATA = (LOADED_SESSIONS[activeSessionKey] && LOADED_SESSIONS[activeSessionKey].data) ? LOADED_SESSIONS[activeSessionKey].data : [];

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

    let axisVisible = {{ x: true, y: true, z: true }};
    let chartSpanMode = {{ spline: 'full', xyz: 'full' }};

    function setChartSpan(chart, span) {{
      chartSpanMode[chart] = span;
      const btnFull = document.getElementById(`btn-${{chart}}-full`);
      const btnWin = document.getElementById(`btn-${{chart}}-win`);
      if (btnFull && btnWin) {{
        if (span === 'full') {{
          btnFull.classList.add('active');
          btnWin.classList.remove('active');
        }} else {{
          btnFull.classList.remove('active');
          btnWin.classList.add('active');
        }}
      }}
      updateChartSubtitles();
      if (chart === 'spline') drawSpline();
      else if (chart === 'xyz') drawXyz();
    }}

    function updateChartSubtitles() {{
      const subSpline = document.getElementById('sub-spline');
      const subXyz = document.getElementById('sub-xyz');
      const togSpline = document.getElementById('tog-spline-mode');
      const togXyz = document.getElementById('tog-xyz-mode');
      if (currentMode === 'historic' && ACTIVE_DATA && ACTIVE_DATA.length > 1) {{
        const durMin = ((ACTIVE_DATA[ACTIVE_DATA.length - 1][0] - ACTIVE_DATA[0][0]) / 60000).toFixed(1);
        if (subSpline) {{
          subSpline.innerText = (chartSpanMode.spline === 'full')
            ? `${{durMin}}-min complete run • Vibration resultant & Acoustic sound amplitude`
            : `40s window • Vibration resultant & Acoustic sound amplitude`;
        }}
        if (subXyz) {{
          subXyz.innerText = (chartSpanMode.xyz === 'full')
            ? `${{durMin}}-min complete run • Isolated X/Y & Z oscilloscope lanes`
            : `40s window • Isolated X/Y & Z oscilloscope lanes`;
        }}
        const btnSplineFull = document.getElementById('btn-spline-full');
        const btnXyzFull = document.getElementById('btn-xyz-full');
        if (btnSplineFull) btnSplineFull.innerText = `Full Run (${{durMin}}m)`;
        if (btnXyzFull) btnXyzFull.innerText = `Full Run (${{durMin}}m)`;

        if (togSpline) togSpline.style.display = 'inline-flex';
        if (togXyz) togXyz.style.display = 'inline-flex';
      }} else {{
        if (subSpline) subSpline.innerText = 'Vibration resultant • Acoustic sound amplitude';
        if (subXyz) subXyz.innerText = 'MPU-6050 Accelerometer • Isolated X/Y & Z oscilloscope lanes';
        if (togSpline) togSpline.style.display = 'none';
        if (togXyz) togXyz.style.display = 'none';
      }}
    }}

    const splineCvs = document.getElementById('spline-canvas');
    const splineCtx = splineCvs.getContext('2d');
    const xyzCvs = document.getElementById('xyz-canvas');
    const xyzCtx = xyzCvs.getContext('2d');
    const areaCvs = document.getElementById('area-canvas');
    const areaCtx = areaCvs.getContext('2d');
    const energyCvs = document.getElementById('energy-canvas');
    const energyCtx = energyCvs ? energyCvs.getContext('2d') : null;

    const timeSlider = document.getElementById('time-slider');
    const scrubLabel = document.getElementById('scrub-label');
    const lblCurrTime = document.getElementById('lbl-curr-time');

    const statusBadge = document.getElementById('badge-live-tag');
    const statusDot = document.getElementById('status-dot-indicator');
    const lblStatusText = document.getElementById('lbl-status-text');

    const statusBadgeMob = document.getElementById('badge-live-tag-mobile');
    const statusDotMob = document.getElementById('status-dot-indicator-mobile');
    const lblStatusTextMob = document.getElementById('lbl-status-text-mobile');

    const offlineBanner = document.getElementById('live-offline-banner');
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

      if (energyCvs) {{
        const eRect = energyCvs.parentElement.getBoundingClientRect();
        energyCvs.width = eRect.width * dpr;
        energyCvs.height = eRect.height * dpr;
      }}

      drawSpline();
      drawXyz();
      drawArea();
      drawEnergy();
    }}
    window.addEventListener('resize', resizeCanvases);

    function formatMs(ms) {{
      const totalSec = Math.floor(ms / 1000);
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
    }}

    function showToast(msg) {{
      const t = document.getElementById('toast');
      if (!t) return;
      t.innerText = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 3500);
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
      const fontSize = 8 * dpr;
      ctx.font = `700 ${{fontSize}}px 'JetBrains Mono', monospace`;
      const tw = ctx.measureText(text).width;
      const pw = tw + (10 * dpr);
      const ph = 16 * dpr;
      const px = align === 'right' ? x - pw : (align === 'center' ? x - (pw / 2) : x);
      let py = y - (ph / 2);
      if (py < 2 * dpr) py = 2 * dpr;

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
      ctx.fillText(text, px + (5 * dpr), py + (11.5 * dpr));
    }}

    function drawTimeGrid(ctx, w, h, marginLeft, marginRight, plotW, plotH, marginTop, dpr, isMobile) {{
      if (currentMode !== 'historic' || !ACTIVE_DATA || ACTIVE_DATA.length < 2) return;
      const startT = ACTIVE_DATA[0][0];
      const endT = ACTIVE_DATA[ACTIVE_DATA.length - 1][0];
      const durMin = (endT - startT) / 60000;
      if (durMin <= 0) return;

      let stepMin = 20;
      if (durMin <= 3) stepMin = 0.5;
      else if (durMin <= 6) stepMin = 1;
      else if (durMin <= 15) stepMin = 2;
      else if (durMin <= 35) stepMin = 5;
      else if (durMin <= 75) stepMin = 10;
      else if (durMin <= 150) stepMin = 20;
      else stepMin = 30;

      const durMs = endT - startT;
      const stepMs = stepMin * 60000;

      for (let ms = stepMs; ms < durMs - (stepMs * 0.45); ms += stepMs) {{
        const frac = ms / durMs;
        const x = marginLeft + (frac * plotW);

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.lineWidth = 1 * dpr;
        ctx.beginPath();
        ctx.moveTo(x, marginTop);
        ctx.lineTo(x, marginTop + plotH);
        ctx.stroke();

        ctx.fillStyle = 'rgba(255, 255, 255, 0.38)';
        ctx.font = `600 ${{ (isMobile ? 7.5 : 8) * dpr }}px 'JetBrains Mono', monospace`;
        ctx.textAlign = 'center';
        const lbl = (ms % 60000 === 0) ? `${{(ms / 60000).toFixed(0)}}m` : `${{(ms / 60000).toFixed(1)}}m`;
        ctx.fillText(lbl, x, h - (4 * dpr));
      }}

      // Start label (0.0m)
      ctx.fillStyle = 'rgba(255, 255, 255, 0.45)';
      ctx.font = `600 ${{ (isMobile ? 7.5 : 8) * dpr }}px 'JetBrains Mono', monospace`;
      ctx.textAlign = 'left';
      ctx.fillText('0.0m', marginLeft + (2 * dpr), h - (4 * dpr));

      // End label (e.g. 102.8m)
      ctx.textAlign = 'right';
      ctx.fillText(`${{durMin.toFixed(1)}}m`, w - marginRight - (2 * dpr), h - (4 * dpr));
      ctx.textAlign = 'left';
    }}

    function setupCanvasScrubbing(canvas) {{
      let isDragging = false;

      function scrubAt(e) {{
        if (currentMode !== 'historic' || !ACTIVE_DATA || ACTIVE_DATA.length < 2) return;
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const isMobile = (canvas.width / dpr) < 580;
        const marginLeft = (isMobile ? 44 : 64) * dpr;
        const marginRight = (isMobile ? 34 : 52) * dpr;
        const plotW = canvas.width - marginLeft - marginRight;
        if (plotW <= 0) return;

        const clientX = (e.touches && e.touches.length > 0) ? e.touches[0].clientX : e.clientX;
        const rawX = (clientX - rect.left) * dpr;
        const frac = Math.max(0, Math.min(1, (rawX - marginLeft) / plotW));
        const targetIdx = Math.round(frac * (ACTIVE_DATA.length - 1));

        if (timeSlider) timeSlider.value = targetIdx;
        onScrub(targetIdx);
      }}

      canvas.addEventListener('mousedown', (e) => {{
        isDragging = true;
        scrubAt(e);
      }});
      window.addEventListener('mousemove', (e) => {{
        if (isDragging) scrubAt(e);
      }});
      window.addEventListener('mouseup', () => {{
        isDragging = false;
      }});

      canvas.addEventListener('touchstart', (e) => {{
        isDragging = true;
        scrubAt(e);
      }}, {{ passive: true }});
      canvas.addEventListener('touchmove', (e) => {{
        if (isDragging) scrubAt(e);
      }}, {{ passive: true }});
      canvas.addEventListener('touchend', () => {{
        isDragging = false;
      }});
    }}

    function getRmsScale(maxObserved) {{
      if (maxObserved > 1100) {{
        const ceil = Math.ceil(maxObserved / 250) * 250;
        return {{
          max: ceil * 1.05,
          ticks: [ceil, Math.round(ceil * 0.75), Math.round(ceil * 0.5), Math.round(ceil * 0.25), 0],
          ticksMobile: [ceil, Math.round(ceil * 0.5), 0]
        }};
      }}
      if (maxObserved > 750) {{
        return {{
          max: 1050,
          ticks: [1000, 750, 500, 250, 0],
          ticksMobile: [1000, 500, 0]
        }};
      }}
      if (maxObserved > 520) {{
        return {{
          max: 840,
          ticks: [800, 600, 400, 200, 0],
          ticksMobile: [800, 400, 0]
        }};
      }}
      return {{
        max: 520,
        ticks: [500, 375, 250, 125, 0],
        ticksMobile: [500, 250, 0]
      }};
    }}

    // Switch active view mode
    function toggleViewMode() {{
      const newMode = (currentMode === 'live') ? 'historic' : 'live';
      if (newMode === 'historic') {{
        switchToSession(activeSessionKey);
      }} else {{
        setViewMode('live');
      }}
    }}

    function onSessionDropdownChange(val) {{
      if (val === 'live') {{
        setViewMode('live');
      }} else {{
        switchToSession(val);
      }}
    }}

    async function switchToSession(key) {{
      if (key === 'live') {{
        setViewMode('live');
        return;
      }}

      if (key.startsWith('cloud_') && (!LOADED_SESSIONS[key] || !LOADED_SESSIONS[key].data)) {{
        const sid = key.replace('cloud_', '');
        await loadCloudSession(sid);
        return;
      }}

      const session = LOADED_SESSIONS[key];
      if (!session || !session.data || session.data.length < 2) return;

      activeSessionKey = key;
      activeSessionName = session.name;
      ACTIVE_DATA = session.data;
      currentIndex = 0;

      const sel = document.getElementById('sel-session');
      if (sel) sel.value = key;

      if (timeSlider) {{
        timeSlider.max = ACTIVE_DATA.length - 1;
        timeSlider.value = 0;
      }}
      if (scrubLabel) {{
        scrubLabel.innerText = '0.0m';
      }}

      setViewMode('historic');
      applyRecord(ACTIVE_DATA[0], false);
      updateChartSubtitles();
      drawSpline();
      drawXyz();
      drawArea();
      drawEnergy();
    }}

    function setViewMode(mode) {{
      currentMode = mode;
      const sel = document.getElementById('sel-session');

      if (currentMode === 'live') {{
        if (sel) sel.value = 'live';
        wrapScrubber.style.display = 'none';
        btnPrimaryAction.innerText = isLivePaused ? 'Resume Live Stream' : 'Pause Live Stream';
        btnSecondarySwitch.innerText = `Switch to Historical: ${{activeSessionName}}`;
        titleTimeline.innerText = 'Live Rig Telemetry Stream';
        subTimeline.innerText = 'Real-time incoming telemetry stream from ESP32';
        lblCurrTime.innerText = 'LIVE (50 Hz)';
        updateRigStatusUI(isRigOnline);
        updateChartSubtitles();
        checkRigHeartbeat();
      }} else {{
        if (isPlaying) togglePlayPause();
        if (sel) sel.value = activeSessionKey;
        wrapScrubber.style.display = 'flex';
        btnPrimaryAction.innerText = `Replay Run (${{activeSessionName}})`;
        btnSecondarySwitch.innerText = 'Switch to Live Rig (Real-Time)';
        const durMin = ((ACTIVE_DATA[ACTIVE_DATA.length - 1][0] - ACTIVE_DATA[0][0]) / 60000).toFixed(1);
        titleTimeline.innerText = `${{activeSessionName}} Archive (${{durMin}} Mins)`;
        subTimeline.innerText = `${{durMin}}-min continuous telemetry waveform • ${{activeSessionName}}`;
        if (timeSlider) timeSlider.max = ACTIVE_DATA.length - 1;
        updateRigStatusUI(false);
        updateChartSubtitles();
        applyRecord(ACTIVE_DATA[currentIndex], false);
      }}
      drawSpline();
      drawXyz();
      drawArea();
      drawEnergy();
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
          if (statusBadge) statusBadge.className = 'status-badge desktop-status-tag';
          if (statusDot) statusDot.className = 'status-dot';
          if (lblStatusText) lblStatusText.innerText = 'Live Rig Active (50 Hz)';

          if (statusBadgeMob) statusBadgeMob.className = 'status-badge mobile-status-tag';
          if (statusDotMob) statusDotMob.className = 'status-dot';
          if (lblStatusTextMob) lblStatusTextMob.innerText = 'Live 50 Hz';

          if (offlineBanner) offlineBanner.style.display = 'none';
        }} else {{
          if (statusBadge) statusBadge.className = 'status-badge offline-badge desktop-status-tag';
          if (statusDot) statusDot.className = 'status-dot dot-offline';
          if (lblStatusText) lblStatusText.innerText = 'Live Rig Offline (No Input)';

          if (statusBadgeMob) statusBadgeMob.className = 'status-badge offline-badge mobile-status-tag';
          if (statusDotMob) statusDotMob.className = 'status-dot dot-offline';
          if (lblStatusTextMob) lblStatusTextMob.innerText = 'Offline';

          if (offlineBanner) offlineBanner.style.display = 'flex';
        }}
      }} else {{
        if (statusBadge) {{
          statusBadge.className = 'status-badge desktop-status-tag';
          if (statusDot) statusDot.className = 'status-dot';
          if (lblStatusText) lblStatusText.innerText = `${{activeSessionName}} Archive`;
        }}
        if (statusBadgeMob) {{
          statusBadgeMob.className = 'status-badge mobile-status-tag';
          if (statusDotMob) statusDotMob.className = 'status-dot';
          const shortName = activeSessionName.length > 18 ? activeSessionName.slice(0, 15) + '...' : activeSessionName;
          if (lblStatusTextMob) lblStatusTextMob.innerText = `${{shortName}} Archive`;
        }}
        if (offlineBanner) offlineBanner.style.display = 'none';
      }}
    }}

    async function checkRigHeartbeat() {{
      try {{
        const res = await fetch('https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app/live.json');
        const d = await res.json();
        const wasOnlineBefore = isRigOnline;

        if (d && (d.cnt !== undefined || d.uptime !== undefined || d.ts !== undefined)) {{
          const isFreshByTs = d.ts ? (Date.now() - d.ts < 12000) : true;
          const hasIncremented = (lastLivePacketCnt !== null && d.cnt !== undefined && d.cnt !== lastLivePacketCnt) ||
                                 (lastLivePacketUptime !== null && d.uptime !== undefined && d.uptime !== lastLivePacketUptime);

          if (hasIncremented && isFreshByTs) {{
            lastPacketArrivedAt = Date.now();
            isRigOnline = true;
          }} else {{
            if (!isFreshByTs) {{
              isRigOnline = false;
            }} else if (lastPacketArrivedAt === 0) {{
              isRigOnline = false;
            }} else if (Date.now() - lastPacketArrivedAt > 4500) {{
              isRigOnline = false;
            }}
          }}

          lastLivePacketCnt = d.cnt;
          lastLivePacketUptime = d.uptime;

          // Push into Live rolling buffer
          if (!isLivePaused && isRigOnline) {{
            const pwr = (d.power !== undefined && d.power !== null) ? d.power : (d.pwr !== undefined ? d.pwr : 0.0);
            const newRec = [d.uptime * 1000, d.ax, d.ay, d.az, d.rms, pwr];
            LIVE_BUFFER.push(newRec);
            if (LIVE_BUFFER.length > 80) LIVE_BUFFER.shift();

            if (currentMode === 'live') {{
              applyRecord(newRec, true);
              drawSpline();
              drawXyz();
              drawArea();
              drawEnergy();
            }}
          }}
        }} else {{
          isRigOnline = false;
        }}

        // When rig finishes transmitting and transitions to offline, immediately discover newly archived cloud session
        if (wasOnlineBefore && !isRigOnline) {{
          discoverFirebaseSessions();
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

      const curVibeEl = document.getElementById('spline-cur-vibe');
      if (curVibeEl) curVibeEl.innerText = vibe.toFixed(2);
      const curRmsEl = document.getElementById('spline-cur-rms');
      if (curRmsEl) curRmsEl.innerText = rms.toFixed(1);

      const strX = (ax >= 0 ? '+' : '') + ax.toFixed(2);
      const strY = (ay >= 0 ? '+' : '') + ay.toFixed(2);
      const strZ = (az >= 0 ? '+' : '') + az.toFixed(2);
      vibeLegX.innerText = strX;
      vibeLegY.innerText = strY;
      vibeLegZ.innerText = strZ;

      if (!isFromLive && ACTIVE_DATA && ACTIVE_DATA.length > 0) {{
        const startT = ACTIVE_DATA[0][0];
        const maxT = ACTIVE_DATA[ACTIVE_DATA.length - 1][0];
        lblCurrTime.innerText = `${{formatMs(t - startT)}} / ${{formatMs(maxT - startT)}}`;
      }}
    }}

    // Canvas 1: Dual-Modality Waveform (Responsive gutters & crisp labels)
    function drawSpline() {{
      const w = splineCvs.width;
      const h = splineCvs.height;
      const dpr = window.devicePixelRatio || 1;
      splineCtx.clearRect(0, 0, w, h);

      const isMobile = (w / dpr) < 580;
      const marginLeft = (isMobile ? 44 : 64) * dpr;
      const marginRight = (isMobile ? 34 : 52) * dpr;
      const marginTop = 16 * dpr;
      const marginBottom = (isMobile ? 18 : 22) * dpr;
      const plotW = w - marginLeft - marginRight;
      const plotH = h - marginTop - marginBottom;

      let points;
      let curRelIdx = 0;
      const isFull = (currentMode === 'historic' && chartSpanMode.spline === 'full');

      if (currentMode === 'live') {{
        points = LIVE_BUFFER.length > 1 ? LIVE_BUFFER : [
          [0, -0.74, 1.40, -9.40, 105.6],
          [2000, -0.74, 1.40, -9.40, 105.6]
        ];
        curRelIdx = points.length - 1;
      }} else if (isFull) {{
        points = ACTIVE_DATA;
        curRelIdx = currentIndex;
      }} else {{
        const winSize = 40;
        const startIdx = Math.max(0, currentIndex - (winSize / 2));
        const endIdx = Math.min(ACTIVE_DATA.length - 1, startIdx + winSize);
        points = ACTIVE_DATA.slice(startIdx, endIdx + 1);
        curRelIdx = currentIndex - startIdx;
      }}

      // Vertical separator lines
      splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      splineCtx.lineWidth = 1 * dpr;
      splineCtx.beginPath();
      splineCtx.moveTo(marginLeft, marginTop);
      splineCtx.lineTo(marginLeft, h - marginBottom);
      splineCtx.moveTo(w - marginRight, marginTop);
      splineCtx.lineTo(w - marginRight, h - marginBottom);
      splineCtx.stroke();

      // Time grid & labels across the bottom (in full historical mode)
      if (isFull) {{
        drawTimeGrid(splineCtx, w, h, marginLeft, marginRight, plotW, plotH, marginTop, dpr, isMobile);
      }}

      // Dynamic RMS scale based on visible points
      const maxRmsInPoints = points.reduce((m, p) => Math.max(m, p[4]), 0);
      const scaleConf = getRmsScale(maxRmsInPoints);
      const rmsMax = scaleConf.max;
      const soundTicks = isMobile ? scaleConf.ticksMobile : scaleConf.ticks;

      // Right side: Sound RMS ticks
      soundTicks.forEach(val => {{
        const y = marginTop + plotH - ((val / rmsMax) * plotH);
        splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        splineCtx.beginPath();
        splineCtx.moveTo(marginLeft, y);
        splineCtx.lineTo(w - marginRight, y);
        splineCtx.stroke();

        splineCtx.fillStyle = 'rgba(251, 146, 60, 0.6)';
        splineCtx.font = `600 ${{ (isMobile ? 7.5 : 8) * dpr }}px 'JetBrains Mono', monospace`;
        splineCtx.textAlign = 'left';
        splineCtx.fillText(`${{val}}`, w - marginRight + (5 * dpr), y + (3 * dpr));
      }});
      splineCtx.fillText('RMS', w - marginRight + (5 * dpr), marginTop - (4 * dpr));

      // Left side: Vibration m/s^2 ticks & dynamic scaling
      const maxVibe = points.reduce((m, p) => Math.max(m, Math.sqrt(p[1]*p[1] + p[2]*p[2] + p[3]*p[3])), 9.81);
      const minVibe = points.reduce((m, p) => Math.min(m, Math.sqrt(p[1]*p[1] + p[2]*p[2] + p[3]*p[3])), 9.81);
      const vibeSpread = Math.max(2.5, maxVibe - 9.81, 9.81 - minVibe);
      const scaleVibe = Math.min((isMobile ? 20 : 25) * dpr, (plotH * 0.38) / vibeSpread);

      const vibeTicks = [
        {{ val: 12.0, lbl: '12.0' }},
        {{ val: 9.81, lbl: isMobile ? '9.81' : '9.81 (1g)' }},
        {{ val: 8.0, lbl: '8.0' }}
      ];
      vibeTicks.forEach(t => {{
        const y = marginTop + (plotH * 0.45) - ((t.val - 9.81) * scaleVibe);
        splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        splineCtx.beginPath();
        splineCtx.moveTo(marginLeft, y);
        splineCtx.lineTo(w - marginRight, y);
        splineCtx.stroke();

        splineCtx.fillStyle = 'rgba(0, 240, 210, 0.6)';
        splineCtx.font = `600 ${{ (isMobile ? 7.5 : 8) * dpr }}px 'JetBrains Mono', monospace`;
        splineCtx.textAlign = 'right';
        splineCtx.fillText(t.lbl, marginLeft - (5 * dpr), y + (3 * dpr));
      }});
      splineCtx.fillText('m/s²', marginLeft - (5 * dpr), marginTop - (4 * dpr));
      splineCtx.textAlign = 'left';

      // Dashed 1g Gravity Baseline
      const y1g = marginTop + (plotH * 0.45);
      splineCtx.strokeStyle = 'rgba(0, 240, 210, 0.2)';
      splineCtx.setLineDash([3 * dpr, 3 * dpr]);
      splineCtx.beginPath();
      splineCtx.moveTo(marginLeft, y1g);
      splineCtx.lineTo(w - marginRight, y1g);
      splineCtx.stroke();
      splineCtx.setLineDash([]);

      if (points.length < 2) return;

      const strokeW = (isFull && points.length > 500) ? (1.5 * dpr) : (2 * dpr);

      // 1. Draw Sound Wave (Coral) strictly within [marginLeft, w - marginRight]
      const gradCoral = splineCtx.createLinearGradient(0, marginTop, 0, marginTop + plotH);
      gradCoral.addColorStop(0, 'rgba(251, 146, 60, 0.15)');
      gradCoral.addColorStop(1, 'rgba(251, 146, 60, 0.0)');

      splineCtx.beginPath();
      splineCtx.moveTo(marginLeft, marginTop + plotH);
      for (let i = 0; i < points.length; i++) {{
        const x = marginLeft + ((i / (points.length - 1)) * plotW);
        const normRms = points[i][4] / rmsMax;
        const y = Math.max(marginTop + (1 * dpr), marginTop + plotH - (normRms * plotH));
        splineCtx.lineTo(x, y);
      }}
      splineCtx.lineTo(w - marginRight, marginTop + plotH);
      splineCtx.closePath();
      splineCtx.fillStyle = gradCoral;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#fb923c';
      splineCtx.lineWidth = strokeW;
      for (let i = 0; i < points.length; i++) {{
        const x = marginLeft + ((i / (points.length - 1)) * plotW);
        const normRms = points[i][4] / rmsMax;
        const y = Math.max(marginTop + (1 * dpr), marginTop + plotH - (normRms * plotH));
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
        const y = marginTop + (plotH * 0.45) - ((v - 9.81) * scaleVibe);
        splineCtx.lineTo(x, y);
      }}
      splineCtx.lineTo(w - marginRight, marginTop + plotH);
      splineCtx.closePath();
      splineCtx.fillStyle = gradTeal;
      splineCtx.fill();

      splineCtx.beginPath();
      splineCtx.strokeStyle = '#00f0d2';
      splineCtx.lineWidth = strokeW;
      for (let i = 0; i < points.length; i++) {{
        const x = marginLeft + ((i / (points.length - 1)) * plotW);
        const v = Math.sqrt(points[i][1]*points[i][1] + points[i][2]*points[i][2] + points[i][3]*points[i][3]);
        const y = marginTop + (plotH * 0.45) - ((v - 9.81) * scaleVibe);
        if (i === 0) splineCtx.moveTo(x, y); else splineCtx.lineTo(x, y);
      }}
      splineCtx.stroke();

      // Vertical Playhead & Active point dots
      if (curRelIdx >= 0 && curRelIdx < points.length) {{
        const cx = marginLeft + ((curRelIdx / (points.length - 1)) * plotW);

        // Vertical Scrubber Cursor Line
        splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        splineCtx.lineWidth = 1.5 * dpr;
        splineCtx.beginPath();
        splineCtx.moveTo(cx, marginTop);
        splineCtx.lineTo(cx, marginTop + plotH);
        splineCtx.stroke();

        const curPt = points[curRelIdx];

        // Active Sound dot (Coral)
        const normRms = curPt[4] / rmsMax;
        const cyRms = Math.max(marginTop + (1 * dpr), marginTop + plotH - (normRms * plotH));
        splineCtx.fillStyle = '#fb923c';
        splineCtx.beginPath();
        splineCtx.arc(cx, cyRms, 4 * dpr, 0, Math.PI * 2);
        splineCtx.fill();
        splineCtx.strokeStyle = '#ffffff';
        splineCtx.lineWidth = 1 * dpr;
        splineCtx.stroke();

        // Active Vibration dot (Teal)
        const v = Math.sqrt(curPt[1]*curPt[1] + curPt[2]*curPt[2] + curPt[3]*curPt[3]);
        const cyVibe = marginTop + (plotH * 0.45) - ((v - 9.81) * scaleVibe);
        splineCtx.fillStyle = '#00f0d2';
        splineCtx.beginPath();
        splineCtx.arc(cx, cyVibe, 4 * dpr, 0, Math.PI * 2);
        splineCtx.fill();
        splineCtx.strokeStyle = '#ffffff';
        splineCtx.lineWidth = 1 * dpr;
        splineCtx.stroke();
      }}
    }}

    // Canvas 2: Tri-Axial Vibration (Zero collisions, Left-anchored baseline labels)
    function drawXyz() {{
      const w = xyzCvs.width;
      const h = xyzCvs.height;
      const dpr = window.devicePixelRatio || 1;
      xyzCtx.clearRect(0, 0, w, h);

      const isMobile = (w / dpr) < 580;
      const marginLeft = (isMobile ? 44 : 64) * dpr;
      const marginRight = (isMobile ? 34 : 52) * dpr;
      const marginTop = 14 * dpr;
      const marginBottom = (isMobile ? 18 : 22) * dpr;
      const plotW = w - marginLeft - marginRight;
      const plotH = h - marginTop - marginBottom;

      const yZero = marginTop + (plotH * 0.32);
      const scaleXY = (isMobile ? 10 : 12) * dpr;
      const yGravity = marginTop + (plotH * 0.78);
      const scaleZ = (isMobile ? 10 : 12) * dpr;

      // Vertical separator line
      xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      xyzCtx.lineWidth = 1 * dpr;
      xyzCtx.beginPath();
      xyzCtx.moveTo(marginLeft, marginTop);
      xyzCtx.lineTo(marginLeft, h - marginBottom);
      xyzCtx.moveTo(w - marginRight, marginTop);
      xyzCtx.lineTo(w - marginRight, h - marginBottom);
      xyzCtx.stroke();

      let points;
      let curRelIdx = 0;
      const isFull = (currentMode === 'historic' && chartSpanMode.xyz === 'full');

      if (currentMode === 'live') {{
        points = LIVE_BUFFER.length > 1 ? LIVE_BUFFER : [
          [0, -0.74, 1.40, -9.40, 105.6],
          [2000, -0.74, 1.40, -9.40, 105.6]
        ];
        curRelIdx = points.length - 1;
      }} else if (isFull) {{
        points = ACTIVE_DATA;
        curRelIdx = currentIndex;
      }} else {{
        const winSize = 40;
        const startIdx = Math.max(0, currentIndex - (winSize / 2));
        const endIdx = Math.min(ACTIVE_DATA.length - 1, startIdx + winSize);
        points = ACTIVE_DATA.slice(startIdx, endIdx + 1);
        curRelIdx = currentIndex - startIdx;
      }}

      // Time grid & labels across the bottom (in full historical mode)
      if (isFull) {{
        drawTimeGrid(xyzCtx, w, h, marginLeft, marginRight, plotW, plotH, marginTop, dpr, isMobile);
      }}

      // Baseline grid lines (cleanly spaced, zero gutter collisions)
      const hLines = isMobile ? [
        {{ y: yZero - (4.0 * scaleXY), lbl: '+4.0', col: 'rgba(255, 255, 255, 0.25)' }},
        {{ y: yZero, lbl: '0.0', col: 'rgba(255, 255, 255, 0.45)' }},
        {{ y: yGravity, lbl: '-9.81', col: 'rgba(167, 139, 250, 0.6)' }},
        {{ y: yGravity - ((-13.0 + 9.81) * scaleZ), lbl: '-13.0', col: 'rgba(167, 139, 250, 0.3)' }}
      ] : [
        {{ y: yZero - (4.0 * scaleXY), lbl: '+4.0 m/s²', col: 'rgba(255, 255, 255, 0.25)' }},
        {{ y: yZero, lbl: '0.0 (X/Y)', col: 'rgba(255, 255, 255, 0.45)' }},
        {{ y: yGravity, lbl: '-9.81 (Z)', col: 'rgba(167, 139, 250, 0.6)' }},
        {{ y: yGravity - ((-13.0 + 9.81) * scaleZ), lbl: '-13.0 m/s²', col: 'rgba(167, 139, 250, 0.3)' }}
      ];

      hLines.forEach(l => {{
        xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        xyzCtx.beginPath();
        xyzCtx.moveTo(marginLeft, l.y);
        xyzCtx.lineTo(w - marginRight, l.y);
        xyzCtx.stroke();

        xyzCtx.fillStyle = l.col;
        xyzCtx.font = `600 ${{ (isMobile ? 7.5 : 8) * dpr }}px 'JetBrains Mono', monospace`;
        xyzCtx.textAlign = 'right';
        xyzCtx.fillText(l.lbl, marginLeft - (5 * dpr), l.y + (3 * dpr));
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

      if (points.length < 2) return;

      const strokeW = (isFull && points.length > 500) ? (1.5 * dpr) : (2 * dpr);

      // Plot Az (Purple)
      if (axisVisible.z) {{
        xyzCtx.beginPath();
        xyzCtx.strokeStyle = '#a78bfa';
        xyzCtx.lineWidth = strokeW;
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
        xyzCtx.lineWidth = strokeW;
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
        xyzCtx.lineWidth = strokeW;
        for (let i = 0; i < points.length; i++) {{
          const x = marginLeft + ((i / (points.length - 1)) * plotW);
          const ax = points[i][1];
          const y = yZero - (ax * scaleXY);
          if (i === 0) xyzCtx.moveTo(x, y); else xyzCtx.lineTo(x, y);
        }}
        xyzCtx.stroke();
      }}

      // Active cursor dots & vertical scrubber line
      if (curRelIdx >= 0 && curRelIdx < points.length) {{
        const cx = marginLeft + ((curRelIdx / (points.length - 1)) * plotW);

        // Vertical Scrubber Cursor Line
        xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        xyzCtx.lineWidth = 1.5 * dpr;
        xyzCtx.beginPath();
        xyzCtx.moveTo(cx, marginTop);
        xyzCtx.lineTo(cx, marginTop + plotH);
        xyzCtx.stroke();

        const pt = points[curRelIdx];
        if (axisVisible.z) {{
          const cyZ = yGravity - ((pt[3] + 9.81) * scaleZ);
          xyzCtx.fillStyle = '#a78bfa';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyZ, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
          xyzCtx.strokeStyle = '#ffffff';
          xyzCtx.lineWidth = 1 * dpr;
          xyzCtx.stroke();
        }}
        if (axisVisible.x) {{
          const cyX = yZero - (pt[1] * scaleXY);
          xyzCtx.fillStyle = '#00f0d2';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyX, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
          xyzCtx.strokeStyle = '#ffffff';
          xyzCtx.lineWidth = 1 * dpr;
          xyzCtx.stroke();
        }}
        if (axisVisible.y) {{
          const cyY = yZero - (pt[2] * scaleXY);
          xyzCtx.fillStyle = '#fb923c';
          xyzCtx.beginPath();
          xyzCtx.arc(cx, cyY, 4 * dpr, 0, Math.PI * 2);
          xyzCtx.fill();
          xyzCtx.strokeStyle = '#ffffff';
          xyzCtx.lineWidth = 1 * dpr;
          xyzCtx.stroke();
        }}
      }}

      // Dynamic Anti-Collision Placement: Always render baseline badges on opposite side of active cursor, AFTER curves are drawn!
      const isCursorOnLeftXyz = (points.length > 1) ? ((curRelIdx / (points.length - 1)) < 0.5) : true;
      const badgeAlign = isCursorOnLeftXyz ? 'right' : 'left';
      const badgeX = isCursorOnLeftXyz ? (w - marginRight - (6 * dpr)) : (marginLeft + (8 * dpr));

      drawPillBadge(xyzCtx, badgeX, yZero - (10 * dpr), isMobile ? '0.0 Baseline' : 'X/Y Zero Baseline', 'rgba(255,255,255,0.45)', badgeAlign, dpr);
      drawPillBadge(xyzCtx, badgeX, yGravity - (10 * dpr), isMobile ? 'Z 1g Gravity' : 'Z 1g Gravity (-9.81 m/s²)', '#a78bfa', badgeAlign, dpr);
    }}

    // Canvas 3: Timeline & Controls (Zero overlapping badges, Clean Scrubber)
    function drawArea() {{
      const w = areaCvs.width;
      const h = areaCvs.height;
      const dpr = window.devicePixelRatio || 1;
      areaCtx.clearRect(0, 0, w, h);

      const isMobile = (w / dpr) < 580;
      const marginLeft = (isMobile ? 44 : 64) * dpr;
      const marginRight = (isMobile ? 34 : 52) * dpr;
      const marginTop = 18 * dpr;
      const marginBottom = (isMobile ? 18 : 22) * dpr;
      const plotW = w - marginLeft - marginRight;
      const plotH = h - marginTop - marginBottom;

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
        dataSeries = ACTIVE_DATA;
        curPointIdx = currentIndex;
      }}

      const total = dataSeries.length;
      if (total < 2) return;

      // Determine RMS scale dynamically based on dataset
      const maxRmsInData = dataSeries.reduce((m, p) => Math.max(m, p[4]), 0);
      const scaleConf = getRmsScale(maxRmsInData);
      const rmsMax = scaleConf.max;
      const getY = (rms) => Math.max(marginTop + (1 * dpr), marginTop + plotH - ((rms / rmsMax) * plotH));

      // Vertical separator line
      areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      areaCtx.lineWidth = 1 * dpr;
      areaCtx.beginPath();
      areaCtx.moveTo(marginLeft, marginTop);
      areaCtx.lineTo(marginLeft, h - marginBottom);
      areaCtx.moveTo(w - marginRight, marginTop);
      areaCtx.lineTo(w - marginRight, h - marginBottom);
      areaCtx.stroke();

      // Time grid & labels across the bottom (in historical mode)
      if (currentMode === 'historic') {{
        drawTimeGrid(areaCtx, w, h, marginLeft, marginRight, plotW, plotH, marginTop, dpr, isMobile);
      }}

      // Horizontal Y-Axis Numeric Rulers in Left Gutter
      const yTicks = isMobile ? scaleConf.ticksMobile : scaleConf.ticks;
      yTicks.forEach(val => {{
        const yVal = marginTop + plotH - ((val / rmsMax) * plotH);
        areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        areaCtx.beginPath();
        areaCtx.moveTo(marginLeft, yVal);
        areaCtx.lineTo(w - marginRight, yVal);
        areaCtx.stroke();

        areaCtx.fillStyle = 'rgba(255, 255, 255, 0.45)';
        areaCtx.font = `600 ${{ (isMobile ? 7.5 : 8.5) * dpr }}px 'JetBrains Mono', monospace`;
        areaCtx.textAlign = 'right';
        areaCtx.fillText(`${{val}}`, marginLeft - (5 * dpr), yVal + (3 * dpr));
      }});
      areaCtx.fillText('RMS', marginLeft - (5 * dpr), marginTop - (6 * dpr));
      areaCtx.textAlign = 'left';

      // Baseline Dashed Line
      const yBase = getY(120.0);
      areaCtx.strokeStyle = 'rgba(0, 240, 210, 0.25)';
      areaCtx.lineWidth = 1 * dpr;
      areaCtx.setLineDash([3 * dpr, 3 * dpr]);
      areaCtx.beginPath();
      areaCtx.moveTo(marginLeft, yBase);
      areaCtx.lineTo(w - marginRight, yBase);
      areaCtx.stroke();
      areaCtx.setLineDash([]);

      // Peak Spike Dashed Line (Dynamic in Live mode, Historical in Historic mode)
      let showPeak = false;
      let peakVal = 511.2;
      let peakLabel = '';

      if (currentMode === 'live') {{
        if (maxRmsInData > 160) {{
          showPeak = true;
          peakVal = maxRmsInData;
          peakLabel = isMobile ? `PEAK: ${{peakVal.toFixed(1)}}` : `LIVE PEAK: ${{peakVal.toFixed(1)}} RMS`;
        }}
      }} else {{
        showPeak = true;
        let peakRec = dataSeries[0];
        for (let i = 0; i < dataSeries.length; i++) {{
          if (dataSeries[i][4] > peakRec[4]) peakRec = dataSeries[i];
        }}
        peakVal = peakRec[4];
        const peakMin = ((peakRec[0] - dataSeries[0][0]) / 60000).toFixed(1);
        peakLabel = isMobile ? `PEAK: ${{peakVal.toFixed(1)}} (${{peakMin}}m)` : `PEAK SPIKE: ${{peakVal.toFixed(1)}} RMS (${{peakMin}}m)`;
      }}

      let yPeak = 0;
      if (showPeak) {{
        yPeak = getY(peakVal);
        areaCtx.strokeStyle = 'rgba(251, 146, 60, 0.4)';
        areaCtx.lineWidth = 1.2 * dpr;
        areaCtx.setLineDash([4 * dpr, 4 * dpr]);
        areaCtx.beginPath();
        areaCtx.moveTo(marginLeft, yPeak);
        areaCtx.lineTo(w - marginRight, yPeak);
        areaCtx.stroke();
        areaCtx.setLineDash([]);
      }}

      // Area gradient
      const grad = areaCtx.createLinearGradient(0, marginTop, 0, marginTop + plotH);
      grad.addColorStop(0, 'rgba(0, 240, 210, 0.25)');
      grad.addColorStop(0.8, 'rgba(0, 240, 210, 0.04)');
      grad.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

      areaCtx.beginPath();
      areaCtx.moveTo(marginLeft, marginTop + plotH);
      for (let i = 0; i < total; i++) {{
        const x = marginLeft + ((i / (total - 1)) * plotW);
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
      areaCtx.lineWidth = (total > 500) ? (1.5 * dpr) : (1.8 * dpr);
      for (let i = 0; i < total; i++) {{
        const x = marginLeft + ((i / (total - 1)) * plotW);
        const y = getY(dataSeries[i][4]);
        if (i === 0) areaCtx.moveTo(x, y); else areaCtx.lineTo(x, y);
      }}
      areaCtx.stroke();

      // Cursor scrubber line & dot
      const getX = (idx) => marginLeft + ((idx / (total - 1)) * plotW);
      const curX = getX(curPointIdx);
      const curRms = dataSeries[curPointIdx][4];
      const curY = getY(curRms);

      areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      areaCtx.lineWidth = 1.5 * dpr;
      areaCtx.beginPath();
      areaCtx.moveTo(curX, marginTop);
      areaCtx.lineTo(curX, marginTop + plotH);
      areaCtx.stroke();

      areaCtx.fillStyle = '#00f0d2';
      areaCtx.beginPath();
      areaCtx.arc(curX, curY, 4 * dpr, 0, Math.PI * 2);
      areaCtx.fill();
      areaCtx.strokeStyle = '#ffffff';
      areaCtx.lineWidth = 1 * dpr;
      areaCtx.stroke();

      // Dynamic Anti-Collision Placement: Always draw baseline & peak on OPPOSITE side of active cursor, AFTER curves are drawn!
      const isCursorOnLeft = (total > 1) ? ((curPointIdx / (total - 1)) < 0.5) : true;
      const baseAlign = isCursorOnLeft ? 'right' : 'left';
      const baseX = isCursorOnLeft ? (w - marginRight - (6 * dpr)) : (marginLeft + (8 * dpr));
      drawPillBadge(areaCtx, baseX, yBase - (10 * dpr), isMobile ? 'BASELINE: 120' : 'NORMAL BASELINE: 120 RMS', '#00f0d2', baseAlign, dpr);

      if (showPeak) {{
        const isPeakOnLeft = (!isCursorOnLeft && curRms > 300 && curX > (w - marginRight - (160 * dpr)));
        const peakAlign = isPeakOnLeft ? 'left' : 'right';
        const peakX = peakAlign === 'right' ? (w - marginRight - (6 * dpr)) : (marginLeft + (8 * dpr));
        drawPillBadge(areaCtx, peakX, yPeak - (10 * dpr), peakLabel, '#fb923c', peakAlign, dpr);
      }}

      // Floating cursor badge (Cleanly bounded, flips if near edges, never clipped)
      const spikeMult = Math.max(1.0, curRms / 120.0).toFixed(1);
      const spikePctVal = Math.round(((curRms - 120.0) / 120.0) * 100);
      const badgeText = isMobile ? `${{curRms.toFixed(1)}} RMS (${{spikeMult}}x)` : `${{curRms.toFixed(1)}} RMS (${{spikeMult}}x ${{spikePctVal > 0 ? '+' + spikePctVal + '%' : 'base'}})`;

      areaCtx.font = `700 ${{ (isMobile ? 7.5 : 8.5) * dpr }}px 'JetBrains Mono', monospace`;
      const tw = areaCtx.measureText(badgeText).width;
      const bw = tw + (10 * dpr);
      const bh = (isMobile ? 17 : 20) * dpr;

      let bx = curX - (bw / 2);
      if (bx < marginLeft + (4 * dpr)) bx = marginLeft + (4 * dpr);
      if (bx + bw > w - marginRight - (4 * dpr)) bx = w - marginRight - bw - (4 * dpr);

      let by = curY - bh - (6 * dpr);
      if (by < marginTop + (2 * dpr)) {{
        by = curY + (10 * dpr);
      }}
      if (by < marginTop + (2 * dpr)) by = marginTop + (2 * dpr);
      if (by + bh > h - marginBottom - (2 * dpr)) by = h - marginBottom - bh - (2 * dpr);

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
      areaCtx.fillText(badgeText, bx + (bw / 2), by + ((isMobile ? 11.5 : 13.5) * dpr));
      areaCtx.textAlign = 'left';
    }}


    // Canvas 4: Electrical Power & Energy Consumption (TP-Link Tapo P110)
    function drawEnergy() {{
      if (!energyCvs || !energyCtx) return;
      const w = energyCvs.width;
      const h = energyCvs.height;
      const dpr = window.devicePixelRatio || 1;
      energyCtx.clearRect(0, 0, w, h);

      const isMobile = (w / dpr) < 580;
      const marginLeft = (isMobile ? 44 : 64) * dpr;
      const marginRight = (isMobile ? 34 : 52) * dpr;
      const marginTop = 16 * dpr;
      const marginBottom = (isMobile ? 18 : 22) * dpr;
      const plotW = w - marginLeft - marginRight;
      const plotH = h - marginTop - marginBottom;

      let dataSeries;
      let curPointIdx = 0;

      if (currentMode === 'live') {{
        dataSeries = LIVE_BUFFER.length > 0 ? LIVE_BUFFER : [
          [0, -0.74, 1.40, -9.40, 105.6, 0.0],
          [2000, -0.74, 1.40, -9.40, 105.6, 0.0]
        ];
        curPointIdx = dataSeries.length - 1;
      }} else {{
        dataSeries = ACTIVE_DATA;
        curPointIdx = currentIndex;
      }}

      if (!dataSeries || dataSeries.length === 0) return;
      const total = dataSeries.length;

      // Extract power series (or infer from physical telemetry)
      function getPowerAt(idx) {{
        const r = dataSeries[idx];
        if (r && r.length >= 6 && r[5] !== null && r[5] !== undefined && !isNaN(r[5])) {{
          return r[5];
        }}
        if (!r) return 0.0;
        const vibe = Math.sqrt(r[1]*r[1] + r[2]*r[2] + r[3]*r[3]);
        const rms = r[4];
        if (vibe > 10.5) return Math.min(680.0, 420.0 + (vibe - 10.5) * 65.0 + (rms * 0.08));
        if (rms > 200.0) return 130.0 + Math.sin(idx * 0.3) * 60.0 + (rms * 0.15);
        if (idx < 25) return 85.0 + Math.sin(idx * 0.5) * 45.0; // dry tumble sensing
        return 4.5; // standby idle
      }}

      let maxPwrObserved = 100.0;
      let sumPwr = 0.0;
      for (let i = 0; i < total; i++) {{
        const p = getPowerAt(i);
        if (p > maxPwrObserved) maxPwrObserved = p;
        sumPwr += p;
      }}
      const avgPwr = sumPwr / total;

      let pwrMax = 700;
      let ticks = [600, 450, 300, 150, 0];
      if (maxPwrObserved > 650) {{
        pwrMax = 2200;
        ticks = [2000, 1500, 1000, 500, 0];
      }}
      const getY = (val) => marginTop + plotH - ((Math.max(0, Math.min(pwrMax, val)) / pwrMax) * plotH);

      // Horizontal gridlines & axis labels
      ticks.forEach(val => {{
        const yVal = getY(val);
        energyCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        energyCtx.beginPath();
        energyCtx.moveTo(marginLeft, yVal);
        energyCtx.lineTo(w - marginRight, yVal);
        energyCtx.stroke();

        energyCtx.fillStyle = 'rgba(255, 255, 255, 0.45)';
        energyCtx.font = `600 ${{(isMobile ? 7.5 : 8.5) * dpr}}px 'JetBrains Mono', monospace`;
        energyCtx.textAlign = 'right';
        energyCtx.fillText(`${{val}}`, marginLeft - (5 * dpr), yVal + (3 * dpr));
      }});
      energyCtx.fillText('Watts', marginLeft - (5 * dpr), marginTop - (6 * dpr));
      energyCtx.textAlign = 'left';

      // Timeline axis grid in historical mode
      if (currentMode === 'historic' && total > 1) {{
        drawTimelineAxisGrid(energyCtx, dataSeries[0][0], dataSeries[total - 1][0], marginLeft, marginRight, marginTop, plotW, plotH, w, h, dpr, isMobile);
      }}

      // Spin guideline (400W)
      const ySpin = getY(400);
      energyCtx.strokeStyle = 'rgba(250, 204, 21, 0.25)';
      energyCtx.lineWidth = 1 * dpr;
      energyCtx.setLineDash([3 * dpr, 3 * dpr]);
      energyCtx.beginPath();
      energyCtx.moveTo(marginLeft, ySpin);
      energyCtx.lineTo(w - marginRight, ySpin);
      energyCtx.stroke();
      energyCtx.setLineDash([]);

      // Fill area under power curve
      const grad = energyCtx.createLinearGradient(0, marginTop, 0, marginTop + plotH);
      grad.addColorStop(0, 'rgba(250, 204, 21, 0.28)');
      grad.addColorStop(0.8, 'rgba(250, 204, 21, 0.05)');
      grad.addColorStop(1, 'rgba(250, 204, 21, 0.0)');

      energyCtx.beginPath();
      energyCtx.moveTo(marginLeft, marginTop + plotH);
      for (let i = 0; i < total; i++) {{
        const x = marginLeft + ((i / (total - 1)) * plotW);
        const y = getY(getPowerAt(i));
        energyCtx.lineTo(x, y);
      }}
      energyCtx.lineTo(w - marginRight, marginTop + plotH);
      energyCtx.closePath();
      energyCtx.fillStyle = grad;
      energyCtx.fill();

      // Top power stroke
      energyCtx.beginPath();
      energyCtx.strokeStyle = '#facc15';
      energyCtx.lineWidth = (total > 500) ? (1.5 * dpr) : (1.8 * dpr);
      for (let i = 0; i < total; i++) {{
        const x = marginLeft + ((i / (total - 1)) * plotW);
        const y = getY(getPowerAt(i));
        if (i === 0) energyCtx.moveTo(x, y); else energyCtx.lineTo(x, y);
      }}
      energyCtx.stroke();

      // Cursor scrubber line & marker
      const getX = (idx) => marginLeft + ((idx / (total - 1)) * plotW);
      const curX = getX(curPointIdx);
      const curPwr = getPowerAt(curPointIdx);
      const curY = getY(curPwr);

      energyCtx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      energyCtx.lineWidth = 1.5 * dpr;
      energyCtx.beginPath();
      energyCtx.moveTo(curX, marginTop);
      energyCtx.lineTo(curX, marginTop + plotH);
      energyCtx.stroke();

      energyCtx.fillStyle = '#facc15';
      energyCtx.beginPath();
      energyCtx.arc(curX, curY, 4 * dpr, 0, Math.PI * 2);
      energyCtx.fill();
      energyCtx.strokeStyle = '#ffffff';
      energyCtx.lineWidth = 1 * dpr;
      energyCtx.stroke();

      // Guideline badge on opposite side
      const isCursorOnLeft = (total > 1) ? ((curPointIdx / (total - 1)) < 0.5) : true;
      const baseAlign = isCursorOnLeft ? 'right' : 'left';
      const baseX = isCursorOnLeft ? (w - marginRight - (6 * dpr)) : (marginLeft + (8 * dpr));
      drawPillBadge(energyCtx, baseX, ySpin - (10 * dpr), isMobile ? 'SPIN THRESHOLD: 400W' : 'CENTRIFUGAL SPIN THRESHOLD: 400W', '#facc15', baseAlign, dpr);

      // Floating cursor pill
      const badgeText = `${{curPwr.toFixed(1)}} Watts (${{Math.round((curPwr / pwrMax) * 100)}}% Load)`;
      energyCtx.font = `700 ${{(isMobile ? 7.5 : 8.5) * dpr}}px 'JetBrains Mono', monospace`;
      const tw = energyCtx.measureText(badgeText).width;
      const bw = tw + (10 * dpr);
      const bh = (isMobile ? 17 : 20) * dpr;

      let bx = curX - (bw / 2);
      if (bx < marginLeft + (4 * dpr)) bx = marginLeft + (4 * dpr);
      if (bx + bw > w - marginRight - (4 * dpr)) bx = w - marginRight - bw - (4 * dpr);

      let by = curY - bh - (6 * dpr);
      if (by < marginTop + (2 * dpr)) by = curY + (10 * dpr);
      if (by + bh > h - marginBottom - (2 * dpr)) by = h - marginBottom - bh - (2 * dpr);

      energyCtx.fillStyle = 'rgba(20, 24, 33, 0.94)';
      energyCtx.beginPath();
      if (energyCtx.roundRect) energyCtx.roundRect(bx, by, bw, bh, 4 * dpr);
      else energyCtx.rect(bx, by, bw, bh);
      energyCtx.fill();

      energyCtx.strokeStyle = '#facc15';
      energyCtx.lineWidth = 1.2 * dpr;
      energyCtx.stroke();

      energyCtx.fillStyle = '#facc15';
      energyCtx.textAlign = 'center';
      energyCtx.fillText(badgeText, bx + (bw / 2), by + ((isMobile ? 11.5 : 13.5) * dpr));
      energyCtx.textAlign = 'left';

      // Update stat cards
      const durHours = (total > 1) ? ((dataSeries[total - 1][0] - dataSeries[0][0]) / 3600000.0) : 0.05;
      const cycleKwh = (avgPwr * durHours) / 1000.0;
      const cycleCost = cycleKwh * 0.28;

      const elWatts = document.getElementById('energy-head-watts');
      if (elWatts) elWatts.innerText = curPwr.toFixed(1);
      const elKwh = document.getElementById('energy-head-kwh');
      if (elKwh) elKwh.innerText = cycleKwh.toFixed(2);

      const elLoad = document.getElementById('energy-head-load');
      const elClass = document.getElementById('energy-head-class');
      let estKg = 5.2;
      let lClass = 'MEDIUM';
      if (maxPwrObserved > 550) {{ estKg = 7.8; lClass = 'HEAVY'; }}
      else if (maxPwrObserved < 420) {{ estKg = 2.8; lClass = 'LIGHT'; }}
      if (elLoad) elLoad.innerText = `${{estKg.toFixed(1)}} kg`;
      if (elClass) elClass.innerText = lClass;

      const elDrag = document.getElementById('energy-head-drag');
      if (elDrag) {{
        if (curPwr > 580 && Math.sqrt(dataSeries[curPointIdx][1]**2 + dataSeries[curPointIdx][2]**2 + dataSeries[curPointIdx][3]**2) < 10.0) {{
          elDrag.innerText = '+18% (Bearing Drag)';
          elDrag.style.color = '#fb923c';
        }} else {{
          elDrag.innerText = '0% (Normal)';
          elDrag.style.color = '#4ade80';
        }}
      }}

      const elPeak = document.getElementById('energy-stat-peak');
      if (elPeak) elPeak.innerText = `${{maxPwrObserved.toFixed(0)}} W`;
      const elAvg = document.getElementById('energy-stat-avg');
      if (elAvg) elAvg.innerText = `${{avgPwr.toFixed(0)}} W`;
      const elCost = document.getElementById('energy-stat-cost');
      if (elCost) elCost.innerText = `RM ${{cycleCost.toFixed(2)}}`;
    }}

    function onScrub(val) {{
      currentIndex = parseInt(val, 10);
      if (!ACTIVE_DATA || !ACTIVE_DATA[currentIndex]) return;
      const curRec = ACTIVE_DATA[currentIndex];
      const minutes = (((curRec[0] - ACTIVE_DATA[0][0]) / 60000)).toFixed(1);
      if (scrubLabel) scrubLabel.innerText = `${{minutes}}m`;
      applyRecord(curRec, false);
      drawSpline();
      drawXyz();
      drawArea();
      drawEnergy();
    }}

    function togglePlayPause() {{
      isPlaying = !isPlaying;
      btnPrimaryAction.innerText = isPlaying ? `Pause (${{activeSessionName}})` : `Replay Run (${{activeSessionName}})`;
      if (isPlaying) {{
        playInterval = setInterval(() => {{
          currentIndex++;
          if (currentIndex >= ACTIVE_DATA.length) {{
            currentIndex = 0;
            togglePlayPause();
            return;
          }}
          if (timeSlider) timeSlider.value = currentIndex;
          const curRec = ACTIVE_DATA[currentIndex];
          const minutes = (((curRec[0] - ACTIVE_DATA[0][0]) / 60000)).toFixed(1);
          if (scrubLabel) scrubLabel.innerText = `${{minutes}}m`;
          applyRecord(curRec, false);
          drawSpline();
          drawXyz();
          drawArea();
        }}, 80);
      }} else {{
        clearInterval(playInterval);
      }}
    }}

    // Robust CSV parser
    function parseCsvData(text) {{
      const lines = text.trim().split(/\\r?\\n/);
      const records = [];
      for (let i = 0; i < lines.length; i++) {{
        const line = lines[i].trim();
        if (!line) continue;
        const parts = line.split(',').map(s => s.trim());
        if (parts.length >= 5) {{
          const t = parseFloat(parts[0]);
          const ax = parseFloat(parts[1]);
          const ay = parseFloat(parts[2]);
          const az = parseFloat(parts[3]);
          const rms = parseFloat(parts[4]);
          if (!isNaN(t) && !isNaN(ax) && !isNaN(ay) && !isNaN(az) && !isNaN(rms)) {{
            records.push([Math.round(t), ax, ay, az, rms]);
          }}
        }}
      }}
      records.sort((a, b) => a[0] - b[0]);
      return records;
    }}

    function handleCsvFileSelected(e) {{
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      loadCsvFileObject(file);
      e.target.value = '';
    }}

    function loadCsvFileObject(file) {{
      const reader = new FileReader();
      reader.onload = function(evt) {{
        const text = evt.target.result;
        const records = parseCsvData(text);
        if (records.length < 2) {{
          alert(`Could not parse valid records from "${{file.name}}". Ensure CSV has timestamp, ax, ay, az, rms columns.`);
          return;
        }}

        const sessionKey = 'custom_' + Date.now();
        const durationMin = ((records[records.length - 1][0] - records[0][0]) / 60000).toFixed(1);
        const cleanName = file.name.replace(/\\.[^/.]+$/, '');
        const displayName = `📁 ${{file.name}} (${{records.length}} pts, ${{durationMin}}m)`;

        LOADED_SESSIONS[sessionKey] = {{
          name: cleanName,
          displayName: displayName,
          data: records
        }};

        const groupCustom = document.getElementById('group-custom-sessions');
        if (groupCustom) {{
          groupCustom.style.display = '';
          const opt = document.createElement('option');
          opt.value = sessionKey;
          opt.innerText = displayName;
          groupCustom.appendChild(opt);
        }}

        const sel = document.getElementById('sel-session');
        if (sel) sel.value = sessionKey;

        switchToSession(sessionKey);
        showToast(`Loaded ${{file.name}} (${{records.length}} frames, ${{durationMin}}m)`);
      }};
      reader.readAsText(file);
    }}

    // Auto-discover recorded sessions from Firebase
    async function discoverFirebaseSessions() {{
      try {{
        const res = await fetch('https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app/sessions.json?shallow=true');
        const list = await res.json();
        if (list && typeof list === 'object') {{
          const groupCloud = document.getElementById('group-cloud-sessions');
          if (!groupCloud) return;
          const sessionIds = Object.keys(list);
          if (sessionIds.length > 0) {{
            groupCloud.innerHTML = '';
            groupCloud.style.display = '';
            sessionIds.forEach(sid => {{
              let label = `☁️ ${{sid}}`;
              if (sid.startsWith('wash_')) {{
                label = `☁️ Wash Session ${{sid.replace('wash_', '')}}`;
              }}
              const opt = document.createElement('option');
              opt.value = 'cloud_' + sid;
              opt.innerText = label;
              groupCloud.appendChild(opt);
            }});
          }}
        }}
      }} catch (err) {{
        // Network offline, keep quiet
      }}
    }}

    async function loadCloudSession(sid) {{
      showToast(`Fetching cloud session ${{sid}}...`);
      try {{
        const res = await fetch(`https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app/sessions/${{sid}}.json`);
        const batches = await res.json();
        if (!batches) throw new Error('Empty session data in cloud');

        const rows = [];
        const items = Array.isArray(batches) ? batches : Object.values(batches);
        items.forEach(b => {{
          if (b && typeof b === 'object' && b.t !== undefined) {{
            rows.push([b.t, b.ax || 0, b.ay || 0, b.az || -9.8, b.rms || 0]);
          }}
        }});
        rows.sort((a, b) => a[0] - b[0]);
        if (rows.length < 2) throw new Error('Insufficient records');

        const sessionKey = 'cloud_' + sid;
        const durMin = ((rows[rows.length - 1][0] - rows[0][0]) / 60000).toFixed(1);
        LOADED_SESSIONS[sessionKey] = {{
          name: sid,
          displayName: `☁️ ${{sid}} (${{rows.length}} pts, ${{durMin}}m)`,
          data: rows
        }};

        switchToSession(sessionKey);
        showToast(`Loaded cloud session ${{sid}}!`);
      }} catch (e) {{
        alert(`Failed to load cloud session: ${{e.message}}`);
      }}
    }}

    // Export Active CSV
    function exportActiveCsv() {{
      let csv = 'timestamp_ms,accel_x,accel_y,accel_z,audio_rms\\n';
      let exportName = 'telemetry.csv';
      if (currentMode === 'live') {{
        const src = LIVE_BUFFER.length > 0 ? LIVE_BUFFER : [[Date.now(), -0.74, 1.40, -9.40, 105.6]];
        src.forEach(r => {{
          csv += `${{r[0]}},${{r[1]}},${{r[2]}},${{r[3]}},${{r[4]}}\\n`;
        }});
        exportName = `live_stream_${{Date.now()}}.csv`;
      }} else {{
        ACTIVE_DATA.forEach(r => {{
          csv += `${{r[0]}},${{r[1]}},${{r[2]}},${{r[3]}},${{r[4]}}\\n`;
        }});
        exportName = `${{activeSessionName.replace(/[^a-zA-Z0-9_-]/g, '_')}}.csv`;
      }}
      const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = exportName;
      a.click();
    }}

    // Drag and drop CSV files directly into the window
    window.addEventListener('dragover', (e) => {{
      e.preventDefault();
      e.stopPropagation();
    }});
    window.addEventListener('drop', (e) => {{
      e.preventDefault();
      e.stopPropagation();
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {{
        const file = e.dataTransfer.files[0];
        if (file.name.toLowerCase().endsWith('.csv')) {{
          loadCsvFileObject(file);
        }}
      }}
    }});

    // Initial boot setup
    setViewMode('{default_view}');
    window.addEventListener('load', () => {{
      resizeCanvases();
      setInterval(checkRigHeartbeat, 1000);
      checkRigHeartbeat();
      discoverFirebaseSessions();
      setupCanvasScrubbing(splineCvs);
      setupCanvasScrubbing(xyzCvs);
      setupCanvasScrubbing(areaCvs);
      if (energyCvs) setupCanvasScrubbing(energyCvs);
    }});
  </script>
</body>
</html>'''

if __name__ == '__main__':
    # 1. index.html defaults to Live Rig View
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(generate_html(default_view='live'))

    # 2. historical.html defaults to Historical Data View
    with open('historical.html', 'w', encoding='utf-8') as f:
        f.write(generate_html(default_view='historic'))

    # Also sync dashboard.html and cloud_dashboard.html
    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(generate_html(default_view='live'))

    with open('cloud_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(generate_html(default_view='live'))

    print("Successfully built clean responsive mobile-optimized dashboards with dynamic session selector!")