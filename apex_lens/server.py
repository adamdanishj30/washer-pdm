"""
server.py
Apex Lens as a read-only MCP server (stdio). Any MCP client (Claude Desktop,
Claude Code, Antigravity, ...) can start it and call the six tools defined in
registry.py. Every call goes through ApexLens.call_full, so the client gets
exactly what the plain-Python tools return: a short text answer (with its
`ref:` and `quality:` lines) and, for render_plot, one PNG.

Rules
-----
* Read-only. It loads data/real_sessions/*.csv (firmware-07 washes) once at
  start-up and never writes a file, opens a network connection, reads .env,
  or touches Firebase / SmartThings / Tapo. No key or secret is needed.
* Arguments are ids and enums only; nothing is ever used as a file path.
* Only recorded washes are visible. Fault-injected copies exist only inside
  the experiment runner, never here.

Run it
------
  py apex_lens/server.py                    # data/real_sessions in this repo
  py apex_lens/server.py --data-dir <folder>
(py -m apex_lens.server also works when started from the repo folder.)

Add to Claude Code:  claude mcp add apex-lens -- py "<repo>/apex_lens/server.py"
(see apex_lens/README.md for Claude Desktop and Antigravity).
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports
# =============================================================================
import argparse
import asyncio
import base64
import sys
import threading
from pathlib import Path
from typing import Any, Optional

import mcp_types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Started as a script (py <path>/apex_lens/server.py) from any working folder:
# put the repo root on the import path so "ml" and "apex_lens" import, and drop
# the apex_lens folder itself so its tools.py / store.py never shadow other modules.
ROOT = Path(__file__).resolve().parent.parent
_HERE = str(Path(__file__).resolve().parent)
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve().as_posix() != Path(_HERE).as_posix()]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apex_lens.registry import TOOLS  # noqa: E402
from apex_lens.store import REAL_SESSIONS_DIR, WashStore  # noqa: E402
from apex_lens.tools import ApexLens  # noqa: E402

SERVER_NAME = "apex-lens"
INSTRUCTIONS = (
    "Apex Lens reads one household washing machine's recorded washes (vibration, sound and power, one row "
    "per 5 s window). Use the tools to look at the data; never ask for the raw table. 'Normal' always means "
    "this washer's other washes. The tools can say that a wash deviates from normal, in which phase and in "
    "which sensor group. They cannot say which part is failing, how long it will last or what a repair "
    "costs, because there are no labelled faults: decline those questions and say what the data can show. "
    "Quote only numbers that appear in tool outputs, cite the ref: line they came from, and mention any "
    "quality: or abstain: line.")


# =============================================================================
# SECTION 2: Server
# =============================================================================
def build_server(lens: Optional[ApexLens] = None, data_dir: Path = REAL_SESSIONS_DIR) -> Server:
    """Create the MCP server. Pass `lens` in tests; otherwise washes load from `data_dir`."""
    lens = lens or ApexLens(WashStore.from_dir(data_dir))
    lock = threading.Lock()
    tool_list = [types.Tool(name=t["name"], description=t["description"], input_schema=t["input_schema"],
                            annotations=types.ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                                              idempotent_hint=True, open_world_hint=False))
                 for t in TOOLS]

    async def on_list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tool_list)

    async def on_call_tool(ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        args = dict(params.arguments or {})

        def run():
            with lock:                       # one tool at a time: the lens caches are not thread-safe
                return lens.call_full(params.name, **args)
        # the tools are CPU-bound pandas code: run them off the event loop
        text, png = await asyncio.to_thread(run)
        content: list = [types.TextContent(type="text", text=text)]
        if png:
            content.append(types.ImageContent(type="image", data=base64.b64encode(png).decode("ascii"),
                                              mime_type="image/png"))
        return types.CallToolResult(content=content, is_error=text.startswith("error:"))

    return Server(SERVER_NAME, version="0.1.0", instructions=INSTRUCTIONS, on_list_tools=on_list_tools, on_call_tool=on_call_tool)


# =============================================================================
# SECTION 3: Entry point (stdio)
# =============================================================================
async def _run(data_dir: Path) -> None:
    server = build_server(data_dir=data_dir)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Apex Lens read-only MCP server (stdio)")
    ap.add_argument("--data-dir", type=Path, default=REAL_SESSIONS_DIR,
                    help="folder with wash_cycle_*.csv files (default: data/real_sessions)")
    a = ap.parse_args(argv)
    asyncio.run(_run(a.data_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
