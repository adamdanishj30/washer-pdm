"""
Samsung SmartThings Client & Telemetry Bridge
Predictive Maintenance (PdM) SideProject - Samsung WW10TP44DSX Washing Machine

Provides authenticated, rate-throttled, token-auto-refreshing access to SmartThings REST API:
- Automatic OAuth2 token refresh via %LOCALAPPDATA%/@smartthings/cli/Data/credentials.json
- Graceful fallback to SMARTTHINGS_ACCESS_TOKEN or SMARTTHINGS_PAT in .env
- Continuous cycle phase tracking (washerJobState: weightSensing, wash, rinse, spin, finish)
- Phase timeline recording into Firebase (/session_phases/{session_id}/{timestamp_ms})
- Phase matching with Last-Observation-Carried-Forward (LOCF) and physics fallbacks.
"""

import os
import sys
import time
import json
import math
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

FIREBASE_HOST = os.getenv("FIREBASE_HOST", "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app")
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH") or os.getenv("FIREBASE_SECRET")
SMARTTHINGS_PAT = os.getenv("SMARTTHINGS_PAT")
SMARTTHINGS_DEVICE_ID = os.getenv("SMARTTHINGS_DEVICE_ID")
SMARTTHINGS_CLIENT_ID = "d18cf96e-c626-4433-bf51-ddbb10c5d1ed"
SMARTTHINGS_REFRESH_URL = "https://auth-global.api.smartthings.com/oauth/token"
SMARTTHINGS_API_URL = "https://api.smartthings.com/v1"

_last_st_call = 0.0
_cached_st_data = None

def get_valid_smartthings_token() -> str:
    """
    Retrieves or automatically refreshes the SmartThings OAuth2 access token.
    Prioritizes persistent CLI credentials with automated token exchange.
    """
    cred_path = Path(os.path.expandvars(r"%LOCALAPPDATA%\@smartthings\cli\Data\credentials.json"))
    
    # 1. Try reading and refreshing CLI credentials file
    if cred_path.is_file():
        try:
            with open(cred_path, "r", encoding="utf-8") as f:
                creds = json.load(f)
            prof = creds.get("default:api.smartthings.com", {})
            acc = prof.get("accessToken")
            ref = prof.get("refreshToken")
            exp_str = prof.get("expires")
            
            needs_refresh = False
            if exp_str:
                try:
                    exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                    now_dt = datetime.now(exp_dt.tzinfo)
                    if (exp_dt - now_dt).total_seconds() < 300:
                        needs_refresh = True
                except Exception:
                    needs_refresh = True
            
            if not needs_refresh and acc:
                return acc
            
            # Refresh using refresh token
            if ref:
                body = urllib.parse.urlencode({
                    "grant_type": "refresh_token",
                    "client_id": SMARTTHINGS_CLIENT_ID,
                    "refresh_token": ref
                }).encode("utf-8")
                req = urllib.request.Request(
                    SMARTTHINGS_REFRESH_URL,
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    new_acc = data.get("access_token")
                    new_ref = data.get("refresh_token") or ref
                    expires_in = data.get("expires_in", 86400)
                    
                    if new_acc:
                        prof["accessToken"] = new_acc
                        if new_ref:
                            prof["refreshToken"] = new_ref
                        import datetime as dt_mod
                        prof["expires"] = (dt_mod.datetime.now(dt_mod.timezone.utc) + dt_mod.timedelta(seconds=expires_in)).isoformat().replace("+00:00", "Z")
                        creds["default:api.smartthings.com"] = prof
                        with open(cred_path, "w", encoding="utf-8") as out_f:
                            json.dump(creds, out_f, indent=4)
                        return new_acc
        except Exception as e:
            print(f"[AUTH CLI NOTICE] CLI token refresh notice: {e}")

    # 2. Check environment variable refresh token
    env_ref = os.getenv("SMARTTHINGS_REFRESH_TOKEN")
    if env_ref:
        try:
            body = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "client_id": SMARTTHINGS_CLIENT_ID,
                "refresh_token": env_ref
            }).encode("utf-8")
            req = urllib.request.Request(
                SMARTTHINGS_REFRESH_URL,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                new_acc = data.get("access_token")
                if new_acc:
                    return new_acc
        except Exception as e:
            print(f"[AUTH ENV NOTICE] Env token refresh notice: {e}")

    # 3. Fallback to access token or PAT
    return os.getenv("SMARTTHINGS_ACCESS_TOKEN") or SMARTTHINGS_PAT

def _safe_get(d, *keys, default=None):
    curr = d
    for k in keys:
        if not isinstance(curr, dict):
            return default
        curr = curr.get(k)
        if curr is None:
            return default
    return curr if curr is not None else default

def query_smartthings() -> dict:
    """Fetch live machine status from Samsung SmartThings REST API."""
    if not SMARTTHINGS_DEVICE_ID:
        return {}
    token = get_valid_smartthings_token()
    if not token:
        return {}
        
    url = f"{SMARTTHINGS_API_URL}/devices/{SMARTTHINGS_DEVICE_ID}/status"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.smartthings+json;v=1",
        "User-Agent": "PdM-SmartThings-Client/1.0"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            main = data.get("components", {}).get("main", {})
            
            # Operating state
            job_state = _safe_get(main, "washerOperatingState", "washerJobState", "value", default="none")
            mach_state = _safe_get(main, "washerOperatingState", "machineState", "value", default="stop")
            comp_time = _safe_get(main, "washerOperatingState", "completionTime", "value")
            
            # Samsung custom capabilities
            remaining_mins = _safe_get(main, "samsungce.washerOperatingState", "remainingTime", "value", default=0)
            progress_pct = _safe_get(main, "samsungce.washerOperatingState", "progress", "value", default=0)
            
            cycle = _safe_get(main, "samsungce.washerCycle", "washerCycle", "value", default="unknown")
            spin_val = (_safe_get(main, "custom.washerSpinLevel", "washerSpinLevel", "value") or
                        _safe_get(main, "samsungce.washerSpinLevel", "spinLevel", "value"))
            try:
                target_rpm = int(spin_val) if spin_val and str(spin_val).isdigit() else 0
            except Exception:
                target_rpm = 0
                
            water_level = _safe_get(main, "samsungce.washerWaterLevel", "waterLevel", "value", default="normal")
            water_temp = (_safe_get(main, "custom.washerWaterTemperature", "washerWaterTemperature", "value") or
                          _safe_get(main, "samsungce.washerWaterTemperature", "waterTemperature", "value", default="cold"))
            rinse_cycles = _safe_get(main, "custom.washerRinseCycles", "washerRinseCycles", "value", default=0)
            detergent = _safe_get(main, "samsungce.autoDispenseDetergent", "remainingAmount", "value", default="unknown")
            softener = _safe_get(main, "samsungce.autoDispenseSoftener", "remainingAmount", "value", default="unknown")
            kids_lock = _safe_get(main, "samsungce.kidsLock", "lockState", "value", default="unlocked")
            
            cum_water = _safe_get(main, "samsungce.waterConsumptionReport", "waterConsumption", "value", "cumulativeAmount", default=0)

            return {
                "job_state": str(job_state).lower() if job_state else "none",
                "machine_state": str(mach_state).lower() if mach_state else "stop",
                "completion_time": comp_time,
                "remaining_mins": remaining_mins,
                "progress_pct": progress_pct,
                "cycle": cycle,
                "target_rpm": target_rpm,
                "water_level": water_level,
                "water_temp": water_temp,
                "rinse_cycles": rinse_cycles,
                "detergent_remaining": detergent,
                "softener_remaining": softener,
                "kids_lock": kids_lock,
                "cumulative_water_l": round(cum_water / 1000.0, 1) if cum_water else 0.0,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        print(f"[SMARTTHINGS CLIENT ERR] {e}")
        return {}

def get_smartthings_status(min_interval_s: float = 30.0) -> dict:
    """
    Fetches SmartThings status with throttling to protect cloud rate limits.
    Default: at most once every 30 seconds.
    """
    global _last_st_call, _cached_st_data
    now = time.time()
    if _cached_st_data is not None and (now - _last_st_call) < min_interval_s:
        return _cached_st_data
    
    _last_st_call = now  # Throttle regardless of success/failure
    data = query_smartthings()
    if data:
        _cached_st_data = data
    return _cached_st_data or {}

def push_phase_to_firebase(st_data: dict, session_id: str = None) -> bool:
    """
    Mirrors live phase to Firebase /live_phase.json
    and if session_id is active, appends checkpoint to /session_phases/{session_id}/{now_ms}.json
    """
    if not st_data:
        return False
        
    now_ms = int(time.time() * 1000)
    
    # 1. Update /live_phase.json
    try:
        url = f"{FIREBASE_HOST}/live_phase.json?auth={FIREBASE_AUTH}"
        data = json.dumps(st_data).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4):
            pass
    except Exception as e:
        print(f"[FIREBASE PUT live_phase ERR] {e}")

    # 2. Record checkpoint to session timeline
    if session_id:
        try:
            checkpoint = {
                "ts": now_ms,
                "phase": st_data.get("job_state", "none"),
                "machine_state": st_data.get("machine_state", "stop"),
                "progress_pct": st_data.get("progress_pct", 0),
                "remaining_mins": st_data.get("remaining_mins", 0),
                "target_rpm": st_data.get("target_rpm", 0)
            }
            url = f"{FIREBASE_HOST}/session_phases/{session_id}/{now_ms}.json?auth={FIREBASE_AUTH}"
            data = json.dumps(checkpoint).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=4):
                pass
            return True
        except Exception as e:
            print(f"[FIREBASE PUT session_phase ERR] {e}")

    return True

def fetch_session_phase_timeline(session_id: str) -> list:
    """Retrieves recorded phase checkpoints for a given session from Firebase."""
    if not session_id:
        return []
    try:
        url = f"{FIREBASE_HOST}/session_phases/{session_id}.json?auth={FIREBASE_AUTH}"
        req = urllib.request.Request(url, headers={"User-Agent": "PdM-SmartThings-Client"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data or not isinstance(data, dict):
                return []
            
            # Sort by timestamp
            timeline = []
            for k, v in data.items():
                if isinstance(v, dict):
                    ts = v.get("ts") or (int(k) if str(k).isdigit() else 0)
                    timeline.append({
                        "ts": ts,
                        "phase": v.get("phase", "none"),
                        "machine_state": v.get("machine_state", "run"),
                        "progress_pct": v.get("progress_pct", 0),
                        "target_rpm": v.get("target_rpm", 0)
                    })
            timeline.sort(key=lambda x: x["ts"])
            return timeline
    except Exception:
        return []

def estimate_point_phase_fallback(power_w: float, vibe_mag: float, audio_rms: float, t_ms: int, total_duration_ms: int = None, last_phase: str = "wash") -> str:
    """
    Intelligent physics-informed fallback when SmartThings API timeline is unrecorded.
    Uses mechanical kinematics, acoustic pressure, active electrical draw, and cycle progress.
    """
    vibe_diff = abs(vibe_mag - 9.81)

    # 1. Active heating wash element (1800-2000W)
    if power_w > 1500.0:
        return "wash"

    # 2. Spin cycle (high speed extraction: high vibration, acoustic roar > 350 RMS, or motor power > 300W)
    if vibe_mag > 10.8 or audio_rms > 350.0 or power_w > 300.0:
        return "spin"

    # 3. Drain pump (electric pump active 25-65W with stationary drum)
    if 25.0 <= power_w <= 65.0 and audio_rms < 150.0 and vibe_diff < 0.25:
        return "drain"

    # 4. Weight sensing (initial dry tumble inertia sensing in the first 2 minutes)
    if t_ms < 120000:
        return "weightSensing"

    # 5. Normal tumbling / agitation (detectable by power OR acoustic audio RMS OR drum oscillation)
    if power_w > 45.0 or audio_rms > 35.0 or vibe_diff > 0.15:
        if total_duration_ms and total_duration_ms > 0:
            return "wash" if t_ms < (total_duration_ms * 0.60) else "rinse"
        elif t_ms < 2400000:  # First 40 mins
            return "wash"
        else:
            return "rinse"

    # 6. Momentary tumble pause between drum reversals (3-5s soak pause)
    # If inside an active session, carry forward the ongoing phase instead of spurious 'none'
    if last_phase and last_phase not in ("none", "finish", "stop"):
        return last_phase

    return "none"

def compute_weight_and_class(rows: list, st_info: dict = None) -> tuple:
    """
    Computes standardized load class (LIGHT, MEDIUM, HEAVY) and estimated weight (kg)
    from Tapo P110 initial dry-tumble motor power inertia or SmartThings water level.
    Returns: (load_class: str, est_kg: float)
    """
    sensing_powers = []
    for r in rows[:30]:
        pwr = r.get("pwr") if "pwr" in r else r.get("power")
        if pwr is not None and 60.0 <= float(pwr) <= 350.0:
            sensing_powers.append(float(pwr))

    if sensing_powers:
        avg_sensing_w = sum(sensing_powers) / len(sensing_powers)
        est_kg = max(1.0, min(10.5, (avg_sensing_w - 70.0) / 15.0))
    else:
        wl = str((st_info.get("water_level") if st_info else "") or "").lower()
        if wl in ("low", "1"):
            avg_sensing_w, est_kg = 100.0, 2.5
        elif wl in ("high", "3"):
            avg_sensing_w, est_kg = 240.0, 8.0
        else:
            avg_sensing_w, est_kg = 160.0, 5.0

    if est_kg < 3.2 or avg_sensing_w < 120.0:
        load_class = "LIGHT"
    elif est_kg <= 6.8 or avg_sensing_w <= 220.0:
        load_class = "MEDIUM"
    else:
        load_class = "HEAVY"

    return load_class, round(est_kg, 1)
