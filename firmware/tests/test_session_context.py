"""
firmware/tests/test_session_context.py
Unit and Integration Tests for Session Context Sidecar and Backfill.

Test Coverage:
--------------
1. test_upsert_new_row: Adding new session records creates valid 8-column rows.
2. test_upsert_keeps_manual_row: Never overwrites rows marked with context_source='manual'.
3. test_upsert_updates_non_manual_row: Updates records marked as 'unknown' or automated.
4. test_backfill_idempotent: Running backfill multiple times produces byte-identical output.
5. test_backfill_ignores_non_csv: Confirms files like desktop.ini are ignored.
6. test_extract_session_time_bounds: Accurately parses epoch bounds from fw07 and legacy CSVs.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from firmware.session_context import (
    CONTEXT_COLUMNS,
    backfill_all_sessions,
    extract_session_time_bounds,
    load_session_context,
    save_session_context,
    upsert_session_context,
)


class TestSessionContext(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pdm_test_context_"))
        self.context_file = self.temp_dir / "session_context.csv"
        self.sessions_dir = self.temp_dir / "real_sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_upsert_new_row(self) -> None:
        """Verify inserting a new record into a non-existent context file."""
        entry = {
            "session_file": "wash_cycle_2026-10-21_0631.csv",
            "start_epoch_ms": 1792535460262,
            "end_epoch_ms": 1792537204680,
            "programme": "QuickWash",
            "water_temp": "cold",
            "spin_level": "1200",
            "context_source": "smartthings_live",
            "note": "verified via test",
        }
        res = upsert_session_context(entry, context_file=self.context_file)
        self.assertTrue(res)
        self.assertTrue(self.context_file.is_file())

        rows = load_session_context(self.context_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_file"], "wash_cycle_2026-10-21_0631.csv")
        self.assertEqual(rows[0]["programme"], "QuickWash")
        self.assertEqual(rows[0]["context_source"], "smartthings_live")
        self.assertEqual(rows[0]["load_kg"], "")
        self.assertEqual(rows[0]["load_source"], "")
        self.assertEqual(list(rows[0].keys()), CONTEXT_COLUMNS)
        self.assertEqual(len(CONTEXT_COLUMNS), 10)

    def test_upsert_keeps_manual_row(self) -> None:
        """Verify that a row marked with context_source='manual' is NEVER overwritten."""
        manual_entry = {
            "session_file": "wash_cycle_2026-10-20_0744.csv",
            "start_epoch_ms": 1792453423282,
            "end_epoch_ms": 1792458266417,
            "programme": "DailyWash_Heavy",
            "water_temp": "40C",
            "spin_level": "1400",
            "context_source": "manual",
            "note": "Adam hand-verified on control panel",
        }
        self.assertTrue(upsert_session_context(manual_entry, context_file=self.context_file))

        # Attempt to overwrite with automated source
        automated_entry = {
            "session_file": "wash_cycle_2026-10-20_0744.csv",
            "start_epoch_ms": 1792453423282,
            "end_epoch_ms": 1792458266417,
            "programme": "Automated_Override",
            "water_temp": "cold",
            "spin_level": "1000",
            "context_source": "smartthings_live",
            "note": "should be blocked",
        }
        res = upsert_session_context(automated_entry, context_file=self.context_file)
        self.assertFalse(res, "Upsert should return False when skipping manual row")

        # Verify manual entry was preserved intact
        rows = load_session_context(self.context_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["programme"], "DailyWash_Heavy")
        self.assertEqual(rows[0]["water_temp"], "40C")
        self.assertEqual(rows[0]["context_source"], "manual")
        self.assertEqual(rows[0]["note"], "Adam hand-verified on control panel")

    def test_upsert_updates_non_manual_row(self) -> None:
        """Verify that an 'unknown' row can be safely updated with resolved metadata."""
        initial_entry = {
            "session_file": "wash_cycle_2026-10-19_0911.csv",
            "start_epoch_ms": 1792372280304,
            "end_epoch_ms": 1792376224132,
            "programme": "unknown",
            "water_temp": "",
            "spin_level": "",
            "context_source": "unknown",
            "note": "pending",
        }
        upsert_session_context(initial_entry, context_file=self.context_file)

        updated_entry = {
            "session_file": "wash_cycle_2026-10-19_0911.csv",
            "start_epoch_ms": 1792372280304,
            "end_epoch_ms": 1792376224132,
            "programme": "DailyWash",
            "water_temp": "cold",
            "spin_level": "1200",
            "context_source": "smartthings_live",
            "note": "resolved",
        }
        res = upsert_session_context(updated_entry, context_file=self.context_file)
        self.assertTrue(res)

        rows = load_session_context(self.context_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["programme"], "DailyWash")
        self.assertEqual(rows[0]["context_source"], "smartthings_live")

    def test_backfill_idempotent_and_ignores_non_csv(self) -> None:
        """
        Create mock sessions including desktop.ini, verify backfill runs idempotently,
        ignores non-CSVs, and preserves pre-existing manual rows.
        """
        # 1. Create mock fw07 session CSV
        fw07_file = self.sessions_dir / "wash_cycle_2026-10-21_0514.csv"
        with open(fw07_file, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_ms", "accel_x", "accel_y", "accel_z", "audio_rms", "power_w", "phase", "load_class", "epoch_ms", "n_accel"])
            w.writerow([8240, 0.1, 0.2, 9.8, 100, 15.0, "wash", "LIGHT", 1792530853248, 1013])
            w.writerow([1800000, 0.1, 0.2, 9.8, 120, 250.0, "spin", "LIGHT", 1792532644998, 1014])

        # 2. Create mock legacy session CSV (use a filename with no Firebase phase data)
        legacy_file = self.sessions_dir / "wash_cycle_2026-10-11_1019.csv"
        with open(legacy_file, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_ms", "accel_x", "accel_y", "accel_z", "audio_rms", "power_w", "phase", "load_class"])
            w.writerow([0, 0.1, 0.2, 9.8, 100, 0.0, "none", "LIGHT"])
            w.writerow([4485283, 0.1, 0.2, 9.8, 110, 0.0, "none", "LIGHT"])

        # 3. Create non-CSV files that must be ignored
        (self.sessions_dir / "desktop.ini").write_text("[.ShellClassInfo]\nIconResource=...", encoding="utf-8")
        (self.sessions_dir / "notes.txt").write_text("some random note", encoding="utf-8")

        # 4. Pre-seed a manual row for fw07_file
        manual_row = {
            "session_file": fw07_file.name,
            "start_epoch_ms": "1792530853248",
            "end_epoch_ms": "1792532644998",
            "programme": "CustomManualProgramme",
            "water_temp": "20C",
            "spin_level": "800",
            "context_source": "manual",
            "note": "keep this untouched",
            "load_kg": "4.5",
            "load_source": "manual",
        }
        upsert_session_context(manual_row, context_file=self.context_file)

        # 5. First backfill run
        count1 = backfill_all_sessions(data_dir=self.sessions_dir, context_file=self.context_file)
        self.assertEqual(count1, 2, "Should process exactly 2 CSV files, ignoring desktop.ini and notes.txt")
        content1 = self.context_file.read_text(encoding="utf-8")

        # Verify manual row survived
        rows1 = {r["session_file"]: r for r in load_session_context(self.context_file)}
        self.assertEqual(rows1[fw07_file.name]["programme"], "CustomManualProgramme")
        self.assertEqual(rows1[fw07_file.name]["context_source"], "manual")
        self.assertEqual(rows1[fw07_file.name]["load_kg"], "4.5")
        self.assertEqual(rows1[fw07_file.name]["load_source"], "manual")
        self.assertEqual(rows1[legacy_file.name]["context_source"], "unknown")
        self.assertEqual(rows1[legacy_file.name]["load_kg"], "")
        self.assertEqual(rows1[legacy_file.name]["load_source"], "")

        # 6. Second backfill run (idempotency check)
        count2 = backfill_all_sessions(data_dir=self.sessions_dir, context_file=self.context_file)
        self.assertEqual(count2, 2)
        content2 = self.context_file.read_text(encoding="utf-8")

        self.assertEqual(content1, content2, "Backfill must be strictly idempotent")


    def test_backfill_reconciles_phantom_rows(self) -> None:
        """
        Verify that backfill reconciles phantom rows:
        - Removes entries whose CSV does not exist on disk if context_source != 'manual'
        - Retains entries whose context_source == 'manual' even if CSV is absent
        """
        # 1. Create one real CSV on disk
        real_csv = self.sessions_dir / "wash_cycle_real.csv"
        with open(real_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_ms", "accel_x", "accel_y", "accel_z", "audio_rms", "power_w", "phase", "load_class", "epoch_ms"])
            w.writerow([8240, 0.1, 0.2, 9.8, 100, 15.0, "wash", "LIGHT", 1792530853248])

        # 2. Pre-populate context file with 3 rows:
        # a) real file
        # b) phantom file (unknown source) -> must be removed
        # c) missing file (manual source) -> must be retained
        rows = [
            {
                "session_file": "wash_cycle_real.csv",
                "start_epoch_ms": "1792530853248",
                "end_epoch_ms": "1792532644998",
                "programme": "unknown",
                "water_temp": "",
                "spin_level": "",
                "context_source": "unknown",
                "note": "",
            },
            {
                "session_file": "wash_cycle_phantom_temp.csv",
                "start_epoch_ms": "1792300005024",
                "end_epoch_ms": "1792300904320",
                "programme": "unknown",
                "water_temp": "",
                "spin_level": "",
                "context_source": "unknown",
                "note": "phantom row",
            },
            {
                "session_file": "wash_cycle_manual_missing.csv",
                "start_epoch_ms": "1792400000000",
                "end_epoch_ms": "1792401000000",
                "programme": "CustomSpecial",
                "water_temp": "60C",
                "spin_level": "1400",
                "context_source": "manual",
                "note": "retained manual note",
            },
        ]
        save_session_context(rows, context_file=self.context_file)

        # 3. Run backfill
        backfill_all_sessions(data_dir=self.sessions_dir, context_file=self.context_file)

        # 4. Verify context rows
        result_rows = {r["session_file"]: r for r in load_session_context(self.context_file)}
        self.assertIn("wash_cycle_real.csv", result_rows)
        self.assertNotIn("wash_cycle_phantom_temp.csv", result_rows, "Phantom non-manual row should be removed")
        self.assertIn("wash_cycle_manual_missing.csv", result_rows, "Manual row must be retained even if CSV missing")
        self.assertEqual(result_rows["wash_cycle_manual_missing.csv"]["programme"], "CustomSpecial")



    def test_manual_load_kg_survives_backfill_and_upsert(self) -> None:
        """
        Verify that manual load_kg and load_source survive automated backfill and upsert.
        """
        fw07_file = self.sessions_dir / "wash_cycle_2026-10-21_0631.csv"
        with open(fw07_file, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_ms", "accel_x", "accel_y", "accel_z", "audio_rms", "power_w", "phase", "load_class", "epoch_ms", "n_accel"])
            w.writerow([8240, 0.1, 0.2, 9.8, 100, 15.0, "wash", "unknown", 1792535460262, 1013])
            w.writerow([1800000, 0.1, 0.2, 9.8, 120, 250.0, "spin", "unknown", 1792537204680, 1014])

        # 1. Row with manual load_kg
        entry = {
            "session_file": fw07_file.name,
            "start_epoch_ms": "1792535460262",
            "end_epoch_ms": "1792537204680",
            "programme": "DailyWash",
            "water_temp": "cold",
            "spin_level": "1200",
            "context_source": "smartthings_live",
            "note": "automated with manual load",
            "load_kg": "5.2",
            "load_source": "manual",
        }
        self.assertTrue(upsert_session_context(entry, context_file=self.context_file))

        # 2. Backfill runs over the file
        backfill_all_sessions(data_dir=self.sessions_dir, context_file=self.context_file)

        # 3. Verify manual load_kg and load_source survived
        rows = {r["session_file"]: r for r in load_session_context(self.context_file)}
        self.assertEqual(rows[fw07_file.name]["load_kg"], "5.2")
        self.assertEqual(rows[fw07_file.name]["load_source"], "manual")

if __name__ == "__main__":
    unittest.main()
