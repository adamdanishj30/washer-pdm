"""
test_server.py
The MCP wrapper on SYNTHETIC washes, in-process (no subprocess, no network):
exactly the six registry tools are listed with their schemas, every tool is
read-only, list_washes answers with text and render_plot with an image.

Run:  python -m pytest apex_lens/tests -q
"""
import sys
from pathlib import Path

import anyio
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

pytest.importorskip("mcp")
from mcp import Client  # noqa: E402

from apex_lens.registry import TOOLS  # noqa: E402
from apex_lens.server import build_server  # noqa: E402
from apex_lens.store import WashStore  # noqa: E402
from apex_lens.tools import ApexLens  # noqa: E402
from ml.tests.test_pipeline_synthetic import make_cycle  # noqa: E402


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    d = tmp_path_factory.mktemp("washes")
    for i in range(5):
        make_cycle(400 + i).to_csv(d / f"wash_cycle_2026-12-0{i + 1}_0800.csv", index=False)
    return build_server(ApexLens(WashStore.from_dir(d)))


def test_server_lists_and_calls_tools(server):
    async def go():
        async with Client(server) as c:
            listed = (await c.list_tools()).tools
            assert [t.name for t in listed] == [t["name"] for t in TOOLS]
            for t, spec in zip(listed, TOOLS):
                assert t.input_schema == spec["input_schema"]
                assert t.annotations.read_only_hint is True and t.annotations.destructive_hint is False

            r = await c.call_tool("list_washes", {})
            assert not r.is_error and r.content[0].type == "text" and "2026-12-01_0800" in r.content[0].text

            r = await c.call_tool("render_plot", {"wash_id": "2026-12-01_0800", "kind": "bands"})
            kinds = [x.type for x in r.content]
            assert kinds == ["text", "image"] and r.content[1].mime_type == "image/png"

            r = await c.call_tool("wash_overview", {"wash_id": "nope"})
            assert r.is_error and r.content[0].text.startswith("error:")
    anyio.run(go)


def test_server_and_tools_are_read_only():
    """No network library imported, no file-writing call, no .env access (checked on the code, not comments)."""
    import ast
    banned_imports = {"requests", "urllib", "httpx", "socket", "firebase_admin", "kasa", "dotenv"}
    banned_calls = {"open", "write_text", "write_bytes", "to_csv", "savefig_to_disk", "load_dotenv"}
    for f in ("server.py", "tools.py", "store.py", "plots.py", "registry.py"):
        tree = ast.parse((ROOT / "apex_lens" / f).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {a.name.split(".")[0] for a in node.names} & banned_imports, f
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in banned_imports, f
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                assert name not in banned_calls, (f, name)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith(".env"):
                raise AssertionError(f"{f} refers to a .env file")
