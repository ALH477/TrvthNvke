import io
import json
import sys
from pathlib import Path

from truthgate.mcp_server import TruthgateMCP, run_stdio


def _repo(tmp: Path) -> Path:
    (tmp / "README.md").write_text("# App\n\n## Install\n\nHello.\n", encoding="utf-8")
    return tmp


def test_handle_initialize_and_tools(tmp_path: Path) -> None:
    server = TruthgateMCP(_repo(tmp_path))
    init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init and init["result"]["serverInfo"]["name"] == "truthgate"
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    tools = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in tools["result"]["tools"]}
    assert "truthgate_apply_edit" in names


def test_stdio_replies_are_newline_delimited(tmp_path: Path, monkeypatch=None) -> None:
    _repo(tmp_path)
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "truthgate_status", "arguments": {}}},
    ]
    stdin, stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
    sys.stdout = io.StringIO()
    try:
        run_stdio(tmp_path)
        out = sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = stdin, stdout
    lines = out.splitlines()
    assert len(lines) == 3, out
    assert "Content-Length" not in out
    ids = [json.loads(line)["id"] for line in lines]
    assert ids == [1, 2, 3]


def test_stdio_answers_content_length_in_kind(tmp_path: Path) -> None:
    _repo(tmp_path)
    body = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"})
    stdin, stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(f"Content-Length: {len(body.encode())}\r\n\r\n{body}")
    sys.stdout = io.StringIO()
    try:
        run_stdio(tmp_path)
        out = sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = stdin, stdout
    assert out.startswith("Content-Length: ")
    assert json.loads(out.split("\r\n\r\n", 1)[1])["id"] == 7
