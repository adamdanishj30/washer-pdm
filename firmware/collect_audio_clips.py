"""
collect_audio_clips.py
Collect short raw audio clips from the rig over the LOCAL network (no Firebase).

Why
---
Envelope analysis of bearing spall impacts (and the waveform-level fault
injection study in ml/waveform_fault_study.py) needs RAW audio, which is far
too large for Firebase (16 kHz x 2 B = 32 kB/s). Firmware 07 serves a live
clip at http://<rig>/clip.wav?sec=2. This script asks for one clip every
--every seconds while a wash session is running and saves it to

    data/audio_clips/<session_id>/<epoch_ms>_<phase>.wav

Cost: zero Firebase usage (LAN only). ~64 kB per clip; one clip per minute
for a 90-minute wash is ~6 MB of disk.

Usage
  py firmware/collect_audio_clips.py                      # rig at washer-pdm.local
  py firmware/collect_audio_clips.py --host 192.168.0.50 --every 60 --sec 2
"""

# =============================================================================
# SECTION 1: Imports & paths
# =============================================================================
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLIP_DIR = BASE_DIR / "data" / "audio_clips"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from firmware.smartthings_client import fetch_session_phase_timeline  # noqa: E402  (local file first)


def http_get(url: str, timeout: float) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "PdM-ClipCollector"}),
                                timeout=timeout) as r:
        return r.read()


# =============================================================================
# SECTION 2: Main loop
# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="Collect raw audio clips from firmware 07 over the LAN")
    ap.add_argument("--host", default="washer-pdm.local", help="rig hostname or IP")
    ap.add_argument("--every", type=float, default=60.0, help="seconds between clips while washing")
    ap.add_argument("--sec", type=int, default=2, help="clip length in seconds (firmware max 2)")
    a = ap.parse_args()
    base = f"http://{a.host}"
    print(f"[CLIPS] polling {base}/window.json; one {a.sec}s clip every {a.every:g}s while a session runs")

    while True:
        try:
            win = json.loads(http_get(f"{base}/window.json", 5))
            sid = win.get("session") or ""
            if sid:
                tl = fetch_session_phase_timeline(sid)
                phase = tl[-1]["phase"] if tl else "unknown"
                wav = http_get(f"{base}/clip.wav?sec={a.sec}", a.sec + 8)
                if wav[:4] == b"RIFF":
                    out = CLIP_DIR / sid
                    out.mkdir(parents=True, exist_ok=True)
                    f = out / f"{int(time.time() * 1000)}_{phase}.wav"
                    f.write_bytes(wav)
                    print(f"[CLIPS] saved {f.relative_to(BASE_DIR)} ({len(wav) // 1024} kB, phase={phase})")
            time.sleep(a.every if sid else 30)
        except KeyboardInterrupt:
            return
        except Exception as e:
            print(f"[CLIPS] rig not reachable ({e}); retrying in 30 s")
            time.sleep(30)


if __name__ == "__main__":
    main()
