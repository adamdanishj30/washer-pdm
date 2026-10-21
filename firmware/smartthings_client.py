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
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SMARTTHINGS_PAT = os.getenv("SMARTTHINGS_PAT")
SMARTTHINGS_DEVICE_ID = os.getenv("SMARTTHINGS_DEVICE_ID")
SMARTTHINGS_CLIENT_ID = "d18cf96e-c626-4433-bf51-ddbb10c5d1ed"
SMARTTHINGS_REFRESH_URL = "https://auth-global.api.smartthings.com/oauth/token"
SMARTTHINGS_API_URL = "https://api.smartthings.com/v1"
# Store token cache strictly outside Google Drive sync folder to protect secrets
TOKEN_CACHE_FILE = Path(os.path.expandvars(r"%LOCALAPPDATA%\PdM_Washer\smartthings_token_cache.json"))

_last_st_call = 0.0
_cached_st_data = None
_auth_warning_logged = False


def _refresh_oauth_token(refresh_token: str) -> tuple[str | None, str | None, int]:
    """Attempt OAuth2 refresh against SmartThings endpoint. Returns (access_token, refresh_token, expires_in)."""
    try:
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "client_id": SMARTTHINGS_CLIENT_ID,
            "refresh_token": refresh_token
        }).encode("utf-8")
        req = urllib.request.Request(
            SMARTTHINGS_REFRESH_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("access_token"), data.get("refresh_token") or refresh_token, data.get("expires_in", 86400)
    except Exception as e:
        return None, None, 0


def get_valid_smartthings_token() -> str | None:
    """
    Retrieves or automatically refreshes the SmartThings OAuth2 access token.
    1. Checks local persistent token cache (.smartthings_token_cache.json)
    2. Checks CLI credentials (%LOCALAPPDATA%/@smartthings/cli/Data/credentials.json)
    3. Checks environment variable SMARTTHINGS_REFRESH_TOKEN (and caches rotated tokens)
    4. Fallbacks to SMARTTHINGS_PAT or SMARTTHINGS_ACCESS_TOKEN
    """
    import datetime as dt_mod

    # 1. Local persistent token cache (survives token rotation across daemon runs)
    if TOKEN_CACHE_FILE.is_file():
        try:
            with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            acc = cached.get("accessToken")
            ref = cached.get("refreshToken")
            exp_str = cached.get("expires")
            
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
            
            if ref:
                new_acc, new_ref, exp_in = _refresh_oauth_token(ref)
                if new_acc:
                    cached["accessToken"] = new_acc
                    cached["refreshToken"] = new_ref
                    cached["expires"] = (datetime.now(timezone.utc) + dt_mod.timedelta(seconds=exp_in)).isoformat().replace("+00:00", "Z")
                    TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as out_f:
                        json.dump(cached, out_f, indent=2)
                    return new_acc
        except Exception as e:
            print(f"[AUTH CACHE NOTICE] Token cache notice: {e}")

    # 2. SmartThings CLI credentials file
    cred_path = Path(os.path.expandvars(r"%LOCALAPPDATA%\@smartthings\cli\Data\credentials.json"))
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
            
            if ref:
                new_acc, new_ref, exp_in = _refresh_oauth_token(ref)
                if new_acc:
                    prof["accessToken"] = new_acc
                    prof["refreshToken"] = new_ref
                    prof["expires"] = (datetime.now(timezone.utc) + dt_mod.timedelta(seconds=exp_in)).isoformat().replace("+00:00", "Z")
                    creds["default:api.smartthings.com"] = prof
                    with open(cred_path, "w", encoding="utf-8") as out_f:
                        json.dump(creds, out_f, indent=4)
                    return new_acc
        except Exception as e:
            print(f"[AUTH CLI NOTICE] CLI token refresh notice: {e}")

    # 3. Environment variable refresh token (cache new rotation pair locally so it doesn't break)
    env_ref = os.getenv("SMARTTHINGS_REFRESH_TOKEN")
    if env_ref:
        new_acc, new_ref, exp_in = _refresh_oauth_token(env_ref)
        if new_acc:
            try:
                cache_data = {
                    "accessToken": new_acc,
                    "refreshToken": new_ref,
                    "expires": (datetime.now(timezone.utc) + dt_mod.timedelta(seconds=exp_in)).isoformat().replace("+00:00", "Z")
                }
                TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as out_f:
                    json.dump(cache_data, out_f, indent=2)
            except Exception:
                pass
            return new_acc

    # 4. Fallback: prioritize fresh SMARTTHINGS_PAT over static SMARTTHINGS_ACCESS_TOKEN
    return SMARTTHINGS_PAT or os.getenv("SMARTTHINGS_ACCESS_TOKEN")

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
    except urllib.error.HTTPError as e:
        global _auth_warning_logged
        if e.code == 401:
            if not _auth_warning_logged:
                print("[SMARTTHINGS AUTH 401] Token unauthorized/expired. (Samsung PATs expire in 24h per Dec 2024 policy). Falling back to power/vibration heuristics.")
                _auth_warning_logged = True
        else:
            print(f"[SMARTTHINGS CLIENT HTTP {e.code}] {e}")
        return {}
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

# -----------------------------------------------------------------------------
# Phase timeline storage
#   * Local copy: data/.phase_timelines/<session_id>.jsonl (one checkpoint per
#     line). The archiver reads this first, so it does NOT have to download
#     the timeline back from Firebase (saves Spark-plan download quota).
#   * Firebase copy: /session_phases/<session_id>/<ts> (for other machines
#     and the live dashboards), written with print=silent.
# -----------------------------------------------------------------------------
PHASE_DIR = BASE_DIR / "data" / ".phase_timelines"


def _local_timeline_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return PHASE_DIR / f"{safe}.jsonl"


def push_phase_to_firebase(st_data: dict, session_id: str = None) -> bool:
    """
    Mirrors live phase to Firebase /live_phase.json and, if a session is
    active, appends a checkpoint to /session_phases/{session_id}/{now_ms}
    AND to the local timeline file.
    """
    if not st_data:
        return False
    from firmware.firebase_rest import get_client   # local import avoids a cycle
    fb = get_client()
    now_ms = int(time.time() * 1000)

    # 1. Live phase (single small node, overwritten)
    try:
        fb.put("live_phase", st_data)
    except Exception as e:
        print(f"[FIREBASE PUT live_phase ERR] {e}")

    if not session_id:
        return True

    checkpoint = {
        "ts": now_ms,
        "phase": st_data.get("job_state", "none"),
        "machine_state": st_data.get("machine_state", "stop"),
        "progress_pct": st_data.get("progress_pct", 0),
        "remaining_mins": st_data.get("remaining_mins", 0),
        "target_rpm": st_data.get("target_rpm", 0),
        "cycle": st_data.get("cycle", "unknown"),
        "water_temp": st_data.get("water_temp", ""),
    }
    # 2. Local timeline (authoritative for archiving on this PC)
    try:
        PHASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_local_timeline_path(session_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(checkpoint) + "\n")
    except OSError as e:
        print(f"[PHASE LOCAL WRITE ERR] {e}")
    # 3. Firebase copy
    try:
        fb.put(f"session_phases/{session_id}/{now_ms}", checkpoint)
    except Exception as e:
        print(f"[FIREBASE PUT session_phase ERR] {e}")
    return True


def fetch_session_phase_timeline(session_id: str) -> list:
    """Phase checkpoints for a session: local file first, Firebase as fallback."""
    if not session_id:
        return []
    timeline = []
    local = _local_timeline_path(session_id)
    if local.is_file():
        try:
            for line in local.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    timeline.append(json.loads(line))
        except (OSError, ValueError):
            timeline = []
    if not timeline:
        try:
            from firmware.firebase_rest import get_client
            data = get_client().get(f"session_phases/{session_id}")
        except Exception:
            data = None
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    v = dict(v)
                    v["ts"] = v.get("ts") or (int(k) if str(k).isdigit() else 0)
                    timeline.append(v)
    # Build normalized output dictionary for each timeline checkpoint.
    # We preserve all existing keys ('ts', 'phase', 'machine_state', 'progress_pct', 'target_rpm')
    # and additively include 'cycle' (programme) and 'water_temp' to support session context tracking.
    out = [
        {
            "ts": c.get("ts", 0),
            "phase": c.get("phase", "none"),
            "machine_state": c.get("machine_state", "run"),
            "progress_pct": c.get("progress_pct", 0),
            "target_rpm": c.get("target_rpm", 0),
            "cycle": c.get("cycle", "unknown"),
            "water_temp": c.get("water_temp", ""),
        }
        for c in timeline
    ]
    out.sort(key=lambda x: x["ts"])
    return out


def estimate_point_phase_fallback(power_w: float, vibe_mag: float, audio_rms: float, t_ms: int, total_duration_ms: int = None, last_phase: str = "none") -> str:
    """
    Fallback phase tracker when SmartThings API timeline is unrecorded or not updating.
    Strictly avoids acoustic noise or arbitrary heuristic guessing to preserve ML ground truth integrity.

    Rules:
    1. Standby / Finished Check:
       If machine power is in standby (power_w <= 3.5W, or <= 6.0W with LCD on and stationary drum):
       - If preceded by an active cycle ('wash', 'rinse', 'spin', 'drain', 'weightSensing', 'finish'), mark 'finish'.
       - Otherwise, keep at 'none'.
    2. SmartThings not updating during an active cycle block:
       - Keep the before phase (last_phase) carried forward to the current block (LOCF).
    3. If SmartThings was not updating and no before phase exists:
       - Keep at 'none' (never invent synthetic phase labels using acoustics or heuristics).
    """
    vibe_diff = abs(vibe_mag - 9.81)

    # 1. Standby / Cycle Finished Check
    # Idle standby is ~1.0W - 1.3W (or <= 3.5W with dimming, up to 6.0W with LCD on) with stationary drum
    if (power_w <= 3.5 and (vibe_diff < 0.5 or vibe_mag < 10.3)) or \
       (power_w <= 6.0 and vibe_diff < 0.25 and last_phase in ("wash", "rinse", "spin", "drain", "weightSensing", "finish")):
        if last_phase in ("wash", "rinse", "spin", "drain", "weightSensing", "finish"):
            return "finish"
        return "none"

    # 2. SmartThings not updating during active block: keep before phase carried forward (LOCF)
    if last_phase and last_phase not in ("none", "finish", "stop", "offline", "unknown"):
        return last_phase

    # 3. If SmartThings is not updating and no before phase exists, keep at 'none'
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
