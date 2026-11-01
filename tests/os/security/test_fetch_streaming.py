from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from xninetzy.os.security.guards import SecurityError, safe_fetch


def _make_server(body: bytes, content_type: str = "text/html; charset=utf-8"):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.fixture()
def large_server():
    server, thread = _make_server(b"A" * (2 * 1024 * 1024))
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/big"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture()
def small_server():
    server, thread = _make_server(b"hello world")
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/small"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_safe_fetch_rejects_oversized_body(large_server):
    with pytest.raises(SecurityError) as exc:
        await safe_fetch(large_server, allow_private=True, max_bytes=64 * 1024)
    assert exc.value.code == "RESPONSE_TOO_LARGE"


@pytest.mark.asyncio
async def test_safe_fetch_returns_small_body(small_server):
    body = await safe_fetch(small_server, allow_private=True, max_bytes=64 * 1024)
    assert body == b"hello world"


@pytest.mark.asyncio
async def test_safe_get_truncates_to_max_bytes(large_server, monkeypatch):
    from xninetzy.os.research import safe_fetch as research_fetch

    monkeypatch.setattr(research_fetch, "_validate_host", lambda host: None)
    text = await research_fetch.safe_get(large_server, max_bytes=1000)
    assert len(text) == 1000
