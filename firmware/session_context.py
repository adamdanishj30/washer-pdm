"""
firmware/session_context.py
Session Context Sidecar Manager for Washer PdM Project.

Purpose:
--------
Firmware-07 wash cycles vary in length and electrical profile because they run
different wash programmes (e.g. Quick Wash ~21 min vs Daily Wash ~70 min), not
because sensor capture is erratic.

This module maintains a sidecar metadata registry in `data/session_context.csv`
recording each wash session's:
  - session_file: filename (e.g. wash_cycle_2026-10-21_0631.csv)
  - start_epoch_ms: Unix millisecond timestamp at session start
  - end_epoch_ms: Unix millisecond timestamp at session end
  - programme: wash programme name from SmartThings (e.g. DailyWash, QuickWash)
  - water_temp: water temperature setting (e.g. cold, 40C)
  - spin_level: spin speed setting or target RPM (e.g. 1200, 1400)
  - context_source: 'smartthings_live', 'smartthings_history', 'manual', or 'unknown'
  - note: optional human or system annotation
  - load_kg: measured dry laundry mass in kg (empty if unmeasured, never guessed)
  - load_source: 'manual', 'smartthings', or empty

Golden Invariants:
------------------
1. Original session files in `data/real_sessions/*.csv` are NEVER modified in place.
2. If a row in `data/session_context.csv` has `context_source == 'manual'`, it is
   NEVER overwritten by automated archivers or backfills (Adam's manual notes win).
3. The schema has exactly the 10 standard columns above.
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports and Directory Constants
# =============================================================================
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Project root setup
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REAL_SESSIONS_DIR = DATA_DIR / "real_sessions"
DEFAULT_CONTEXT_FILE = DATA_DIR / "session_context.csv"
SYNC_HISTORY_FILE = DATA_DIR / ".sync_history.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Standard columns required by PLAN.md
CONTEXT_COLUMNS = [
    "session_file",
    "start_epoch_ms",
    "end_epoch_ms",
    "programme",
    "water_temp",
    "spin_level",
    "context_source",
    "note",
    "load_kg",
    "load_source",
]

# Valid sources for measured laundry load
VALID_LOAD_SOURCES = {
    "manual",
    "smartthings",
    "",
}

# Valid sources for context data
VALID_SOURCES = {
    "smartthings_live",
    "smartthings_history",
    "manual",
    "unknown",
}


# =============================================================================
# SECTION 2: CSV Persistence (Load, Save, and Upsert)
# =============================================================================
def load_session_context(context_file: Optional[Path] = None) -> List[Dict[str, str]]:
    """
    Load all existing context rows from the sidecar CSV file.
    Returns an empty list if the file does not exist yet.
    """
    target = context_file or DEFAULT_CONTEXT_FILE
    if not target.is_file():
        return []

    rows: List[Dict[str, str]] = []
    try:
        with open(target, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Ensure all expected columns exist in each record
                row_clean = {col: str(r.get(col, "") or "").strip() for col in CONTEXT_COLUMNS}
                rows.append(row_clean)
    except (OSError, csv.Error) as err:
        print(f"[SESSION CONTEXT] Warning reading {target.name}: {err}")
        return []

    return rows


def save_session_context(rows: List[Dict[str, str]], context_file: Optional[Path] = None) -> None:
    """
    Write all context rows to the sidecar CSV file in chronological order.
    Creates parent directories if necessary.
    """
    target = context_file or DEFAULT_CONTEXT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    # Sort rows chronologically by start_epoch_ms (numeric if possible), then filename
    def sort_key(item: Dict[str, str]) -> Tuple[int, str]:
        start_str = item.get("start_epoch_ms", "")
        try:
            start_num = int(float(start_str))
        except (ValueError, TypeError):
            start_num = 0
        return (start_num, item.get("session_file", ""))

    sorted_rows = sorted(rows, key=sort_key)

    with open(target, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CONTEXT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for r in sorted_rows:
            # Ensure every column is filled and formatted
            out_row = {col: str(r.get(col, "") or "") for col in CONTEXT_COLUMNS}
            writer.writerow(out_row)


def upsert_session_context(
    new_entry: Dict[str, Any],
    context_file: Optional[Path] = None,
) -> bool:
    """
    Upsert a session context row by 'session_file'.

    Rules:
    - If a record with this 'session_file' does not exist, insert it.
    - If it already exists and has `context_source == 'manual'`, do NOT overwrite.
      Return False and preserve the manual record intact.
    - If it already exists with any other source, update it with new_entry.
    - Return True if inserted or updated, False if skipped.
    """
    session_file = str(new_entry.get("session_file", "")).strip()
    if not session_file:
        print("[SESSION CONTEXT] Error: session_file is required for upsert.")
        return False

    existing_rows = load_session_context(context_file)
    updated = False
    row_found = False

    cleaned_entry = {
        "session_file": session_file,
        "start_epoch_ms": str(new_entry.get("start_epoch_ms", "") or ""),
        "end_epoch_ms": str(new_entry.get("end_epoch_ms", "") or ""),
        "programme": str(new_entry.get("programme", "unknown") or "unknown"),
        "water_temp": str(new_entry.get("water_temp", "") or ""),
        "spin_level": str(new_entry.get("spin_level", "") or ""),
        "context_source": str(new_entry.get("context_source", "unknown") or "unknown"),
        "note": str(new_entry.get("note", "") or ""),
        "load_kg": str(new_entry.get("load_kg", "") or ""),
        "load_source": str(new_entry.get("load_source", "") or ""),
    }

    # Verify source validity
    if cleaned_entry["context_source"] not in VALID_SOURCES:
        cleaned_entry["context_source"] = "unknown"
    if cleaned_entry["load_source"] not in VALID_LOAD_SOURCES:
        cleaned_entry["load_source"] = ""

    for i, r in enumerate(existing_rows):
        if r.get("session_file") == session_file:
            row_found = True
            # Invariant: NEVER overwrite a manual record with automated metadata
            if r.get("context_source") == "manual":
                print(f"  [SESSION CONTEXT] Keeping manual record for {session_file} (not overwriting)")
                return False

            # Invariant: Preserve manual load entries when automated backfill runs
            if r.get("load_source") == "manual" and cleaned_entry["load_source"] != "manual":
                cleaned_entry["load_kg"] = r.get("load_kg", "")
                cleaned_entry["load_source"] = "manual"
            elif r.get("load_kg") and not cleaned_entry["load_kg"]:
                cleaned_entry["load_kg"] = r.get("load_kg", "")
                cleaned_entry["load_source"] = r.get("load_source", "")

            # Update existing non-manual record
            existing_rows[i] = cleaned_entry
            updated = True
            break

    if not row_found:
        existing_rows.append(cleaned_entry)
        updated = True

    if updated:
        save_session_context(existing_rows, context_file)

    return True


# =============================================================================
# SECTION 3: Session File Metadata Extraction
# =============================================================================
def extract_session_time_bounds(csv_path: Path) -> Tuple[int, int]:
    """
    Read first and last data rows of a session CSV to determine start_epoch_ms and end_epoch_ms.

    Handles two file schemas:
    1. Firmware 07 (V3): contains the 'epoch_ms' column directly.
    2. Legacy (Firmware 05/06):
       - If 'timestamp_ms' > 1.7e12, it is already an epoch millisecond timestamp.
       - Otherwise, 'timestamp_ms' is relative to boot/cycle start. In this case,
         parse the base datetime from the filename (e.g. wash_cycle_YYYY-MM-DD_HHMM.csv)
         and add the relative millisecond offset.
    """
    if not csv_path.is_file():
        return (0, 0)

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return (0, 0)

            first_row = next(reader, None)
            if not first_row:
                return (0, 0)

            last_row = first_row
            for row in reader:
                if row:
                    last_row = row

        # Case 1: Firmware 07 contains explicit 'epoch_ms'
        if "epoch_ms" in header:
            idx = header.index("epoch_ms")
            start_ms = int(float(first_row[idx]))
            end_ms = int(float(last_row[idx]))
            return (start_ms, end_ms)

        # Case 2: Legacy files
        if "timestamp_ms" in header:
            idx = header.index("timestamp_ms")
            t0 = float(first_row[idx])
            t1 = float(last_row[idx])

            # Absolute epoch timestamp
            if t0 > 1_700_000_000_000:
                return (int(t0), int(t1))

            # Relative timestamp: estimate base from filename
            fname = csv_path.stem  # e.g. wash_cycle_2026-10-15_1020
            parts = fname.split("_")
            # Expected pattern: ['wash', 'cycle', 'YYYY-MM-DD', 'HHMM']
            if len(parts) >= 4:
                date_str = parts[2]
                time_str = parts[3]
                if time_str.isdigit() and len(time_str) == 4:
                    dt = datetime.strptime(f"{date_str}_{time_str}", "%Y-%m-%d_%H%M")
                else:
                    dt = datetime.strptime(f"{date_str}_0800", "%Y-%m-%d_%H%M")
                base_epoch_ms = int(dt.timestamp() * 1000)
                return (int(base_epoch_ms + t0), int(base_epoch_ms + t1))

    except Exception as e:
        print(f"[SESSION CONTEXT] Error parsing time bounds for {csv_path.name}: {e}")

    return (0, 0)


# =============================================================================
# SECTION 4: Context Resolution & Live Timeline Matching
# =============================================================================
def find_session_id_for_file(session_file: str) -> Optional[str]:
    """
    Reverse-map session filename to session_id using data/.sync_history.json.
    """
    if SYNC_HISTORY_FILE.is_file():
        try:
            history = json.loads(SYNC_HISTORY_FILE.read_text(encoding="utf-8"))
            for sid, meta in history.items():
                if isinstance(meta, dict) and meta.get("file") == session_file:
                    return sid
        except Exception:
            pass
    return None


def resolve_context_for_session(
    session_file: str,
    session_id: Optional[str] = None,
    csv_path: Optional[Path] = None,
    context_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Determine wash programme context for a session:
    1. If the row already exists and context_source is not 'unknown', return existing row
       (ensures at most one history/network lookup per session).
    2. Try live SmartThings timeline (via smartthings_client).
    3. If not found, mark context_source = 'unknown' (step 1 probe returned 403).
    """
    existing_rows = {r["session_file"]: r for r in load_session_context(context_file)}
    existing_entry = existing_rows.get(session_file, {})
    if session_file in existing_rows:
        curr = existing_rows[session_file]
        # If context is already resolved or manual, return it directly
        if curr.get("context_source") and curr.get("context_source") != "unknown":
            return curr

    sid = session_id or find_session_id_for_file(session_file)

    programme = "unknown"
    water_temp = ""
    spin_level = ""
    source = "unknown"
    note = ""
    # Retain existing load values if present; never guess kg
    load_kg = existing_entry.get("load_kg", "")
    load_source = existing_entry.get("load_source", "")

    # Attempt to query live SmartThings timeline if session_id is available
    if sid:
        try:
            from firmware.smartthings_client import fetch_session_phase_timeline
            timeline = fetch_session_phase_timeline(sid)
            for item in timeline:
                c = item.get("cycle")
                if c and c != "unknown":
                    programme = c
                    source = "smartthings_live"
                wt = item.get("water_temp")
                if wt:
                    water_temp = wt
                tgt_rpm = item.get("target_rpm")
                if tgt_rpm and tgt_rpm > 0:
                    spin_level = str(tgt_rpm)
        except Exception as e:
            note = f"timeline query error: {e}"

    # Minor rule: If programme is unknown but water_temp or spin_level was retrieved
    # from the live timeline, attribute context_source to smartthings_live with note.
    if programme == "unknown" and (water_temp or spin_level):
        source = "smartthings_live"
        note = "partial: no programme"

    # Calculate start and end epoch
    path_to_check = csv_path or (REAL_SESSIONS_DIR / session_file)
    start_ms, end_ms = extract_session_time_bounds(path_to_check)

    return {
        "session_file": session_file,
        "start_epoch_ms": start_ms,
        "end_epoch_ms": end_ms,
        "programme": programme,
        "water_temp": water_temp,
        "spin_level": spin_level,
        "context_source": source,
        "note": note,
        "load_kg": load_kg,
        "load_source": load_source,
    }


# =============================================================================
# SECTION 5: Backfill Command
# =============================================================================
def backfill_all_sessions(
    data_dir: Optional[Path] = None,
    context_file: Optional[Path] = None,
) -> int:
    """
    Scan all session CSVs in data/real_sessions/ (strictly ignoring non-CSV files
    such as desktop.ini), determine context, and upsert into session_context.csv.
    Preserves existing 'manual' rows without overwriting them.
    """
    target_dir = data_dir or REAL_SESSIONS_DIR
    target_context = context_file or DEFAULT_CONTEXT_FILE

    if not target_dir.is_dir():
        print(f"[SESSION CONTEXT] Error: sessions directory {target_dir} does not exist.")
        return 0

    # Collect only .csv files, explicitly ignoring desktop.ini or temporary files
    csv_files = sorted([f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() == ".csv"])
    valid_files = {f.name for f in csv_files}

    # Reconcile sidecar against existing files:
    # Any row in session_context.csv whose session_file does not exist on disk is removed,
    # UNLESS context_source == 'manual' (which is preserved with a warning).
    existing_rows = load_session_context(target_context)
    if existing_rows:
        reconciled_rows = []
        for r in existing_rows:
            sf = r.get("session_file")
            if sf in valid_files:
                reconciled_rows.append(r)
            else:
                if r.get("context_source") == "manual":
                    print(f"  [SESSION CONTEXT] Warning: manual record for {sf} retained but file is missing from {target_dir.name}")
                    reconciled_rows.append(r)
                else:
                    print(f"  [SESSION CONTEXT] Reconciling: removing phantom session {sf}")
        save_session_context(reconciled_rows, target_context)

    print(f"[SESSION CONTEXT] Backfilling context for {len(csv_files)} sessions from {target_dir.name}...")
    processed = 0

    for f in csv_files:
        ctx = resolve_context_for_session(f.name, csv_path=f, context_file=target_context)
        upsert_session_context(ctx, context_file=target_context)
        processed += 1

    print(f"[SESSION CONTEXT] Successfully processed {processed} session(s) into {target_context.name}.")
    return processed


# =============================================================================
# SECTION 6: CLI Entrypoint
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Manage wash session context sidecar metadata.")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Scan data/real_sessions/*.csv and backfill data/session_context.csv",
    )
    parser.add_argument(
        "--context-file",
        type=str,
        default=None,
        help="Custom path to session_context.csv (for testing)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Custom path to real_sessions folder (for testing)",
    )

    args = parser.parse_args()

    ctx_path = Path(args.context_file) if args.context_file else None
    dir_path = Path(args.data_dir) if args.data_dir else None

    if args.backfill:
        count = backfill_all_sessions(data_dir=dir_path, context_file=ctx_path)
        print(f"Backfill complete: {count} sessions registered.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
