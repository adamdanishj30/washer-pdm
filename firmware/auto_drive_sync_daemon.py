"""
auto_drive_sync_daemon.py
Autonomous Firebase -> local CSV archiver for the Washer PdM rig (v2, quota-aware).

What it does
------------
1. Polls /live.json (small) every --interval seconds while a wash runs
   (4x less often, max 2 min, while idle) over ONE keep-alive connection to
   learn whether the rig is online and which session is open.
2. While a wash session is open, polls SmartThings every 30 s and records the
   phase checkpoints locally + in Firebase (smartthings_client).
3. Archives a session ONCE, when it is finished:
     * firmware 07 : /session_meta/<sid>/end exists (rig closed the session),
                     or the rig moved on to another session id;
     * firmware 05/06 (legacy): the rig stopped updating /live for --timeout s.
   "Archive" = download /sessions/<sid> one time, write the CSV via
   session_export.py, mark /session_meta/<sid>/archived.
4. Never re-downloads sessions already listed in data/.sync_history.json
   (the old daemon downloaded EVERY session on start-up and after every cycle).
5. Optional --prune-archived: delete archived sessions from Firebase after the
   CSV is verified on disk (keeps the 1 GB Spark storage cap far away).

Firebase cost (rough, see firmware/07_feature_streamer/README.md):
   polling /live every 30 s with keep-alive  ~ 1-2 MB/day
   archiving one ~90 min v3 session          ~ 0.6 MB once

Usage
-----
  py firmware/auto_drive_sync_daemon.py                 # run forever
  py firmware/auto_drive_sync_daemon.py --once          # archive finished sessions, exit
  py firmware/auto_drive_sync_daemon.py --prune-archived
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & paths
# =============================================================================
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SYNC_HISTORY_FILE = DATA_DIR / ".sync_history.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from firmware.firebase_rest import FirebaseAuthError, get_client  # noqa: E402
from firmware.session_export import (batches_to_rows, export_session_to_csv,  # noqa: E402
                                     first_epoch_ms, target_path)
from firmware.smartthings_client import get_smartthings_status, push_phase_to_firebase  # noqa: E402

END_GRACE_S = 60             # wait after a session END marker before downloading
META_SCAN_EVERY_S = 1800     # how often to look for finished-but-unarchived sessions


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


# =============================================================================
# SECTION 2: Sync history (what is already on disk)
# =============================================================================
def load_history() -> Dict[str, Any]:
    if SYNC_HISTORY_FILE.is_file():
        try:
            return json.loads(SYNC_HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {}


def save_history(h: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SYNC_HISTORY_FILE.write_text(json.dumps(h, indent=2), encoding="utf-8")


def is_archived(h: Dict[str, Any], sid: str) -> bool:
    return bool(h.get(sid, {}).get("completed"))


# =============================================================================
# SECTION 3: Archive one session
# =============================================================================
def archive_session(sid: str, history: Dict[str, Any], prune: bool = False,
                    overwrite: bool = False) -> bool:
    """Download a finished session once, write CSV, record it. True on success."""
    fb = get_client()
    print(f"\n[{now_str()}] [ARCHIVE] downloading session '{sid}' ...")
    batches = fb.get(f"sessions/{sid}")
    rows = batches_to_rows(batches)
    if not rows:
        print("  [SKIP] no records")
        return False
    # Never overwrite a CSV that already exists but is missing from the
    # history (e.g. archived by an older script): adopt it instead.
    planned = target_path(sid, rows)
    if planned.exists() and not overwrite:
        print(f"  [KEEP] {planned.name} already exists - recording it as archived, not overwriting")
        history[sid] = {"completed": True, "file": planned.name, "folder": planned.parent.name,
                        "synced_at": datetime.now().isoformat(timespec="seconds"),
                        "points": len(rows), "note": "adopted existing file"}
        save_history(history)
        return False
    st = get_smartthings_status(min_interval_s=60.0)
    path = export_session_to_csv(sid, batches, st_info=st, out_path=planned)
    if not path:
        history[sid] = {
            "completed": True,
            "discarded": True,
            "points": len(rows),
            "synced_at": datetime.now().isoformat(timespec="seconds"),
            "note": f"discarded (< 3 records: {len(rows)})"
        }
        save_history(history)
        return False
    history[sid] = {
        "completed": True,
        "file": path.name,
        "folder": path.parent.name,
        "synced_at": datetime.now().isoformat(timespec="seconds"),
        "points": len(rows),
        "first_ts": first_epoch_ms(rows),
        "last_t": rows[-1].get("t", 0),
        "schema": 3 if any("aku" in r for r in rows[:5]) else 1,
    }
    save_history(history)

    # Record wash programme context into sidecar data/session_context.csv for
    # firmware-07 sessions (schema 3). Never let context failure abort or fail archiving.
    if history[sid].get("schema") == 3:
        try:
            from firmware.session_context import resolve_context_for_session, upsert_session_context
            target_context = DATA_DIR / "session_context.csv"
            ctx = resolve_context_for_session(path.name, session_id=sid, csv_path=path, context_file=target_context)
            upsert_session_context(ctx, context_file=target_context)
            print(f"  [CONTEXT] recorded session context: {ctx.get('programme', 'unknown')} ({ctx.get('context_source', 'unknown')})")
        except Exception as ctx_err:
            print(f"  [WARN] could not record session context: {ctx_err}")
    try:
        fb.patch(f"session_meta/{sid}", {"archived": True,
                                         "archived_at": datetime.now().isoformat(timespec="seconds"),
                                         "archived_file": path.name})
    except Exception as e:
        print(f"  [WARN] could not mark archived in Firebase: {e}")

    if prune:
        # Only delete after the CSV exists and has the expected number of lines.
        n_lines = sum(1 for _ in open(path, encoding="utf-8")) - 1
        if n_lines == len(rows):
            fb.delete(f"sessions/{sid}")
            print(f"  [PRUNE] deleted /sessions/{sid} from Firebase ({n_lines} rows verified on disk)")
        else:
            print(f"  [PRUNE] skipped: CSV has {n_lines} rows, Firebase had {len(rows)}")
    fb.record_usage()
    return True


def rebuild_derived() -> None:
    """Dashboards + legacy standardized dataset (unchanged behaviour)."""
    for script in (BASE_DIR / "build_clean_dashboard.py", BASE_DIR / "firmware" / "pdm_ml_standardizer.py"):
        if script.is_file():
            try:
                subprocess.run([sys.executable, str(script)], cwd=str(BASE_DIR), check=True)
            except Exception as e:
                print(f"  [WARN] {script.name} failed: {e}")


# =============================================================================
# SECTION 4: Find finished sessions that are not archived yet
# =============================================================================
def scan_unarchived(history: Dict[str, Any], active_sid: Optional[str], prune: bool) -> int:
    """
    Cheap scan: shallow key lists only (no session data downloaded unless a
    session is finished AND missing from the local history).
    """
    fb = get_client()
    meta = fb.get("session_meta") or {}               # small: one dict per v3 session
    keys = fb.get("sessions", shallow=True) or {}     # just the session ids
    done = 0
    for sid in sorted(keys):
        if sid == active_sid or is_archived(history, sid):
            continue
        m = meta.get(sid) if isinstance(meta, dict) else None
        if isinstance(m, dict):
            if not m.get("end"):
                continue                               # v3 session still open (or rig died mid-run)
        # legacy sessions (no meta) are only archived when not the active one
        if archive_session(sid, history, prune):
            done += 1
    return done


# =============================================================================
# SECTION 5: Main loop
# =============================================================================
def run(poll_s: int, offline_timeout_s: int, once: bool, prune: bool) -> None:
    fb = get_client()
    history = load_history()
    print("=" * 70)
    print(" Washer PdM archive daemon v2 (quota-aware)")
    print(f" poll {poll_s}s | legacy offline timeout {offline_timeout_s}s | prune={prune}")
    print("=" * 70)

    live0 = fb.get("live") or {}
    n = scan_unarchived(history, live0.get("session") if live0.get("active", True) else None, prune)
    print(f"[{now_str()}] initial scan archived {n} session(s)")
    if n:
        rebuild_derived()
    if once:
        fb.record_usage()
        return

    tracked_sid: Optional[str] = None     # session currently open on the rig
    last_change = time.time()
    last_sig = None
    last_st_poll = 0.0
    last_scan = time.time()
    end_seen_at: Dict[str, float] = {}

    while True:
        try:
            live = fb.get("live") or {}
            sig = (live.get("uptime"), live.get("cnt"))
            if sig != last_sig:
                last_sig, last_change = sig, time.time()
            online = (time.time() - last_change) < offline_timeout_s
            is_v3 = str(live.get("fw", "")).startswith("07")
            live_sid = live.get("session") or None
            if is_v3 and not live.get("active"):
                live_sid = None

            # --- 5a: session open -> keep SmartThings phases flowing ---
            if live_sid and online and time.time() - last_st_poll >= 30:
                st = get_smartthings_status(min_interval_s=30.0)
                if st:
                    push_phase_to_firebase(st, session_id=live_sid)
                last_st_poll = time.time()

            # --- 5b: detect the end of the tracked session ---
            if tracked_sid and tracked_sid != live_sid:
                end_seen_at.setdefault(tracked_sid, time.time())
                print(f"[{now_str()}] session '{tracked_sid}' ended ({'rig offline' if not online else 'closed by rig'})")
                tracked_sid = None
            if live_sid and online:
                if tracked_sid != live_sid:
                    print(f"[{now_str()}] rig running session '{live_sid}' (fw {live.get('fw', '05/06')})")
                tracked_sid = live_sid
            if tracked_sid and not online and not is_v3:
                end_seen_at.setdefault(tracked_sid, time.time())     # legacy: offline == finished
                tracked_sid = None

            # --- 5c: archive sessions whose end is older than the grace period ---
            archived_any = False
            for sid, t_end in list(end_seen_at.items()):
                if time.time() - t_end < END_GRACE_S:
                    continue
                if not is_archived(history, sid) and archive_session(sid, history, prune):
                    archived_any = True
                end_seen_at.pop(sid, None)

            # --- 5d: periodic safety scan (e.g. daemon was off during a wash) ---
            if time.time() - last_scan > META_SCAN_EVERY_S:
                last_scan = time.time()
                if scan_unarchived(history, tracked_sid, prune):
                    archived_any = True
            if archived_any:
                rebuild_derived()
            fb.record_usage()
        except FirebaseAuthError as e:
            print(f"[{now_str()}] [AUTH] {e}\n  -> fix FIREBASE_AUTH in .env; sleeping 10 min instead of hammering Firebase")
            time.sleep(600)
        except Exception as e:
            print(f"[{now_str()}] [LOOP NOTICE] {e}")
        # idle -> poll 4x less often (max 2 min); a wash is detected within ~2 min anyway
        time.sleep(poll_s if tracked_sid else min(4 * poll_s, 120))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Washer PdM Firebase -> CSV archive daemon (quota-aware)")
    ap.add_argument("--interval", type=int, default=30, help="poll /live every N s (default 30)")
    ap.add_argument("--timeout", type=int, default=150,
                    help="legacy firmware: seconds without /live updates = rig offline (default 150)")
    ap.add_argument("--once", action="store_true", help="archive finished sessions and exit")
    ap.add_argument("--prune-archived", action="store_true",
                    help="delete a session from Firebase after its CSV is verified on disk")
    a = ap.parse_args()
    run(a.interval, a.timeout, a.once, a.prune_archived)
