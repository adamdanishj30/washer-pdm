import hashlib
import json
import os
import sys
import numpy as np

# Import shared physics-based cycle signature thresholds and classification rules
# (Ensures zero threshold duplication between ML reporting and dashboard display)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ml.cycle_signature_report import (
    HEATER_W,
    SPIN_MIN_W,
    MAX_POWER_NO_DATA_W,
    classify_signature,
    count_spin_blocks,
    find_signature_blocks,
    load_session_context_map,
)

# =============================================================================
# CSV Ingestion & Pre-computed Session Discovery
# =============================================================================
# Column meanings in Firmware 07 (V3 schema):
# - accel_x, accel_y, accel_z (ax, ay, az): window MEANS (~ -0.66, +2.88, -9.00 m/s^2).
#   These represent gravity tilt orientation, NOT dynamic vibration.
# - vib_mag_std (sm): standard deviation of vector magnitude sqrt(x^2+y^2+z^2) (dynamic vibration).
# - vib_std_x, vib_std_y, vib_std_z (sx, sy, sz): per-axis standard deviations.
# - vib_dom_hz (vdf): dominant vibration frequency in 0.5-45 Hz (tracks drum speed during spin).
# Legacy files (firmware 05/06) lack vib_mag_std; they provide 5s snapshot means and magnitude.
# Output record layout for firmware 07: [t, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf]
# (Note: client-side JavaScript parseCsvData() in the dashboard must match this exact 12-element record layout)
# Output record layout for legacy: [t, ax, ay, az, rms] or [t, ax, ay, az, rms, pwr]
def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if not lines:
        return []

    header_line = lines[0].strip()
    headers = [h.strip() for h in header_line.split(',')]

    # Check if firmware 07 (V3 schema) with dynamic vibration features
    if 'vib_mag_std' in headers:
        col_map = {col: idx for idx, col in enumerate(headers)}
        idx_t = col_map.get('timestamp_ms', 0)
        idx_ax = col_map.get('accel_x', 1)
        idx_ay = col_map.get('accel_y', 2)
        idx_az = col_map.get('accel_z', 3)
        idx_rms = col_map.get('audio_rms', 4)
        idx_pwr = col_map.get('power_w')
        idx_sm = col_map.get('vib_mag_std')
        idx_sx = col_map.get('vib_std_x')
        idx_sy = col_map.get('vib_std_y')
        idx_sz = col_map.get('vib_std_z')
        idx_vdf = col_map.get('vib_dom_hz')

        def parse_float(val):
            if val is None or val == '':
                return None
            try:
                return round(float(val), 4)
            except (ValueError, TypeError):
                return None

        rows = []
        for l in lines[1:]:
            parts = l.strip().split(',')
            if len(parts) <= max(idx_t, idx_ax, idx_ay, idx_az, idx_rms):
                continue
            try:
                t = int(float(parts[idx_t]))
                ax = round(float(parts[idx_ax]), 4)
                ay = round(float(parts[idx_ay]), 4)
                az = round(float(parts[idx_az]), 4)
                rms = round(float(parts[idx_rms]), 4)
                pwr = parse_float(parts[idx_pwr]) if idx_pwr is not None and idx_pwr < len(parts) else None
                sm = parse_float(parts[idx_sm]) if idx_sm is not None and idx_sm < len(parts) else None
                sx = parse_float(parts[idx_sx]) if idx_sx is not None and idx_sx < len(parts) else None
                sy = parse_float(parts[idx_sy]) if idx_sy is not None and idx_sy < len(parts) else None
                sz = parse_float(parts[idx_sz]) if idx_sz is not None and idx_sz < len(parts) else None
                vdf = parse_float(parts[idx_vdf]) if idx_vdf is not None and idx_vdf < len(parts) else None
                rows.append([t, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf])
            except (ValueError, IndexError):
                pass
        return rows

    # Legacy firmware 05/06 parser (kept strictly unchanged for byte-identical output)
    rows = []
    for l in lines[1:]:
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
    context_map = load_session_context_map()
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

                # Compute physical summary dict for wash-type badge, summary line, and block shading
                powers = [r[5] if (len(r) > 5 and r[5] is not None) else 0.0 for r in rows]
                timestamps_ms = [r[0] for r in rows]
                is_fw07 = len(rows[0]) >= 12
                dt_seconds = 5.024 if is_fw07 else 5.0
                max_power = max(powers) if powers else 0.0
                has_valid_power = max_power >= MAX_POWER_NO_DATA_W

                if not has_valid_power:
                    active_min = 0
                    heater_min = 0.0
                    spin_blocks = 0
                    blocks = []
                else:
                    active_indices = [i for i, p in enumerate(powers) if p >= 8.0]
                    if active_indices:
                        t_start = timestamps_ms[active_indices[0]]
                        t_end = timestamps_ms[active_indices[-1]]
                        dt_ms = dt_seconds * 1000.0
                        span_min = (t_end - t_start + dt_ms) / 60000.0 if t_end >= t_start else (len(active_indices) * dt_seconds / 60.0)
                        active_min = int(round(span_min))
                    else:
                        active_min = 0

                    heater_count = sum(1 for p in powers if p > HEATER_W)
                    heater_min = round((heater_count * dt_seconds) / 60.0, 1)
                    spin_blocks = count_spin_blocks(powers)
                    blocks = find_signature_blocks(powers)

                sig_class = classify_signature(max_power, heater_min, spin_blocks, float(active_min))
                ctx = context_map.get(fname, {})
                ctx_source = ctx.get('context_source', '').strip()
                ctx_prog = ctx.get('programme', '').strip()
                ctx_temp = ctx.get('water_temp', '').strip()

                prog_val = ctx_prog if (ctx_source in ('smartthings_live', 'smartthings_history', 'manual') and ctx_prog and ctx_prog.lower() != 'unknown') else None
                temp_val = ctx_temp if (prog_val and ctx_temp and ctx_temp.lower() != 'unknown') else None

                run_medians = None
                if is_fw07:
                    running = [r for r in rows if r[6] is not None and r[6] > 0.08]
                    if running:
                        run_medians = {
                            'vib_dom_hz': round(float(np.median([r[11] for r in running if r[11] is not None])), 1),
                            'vib_std_x': round(float(np.median([r[8] for r in running if r[8] is not None])), 3),
                            'vib_std_y': round(float(np.median([r[9] for r in running if r[9] is not None])), 3),
                            'vib_std_z': round(float(np.median([r[10] for r in running if r[10] is not None])), 3),
                            'vib_mag_std': round(float(np.median([r[6] for r in running if r[6] is not None])), 3),
                        }

                summary = {
                    'signature': sig_class,
                    'programme': prog_val,
                    'water_temp': temp_val,
                    'context_source': ctx_source if prog_val else None,
                    'active_min': active_min,
                    'heater_min': heater_min,
                    'spin_blocks': spin_blocks,
                    'blocks': blocks,
                    'run_medians': run_medians
                }
                
                if '2026-10-17_0835' in fname:
                    disp = f"🧺 17 Oct 2026, 08:35 AM ({duration_m}m Full Wash, {pts_cnt} pts)"
                elif '2026-10-17_0718' in fname:
                    disp = f"🧺 17 Oct 2026, 07:18 AM ({duration_m}m Full Wash, {pts_cnt} pts)"
                elif '2026-10-16_0857' in fname:
                    disp = f"🧺 16 Oct 2026, 08:57 AM ({duration_m}m Multimodal Wash, {pts_cnt} pts)"
                elif 'morning' in fname:
                    disp = f"🧺 15 Oct 2026 Morning Wash ({duration_m}m, {pts_cnt} pts)"
                elif '2026-10-15_1020' in fname:
                    disp = f"🧺 15 Oct 2026, 12:41 AM ({duration_m}m Live Wash, {pts_cnt} pts)"
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
                    'category': 'real',
                    'summary': summary
                }
                real_options.append(f'<option value="{s_key}">{disp}</option>')
                
    if real_options:
        options.append('<optgroup label="🧺 Real Wash Sessions">')
        options.extend(real_options)
        options.append('</optgroup>')

    # 2. Testing & Calibration Data (from data/testing_data)
    test_options = []
    real_filenames = set(os.listdir(real_dir)) if os.path.exists(real_dir) else set()
    if os.path.exists(test_dir):
        for fname in sorted(os.listdir(test_dir), reverse=True):
            if fname.endswith('.csv') and not fname.startswith('.') and fname not in real_filenames:
                fpath = os.path.join(test_dir, fname)
                rows = load_csv(fpath)
                if rows:
                    s_key = 'preset_test_' + fname.replace('.csv', '').replace('-', '_').replace('.', '_')
                    pts_cnt = len(rows)
                    if '2026-10-12_0800' in fname:
                        disp = f"🧪 12 Oct Bench / Idle Run ({pts_cnt} pts)"
                    elif '2026-10-12_1009' in fname:
                        disp = f"🧪 12 Oct Bench Pre-Wash Test ({pts_cnt} pts)"
                    elif '2026-10-12_1020' in fname:
                        disp = f"🧪 12 Oct Bench Spin Test ({pts_cnt} pts)"
                    elif 'wifi_test' in fname:
                        disp = f"🧪 Wi-Fi Telemetry Stream Test ({pts_cnt} pts)"
                    elif '0852' in fname:
                        disp = f"🧪 16 Oct Bench Power Test ({pts_cnt} pts)"
                    elif '0127' in fname:
                        disp = f"🧪 16 Oct Offline Dump Test 2 ({pts_cnt} pts)"
                    elif '0123' in fname:
                        disp = f"🧪 16 Oct Offline Dump Test 1 ({pts_cnt} pts)"
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

# Shared external preset sessions JavaScript file for caching and page budget (< 250 KB)
PRESET_SESSIONS_JS_CONTENT = (
    "// generated by build_clean_dashboard.py, do not edit\n"
    f"const PRESET_SESSIONS = {PRESET_SESSIONS_JSON};\n"
)
PRESET_SESSIONS_HASH = hashlib.sha256(PRESET_SESSIONS_JS_CONTENT.encode("utf-8")).hexdigest()[:10]


def generate_html(default_view='live'):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Apex PdM - Samsung Washer Live Rig &amp; Historical Diagnostics</title>
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
    /* Inactivity Auto-Pause Alert Banner */
    .live-inactivity-banner {{
      background: rgba(251, 146, 60, 0.12);
      border: 1px solid rgba(251, 146, 60, 0.35);
      border-radius: 10px;
      padding: 10px 18px;
      color: #fdba74;
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      animation: fadeIn 0.3s ease;
      margin-bottom: 2px;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(-4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* AFK Freeze Modal Backdrop & Card */
    .afk-modal-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(15, 18, 24, 0.85);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      padding: 20px;
      animation: fadeIn 0.25s ease-out;
    }}
    .afk-modal-card {{
      background: #252934;
      border: 1px solid rgba(0, 240, 210, 0.35);
      box-shadow: 0 20px 48px rgba(0, 0, 0, 0.7), 0 0 28px rgba(0, 240, 210, 0.18);
      border-radius: 16px;
      max-width: 460px;
      width: 100%;
      padding: 28px 24px;
      text-align: center;
      color: #f3f4f6;
    }}
    .afk-modal-icon {{
      font-size: 38px;
      margin-bottom: 12px;
    }}
    .afk-modal-title {{
      font-size: 18px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 8px;
    }}
    .afk-modal-desc {{
      font-size: 13px;
      color: #9ca3af;
      line-height: 1.5;
      margin-bottom: 18px;
    }}
    .afk-modal-meta {{
      background: #1a1d24;
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 12px;
      color: #9ca3af;
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 20px;
      text-align: left;
      font-family: 'JetBrains Mono', monospace;
    }}
    .afk-resume-btn {{
      width: 100%;
      padding: 12px 20px;
      font-size: 13px;
      font-weight: 700;
      border-radius: 8px;
      cursor: pointer;
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
    .span-btn:disabled, .span-btn.disabled {{
      opacity: 0.35;
      cursor: not-allowed;
      pointer-events: auto;
    }}

    /* Wash Type Badge */
    .badge-wash-type {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 9px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.2px;
      cursor: help;
      transition: all 0.2s ease;
      white-space: nowrap;
    }}
    .badge-wash-type.hot {{
      background: rgba(251, 146, 60, 0.14);
      border: 1px solid rgba(251, 146, 60, 0.45);
      color: var(--coral-accent);
    }}
    .badge-wash-type.cold {{
      background: rgba(0, 240, 210, 0.14);
      border: 1px solid rgba(0, 240, 210, 0.45);
      color: var(--teal-accent);
    }}
    .badge-wash-type.quick {{
      background: rgba(96, 165, 250, 0.14);
      border: 1px solid rgba(96, 165, 250, 0.45);
      color: #60a5fa;
    }}
    .badge-wash-type.unmetered {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.18);
      color: var(--text-dim);
    }}
    .badge-wash-type.programme {{
      background: rgba(168, 85, 247, 0.14);
      border: 1px solid rgba(168, 85, 247, 0.45);
      color: #c084fc;
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
      .live-offline-banner,
      .live-inactivity-banner {{
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        padding: 8px 10px;
        font-size: 11px;
      }}
      .live-offline-banner button,
      .live-inactivity-banner button {{
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
        <span class="brand-pill">APEX PDM</span>
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
            <option value="live">📡 Live Rig Telemetry (Adaptive Sync)</option>
          </optgroup>
          {PRESET_OPTIONS_HTML}
          <optgroup label="Custom Loaded Files" id="group-custom-sessions" style="display: none;"></optgroup>
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

    <!-- Inactivity Auto-Pause Alert Banner (shown when tab is idle > 5 mins to protect quota) -->
    <div id="live-inactivity-banner" class="live-inactivity-banner" style="display: none;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 14px;">⏸️</span>
        <span><strong>Live Stream Paused:</strong> Inactive for 5 minutes. Live stream frozen to conserve data quota.</span>
      </div>
      <button class="btn-dark-primary" style="padding: 5px 14px; font-size: 11px; width: auto;" onclick="confirmAndResume()">▶ Resume Live Stream</button>
    </div>

    <!-- AFK Freeze Confirmation Modal (Zero requests while away) -->
    <div id="afk-freeze-modal" class="afk-modal-backdrop" style="display: none;">
      <div class="afk-modal-card">
        <div class="afk-modal-icon">⏸️</div>
        <h3 class="afk-modal-title">Live Monitoring Paused</h3>
        <p class="afk-modal-desc">
          No activity detected for 5 minutes. Real-time Firebase polling has been <strong>completely frozen (0 req/s)</strong> to conserve network quota.
        </p>
        <div class="afk-modal-meta">
          <span>Paused at: <strong id="afk-pause-time" style="color: var(--coral-accent);">--:--:--</strong></span>
          <span>Pending sync: <strong id="afk-pending-status" style="color: var(--teal-accent);">Auto catch-up on confirm</strong></span>
        </div>
        <button id="btn-confirm-resume" class="btn-dark-primary afk-resume-btn" onclick="confirmAndResume()">
          ▶ Confirm &amp; Resume Monitoring
        </button>
      </div>
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
          <span id="legend-spline-blocks" class="legend-item-dot" style="display: none; margin-right: 4px;">
            <span style="display:inline-flex; align-items:center; gap:3px; margin-right:6px;"><span style="width:8px; height:8px; background:rgba(251,146,60,0.45); border:1px solid #fb923c; border-radius:2px;"></span><span style="font-size:10px; color:#fb923c;">Heater</span></span>
            <span style="display:inline-flex; align-items:center; gap:3px;"><span style="width:8px; height:8px; background:rgba(0,240,210,0.35); border:1px solid #00f0d2; border-radius:2px;"></span><span style="font-size:10px; color:#00f0d2;">Spin</span></span>
          </span>
          <span class="legend-item-dot">
            <span class="dot-indicator" style="background: var(--teal-accent);"></span> <span id="lbl-spline-vibe-title">|a|</span>: <strong id="spline-cur-vibe" style="color: var(--teal-accent); font-family: 'JetBrains Mono', monospace;">9.54</strong> m/s&sup2;
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
          <span class="axis-toggle-clean" id="pill-dom-freq" style="color: #60a5fa;" title="Dominant vibration frequency in 0.5–45 Hz. Peak frequency during mechanical spin extraction.">
            <span id="lbl-pill-dom-freq">Dom. freq:</span> <strong id="vib-dom-freq" style="margin-left: 3px;">—</strong>
          </span>
          <span class="axis-toggle-clean" id="pill-tog-x" style="color: var(--teal-accent);" onclick="toggleAxis('x')">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--teal-accent);"></span>
            <span id="lbl-pill-x">Ax:</span> <strong id="vibe-leg-x">-0.74</strong> m/s&sup2;
          </span>
          <span class="axis-toggle-clean" id="pill-tog-y" style="color: var(--coral-accent);" onclick="toggleAxis('y')">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--coral-accent);"></span>
            <span id="lbl-pill-y">Ay:</span> <strong id="vibe-leg-y">+1.40</strong> m/s&sup2;
          </span>
          <span class="axis-toggle-clean" id="pill-tog-z" style="color: var(--purple-accent);" onclick="toggleAxis('z')">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--purple-accent);"></span>
            <span id="lbl-pill-z">Az:</span> <strong id="vibe-leg-z">-9.40</strong> m/s&sup2;
          </span>
          <span class="axis-toggle-clean" id="pill-tog-mag" style="color: #fff;">
            <span id="lbl-pill-mag">|a|:</span> <strong id="head-vibe-mag">9.53</strong> m/s&sup2;
          </span>
        </div>
      </div>
      <!-- Run medians row for historic sessions -->
      <div id="card2-run-medians" style="display: none; padding: 4px 10px; margin-bottom: 8px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; font-size: 11px; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; flex-wrap: wrap; gap: 8px; align-items: center;">
        <span style="color: var(--text-muted); font-weight: 600;">Run median (active):</span>
        <span>Dom. freq <strong id="run-med-dom" style="color: #60a5fa;">—</strong></span>
        <span>&bull;</span>
        <span>&sigma;x/&sigma;y/&sigma;z <strong id="run-med-sigma" style="color: var(--teal-accent);">—</strong></span>
        <span>&bull;</span>
        <span>&sigma;|a| <strong id="run-med-mag" style="color: #fff;">—</strong></span>
      </div>
      <div class="canvas-container-box box-xyz">
        <canvas id="xyz-canvas"></canvas>
      </div>
    </div>

    <!-- Card 3: Timeline & Controls -->
    <div class="card">
      <div class="card-header-row">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span class="card-title-text" id="title-timeline">Live Rig Telemetry Stream</span>
            <span id="badge-wash-type" class="badge-wash-type" style="display: none;"></span>
          </div>
          <span class="card-sub-txt" id="sub-timeline">Real-time incoming telemetry stream from ESP32</span>
        </div>
        <div class="timeline-stats-container">
          <!-- Adaptive Sync Indicator -->
          <div class="view-toggle-pill" id="tog-live-rate" style="display: none;">
            <span class="span-btn active" id="lbl-sync-mode" onclick="showToast('ℹ️ Adaptive sync: 10s during wash cycles, 60s idle heartbeat to conserve Firebase quota.')" style="cursor: pointer; padding: 3px 10px; font-size: 11px;">📡 60s Idle Heartbeat</span>
          </div>
          <span class="axis-toggle-clean" style="color: var(--teal-accent);">
            Current: <strong id="timeline-head-rms">105.6</strong> RMS
          </span>
          <span class="axis-toggle-clean" style="color: var(--coral-accent);">
            State: <strong id="timeline-head-spike" title="Provisional: vibration std > 0.08 m/s² (same as firmware fallback); retune after first firmware-07 wash">—</strong>
          </span>
          <span class="time-readout-pill" id="lbl-curr-time">
            LIVE (Adaptive)
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
          <span class="card-sub-txt" id="sub-energy">TP-Link Tapo P110 (1 Hz) &bull; Active power and energy over the shown span</span>
        </div>
        <div class="vibe-badges-container">
          <span id="legend-energy-blocks" class="axis-toggle-clean" style="display: none;">
            <span style="display:inline-flex; align-items:center; gap:3px; margin-right:6px;"><span style="width:8px; height:8px; background:rgba(251,146,60,0.45); border:1px solid #fb923c; border-radius:2px;"></span><span style="font-size:10px; color:#fb923c;">Heater</span></span>
            <span style="display:inline-flex; align-items:center; gap:3px;"><span style="width:8px; height:8px; background:rgba(0,240,210,0.35); border:1px solid #00f0d2; border-radius:2px;"></span><span style="font-size:10px; color:#00f0d2;">Spin</span></span>
          </span>
          <span class="axis-toggle-clean" style="color: #facc15;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: #facc15;"></span>
            Active: <strong id="energy-head-watts">0.0</strong> W
          </span>
          <span class="axis-toggle-clean" style="color: var(--teal-accent);">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--teal-accent);"></span>
            Energy (shown span): <strong id="energy-head-kwh">0.00</strong> kWh
          </span>
        </div>
      </div>
      <div class="canvas-container-box box-energy">
        <canvas id="energy-canvas"></canvas>
      </div>
      <div class="energy-metrics-bar" style="display: flex; gap: 16px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-sub); font-size: 11px; color: var(--text-dim); flex-wrap: wrap;">
        <span>Peak Power: <strong id="energy-stat-peak" style="color: var(--text-main); font-family: 'JetBrains Mono', monospace;">0 W</strong></span>
        <span>Avg Active: <strong id="energy-stat-avg" style="color: var(--text-main); font-family: 'JetBrains Mono', monospace;">0 W</strong></span>
      </div>
    </div>

  </main>

  <div id="toast" class="toast-notification">Notification</div>

  <script src="preset_sessions.js?v={PRESET_SESSIONS_HASH}"></script>
  <script>
    let LOADED_SESSIONS = Object.assign({{}}, PRESET_SESSIONS);
    let activeSessionKey = '{FIRST_SESSION_KEY}';
    if (!LOADED_SESSIONS[activeSessionKey]) {{
      const _sessionKeys = Object.keys(LOADED_SESSIONS);
      activeSessionKey = _sessionKeys.length > 0 ? _sessionKeys[0] : '';
    }}
    let activeSessionName = LOADED_SESSIONS[activeSessionKey] ? (LOADED_SESSIONS[activeSessionKey].name || '{FIRST_SESSION_NAME}') : '{FIRST_SESSION_NAME}';
    let ACTIVE_DATA = (LOADED_SESSIONS[activeSessionKey] && LOADED_SESSIONS[activeSessionKey].data) ? LOADED_SESSIONS[activeSessionKey].data : [];

    let currentMode = (activeSessionKey === '' && '{default_view}' === 'historic') ? 'live' : '{default_view}'; // 'live' or 'historic'
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

    // =========================================================================
    // Vibration Display Helpers
    // Firmware 07 records provide per-window dynamic vibration standard deviations
    // (vib_mag_std = p[6], vib_std_x = p[8], vib_std_y = p[9], vib_std_z = p[10],
    // vib_dom_hz = p[11]). Window means (ax, ay, az = p[1..3]) are tilt/gravity.
    // =========================================================================
    function getVibStd(p) {{
      return (p && p.length >= 7 && typeof p[6] === 'number' && Number.isFinite(p[6])) ? p[6] : null;
    }}

    function getAxisStd(p, axis) {{
      if (!p || p.length < 9) return null;
      const idx = (axis === 0 || axis === 'x') ? 8 : ((axis === 1 || axis === 'y') ? 9 : ((axis === 2 || axis === 'z') ? 10 : -1));
      if (idx === -1 || p.length <= idx) return null;
      const v = p[idx];
      return (typeof v === 'number' && Number.isFinite(v)) ? v : null;
    }}

    function seriesHasVibStd(points) {{
      if (!points || !points.length) return false;
      return points.some(p => getVibStd(p) !== null);
    }}

    function seriesHasAxisStd(points) {{
      if (!points || !points.length) return false;
      return points.some(p => getAxisStd(p, 0) !== null);
    }}

    function getNiceVibScale(maxVal) {{
      let top = Math.max(0.5, maxVal || 0.5);
      let step = 0.25;
      if (top <= 0.5) {{
        top = 0.5;
        step = 0.25;
      }} else if (top <= 1.0) {{
        top = 1.0;
        step = 0.5;
      }} else if (top <= 2.0) {{
        top = Math.ceil(top * 2) / 2;
        step = 0.5;
      }} else {{
        top = Math.ceil(top);
        step = top <= 5 ? 1.0 : (top <= 10 ? 2.5 : Math.ceil(top / 4));
      }}
      const ticks = [];
      for (let v = top; v >= -1e-6; v -= step) {{
        ticks.push(Number(v.toFixed(2)));
      }}
      return {{ max: top, ticks: ticks }};
    }}

    function updateCard2Labels(isAxisSigma) {{
      const titleXyz = document.getElementById('title-xyz');
      const lblPillDom = document.getElementById('lbl-pill-dom-freq');
      const lblPillX = document.getElementById('lbl-pill-x');
      const lblPillY = document.getElementById('lbl-pill-y');
      const lblPillZ = document.getElementById('lbl-pill-z');
      const lblPillMag = document.getElementById('lbl-pill-mag');

      const isHistoric = (currentMode === 'historic');

      if (lblPillDom) {{
        lblPillDom.innerText = isHistoric ? 'Dom. freq (at cursor):' : 'Dom. freq:';
      }}

      if (isAxisSigma) {{
        if (titleXyz) titleXyz.innerText = 'Per-Axis Vibration (std per 5 s window)';
        if (lblPillX) lblPillX.innerText = isHistoric ? '\u03c3x (at cursor):' : '\u03c3x:';
        if (lblPillY) lblPillY.innerText = isHistoric ? '\u03c3y (at cursor):' : '\u03c3y:';
        if (lblPillZ) lblPillZ.innerText = isHistoric ? '\u03c3z (at cursor):' : '\u03c3z:';
        if (lblPillMag) lblPillMag.innerText = isHistoric ? '\u03c3|a| (at cursor):' : '\u03c3|a|:';
      }} else {{
        if (titleXyz) titleXyz.innerText = 'Tri-Axial Vibration (Ax, Ay, Az)';
        if (lblPillX) lblPillX.innerText = isHistoric ? 'Ax (at cursor):' : 'Ax:';
        if (lblPillY) lblPillY.innerText = isHistoric ? 'Ay (at cursor):' : 'Ay:';
        if (lblPillZ) lblPillZ.innerText = isHistoric ? 'Az (at cursor):' : 'Az:';
        if (lblPillMag) lblPillMag.innerText = isHistoric ? '|a| (at cursor):' : '|a|:';
      }}
    }}

    function updateWashTypeBadgeAndSummary(session) {{
      const badgeEl = document.getElementById('badge-wash-type');
      const legSpline = document.getElementById('legend-spline-blocks');
      const legEnergy = document.getElementById('legend-energy-blocks');
      const card2Medians = document.getElementById('card2-run-medians');

      if (currentMode === 'live' || !session || session.category === 'test') {{
        if (badgeEl) badgeEl.style.display = 'none';
        if (legSpline) legSpline.style.display = 'none';
        if (legEnergy) legEnergy.style.display = 'none';
        if (card2Medians) card2Medians.style.display = 'none';
        return;
      }}

      const sum = session.summary;
      if (!sum) {{
        if (badgeEl) {{
          badgeEl.style.display = 'inline-flex';
          badgeEl.className = 'badge-wash-type unmetered';
          badgeEl.innerText = (session.category === 'custom') ? 'not classified' : 'Unclassified';
          badgeEl.title = (session.category === 'custom') ? 'Custom uploaded CSV file (not classified).' : 'Built-in wash without physical summary.';
        }}
        if (legSpline) legSpline.style.display = 'none';
        if (legEnergy) legEnergy.style.display = 'none';
        if (card2Medians) card2Medians.style.display = 'none';
        return;
      }}

      // 1. Wash-type badge pill
      if (badgeEl) {{
        badgeEl.style.display = 'inline-flex';
        badgeEl.title = 'Classification rule: Heater > 1 kW for > 2 min and \u2265 2 spin blocks \u2192 Long hot; no heater and \u2265 3 spin blocks \u2192 Long cold; no heater, 1 spin block, < 35 min active \u2192 Quick; max power < 50 W \u2192 No power data. Spin block = \u2265 20 consecutive windows (100 s) at 200\u20131,000 W.';
        if (sum.programme) {{
          badgeEl.className = 'badge-wash-type programme';
          const tempPart = sum.water_temp ? ` \u00b7 ${{sum.water_temp}}` : '';
          const srcPart = sum.context_source === 'manual' ? 'manual' : 'SmartThings';
          badgeEl.innerText = `${{sum.programme}}${{tempPart}} (${{srcPart}})`;
        }} else {{
          const sig = sum.signature || 'Unclassified';
          if (sig.includes('Long hot')) {{
            badgeEl.className = 'badge-wash-type hot';
            badgeEl.innerText = 'Long hot (inferred from power)';
          }} else if (sig.includes('Long cold')) {{
            badgeEl.className = 'badge-wash-type cold';
            badgeEl.innerText = 'Long cold (inferred from power)';
          }} else if (sig.includes('Quick')) {{
            badgeEl.className = 'badge-wash-type quick';
            badgeEl.innerText = 'Quick (inferred from power)';
          }} else if (sig === 'No power data') {{
            badgeEl.className = 'badge-wash-type unmetered';
            badgeEl.innerText = 'No power data';
          }} else {{
            badgeEl.className = 'badge-wash-type unmetered';
            badgeEl.innerText = `${{sig}} (inferred from power)`;
          }}
        }}
      }}

      // 2. Timeline subtitle summary line
      if (subTimeline && ACTIVE_DATA && ACTIVE_DATA.length > 0) {{
        const durMin = ((ACTIVE_DATA[ACTIVE_DATA.length - 1][0] - ACTIVE_DATA[0][0]) / 60000).toFixed(1);
        if (sum.signature === 'No power data') {{
          subTimeline.innerText = `${{durMin}}-min run • No electrical power data tracked for this cycle • ${{activeSessionName}}`;
        }} else {{
          const act = sum.active_min;
          const heat = sum.heater_min;
          const heatStr = heat > 0 ? ((heat % 1 === 0 ? heat.toFixed(0) : heat.toFixed(1)) + ' min heater') : 'no heater';
          const spins = sum.spin_blocks;
          const spinStr = `${{spins}} spin block${{spins === 1 ? '' : 's'}}`;
          const tailNote = (durMin - act >= 8) ? ' (~10 min idle tail)' : '';
          subTimeline.innerText = `${{act}} min active \u00b7 ${{heatStr}} \u00b7 ${{spinStr}} • ${{durMin}} min recorded${{tailNote}} • ${{activeSessionName}}`;
        }}
      }}

      // 3. Block shading chart legends
      const hasBlocks = (sum.blocks && sum.blocks.length > 0);
      if (legSpline) legSpline.style.display = hasBlocks ? 'inline-flex' : 'none';
      if (legEnergy) legEnergy.style.display = hasBlocks ? 'inline-flex' : 'none';

      // 4. Run medians in Card 2
      if (card2Medians) {{
        if (sum.run_medians) {{
          const rm = sum.run_medians;
          card2Medians.style.display = 'flex';
          const domEl = document.getElementById('run-med-dom');
          const sigEl = document.getElementById('run-med-sigma');
          const magEl = document.getElementById('run-med-mag');
          if (domEl) domEl.innerText = rm.vib_dom_hz !== null ? `${{rm.vib_dom_hz.toFixed(1)}} Hz` : '\u2014';
          if (sigEl) sigEl.innerText = `${{rm.vib_std_x.toFixed(3)}} / ${{rm.vib_std_y.toFixed(3)}} / ${{rm.vib_std_z.toFixed(3)}} m/s\u00b2`;
          if (magEl) magEl.innerText = `${{rm.vib_mag_std.toFixed(3)}} m/s\u00b2`;
        }} else {{
          card2Medians.style.display = 'none';
        }}
      }}
    }}

    function updateChartSubtitles() {{
      const subSpline = document.getElementById('sub-spline');
      const subXyz = document.getElementById('sub-xyz');
      const togSpline = document.getElementById('tog-spline-mode');
      const togXyz = document.getElementById('tog-xyz-mode');
      const isHistoric = (currentMode === 'historic' && ACTIVE_DATA && ACTIVE_DATA.length > 1);
      const isSigma = isHistoric ? seriesHasVibStd(ACTIVE_DATA) : seriesHasVibStd(LIVE_BUFFER);
      const isAxisSigma = isHistoric ? seriesHasAxisStd(ACTIVE_DATA) : seriesHasAxisStd(LIVE_BUFFER);

      updateCard2Labels(isAxisSigma);
      const activeSession = LOADED_SESSIONS[activeSessionKey] || (Object.keys(LOADED_SESSIONS).length > 0 ? LOADED_SESSIONS[Object.keys(LOADED_SESSIONS)[0]] : null);
      updateWashTypeBadgeAndSummary(isHistoric ? activeSession : null);

      if (isHistoric) {{
        const durMin = ((ACTIVE_DATA[ACTIVE_DATA.length - 1][0] - ACTIVE_DATA[0][0]) / 60000).toFixed(1);
        if (subSpline) {{
          if (isSigma) {{
            subSpline.innerText = `${{durMin}}-min run • Vibration \u03c3 (window std) & sound RMS`;
          }} else {{
            subSpline.innerText = `${{durMin}}-min run • Legacy 5 s snapshots: |a| magnitude (not vibration std) & sound`;
          }}
        }}
        if (subXyz) {{
          if (isAxisSigma) {{
            subXyz.innerText = (chartSpanMode.xyz === 'full')
              ? `${{durMin}}-min run • Per-axis vibration std (\u03c3x, \u03c3y, \u03c3z)`
              : `40s window • Per-axis vibration std (\u03c3x, \u03c3y, \u03c3z)`;
          }} else {{
            subXyz.innerText = (chartSpanMode.xyz === 'full')
              ? `${{durMin}}-min complete run • Isolated X/Y & Z oscilloscope lanes`
              : `40s window • Isolated X/Y & Z oscilloscope lanes`;
          }}
        }}
        const btnSplineFull = document.getElementById('btn-spline-full');
        const btnXyzFull = document.getElementById('btn-xyz-full');
        if (btnSplineFull) btnSplineFull.innerText = `Full Run (${{durMin}}m)`;
        if (btnXyzFull) btnXyzFull.innerText = `Full Run (${{durMin}}m)`;

        if (togSpline) togSpline.style.display = 'inline-flex';
        if (togXyz) togXyz.style.display = 'inline-flex';
      }} else {{
        if (subSpline) {{
          subSpline.innerText = isSigma
            ? 'Live vibration \u03c3 (window std) & sound RMS'
            : 'Vibration resultant • Acoustic sound amplitude';
        }}
        if (subXyz) {{
          subXyz.innerText = isAxisSigma
            ? 'MPU-6050 Accelerometer • Per-axis vibration std (\u03c3x, \u03c3y, \u03c3z)'
            : 'MPU-6050 Accelerometer • Isolated X/Y & Z oscilloscope lanes';
        }}
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
    const inactivityBanner = document.getElementById('live-inactivity-banner');
    const FIREBASE_BASE_URL = 'https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app';
    const FIREBASE_FALLBACK_URL = `${{FIREBASE_BASE_URL}}/live.json`;
    const LIVE_ENDPOINT = (window.location.protocol === 'http:' || window.location.protocol === 'https:')
      ? '/api/live'
      : FIREBASE_FALLBACK_URL;

    // Page-Level Isolation Guard (historical.html never runs live controller)
    const PAGE_DEFAULT_VIEW = '{default_view}';

    // Sticky Edge-to-Direct Fallback Tracker (avoids double-fetching on persistent proxy errors)
    let apiLiveFailCount = 0;
    let lastApiLiveFailTime = 0;

    // Opus-Style Generation Polling Controller & AFK Freeze Guard
    let generation = 0;          // Monotonic counter bumped on every freeze/resume; stale callbacks compare against it
    let pollTimer = null;        // Handle for the single scheduled setTimeout (never setInterval)
    let inflight = null;         // AbortController for the request currently on the wire
    let lastSeenT = null;        // Rig-time cursor: newest epoch timestamp (ms) actually received
    let lastWindowKey = null;    // Key cursor for /sessions/<sid> (e.g. "w000482")
    let frozenSessionId = null;  // Session that was live when we froze, for boundary checks on resume
    let isAfkFrozen = false;     // True when AFK modal is active
    let isResuming = false;      // Guards against double-clicking Resume
    let activeLiveSessionId = null;

    // Testing aid: read ?afk_test_ms= from URL (clamped to >= 10000ms), defaulting to 5 mins
    const urlParams = new URLSearchParams(window.location.search);
    const afkTestMsParam = parseInt(urlParams.get('afk_test_ms'), 10);
    const INACTIVITY_TIMEOUT_MS = (!isNaN(afkTestMsParam) && afkTestMsParam >= 10000)
      ? afkTestMsParam
      : (5 * 60 * 1000); // 5 min default idle auto-pause
    let inactivityTimer = null;

    // Cadence constants (Section 3 Invariant: never poll faster than 5s per viewer)
    const POLL_ACTIVE_MS = 10000;   // 10s active sync when rig is washing
    const POLL_IDLE_MS = 25000;     // 25s heartbeat poll when rig is idle
    const POLL_OFFLINE_MS = 30000;  // 30s backoff poll when rig is offline
    const WINDOW_FETCH_MS = 30000;  // 30s window batch fetch during active wash
    // Provisional vibration threshold to discriminate idle from running state.
    // Matches firmware fallback threshold (|a| std > 0.08 m/s²); retune after first firmware-07 wash.
    const VIB_RUNNING_THRESHOLD = 0.08;

    let isRigActive = false;
    let lastBackfillMs = 0;
    const togLiveRate = document.getElementById('tog-live-rate');
    const lblSyncMode = document.getElementById('lbl-sync-mode');

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
        lblCurrTime.innerText = isRigActive ? 'LIVE (10s)' : 'LIVE (Adaptive)';
        if (togLiveRate) togLiveRate.style.display = 'inline-flex';
        updateRigStatusUI(isRigOnline);
        updateChartSubtitles();
        if (inactivityBanner && !isAfkFrozen) inactivityBanner.style.display = 'none';
        recordUserActivity();
        generation++;
        pollOnce(generation);
      }} else {{
        if (togLiveRate) togLiveRate.style.display = 'none';
        stopLivePolling();
        if (inactivityBanner) inactivityBanner.style.display = 'none';
        const modal = document.getElementById('afk-freeze-modal');
        if (modal) modal.style.display = 'none';
        isAfkFrozen = false;
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
        if (isLivePaused) {{
          stopLivePolling();
          showToast('⏸️ Live stream paused (network polling stopped)');
        }} else {{
          recordUserActivity();
          resumeFromTabVisibility();
        }}
      }} else {{
        togglePlayPause();
      }}
    }}

    function updateRigStatusUI(online) {{
      if (currentMode === 'live') {{
        if (online) {{
          if (lblSyncMode) {{
            lblSyncMode.innerHTML = isRigActive ? '⚡ 10s Active Sync' : '💤 60s Idle Heartbeat';
            lblSyncMode.className = 'span-btn active';
            lblSyncMode.style.color = 'var(--teal-accent)';
          }}
          if (statusBadge) statusBadge.className = 'status-badge desktop-status-tag';
          if (statusDot) statusDot.className = 'status-dot';
          if (lblStatusText) lblStatusText.innerText = isRigActive ? 'Live Rig Active (10s Active Sync)' : 'Live Rig Idle (60s Idle Heartbeat)';

          if (statusBadgeMob) statusBadgeMob.className = 'status-badge mobile-status-tag';
          if (statusDotMob) statusDotMob.className = 'status-dot';
          if (lblStatusTextMob) lblStatusTextMob.innerText = isRigActive ? 'Active 10s' : 'Idle 60s';

          if (lblCurrTime) lblCurrTime.innerText = isRigActive ? 'LIVE (10s)' : 'LIVE (Idle)';

          if (offlineBanner) offlineBanner.style.display = 'none';
        }} else {{
          if (lblSyncMode) {{
            lblSyncMode.innerHTML = '⚠️ Offline';
            lblSyncMode.className = 'span-btn disabled';
            lblSyncMode.style.color = '#ef4444';
          }}
          if (statusBadge) statusBadge.className = 'status-badge offline-badge desktop-status-tag';
          if (statusDot) statusDot.className = 'status-dot dot-offline';
          if (lblStatusText) lblStatusText.innerText = 'Live Rig Offline (No Input)';

          if (statusBadgeMob) statusBadgeMob.className = 'status-badge offline-badge mobile-status-tag';
          if (statusDotMob) statusDotMob.className = 'status-dot dot-offline';
          if (lblStatusTextMob) lblStatusTextMob.innerText = 'Offline';

          if (lblCurrTime) lblCurrTime.innerText = 'LIVE (Offline)';

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

    function recordUserActivity() {{
      if (PAGE_DEFAULT_VIEW !== 'live' || currentMode !== 'live' || isAfkFrozen || isLivePaused) return;
      if (inactivityTimer) clearTimeout(inactivityTimer);
      inactivityTimer = setTimeout(() => {{
        if (currentMode === 'live' && PAGE_DEFAULT_VIEW === 'live' && !isLivePaused) {{
          freezeForAfk();
        }}
      }}, INACTIVITY_TIMEOUT_MS);
    }}

    // Helper: Stop all live polling and cancel pending network requests
    function stopLivePolling() {{
      generation++;
      if (pollTimer) {{
        clearTimeout(pollTimer);
        pollTimer = null;
      }}
      if (inflight) {{
        try {{ inflight.abort(); }} catch (_) {{}}
        inflight = null;
      }}
    }}

    function freezeForAfk() {{
      if (isAfkFrozen || PAGE_DEFAULT_VIEW !== 'live') return;
      isAfkFrozen = true;
      stopLivePolling();

      frozenSessionId = activeLiveSessionId || null;
      const pauseTimeStr = new Date().toLocaleTimeString();
      const pauseEl = document.getElementById('afk-pause-time');
      if (pauseEl) pauseEl.innerText = pauseTimeStr;

      const modal = document.getElementById('afk-freeze-modal');
      if (modal) modal.style.display = 'flex';
      if (inactivityBanner) inactivityBanner.style.display = 'flex';
      showToast('⏸️ Live stream frozen due to inactivity');
    }}

    function hideAfkModal() {{
      const modal = document.getElementById('afk-freeze-modal');
      if (modal) modal.style.display = 'none';
      if (inactivityBanner) inactivityBanner.style.display = 'none';
    }}

    // Helper: Epoch ms time base validators (> 1.7e12 corresponds to post-2023 epochs)
    function liveEpochMs(d) {{
      if (!d || typeof d !== 'object') return null;
      const ts = d.ts;
      return (typeof ts === 'number' && isFinite(ts) && ts > 1.7e12) ? ts : null;
    }}

    function windowEpochMs(w) {{
      if (!w || typeof w !== 'object') return null;
      const e = w.e;
      return (typeof e === 'number' && isFinite(e) && e > 1.7e12) ? e : null;
    }}

    // Helper: Shared record converters (Tag 'w' for window, 'h' for heartbeat)
    // No vdf fallback anywhere (w.vdf is frequency in Hz, not vibration amplitude)
    function windowToRecord(w) {{
      const e = windowEpochMs(w);
      if (e === null) return null;
      const ax = (typeof w.ax === 'number' && isFinite(w.ax)) ? w.ax : 0.0;
      const ay = (typeof w.ay === 'number' && isFinite(w.ay)) ? w.ay : 0.0;
      const az = (typeof w.az === 'number' && isFinite(w.az)) ? w.az : -9.81;
      const rms = (typeof w.rms === 'number' && isFinite(w.rms)) ? w.rms : 120.0;
      const pwr = (typeof w.pwr === 'number' && isFinite(w.pwr)) ? w.pwr : 0.0;
      const sm = (typeof w.sm === 'number' && isFinite(w.sm)) ? w.sm : null;
      const sx = (typeof w.sx === 'number' && isFinite(w.sx)) ? w.sx : null;
      const sy = (typeof w.sy === 'number' && isFinite(w.sy)) ? w.sy : null;
      const sz = (typeof w.sz === 'number' && isFinite(w.sz)) ? w.sz : null;
      const vdf = (typeof w.vdf === 'number' && isFinite(w.vdf)) ? w.vdf : null;
      return [e, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf];
    }}

    function liveToRecord(d, pointT) {{
      if (pointT === null) return null;
      const ax = (typeof d.ax === 'number' && isFinite(d.ax)) ? d.ax : 0.0;
      const ay = (typeof d.ay === 'number' && isFinite(d.ay)) ? d.ay : 0.0;
      const az = (typeof d.az === 'number' && isFinite(d.az)) ? d.az : -9.81;
      const rms = (typeof d.rms === 'number' && isFinite(d.rms)) ? d.rms : 120.0;
      const pwr = (d.power !== undefined && d.power !== null) ? d.power : (d.pwr !== undefined ? d.pwr : 0.0);
      const vibStd = (d.vib_std !== undefined && d.vib_std !== null) ? d.vib_std : Math.abs(Math.sqrt(ax*ax + ay*ay + az*az) - 9.81);
      return [pointT, ax, ay, az, rms, pwr, vibStd, 'h'];
    }}

    // Helper: Centralized merge helper
    // Sorts by t, dedupes by t, drops 'h' records whose t >= earliest window t in incoming,
    // trims to newest 120, and updates lastSeenT and lastWindowKey
    function mergeRecords(incoming) {{
      if (!incoming || incoming.length === 0) return;

      const windowRecords = incoming.filter(r => r.length >= 8 && r[7] === 'w');
      if (windowRecords.length > 0) {{
        const minWindowT = Math.min(...windowRecords.map(r => r[0]));
        LIVE_BUFFER = LIVE_BUFFER.filter(r => !(r.length >= 8 && r[7] === 'h' && r[0] >= minWindowT));
      }}

      LIVE_BUFFER = LIVE_BUFFER.concat(incoming);

      // Prioritize 'w' over 'h' if timestamps collide
      LIVE_BUFFER.sort((a, b) => {{
        if (a[0] !== b[0]) return a[0] - b[0];
        if (a[7] === 'w' && b[7] !== 'w') return 1;
        if (b[7] === 'w' && a[7] !== 'w') return -1;
        return 0;
      }});

      const uniqueMap = new Map();
      for (const r of LIVE_BUFFER) {{
        uniqueMap.set(r[0], r);
      }}
      LIVE_BUFFER = Array.from(uniqueMap.values()).sort((a, b) => a[0] - b[0]);

      while (LIVE_BUFFER.length > 120) {{
        LIVE_BUFFER.shift();
      }}

      if (LIVE_BUFFER.length > 0) {{
        lastSeenT = LIVE_BUFFER[LIVE_BUFFER.length - 1][0];
      }}

      for (const r of incoming) {{
        if (r._key) {{
          if (!lastWindowKey || r._key > lastWindowKey) {{
            lastWindowKey = r._key;
          }}
        }}
      }}
    }}

    // Helper: Detect time gaps across unobserved intervals
    // >20s for window ('w') records, >150s for heartbeat ('h') records, or tag transitions
    function isGapBefore(points, i) {{
      if (i <= 0 || !points || i >= points.length) return false;
      const pPrev = points[i - 1];
      const pCurr = points[i];
      if (!pPrev || !pCurr) return false;
      const tagPrev = pPrev.length >= 8 ? pPrev[7] : null;
      const tagCurr = pCurr.length >= 8 ? pCurr[7] : null;
      if (!tagPrev || !tagCurr) return false;
      const dt = pCurr[0] - pPrev[0];
      if (tagCurr === 'w' && dt > 20000) return true;
      if (tagCurr === 'h' && dt > 150000) return true;
      if (tagCurr !== tagPrev && dt > 20000) return true;
      return false;
    }}

    // Sticky Edge-to-Direct Fallback Fetcher:
    // If /api/live fails twice, sticks to direct Firebase for 60s to prevent double-fetching on every tick
    async function fetchLiveResponse(signal) {{
      const now = Date.now();
      const preferDirect = (apiLiveFailCount >= 2 && (now - lastApiLiveFailTime < 60000));
      const primaryUrl = preferDirect ? FIREBASE_FALLBACK_URL : LIVE_ENDPOINT;
      const secondaryUrl = preferDirect ? LIVE_ENDPOINT : FIREBASE_FALLBACK_URL;

      try {{
        const res = await fetch(primaryUrl, {{ signal }});
        if (res.ok) {{
          if (!preferDirect) apiLiveFailCount = 0;
          return res;
        }}
      }} catch (err) {{
        if (err.name === 'AbortError') throw err;
      }}

      if (primaryUrl !== secondaryUrl) {{
        apiLiveFailCount++;
        lastApiLiveFailTime = now;
        return await fetch(secondaryUrl, {{ signal }});
      }}
      throw new Error('All live endpoints failed');
    }}

    // Helper: Key-Cursor Bounded Window Fetch
    // Queries /sessions/<sid>.json?orderBy="%24key"&startAt="<sinceKey>"&limitToLast=<limit>
    async function fetchWindowsSince(sid, sinceKey = null, limit = 120, signal = null) {{
      if (!sid) return [];
      try {{
        let qUrl = `${{FIREBASE_BASE_URL}}/sessions/${{encodeURIComponent(sid)}}.json?orderBy=%22%24key%22`;
        if (sinceKey) {{
          qUrl += `&startAt=%22${{encodeURIComponent(sinceKey)}}%22`;
        }}
        qUrl += `&limitToLast=${{limit}}`;

        const res = await fetch(qUrl, signal ? {{ signal }} : {{}});
        if (!res.ok) return [];
        const winMap = await res.json();
        if (!winMap || typeof winMap !== 'object') return [];

        const sortedEntries = Object.entries(winMap).sort((a, b) => a[0].localeCompare(b[0]));
        const records = [];
        for (const [k, w] of sortedEntries) {{
          if (sinceKey && k === sinceKey) continue; // Drop boundary duplicate
          const rec = windowToRecord(w);
          if (rec) {{
            rec._key = k;
            records.push(rec);
          }}
        }}
        return records;
      }} catch (err) {{
        if (err.name === 'AbortError') throw err;
        console.warn('fetchWindowsSince failed:', err);
        return [];
      }}
    }}

    async function confirmAndResume() {{
      if (isResuming) return;
      isResuming = true;
      const myGen = ++generation; // This resume now owns the loop
      const btn = document.getElementById('btn-confirm-resume');
      if (btn) btn.innerText = 'Catching up data...';

      try {{
        // Network call #1: Fetch current rig status
        let live = null;
        try {{
          const res = await fetchLiveResponse(inflight?.signal);
          if (res && res.ok) live = await res.json();
        }} catch (e) {{
          if (e.name === 'AbortError') return;
          console.warn('Resume initial fetch error:', e);
        }}

        // Generation check after await #1
        if (myGen !== generation) return;

        const currSid = live ? (live.session || live.sessionId || null) : null;

        // Session boundary check
        if (live && currSid && frozenSessionId && currSid === frozenSessionId) {{
          // Network call #2: Bounded backfill using key cursor
          const missed = await fetchWindowsSince(currSid, lastWindowKey, 120, inflight?.signal);

          // Generation check after await #2
          if (myGen !== generation) return;

          if (missed && missed.length > 0) {{
            mergeRecords(missed);
            showToast(`⚡ Caught up ${{missed.length}} missed wash points`);
          }}
        }} else if (currSid && frozenSessionId && currSid !== frozenSessionId) {{
          LIVE_BUFFER = [];
          lastSeenT = null;
          lastWindowKey = null;
          showToast(`🔄 Rig switched session: ${{currSid}}`);
        }}

        isAfkFrozen = false;
        hideAfkModal();
        recordUserActivity();

        if (LIVE_BUFFER.length > 0) {{
          applyRecord(LIVE_BUFFER[LIVE_BUFFER.length - 1], true);
          drawSpline();
          drawXyz();
          drawArea();
          drawEnergy();
        }}

        pollOnce(myGen);
      }} catch (err) {{
        console.warn('Resume failed, starting cold:', err);
        if (myGen === generation) {{
          isAfkFrozen = false;
          hideAfkModal();
          recordUserActivity();
          pollOnce(myGen);
        }}
      }} finally {{
        isResuming = false;
        if (btn) btn.innerText = '▶ Confirm & Resume Monitoring';
      }}
    }}

    // Catch-up on tab visibility return (when not AFK frozen or paused)
    async function resumeFromTabVisibility() {{
      if (PAGE_DEFAULT_VIEW !== 'live' || currentMode !== 'live' || isLivePaused || document.hidden || isAfkFrozen) return;
      const myGen = ++generation;
      try {{
        const res = await fetchLiveResponse(inflight?.signal);
        if (myGen !== generation || document.hidden || isAfkFrozen || isLivePaused) return;
        const live = await res.json();
        if (myGen !== generation || document.hidden || isAfkFrozen || isLivePaused) return;

        const currSid = live ? (live.session || live.sessionId || null) : null;
        if (live && currSid && activeLiveSessionId && currSid === activeLiveSessionId) {{
          const missed = await fetchWindowsSince(currSid, lastWindowKey, 120, inflight?.signal);
          if (myGen !== generation || document.hidden || isAfkFrozen || isLivePaused) return;

          if (missed && missed.length > 0) {{
            mergeRecords(missed);
          }}
        }} else if (currSid && activeLiveSessionId && currSid !== activeLiveSessionId) {{
          LIVE_BUFFER = [];
          lastSeenT = null;
          lastWindowKey = null;
        }}

        if (LIVE_BUFFER.length > 0) {{
          applyRecord(LIVE_BUFFER[LIVE_BUFFER.length - 1], true);
          drawSpline();
          drawXyz();
          drawArea();
          drawEnergy();
        }}
        pollOnce(myGen);
      }} catch (e) {{
        if (myGen === generation && !isLivePaused && !document.hidden && !isAfkFrozen) pollOnce(myGen);
      }}
    }}

    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(evt => {{
      window.addEventListener(evt, recordUserActivity, {{ passive: true }});
    }});

    function setLiveSyncRate(rate) {{
      showToast('⚡ Live sync: Adaptive streaming (10s active / 25s idle) with AFK freeze protection.');
    }}

    async function pollOnce(myGen) {{
      // Hard page-level guard against historical mode or inactive states running live controller
      if (PAGE_DEFAULT_VIEW !== 'live' || currentMode !== 'live' || isAfkFrozen || isLivePaused || document.hidden) return;
      if (myGen !== generation) return;

      inflight = new AbortController();
      try {{
        let res;
        try {{
          res = await fetchLiveResponse(inflight.signal);
        }} catch (netErr) {{
          if (netErr.name === 'AbortError') return;
          throw netErr;
        }}

        if (myGen !== generation) return;

        const d = await res.json();
        if (myGen !== generation) return;

        if (d && (d.cnt !== undefined || d.uptime !== undefined || d.ts !== undefined)) {{
          const maxAgeMs = (d.schema >= 3 && d.active === false) ? 75000 : 25000;
          const isFreshByTs = d.ts ? (Date.now() - d.ts < maxAgeMs) : true;
          const pointT = liveEpochMs(d);

          const hasIncremented = (lastLivePacketCnt !== null && d.cnt !== undefined && d.cnt !== lastLivePacketCnt) ||
                                 (lastLivePacketUptime !== null && d.uptime !== undefined && d.uptime !== lastLivePacketUptime) ||
                                 (lastSeenT !== null && pointT !== null && pointT !== lastSeenT);

          if (isFreshByTs) {{
            isRigOnline = true;
          }} else {{
            isRigOnline = false;
          }}

          isRigActive = (d.active === true);
          const currSid = d.session || d.sessionId || null;

          if (currSid && activeLiveSessionId && currSid !== activeLiveSessionId) {{
            LIVE_BUFFER = [];
            lastSeenT = null;
            lastWindowKey = null;
            showToast(`🔄 Rig started a new wash cycle: ${{currSid}}`);
          }}
          activeLiveSessionId = currSid;

          lastLivePacketCnt = d.cnt;
          lastLivePacketUptime = d.uptime;

          // Single source per state discipline:
          // 1. When rig is idle (d.active !== true): trace is fed by /live heartbeat points.
          // 2. When rig is washing (d.active === true): applyRecord() keeps readouts fresh every 10s,
          //    but chart trace is fed strictly by window records (/sessions/<sid>) every 30s.
          if (!isLivePaused && isRigOnline) {{
            const newRec = liveToRecord(d, pointT);
            if (newRec) {{
              applyRecord(newRec, true);

              if (d.active !== true) {{
                if (hasIncremented || LIVE_BUFFER.length === 0 || (pointT !== null && pointT !== lastSeenT)) {{
                  mergeRecords([newRec]);
                  if (currentMode === 'live') {{
                    drawSpline();
                    drawXyz();
                    drawArea();
                    drawEnergy();
                  }}
                }}
              }}
            }}

            // If active wash session, fetch 5s window summaries every ~30s with race guards
            if (d.active && d.session && (Date.now() - lastBackfillMs > WINDOW_FETCH_MS)) {{
              lastBackfillMs = Date.now();
              const fetchSid = d.session;
              fetchWindowsSince(fetchSid, lastWindowKey, 12, inflight.signal).then(missed => {{
                if (myGen !== generation || fetchSid !== activeLiveSessionId || currentMode !== 'live' || isAfkFrozen || isLivePaused || document.hidden) return;
                if (missed && missed.length > 0) {{
                  mergeRecords(missed);
                  if (LIVE_BUFFER.length > 0) {{
                    applyRecord(LIVE_BUFFER[LIVE_BUFFER.length - 1], true);
                    drawSpline();
                    drawXyz();
                    drawArea();
                    drawEnergy();
                  }}
                }}
              }}).catch(err => {{
                if (err.name !== 'AbortError') console.warn('Periodic window fetch error:', err);
              }});
            }}
          }}
        }} else {{
          isRigOnline = false;
          isRigActive = false;
        }}
      }} catch (err) {{
        if (err.name === 'AbortError') return;
        isRigOnline = false;
        isRigActive = false;
      }}

      updateRigStatusUI(isRigOnline);

      // Reschedule next poll: 30s offline, 10s active, 25s idle (Section 3 Invariant: never < 5000ms)
      if (myGen === generation && currentMode === 'live' && !isAfkFrozen && !isLivePaused && !document.hidden && PAGE_DEFAULT_VIEW === 'live') {{
        const delay = !isRigOnline ? POLL_OFFLINE_MS : (isRigActive ? POLL_ACTIVE_MS : POLL_IDLE_MS);
        if (pollTimer) clearTimeout(pollTimer);
        pollTimer = setTimeout(() => pollOnce(myGen), delay);
      }}
    }}

    function applyRecord(rec, isFromLive = false) {{
      const [t, ax, ay, az, rms] = rec;
      const vibe = Math.sqrt(ax*ax + ay*ay + az*az);
      const vibStd = getVibStd(rec);

      if (timelineHeadRms) timelineHeadRms.innerText = rms.toFixed(1);
      if (timelineHeadSpike) {{
        if (vibStd !== null) {{
          timelineHeadSpike.innerText = vibStd > VIB_RUNNING_THRESHOLD ? 'Running' : 'Idle';
        }} else {{
          timelineHeadSpike.innerText = '—';
        }}
        timelineHeadSpike.title = 'Provisional: vibration std > 0.08 m/s² (same as firmware fallback); retune after first firmware-07 wash';
      }}

      // Card 1 legend: show 'Vib (σ)' with 3 decimals whenever vibStd is available, in both live and historic
      const curVibeEl = document.getElementById('spline-cur-vibe');
      const curVibeTitle = document.getElementById('lbl-spline-vibe-title');
      if (curVibeEl) {{
        if (vibStd !== null) {{
          if (curVibeTitle) curVibeTitle.innerText = 'Vib (\u03c3)';
          curVibeEl.innerText = vibStd.toFixed(3);
        }} else {{
          if (curVibeTitle) curVibeTitle.innerText = '|a|';
          curVibeEl.innerText = vibe.toFixed(2);
        }}
      }}
      const curRmsEl = document.getElementById('spline-cur-rms');
      if (curRmsEl) curRmsEl.innerText = rms.toFixed(1);

      // Card 2 pills & title: per-axis vibration std in sigma mode vs mean lanes in legacy mode
      const isAxisSigma = (currentMode === 'historic')
        ? seriesHasAxisStd(ACTIVE_DATA)
        : (seriesHasAxisStd(LIVE_BUFFER) || (rec && getAxisStd(rec, 0) !== null));

      updateCard2Labels(isAxisSigma);

      if (isAxisSigma) {{
        const sx = getAxisStd(rec, 0);
        const sy = getAxisStd(rec, 1);
        const sz = getAxisStd(rec, 2);
        vibeLegX.innerText = sx !== null ? sx.toFixed(3) : '—';
        vibeLegY.innerText = sy !== null ? sy.toFixed(3) : '—';
        vibeLegZ.innerText = sz !== null ? sz.toFixed(3) : '—';
        if (headVibeMag) headVibeMag.innerText = vibStd !== null ? vibStd.toFixed(3) : '—';
      }} else {{
        const strX = (ax >= 0 ? '+' : '') + ax.toFixed(2);
        const strY = (ay >= 0 ? '+' : '') + ay.toFixed(2);
        const strZ = (az >= 0 ? '+' : '') + az.toFixed(2);
        vibeLegX.innerText = strX;
        vibeLegY.innerText = strY;
        vibeLegZ.innerText = strZ;
        if (headVibeMag) {{
          if (isFromLive && vibStd !== null) {{
            headVibeMag.innerHTML = `${{vibe.toFixed(2)}} <span style="color: var(--teal-accent); font-size: 11px; font-weight: 500;">(&sigma;: ${{vibStd.toFixed(2)}})</span>`;
          }} else {{
            headVibeMag.innerText = vibe.toFixed(2);
          }}
        }}
      }}

      // Dominant frequency readout: gated on VIB_RUNNING_THRESHOLD
      const vibDomFreqEl = document.getElementById('vib-dom-freq');
      if (vibDomFreqEl) {{
        const vdf = (rec && rec.length >= 12 && typeof rec[11] === 'number' && Number.isFinite(rec[11])) ? rec[11] : null;
        if (vibStd !== null && vibStd > VIB_RUNNING_THRESHOLD && vdf !== null) {{
          vibDomFreqEl.innerText = `${{vdf.toFixed(1)}} Hz`;
        }} else {{
          vibDomFreqEl.innerText = '—';
        }}
      }}

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

      // Shaded blocks for electrical heater (amber) and mechanical spin (teal)
      if (currentMode === 'historic' && ACTIVE_DATA && ACTIVE_DATA.length > 1) {{
        const session = LOADED_SESSIONS[activeSessionKey] || (Object.keys(LOADED_SESSIONS).length > 0 ? LOADED_SESSIONS[Object.keys(LOADED_SESSIONS)[0]] : null);
        const blocks = (session && session.summary) ? (session.summary.blocks || []) : [];
        if (blocks.length > 0) {{
          const totalPts = ACTIVE_DATA.length;
          const winSize = 40;
          const startIdx = isFull ? 0 : Math.max(0, currentIndex - Math.floor(winSize / 2));
          const endIdx = isFull ? (totalPts - 1) : Math.min(totalPts - 1, startIdx + winSize);
          const ptsCount = isFull ? totalPts : (endIdx - startIdx + 1);

          for (let b = 0; b < blocks.length; b++) {{
            const blk = blocks[b];
            const ov0 = Math.max(blk.i0, startIdx);
            const ov1 = Math.min(blk.i1, endIdx);
            if (ov0 <= ov1 && ptsCount > 1) {{
              const x0 = marginLeft + (((ov0 - startIdx) / (ptsCount - 1)) * plotW);
              const x1 = marginLeft + (((ov1 - startIdx) / (ptsCount - 1)) * plotW);
              const clX0 = Math.max(marginLeft, Math.min(w - marginRight, x0));
              const clX1 = Math.max(marginLeft, Math.min(w - marginRight, x1));
              const rectW = Math.max(1 * dpr, clX1 - clX0);

              if (blk.type === 'heater') {{
                splineCtx.fillStyle = 'rgba(251, 146, 60, 0.16)';
                splineCtx.fillRect(clX0, marginTop, rectW, plotH);
                splineCtx.fillStyle = 'rgba(251, 146, 60, 0.6)';
                splineCtx.fillRect(clX0, marginTop, rectW, 2 * dpr);
              }} else if (blk.type === 'spin') {{
                splineCtx.fillStyle = 'rgba(0, 240, 210, 0.14)';
                splineCtx.fillRect(clX0, marginTop, rectW, plotH);
                splineCtx.fillStyle = 'rgba(0, 240, 210, 0.6)';
                splineCtx.fillRect(clX0, marginTop, rectW, 2 * dpr);
              }}
            }}
          }}
        }}
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

      const isSigmaMode = seriesHasVibStd(points);

      let vibMax = 1.0;
      let scaleVibe = 1.0;

      if (isSigmaMode) {{
        // Sigma mode (Firmware 07): honest dynamic vibration scale from 0 to nice max (>= 0.5)
        let maxVibInPoints = 0.0;
        for (let i = 0; i < points.length; i++) {{
          const s = getVibStd(points[i]);
          if (s !== null && s > maxVibInPoints) maxVibInPoints = s;
        }}
        const vScale = getNiceVibScale(maxVibInPoints);
        vibMax = vScale.max;

        vScale.ticks.forEach(val => {{
          const y = marginTop + plotH - ((val / vibMax) * plotH);
          splineCtx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
          splineCtx.beginPath();
          splineCtx.moveTo(marginLeft, y);
          splineCtx.lineTo(w - marginRight, y);
          splineCtx.stroke();

          splineCtx.fillStyle = 'rgba(0, 240, 210, 0.7)';
          splineCtx.font = `600 ${{ (isMobile ? 7.5 : 8) * dpr }}px 'JetBrains Mono', monospace`;
          splineCtx.textAlign = 'right';
          splineCtx.fillText(val.toFixed(val < 1 && val > 0 ? 2 : 1), marginLeft - (5 * dpr), y + (3 * dpr));
        }});
        splineCtx.fillText('\u03c3 m/s\u00b2', marginLeft - (5 * dpr), marginTop - (4 * dpr));
        splineCtx.textAlign = 'left';

        // Dashed Sensor Noise Floor Marker (~0.03 m/s^2)
        const yFloor = marginTop + plotH - ((0.03 / vibMax) * plotH);
        splineCtx.strokeStyle = 'rgba(0, 240, 210, 0.35)';
        splineCtx.setLineDash([3 * dpr, 3 * dpr]);
        splineCtx.beginPath();
        splineCtx.moveTo(marginLeft, yFloor);
        splineCtx.lineTo(w - marginRight, yFloor);
        splineCtx.stroke();
        splineCtx.setLineDash([]);

        splineCtx.fillStyle = 'rgba(0, 240, 210, 0.5)';
        splineCtx.font = `500 ${{ (isMobile ? 7 : 7.5) * dpr }}px 'JetBrains Mono', monospace`;
        splineCtx.textAlign = 'left';
        splineCtx.fillText('sensor floor ~0.03', marginLeft + (4 * dpr), yFloor - (3 * dpr));
      }} else {{
        // Legacy mode (Firmware 05/06 snapshots): |a| resultant around 9.81
        const maxVibe = points.reduce((m, p) => Math.max(m, Math.sqrt(p[1]*p[1] + p[2]*p[2] + p[3]*p[3])), 9.81);
        const minVibe = points.reduce((m, p) => Math.min(m, Math.sqrt(p[1]*p[1] + p[2]*p[2] + p[3]*p[3])), 9.81);
        const vibeSpread = Math.max(2.5, maxVibe - 9.81, 9.81 - minVibe);
        scaleVibe = Math.min((isMobile ? 20 : 25) * dpr, (plotH * 0.38) / vibeSpread);

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
        splineCtx.fillText('m/s\u00b2', marginLeft - (5 * dpr), marginTop - (4 * dpr));
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
      }}

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
        if (i === 0 || (currentMode === 'live' && isGapBefore(points, i))) splineCtx.moveTo(x, y);
        else splineCtx.lineTo(x, y);
      }}
      splineCtx.stroke();

      // 2. Draw Vibration Wave (Teal) strictly within [marginLeft, w - marginRight]
      if (isSigmaMode) {{
        const gradTeal = splineCtx.createLinearGradient(0, marginTop, 0, marginTop + plotH);
        gradTeal.addColorStop(0, 'rgba(0, 240, 210, 0.2)');
        gradTeal.addColorStop(1, 'rgba(0, 240, 210, 0.0)');

        splineCtx.beginPath();
        let inSubpath = false;
        for (let i = 0; i < points.length; i++) {{
          const v = getVibStd(points[i]);
          const x = marginLeft + ((i / (points.length - 1)) * plotW);
          if (v !== null) {{
            const y = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((v / vibMax) * plotH));
            if (!inSubpath) {{
              splineCtx.moveTo(x, marginTop + plotH);
              splineCtx.lineTo(x, y);
              inSubpath = true;
            }} else {{
              splineCtx.lineTo(x, y);
            }}
          }} else if (inSubpath) {{
            const prevX = marginLeft + (((i - 1) / (points.length - 1)) * plotW);
            splineCtx.lineTo(prevX, marginTop + plotH);
            splineCtx.closePath();
            inSubpath = false;
          }}
        }}
        if (inSubpath) {{
          const lastX = marginLeft + plotW;
          splineCtx.lineTo(lastX, marginTop + plotH);
          splineCtx.closePath();
        }}
        splineCtx.fillStyle = gradTeal;
        splineCtx.fill();

        splineCtx.beginPath();
        splineCtx.strokeStyle = '#00f0d2';
        splineCtx.lineWidth = strokeW;
        let lastValid = false;
        for (let i = 0; i < points.length; i++) {{
          const v = getVibStd(points[i]);
          const x = marginLeft + ((i / (points.length - 1)) * plotW);
          if (v !== null) {{
            const y = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((v / vibMax) * plotH));
            if (!lastValid || (currentMode === 'live' && isGapBefore(points, i))) {{
              splineCtx.moveTo(x, y);
            }} else {{
              splineCtx.lineTo(x, y);
            }}
            lastValid = true;
          }} else {{
            lastValid = false;
          }}
        }}
        splineCtx.stroke();
      }} else {{
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
          if (i === 0 || (currentMode === 'live' && isGapBefore(points, i))) splineCtx.moveTo(x, y);
          else splineCtx.lineTo(x, y);
        }}
        splineCtx.stroke();
      }}

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
        if (isSigmaMode) {{
          const curVibStd = getVibStd(curPt);
          if (curVibStd !== null) {{
            const cyVibe = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((curVibStd / vibMax) * plotH));
            splineCtx.fillStyle = '#00f0d2';
            splineCtx.beginPath();
            splineCtx.arc(cx, cyVibe, 4 * dpr, 0, Math.PI * 2);
            splineCtx.fill();
            splineCtx.strokeStyle = '#ffffff';
            splineCtx.lineWidth = 1 * dpr;
            splineCtx.stroke();
          }}
        }} else {{
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

      // Vertical separator line
      xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      xyzCtx.lineWidth = 1 * dpr;
      xyzCtx.beginPath();
      xyzCtx.moveTo(marginLeft, marginTop);
      xyzCtx.lineTo(marginLeft, h - marginBottom);
      xyzCtx.moveTo(w - marginRight, marginTop);
      xyzCtx.lineTo(w - marginRight, h - marginBottom);
      xyzCtx.stroke();

      // Time grid & labels across the bottom (in full historical mode)
      if (isFull) {{
        drawTimeGrid(xyzCtx, w, h, marginLeft, marginRight, plotW, plotH, marginTop, dpr, isMobile);
      }}

      const isAxisSigmaMode = seriesHasAxisStd(points);
      updateCard2Labels(isAxisSigmaMode);

      let axisVibMax = 1.0;
      const yZero = marginTop + (plotH * 0.32);
      const scaleXY = (isMobile ? 10 : 12) * dpr;
      const yGravity = marginTop + (plotH * 0.78);
      const scaleZ = (isMobile ? 10 : 12) * dpr;

      if (isAxisSigmaMode) {{
        // Sigma mode: shared axis 0 to nice max (>= 0.5 m/s^2)
        let maxAxisSigma = 0.5;
        for (let i = 0; i < points.length; i++) {{
          const sx = getAxisStd(points[i], 0);
          const sy = getAxisStd(points[i], 1);
          const sz = getAxisStd(points[i], 2);
          if (sx !== null && sx > maxAxisSigma) maxAxisSigma = sx;
          if (sy !== null && sy > maxAxisSigma) maxAxisSigma = sy;
          if (sz !== null && sz > maxAxisSigma) maxAxisSigma = sz;
        }}
        const vScale = getNiceVibScale(maxAxisSigma);
        axisVibMax = vScale.max;

        vScale.ticks.forEach(val => {{
          const y = marginTop + plotH - ((val / axisVibMax) * plotH);
          xyzCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
          xyzCtx.beginPath();
          xyzCtx.moveTo(marginLeft, y);
          xyzCtx.lineTo(w - marginRight, y);
          xyzCtx.stroke();

          xyzCtx.fillStyle = 'rgba(255, 255, 255, 0.45)';
          xyzCtx.font = `600 ${{ (isMobile ? 7.5 : 8) * dpr }}px 'JetBrains Mono', monospace`;
          xyzCtx.textAlign = 'right';
          xyzCtx.fillText(val.toFixed(val < 1 && val > 0 ? 2 : 1), marginLeft - (5 * dpr), y + (3 * dpr));
        }});
        xyzCtx.fillText('\u03c3 m/s\u00b2', marginLeft - (5 * dpr), marginTop - (4 * dpr));
        xyzCtx.textAlign = 'left';

        // Dashed Sensor Noise Floor Marker (~0.03 m/s^2)
        const yFloor = marginTop + plotH - ((0.03 / axisVibMax) * plotH);
        xyzCtx.strokeStyle = 'rgba(0, 240, 210, 0.25)';
        xyzCtx.setLineDash([3 * dpr, 3 * dpr]);
        xyzCtx.beginPath();
        xyzCtx.moveTo(marginLeft, yFloor);
        xyzCtx.lineTo(w - marginRight, yFloor);
        xyzCtx.stroke();
        xyzCtx.setLineDash([]);
      }} else {{
        // Legacy mode: Baseline grid lines (cleanly spaced, zero gutter collisions)
        const hLines = isMobile ? [
          {{ y: yZero - (4.0 * scaleXY), lbl: '+4.0', col: 'rgba(255, 255, 255, 0.25)' }},
          {{ y: yZero, lbl: '0.0', col: 'rgba(255, 255, 255, 0.45)' }},
          {{ y: yGravity, lbl: '-9.81', col: 'rgba(167, 139, 250, 0.6)' }},
          {{ y: yGravity - ((-13.0 + 9.81) * scaleZ), lbl: '-13.0', col: 'rgba(167, 139, 250, 0.3)' }}
        ] : [
          {{ y: yZero - (4.0 * scaleXY), lbl: '+4.0 m/s\u00b2', col: 'rgba(255, 255, 255, 0.25)' }},
          {{ y: yZero, lbl: '0.0 (X/Y)', col: 'rgba(255, 255, 255, 0.45)' }},
          {{ y: yGravity, lbl: '-9.81 (Z)', col: 'rgba(167, 139, 250, 0.6)' }},
          {{ y: yGravity - ((-13.0 + 9.81) * scaleZ), lbl: '-13.0 m/s\u00b2', col: 'rgba(167, 139, 250, 0.3)' }}
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
      }}

      if (points.length < 2) return;

      const strokeW = (isFull && points.length > 500) ? (1.5 * dpr) : (2 * dpr);

      if (isAxisSigmaMode) {{
        // Plot σz (Purple)
        if (axisVisible.z) {{
          xyzCtx.beginPath();
          xyzCtx.strokeStyle = '#a78bfa';
          xyzCtx.lineWidth = strokeW;
          let lastValid = false;
          for (let i = 0; i < points.length; i++) {{
            const sz = getAxisStd(points[i], 2);
            const x = marginLeft + ((i / (points.length - 1)) * plotW);
            if (sz !== null) {{
              const y = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((sz / axisVibMax) * plotH));
              if (!lastValid || (currentMode === 'live' && isGapBefore(points, i))) xyzCtx.moveTo(x, y);
              else xyzCtx.lineTo(x, y);
              lastValid = true;
            }} else {{
              lastValid = false;
            }}
          }}
          xyzCtx.stroke();
        }}

        // Plot σy (Coral)
        if (axisVisible.y) {{
          xyzCtx.beginPath();
          xyzCtx.strokeStyle = '#fb923c';
          xyzCtx.lineWidth = strokeW;
          let lastValid = false;
          for (let i = 0; i < points.length; i++) {{
            const sy = getAxisStd(points[i], 1);
            const x = marginLeft + ((i / (points.length - 1)) * plotW);
            if (sy !== null) {{
              const y = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((sy / axisVibMax) * plotH));
              if (!lastValid || (currentMode === 'live' && isGapBefore(points, i))) xyzCtx.moveTo(x, y);
              else xyzCtx.lineTo(x, y);
              lastValid = true;
            }} else {{
              lastValid = false;
            }}
          }}
          xyzCtx.stroke();
        }}

        // Plot σx (Teal)
        if (axisVisible.x) {{
          xyzCtx.beginPath();
          xyzCtx.strokeStyle = '#00f0d2';
          xyzCtx.lineWidth = strokeW;
          let lastValid = false;
          for (let i = 0; i < points.length; i++) {{
            const sx = getAxisStd(points[i], 0);
            const x = marginLeft + ((i / (points.length - 1)) * plotW);
            if (sx !== null) {{
              const y = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((sx / axisVibMax) * plotH));
              if (!lastValid || (currentMode === 'live' && isGapBefore(points, i))) xyzCtx.moveTo(x, y);
              else xyzCtx.lineTo(x, y);
              lastValid = true;
            }} else {{
              lastValid = false;
            }}
          }}
          xyzCtx.stroke();
        }}
      }} else {{
        // Legacy mode: Plot Az (Purple)
        if (axisVisible.z) {{
          xyzCtx.beginPath();
          xyzCtx.strokeStyle = '#a78bfa';
          xyzCtx.lineWidth = strokeW;
          for (let i = 0; i < points.length; i++) {{
            const x = marginLeft + ((i / (points.length - 1)) * plotW);
            const az = points[i][3];
            const y = yGravity - ((az + 9.81) * scaleZ);
            if (i === 0 || (currentMode === 'live' && isGapBefore(points, i))) xyzCtx.moveTo(x, y);
            else xyzCtx.lineTo(x, y);
          }}
          xyzCtx.stroke();
        }}

        // Legacy mode: Plot Ay (Coral)
        if (axisVisible.y) {{
          xyzCtx.beginPath();
          xyzCtx.strokeStyle = '#fb923c';
          xyzCtx.lineWidth = strokeW;
          for (let i = 0; i < points.length; i++) {{
            const x = marginLeft + ((i / (points.length - 1)) * plotW);
            const ay = points[i][2];
            const y = yZero - (ay * scaleXY);
            if (i === 0 || (currentMode === 'live' && isGapBefore(points, i))) xyzCtx.moveTo(x, y);
            else xyzCtx.lineTo(x, y);
          }}
          xyzCtx.stroke();
        }}

        // Legacy mode: Plot Ax (Teal)
        if (axisVisible.x) {{
          xyzCtx.beginPath();
          xyzCtx.strokeStyle = '#00f0d2';
          xyzCtx.lineWidth = strokeW;
          for (let i = 0; i < points.length; i++) {{
            const x = marginLeft + ((i / (points.length - 1)) * plotW);
            const ax = points[i][1];
            const y = yZero - (ax * scaleXY);
            if (i === 0 || (currentMode === 'live' && isGapBefore(points, i))) xyzCtx.moveTo(x, y);
            else xyzCtx.lineTo(x, y);
          }}
          xyzCtx.stroke();
        }}
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
        if (isAxisSigmaMode) {{
          if (axisVisible.z) {{
            const sz = getAxisStd(pt, 2);
            if (sz !== null) {{
              const cyZ = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((sz / axisVibMax) * plotH));
              xyzCtx.fillStyle = '#a78bfa';
              xyzCtx.beginPath();
              xyzCtx.arc(cx, cyZ, 4 * dpr, 0, Math.PI * 2);
              xyzCtx.fill();
              xyzCtx.strokeStyle = '#ffffff';
              xyzCtx.lineWidth = 1 * dpr;
              xyzCtx.stroke();
            }}
          }}
          if (axisVisible.x) {{
            const sx = getAxisStd(pt, 0);
            if (sx !== null) {{
              const cyX = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((sx / axisVibMax) * plotH));
              xyzCtx.fillStyle = '#00f0d2';
              xyzCtx.beginPath();
              xyzCtx.arc(cx, cyX, 4 * dpr, 0, Math.PI * 2);
              xyzCtx.fill();
              xyzCtx.strokeStyle = '#ffffff';
              xyzCtx.lineWidth = 1 * dpr;
              xyzCtx.stroke();
            }}
          }}
          if (axisVisible.y) {{
            const sy = getAxisStd(pt, 1);
            if (sy !== null) {{
              const cyY = Math.max(marginTop + (1 * dpr), marginTop + plotH - ((sy / axisVibMax) * plotH));
              xyzCtx.fillStyle = '#fb923c';
              xyzCtx.beginPath();
              xyzCtx.arc(cx, cyY, 4 * dpr, 0, Math.PI * 2);
              xyzCtx.fill();
              xyzCtx.strokeStyle = '#ffffff';
              xyzCtx.lineWidth = 1 * dpr;
              xyzCtx.stroke();
            }}
          }}
        }} else {{
          // Legacy mode: cursor dots at mean lanes
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
      }}

      // Dynamic Anti-Collision Placement: In legacy mode only, render baseline badges on opposite side of active cursor
      if (!isAxisSigmaMode) {{
        const isCursorOnLeftXyz = (points.length > 1) ? ((curRelIdx / (points.length - 1)) < 0.5) : true;
        const badgeAlign = isCursorOnLeftXyz ? 'right' : 'left';
        const badgeX = isCursorOnLeftXyz ? (w - marginRight - (6 * dpr)) : (marginLeft + (8 * dpr));

        drawPillBadge(xyzCtx, badgeX, yZero - (10 * dpr), isMobile ? '0.0 Baseline' : 'X/Y Zero Baseline', 'rgba(255,255,255,0.45)', badgeAlign, dpr);
        drawPillBadge(xyzCtx, badgeX, yGravity - (10 * dpr), isMobile ? 'Z 1g Gravity' : 'Z 1g Gravity (-9.81 m/s²)', '#a78bfa', badgeAlign, dpr);
      }}
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

      // Peak Dashed Line (Dynamic in Live mode, Historical in Historic mode)
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
        peakLabel = isMobile ? `PEAK: ${{peakVal.toFixed(1)}} (${{peakMin}}m)` : `PEAK: ${{peakVal.toFixed(1)}} RMS (${{peakMin}}m)`;
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
        if (i === 0 || (currentMode === 'live' && isGapBefore(dataSeries, i))) areaCtx.moveTo(x, y);
        else areaCtx.lineTo(x, y);
      }}
      areaCtx.stroke();

      // In live mode, draw a faint dashed vertical line at each gap break
      if (currentMode === 'live') {{
        areaCtx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        areaCtx.setLineDash([2 * dpr, 3 * dpr]);
        areaCtx.lineWidth = 1 * dpr;
        areaCtx.beginPath();
        for (let i = 1; i < total; i++) {{
          if (isGapBefore(dataSeries, i)) {{
            const gx = marginLeft + ((i / (total - 1)) * plotW);
            areaCtx.moveTo(gx, marginTop);
            areaCtx.lineTo(gx, marginTop + plotH);
          }}
        }}
        areaCtx.stroke();
        areaCtx.setLineDash([]);
      }}

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

      // Dynamic Anti-Collision Placement: Always draw peak on OPPOSITE side of active cursor, AFTER curves are drawn!
      const isCursorOnLeft = (total > 1) ? ((curPointIdx / (total - 1)) < 0.5) : true;
      if (showPeak) {{
        const isPeakOnLeft = (!isCursorOnLeft && curRms > 300 && curX > (w - marginRight - (160 * dpr)));
        const peakAlign = isPeakOnLeft ? 'left' : 'right';
        const peakX = peakAlign === 'right' ? (w - marginRight - (6 * dpr)) : (marginLeft + (8 * dpr));
        drawPillBadge(areaCtx, peakX, yPeak - (10 * dpr), peakLabel, '#fb923c', peakAlign, dpr);
      }}

      // Floating cursor badge (Cleanly bounded, flips if near edges, never clipped)
      const badgeText = `${{curRms.toFixed(1)}} RMS`;

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

      // Check if dataset contains genuine positive measured power
      let hasRealPower = false;
      for (let i = 0; i < total; i++) {{
        const row = dataSeries[i];
        if (row && row.length >= 6 && row[5] !== null && row[5] !== undefined && !isNaN(row[5]) && row[5] > 0.05) {{
          hasRealPower = true;
          break;
        }}
      }}

      // Dynamic subtitle update reflecting data source
      const subEnergy = document.getElementById('sub-energy');
      if (subEnergy) {{
        if (hasRealPower) {{
          subEnergy.innerHTML = 'TP-Link Tapo P110 (1 Hz) &bull; Active power and energy over the shown span';
        }} else {{
          subEnergy.innerHTML = 'Active power not tracked for this cycle (0.0 W baseline) &bull; Tapo P110 monitoring inactive';
        }}
      }}

      // Extract power series (returns 0.0 W for untracked datasets such as 12 Oct runs)
      function getPowerAt(idx) {{
        const r = dataSeries[idx];
        if (!r) return 0.0;
        if (hasRealPower && r.length >= 6 && r[5] !== null && r[5] !== undefined && !isNaN(r[5])) {{
          return Math.max(0.0, r[5]);
        }}
        return 0.0;
      }}

      let maxPwrObserved = 0.0;
      let sumPwr = 0.0;
      for (let i = 0; i < total; i++) {{
        const p = getPowerAt(i);
        if (p > maxPwrObserved) maxPwrObserved = p;
        sumPwr += p;
      }}
      const avgPwr = total > 0 ? (sumPwr / total) : 0.0;

      let pwrMax = 700;
      let ticks = [600, 450, 300, 150, 0];
      if (maxPwrObserved > 1100) {{
        pwrMax = 2200;
        ticks = [2000, 1500, 1000, 500, 0];
      }} else if (maxPwrObserved > 650) {{
        pwrMax = 1000;
        ticks = [1000, 800, 600, 400, 200, 0];
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
        drawTimeGrid(energyCtx, w, h, marginLeft, marginRight, plotW, plotH, marginTop, dpr, isMobile);
      }}

      // Shaded blocks for electrical heater (amber) and mechanical spin (teal)
      if (currentMode === 'historic' && total > 1) {{
        const session = LOADED_SESSIONS[activeSessionKey] || (Object.keys(LOADED_SESSIONS).length > 0 ? LOADED_SESSIONS[Object.keys(LOADED_SESSIONS)[0]] : null);
        const blocks = (session && session.summary) ? (session.summary.blocks || []) : [];
        if (blocks.length > 0) {{
          for (let b = 0; b < blocks.length; b++) {{
            const blk = blocks[b];
            const x0 = marginLeft + ((blk.i0 / (total - 1)) * plotW);
            const x1 = marginLeft + ((blk.i1 / (total - 1)) * plotW);
            const clX0 = Math.max(marginLeft, Math.min(w - marginRight, x0));
            const clX1 = Math.max(marginLeft, Math.min(w - marginRight, x1));
            const rectW = Math.max(1 * dpr, clX1 - clX0);

            if (blk.type === 'heater') {{
              energyCtx.fillStyle = 'rgba(251, 146, 60, 0.16)';
              energyCtx.fillRect(clX0, marginTop, rectW, plotH);
              energyCtx.fillStyle = 'rgba(251, 146, 60, 0.6)';
              energyCtx.fillRect(clX0, marginTop, rectW, 2 * dpr);
            }} else if (blk.type === 'spin') {{
              energyCtx.fillStyle = 'rgba(0, 240, 210, 0.14)';
              energyCtx.fillRect(clX0, marginTop, rectW, plotH);
              energyCtx.fillStyle = 'rgba(0, 240, 210, 0.6)';
              energyCtx.fillRect(clX0, marginTop, rectW, 2 * dpr);
            }}
          }}
        }}
      }}

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
        if (i === 0 || (currentMode === 'live' && isGapBefore(dataSeries, i))) energyCtx.moveTo(x, y);
        else energyCtx.lineTo(x, y);
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

      // Floating cursor pill
      const badgeText = hasRealPower
        ? `${{curPwr.toFixed(1)}} W`
        : '0.0 Watts (Not Tracked)';
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

      // Untracked dataset watermark on canvas
      if (!hasRealPower) {{
        energyCtx.fillStyle = 'rgba(255, 255, 255, 0.35)';
        energyCtx.font = `600 ${{(isMobile ? 8.5 : 9.5) * dpr}}px 'JetBrains Mono', monospace`;
        energyCtx.textAlign = 'center';
        energyCtx.fillText('Active Power Not Tracked For This Session (0.0 W Baseline)', marginLeft + (plotW / 2), marginTop + (plotH / 2));
        energyCtx.textAlign = 'left';
      }}

      // Update stat cards
      // Average power × shown duration, an approximation from measured samples
      const durHours = (total > 1) ? ((dataSeries[total - 1][0] - dataSeries[0][0]) / 3600000.0) : 0.05;
      const cycleKwh = hasRealPower ? ((avgPwr * durHours) / 1000.0) : 0.0;

      const elWatts = document.getElementById('energy-head-watts');
      if (elWatts) elWatts.innerText = curPwr.toFixed(1);
      const elKwh = document.getElementById('energy-head-kwh');
      if (elKwh) elKwh.innerText = cycleKwh.toFixed(2);

      const elPeak = document.getElementById('energy-stat-peak');
      if (elPeak) elPeak.innerText = hasRealPower ? `${{maxPwrObserved.toFixed(0)}} W` : '0 W';
      const elAvg = document.getElementById('energy-stat-avg');
      if (elAvg) elAvg.innerText = hasRealPower ? `${{avgPwr.toFixed(0)}} W` : '0 W';
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
          drawEnergy();
        }}, 80);
      }} else {{
        clearInterval(playInterval);
      }}
    }}

    // Robust CSV parser supporting both Firmware 07 (V3 window record with vib_mag_std)
    // and Legacy Firmware 05/06 (snapshot positional format).
    // The record layout produced here MUST match Python load_csv() exactly:
    // Firmware 07 (12 elements): [t, ax, ay, az, rms, pwr, sm, 'w', sx, sy, sz, vdf]
    //   Index 0:  timestamp_ms (Math.round(t))
    //   Index 1:  accel_x (mean tilt, ax)
    //   Index 2:  accel_y (mean tilt, ay)
    //   Index 3:  accel_z (mean tilt, az)
    //   Index 4:  audio_rms (rms)
    //   Index 5:  power_w (pwr or null)
    //   Index 6:  vib_mag_std (sm or null) - dynamic vibration std
    //   Index 7:  'w' (phase marker / schema indicator)
    //   Index 8:  vib_std_x (sx or null)
    //   Index 9:  vib_std_y (sy or null)
    //   Index 10: vib_std_z (sz or null)
    //   Index 11: vib_dom_hz (vdf or null) - dominant frequency in Hz
    // Legacy (5 or 6 elements): [t, ax, ay, az, rms] or [t, ax, ay, az, rms, pwr]
    function parseCsvData(text) {{
      const lines = text.trim().split(/\\r?\\n/);
      const records = [];
      if (!lines.length) return records;

      // Locate first non-empty line as candidate header
      let headerIdx = -1;
      let headerLine = '';
      for (let i = 0; i < lines.length; i++) {{
        const trimmed = lines[i].trim();
        if (trimmed) {{
          headerIdx = i;
          headerLine = trimmed;
          break;
        }}
      }}
      if (headerIdx === -1) return records;

      const rawHeaders = headerLine.split(',').map(s => s.replace(/['"]/g, '').trim());

      // =========================================================================
      // BRANCH 1: Firmware 07 (V3 Schema) - header contains 'vib_mag_std'
      // =========================================================================
      if (rawHeaders.indexOf('vib_mag_std') !== -1) {{
        const colMap = {{}};
        for (let j = 0; j < rawHeaders.length; j++) {{
          colMap[rawHeaders[j]] = j;
        }}

        const idxT = colMap.hasOwnProperty('timestamp_ms') ? colMap['timestamp_ms'] : 0;
        const idxAx = colMap.hasOwnProperty('accel_x') ? colMap['accel_x'] : 1;
        const idxAy = colMap.hasOwnProperty('accel_y') ? colMap['accel_y'] : 2;
        const idxAz = colMap.hasOwnProperty('accel_z') ? colMap['accel_z'] : 3;
        const idxRms = colMap.hasOwnProperty('audio_rms') ? colMap['audio_rms'] : 4;
        const idxPwr = colMap.hasOwnProperty('power_w') ? colMap['power_w'] : -1;
        const idxSm = colMap.hasOwnProperty('vib_mag_std') ? colMap['vib_mag_std'] : -1;
        const idxSx = colMap.hasOwnProperty('vib_std_x') ? colMap['vib_std_x'] : -1;
        const idxSy = colMap.hasOwnProperty('vib_std_y') ? colMap['vib_std_y'] : -1;
        const idxSz = colMap.hasOwnProperty('vib_std_z') ? colMap['vib_std_z'] : -1;
        const idxVdf = colMap.hasOwnProperty('vib_dom_hz') ? colMap['vib_dom_hz'] : -1;

        function parseFloatVal(val) {{
          if (val === undefined || val === null) return null;
          const clean = String(val).replace(/['"]/g, '').trim();
          if (clean === '') return null;
          const num = parseFloat(clean);
          return isNaN(num) ? null : Number(num.toFixed(4));
        }}

        const maxReqIdx = Math.max(idxT, idxAx, idxAy, idxAz, idxRms);

        for (let i = headerIdx + 1; i < lines.length; i++) {{
          const line = lines[i].trim();
          if (!line) continue;
          const parts = line.split(',');
          if (parts.length <= maxReqIdx) continue;

          const tStr = parts[idxT].replace(/['"]/g, '').trim();
          const axStr = parts[idxAx].replace(/['"]/g, '').trim();
          const ayStr = parts[idxAy].replace(/['"]/g, '').trim();
          const azStr = parts[idxAz].replace(/['"]/g, '').trim();
          const rmsStr = parts[idxRms].replace(/['"]/g, '').trim();

          const t = parseFloat(tStr);
          const ax = parseFloat(axStr);
          const ay = parseFloat(ayStr);
          const az = parseFloat(azStr);
          const rms = parseFloat(rmsStr);

          // Skip a row only if t, ax, ay, az or rms is not a number
          if (isNaN(t) || isNaN(ax) || isNaN(ay) || isNaN(az) || isNaN(rms)) continue;

          const pwr = (idxPwr >= 0 && idxPwr < parts.length) ? parseFloatVal(parts[idxPwr]) : null;
          const sm = (idxSm >= 0 && idxSm < parts.length) ? parseFloatVal(parts[idxSm]) : null;
          const sx = (idxSx >= 0 && idxSx < parts.length) ? parseFloatVal(parts[idxSx]) : null;
          const sy = (idxSy >= 0 && idxSy < parts.length) ? parseFloatVal(parts[idxSy]) : null;
          const sz = (idxSz >= 0 && idxSz < parts.length) ? parseFloatVal(parts[idxSz]) : null;
          const vdf = (idxVdf >= 0 && idxVdf < parts.length) ? parseFloatVal(parts[idxVdf]) : null;

          records.push([
            Math.round(t),
            Number(ax.toFixed(4)),
            Number(ay.toFixed(4)),
            Number(az.toFixed(4)),
            Number(rms.toFixed(4)),
            pwr,
            sm,
            'w',
            sx,
            sy,
            sz,
            vdf
          ]);
        }}
        records.sort((a, b) => a[0] - b[0]);
        return records;
      }}

      // =========================================================================
      // BRANCH 2: Legacy Firmware 05/06 (strictly unchanged logic)
      // =========================================================================
      for (let i = 0; i < lines.length; i++) {{
        const line = lines[i].trim();
        if (!line) continue;
        const parts = line.split(',').map(s => s.trim());
        if (parts.length >= 5) {{
          const t = parseFloat(parts[0].replace(/['"]/g, ''));
          const ax = parseFloat(parts[1].replace(/['"]/g, ''));
          const ay = parseFloat(parts[2].replace(/['"]/g, ''));
          const az = parseFloat(parts[3].replace(/['"]/g, ''));
          const rms = parseFloat(parts[4].replace(/['"]/g, ''));
          const pwrStr = (parts.length >= 6) ? parts[5].replace(/['"]/g, '').trim() : '';
          const pwr = (pwrStr !== '' && !isNaN(parseFloat(pwrStr))) ? parseFloat(pwrStr) : null;
          if (!isNaN(t) && !isNaN(ax) && !isNaN(ay) && !isNaN(az) && !isNaN(rms)) {{
            const rec = [Math.round(t), ax, ay, az, rms];
            if (pwr !== null && !isNaN(pwr)) rec.push(pwr);
            records.push(rec);
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
          alert(`Could not parse valid records from "${{file.name}}". Ensure CSV has valid columns (firmware-07 files are read by header with vib_mag_std, legacy files use first 5-6 columns).`);
          return;
        }}

        const sessionKey = 'custom_' + Date.now();
        const durationMin = ((records[records.length - 1][0] - records[0][0]) / 60000).toFixed(1);
        const cleanName = file.name.replace(/\\.[^/.]+$/, '');
        const displayName = `📁 ${{file.name}} (${{records.length}} pts, ${{durationMin}}m)`;

        LOADED_SESSIONS[sessionKey] = {{
          name: cleanName,
          displayName: displayName,
          data: records,
          category: 'custom'
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

    // Export Active CSV
    function exportActiveCsv() {{
      let csv = 'timestamp_ms,accel_x,accel_y,accel_z,audio_rms,power_w\\n';
      let exportName = 'telemetry.csv';
      if (currentMode === 'live') {{
        const src = LIVE_BUFFER.length > 0 ? LIVE_BUFFER : [[Date.now(), -0.74, 1.40, -9.40, 105.6, 0.0]];
        src.forEach(r => {{
          const p = (r.length >= 6 && r[5] !== null && r[5] !== undefined) ? r[5] : 0.0;
          csv += `${{r[0]}},${{r[1]}},${{r[2]}},${{r[3]}},${{r[4]}},${{p.toFixed(1)}}\\n`;
        }});
        exportName = `live_stream_${{Date.now()}}.csv`;
      }} else {{
        ACTIVE_DATA.forEach(r => {{
          const p = (r.length >= 6 && r[5] !== null && r[5] !== undefined) ? r[5] : 0.0;
          csv += `${{r[0]}},${{r[1]}},${{r[2]}},${{r[3]}},${{r[4]}},${{p.toFixed(1)}}\\n`;
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
    const initialSessionParam = urlParams.get('session');
    if (initialSessionParam && LOADED_SESSIONS[initialSessionParam]) {{
      switchToSession(initialSessionParam);
    }} else if (initialSessionParam) {{
      const foundKey = Object.keys(LOADED_SESSIONS).find(k => k.includes(initialSessionParam) || (LOADED_SESSIONS[k].name && LOADED_SESSIONS[k].name.includes(initialSessionParam)));
      if (foundKey) {{
        switchToSession(foundKey);
      }} else {{
        setViewMode('{default_view}');
      }}
    }} else {{
      setViewMode('{default_view}');
    }}
    window.addEventListener('load', () => {{
      resizeCanvases();
      if (PAGE_DEFAULT_VIEW === 'live' && currentMode === 'live') {{
        recordUserActivity();
        generation++;
        pollOnce(generation);
      }}
      setupCanvasScrubbing(splineCvs);
      setupCanvasScrubbing(xyzCvs);
      setupCanvasScrubbing(areaCvs);
      if (energyCvs) setupCanvasScrubbing(energyCvs);
    }});
    document.addEventListener('visibilitychange', () => {{
      if (!document.hidden && currentMode === 'live' && PAGE_DEFAULT_VIEW === 'live') {{
        if (isAfkFrozen || isLivePaused) {{
          // If AFK frozen or manually paused, stay paused/frozen
          return;
        }}
        // Not AFK or paused: catch up on what was missed while tab was backgrounded
        recordUserActivity();
        resumeFromTabVisibility();
      }} else if (document.hidden) {{
        if (currentMode === 'live' && PAGE_DEFAULT_VIEW === 'live' && !isAfkFrozen) {{
          stopLivePolling();
        }}
      }}
    }});
  </script>
</body>
</html>'''

if __name__ == '__main__':
    # 0. Shared cached preset_sessions.js
    with open('preset_sessions.js', 'w', encoding='utf-8') as f:
        f.write(PRESET_SESSIONS_JS_CONTENT)

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