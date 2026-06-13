"""Integration tests for the MCP server subprocess stdio handshake.

These tests spawn the real server process and exercise the JSON-RPC
wire protocol, complementing the unit-level tests in test_mcp_server.py.
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent

_TIMEOUT = 10  # seconds — CI guard

INIT_REQUEST = (
    json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1"},
            },
        }
    )
    + "\n"
)


# ---------------------------------------------------------------------------
# Subprocess handshake
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.xfail(
    reason="MCP server subprocess may not be available in all CI environments",
    strict=False,
)
def test_mcp_stdio_handshake() -> None:
    """Spawn the MCP server, send initialize, assert valid response within 10 s.

    The MCP stdio transport is newline-delimited JSON-RPC.  We write the
    initialize request, then read stdout lines until we find one that
    contains ``"result"`` and parse it.

    Skipped when the optional ``mcp`` extra is not installed.
    """
    pytest.importorskip("mcp")

    proc = subprocess.Popen(
        ["uv", "run", "champi-stt", "mcp", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )

    response: dict | None = None
    reader_error: BaseException | None = None

    def _reader() -> None:
        nonlocal response, reader_error
        try:
            assert proc.stdin is not None
            assert proc.stdout is not None
            proc.stdin.write(INIT_REQUEST)
            proc.stdin.flush()
            for line in proc.stdout:
                stripped = line.strip()
                if stripped and '"result"' in stripped:
                    response = json.loads(stripped)
                    break
        except Exception as exc:
            reader_error = exc

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    thread.join(timeout=_TIMEOUT)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    if reader_error is not None:
        raise AssertionError(f"Reader thread raised: {reader_error}") from reader_error

    assert not thread.is_alive(), "MCP server did not respond within 10 seconds"
    assert response is not None, "No JSON-RPC response received from MCP server"
    assert response["id"] == 1
    assert "result" in response
