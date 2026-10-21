"""
test_daemon_offline.py - simulates Firebase in memory and checks that the
archive daemon (a) never downloads already-archived or still-running
sessions, (b) archives finished v3 sessions once, (c) never overwrites
existing CSVs.   Run:  py firmware/tests/test_daemon_offline.py
"""
# =============================================================================
# SECTION 1: Fake Firebase
# =============================================================================
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class FakeFB:
    def __init__(self, db):
        self.db, self.gets = db, []

    def _node(self, path):
        cur = self.db
        for p in path.strip("/").split("/"):
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    def get(self, path, shallow=False, **_):
        self.gets.append(path + ("?shallow" if shallow else ""))
        n = self._node(path)
        return {k: True for k in n} if (shallow and isinstance(n, dict)) else n

    def patch(self, path, value):
        cur = self.db
        for p in path.strip("/").split("/"):
            cur = cur.setdefault(p, {})
        cur.update(value)

    def put(self, path, value):
        pass

    def delete(self, path):
        parts = path.strip("/").split("/")
        self._node("/".join(parts[:-1])).pop(parts[-1], None)

    def record_usage(self):
        pass


# =============================================================================
# SECTION 2: Test
# =============================================================================
def main() -> int:
    import firmware.auto_drive_sync_daemon as d
    import firmware.session_export as se
    import firmware.smartthings_client as stc
    from firmware.tests.test_session_export import v3_window

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # redirect every output location into the temp dir
        se.REAL_DIR, se.TEST_DIR = td / "real", td / "test"
        d.SYNC_HISTORY_FILE = td / "hist.json"
        d.DATA_DIR = td
        stc.PHASE_DIR = td / "phases"
        import firmware.session_context as sc
        orig_context_file = sc.DEFAULT_CONTEXT_FILE
        orig_real_dir = sc.REAL_SESSIONS_DIR
        try:
            sc.DEFAULT_CONTEXT_FILE = td / "session_context.csv"
            sc.REAL_SESSIONS_DIR = td / "real"
            d.get_smartthings_status = lambda **_: {}
            d.rebuild_derived = lambda: None

            e0 = 1_792_300_000_000
            db = {
                "live": {"fw": "07.0.0", "session": "wash_2026-10-21_090000", "active": True, "uptime": 1, "cnt": 1},
                "sessions": {
                    "wash_old_legacy": {"1": {"t": 1, "ax": 0, "ay": 0, "az": 9.8, "rms": 1}},
                    "wash_2026-10-20_081500": {f"w{i:06d}": v3_window(i, e0) for i in range(1, 181)},
                    "wash_2026-10-21_090000": {f"w{i:06d}": v3_window(i, e0) for i in range(1, 50)},
                    "wash_2026-10-19_070000": {f"w{i:06d}": v3_window(i, e0) for i in range(1, 181)},
                },
                "session_meta": {
                    "wash_2026-10-20_081500": {"start": 1, "end": 2},
                    "wash_2026-10-21_090000": {"start": 3},            # still running
                    "wash_2026-10-19_070000": {"start": 1, "end": 2},
                },
            }
            fake = FakeFB(db)
            d.get_client = lambda: fake
            hist = {"wash_old_legacy": {"completed": True}}
            # pre-existing CSV for the 19 Oct session must NOT be overwritten
            (se.REAL_DIR).mkdir(parents=True)
            existing = se.REAL_DIR / "wash_cycle_2026-10-19_0700.csv"
            existing.write_text("keep me\n")

            n = d.scan_unarchived(hist, active_sid="wash_2026-10-21_090000", prune=True)
            downloads = [g for g in fake.gets if g.startswith("sessions/")]
            assert downloads == ["sessions/wash_2026-10-19_070000", "sessions/wash_2026-10-20_081500"], downloads
            assert n == 1, n
            assert existing.read_text() == "keep me\n", "existing CSV was overwritten!"
            assert (se.REAL_DIR / "wash_cycle_2026-10-20_0815.csv").is_file()
            assert db["session_meta"]["wash_2026-10-20_081500"]["archived"] is True
            assert "wash_2026-10-20_081500" not in db["sessions"], "prune should delete verified session"
            assert "wash_2026-10-21_090000" in db["sessions"], "running session must be untouched"

            fake.gets.clear()
            n2 = d.scan_unarchived(hist, active_sid=None, prune=False)
            assert not [g for g in fake.gets if g.startswith("sessions/") and "shallow" not in g], fake.gets
            assert n2 == 0
            print("[PASS] daemon downloads only finished, unarchived sessions; never overwrites; prune verified")
        finally:
            sc.DEFAULT_CONTEXT_FILE = orig_context_file
            sc.REAL_SESSIONS_DIR = orig_real_dir
    return 0


if __name__ == "__main__":
    sys.exit(main())
