from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

from xninetzy.os.auth.oauth.providers import (
    ProviderDefinition,
    get_provider,
)
from xninetzy.os.auth.sessions.state import (
    AuthSessionStatus,
    find_session_by_state,
    transition,
)


log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CallbackResult:
    code: str
    state: str
    error: str | None = None
    error_description: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "state": self.state,
            "error": self.error,
            "error_description": self.error_description,
        }


@dataclass(frozen=True, slots=True)
class BoundServer:
    host: str
    port: int
    base_url: str
    redirect_uri: str

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "base_url": self.base_url,
            "redirect_uri": self.redirect_uri,
        }


_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765
_CALLBACK_PATH = "/auth/callback"
_HEALTH_PATH = "/auth/health"


CallbackHandler = Callable[[CallbackResult], Awaitable[dict[str, Any]]]


class CallbackServerAlreadyRunning(RuntimeError):
    pass


class CallbackServerNotRunning(RuntimeError):
    pass


_HTML_OK = (
    b"<html><body><h2>Login successful</h2>"
    b"<p>You can close this window and return to your assistant.</p>"
    b"</body></html>"
)
_HTML_BAD = (
    b"<html><body><h2>Login failed</h2>"
    b"<p>{error}: {desc}</p></body></html>"
)


class _State:
    def __init__(self) -> None:
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.handler: CallbackHandler | None = None
        self.bound: BoundServer | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.loop_thread: threading.Thread | None = None
        self.lock = threading.Lock()


_STATE = _State()


def _resolve_config(host: str | None, port: int | None, path: str | None) -> tuple[str, int, str]:
    bind_host = (host or os.environ.get("XNINETZY_OAUTH_CALLBACK_HOST") or _DEFAULT_HOST).strip() or _DEFAULT_HOST
    bind_port = int(port or int(os.environ.get("XNINETZY_OAUTH_CALLBACK_PORT", str(_DEFAULT_PORT))))
    bind_path = (path or os.environ.get("XNINETZY_OAUTH_CALLBACK_PATH") or _CALLBACK_PATH).strip() or _CALLBACK_PATH
    return bind_host, bind_port, bind_path


def _next_free_port(host: str, preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, preferred))
            return preferred
        except OSError:
            s.bind((host, 0))
            return s.getsockname()[1]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        log.debug("oauth callback http: " + fmt, *args)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params: dict[str, str] = {}
        if parsed.query:
            for chunk in parsed.query.split("&"):
                if "=" not in chunk:
                    continue
                k, _, v = chunk.partition("=")
                params[k] = v.replace("+", " ")
        if parsed.path == _HEALTH_PATH:
            body = json.dumps(_STATE.bound.to_safe_dict() if _STATE.bound else {"running": False}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path != _CALLBACK_PATH:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"not found")
            return
        result = CallbackResult(
            code=params.get("code", ""),
            state=params.get("state", ""),
            error=params.get("error"),
            error_description=params.get("error_description"),
        )
        if result.error or not result.code or not result.state:
            body = _HTML_BAD.replace(b"{error}", (result.error or "error").encode()).replace(
                b"{desc}", (result.error_description or "no description").encode()
            )
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self._dispatch(result)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(_HTML_OK)))
        self.end_headers()
        self.wfile.write(_HTML_OK)
        self._dispatch(result)

    def _dispatch(self, result: CallbackResult) -> None:
        handler = _STATE.handler
        loop = _STATE.loop
        if handler is None or loop is None:
            return
        try:
            fut = asyncio.run_coroutine_threadsafe(handler(result), loop)
            fut.result(timeout=30)
        except Exception:
            log.exception("oauth callback handler failed")


def start_callback_server(
    handler: CallbackHandler,
    *,
    host: str | None = None,
    port: int | None = None,
    path: str | None = None,
) -> BoundServer:
    bind_host, bind_port, bind_path = _resolve_config(host, port, path)
    with _STATE.lock:
        if _STATE.server is not None:
            raise CallbackServerAlreadyRunning(
                f"callback server already bound at {_STATE.bound}"
            )
        _STATE.handler = handler
        try:
            loop = asyncio.get_running_loop()
            _STATE.loop = loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            _STATE.loop_thread = threading.Thread(
                target=loop.run_forever,
                name="oauth-callback-loop",
                daemon=True,
            )
            _STATE.loop_thread.start()
            _STATE.loop = loop
        chosen_port = _next_free_port(bind_host, bind_port)
        _STATE.server = ThreadingHTTPServer((bind_host, chosen_port), _Handler)
        _STATE.bound = BoundServer(
            host=bind_host,
            port=chosen_port,
            base_url=f"http://{bind_host}:{chosen_port}",
            redirect_uri=f"http://{bind_host}:{chosen_port}{bind_path}",
        )
        _STATE.thread = threading.Thread(
            target=_STATE.server.serve_forever,
            name="oauth-callback-server",
            daemon=True,
        )
        _STATE.thread.start()
        log.info("oauth callback server bound at %s", _STATE.bound.redirect_uri)
        return _STATE.bound


def stop_callback_server() -> None:
    with _STATE.lock:
        if _STATE.server is not None:
            _STATE.server.shutdown()
            _STATE.server.server_close()
        if _STATE.loop is not None and _STATE.loop_thread is not None:
            try:
                _STATE.loop.call_soon_threadsafe(_STATE.loop.stop)
            except Exception:
                pass
        _STATE.server = None
        _STATE.thread = None
        _STATE.handler = None
        _STATE.loop = None
        _STATE.loop_thread = None
        _STATE.bound = None


def callback_server_status() -> dict[str, Any]:
    return {
        "running": _STATE.server is not None,
        "bound": _STATE.bound.to_safe_dict() if _STATE.bound else None,
    }


def _client_id_env(provider: ProviderDefinition) -> str:
    return os.environ.get(provider.client_id_env, "").strip()


def _client_secret_env(provider: ProviderDefinition) -> str:
    return os.environ.get(provider.client_secret_env, "").strip()


def _safe_json(resp: Any) -> dict[str, Any]:
    try:
        text = resp.text  # type: ignore[attr-defined]
    except Exception:
        return {}
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


async def default_callback_handler(result: CallbackResult) -> dict[str, Any]:
    if result.error:
        return {"status": "error", "error": result.error, "error_description": result.error_description}
    if not result.state:
        return {"status": "error", "error": "missing state"}
    session = find_session_by_state(result.state)
    if session is None:
        return {"status": "error", "error": "unknown state"}
    provider = get_provider(session.provider)
    if provider is None:
        return {"status": "error", "error": f"unknown provider: {session.provider}"}
    transition(session.session_id, to=AuthSessionStatus.CALLBACK_RECEIVED)
    return await exchange_code_for_token(provider, session, result.code)


async def exchange_code_for_token(
    provider: ProviderDefinition,
    session: Any,
    code: str,
) -> dict[str, Any]:
    import httpx

    if not session.pkce_verifier:
        transition(session.session_id, to=AuthSessionStatus.FAILED, error_code="missing_pkce_verifier")
        return {"status": "error", "error": "missing pkce verifier"}
    client_id = _client_id_env(provider)
    client_secret = _client_secret_env(provider)
    if not client_id:
        transition(session.session_id, to=AuthSessionStatus.FAILED, error_code="missing_client_id")
        return {"status": "error", "error": f"missing {provider.client_id_env}"}
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": session.redirect_uri or provider.redirect_uri,
        "client_id": client_id,
        "code_verifier": session.pkce_verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret
    headers = {"Accept": "application/json"}
    transition(session.session_id, to=AuthSessionStatus.EXCHANGING)
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(provider.token_endpoint, data=data, headers=headers)
    except Exception as exc:
        transition(session.session_id, to=AuthSessionStatus.FAILED, error_code=type(exc).__name__)
        return {"status": "error", "error": str(exc)}
    payload = _safe_json(resp)
    if resp.status_code >= 400:
        transition(
            session.session_id,
            to=AuthSessionStatus.FAILED,
            error_code=f"http_{resp.status_code}",
        )
        return {"status": "error", "error": f"http {resp.status_code}", "response": payload}
    transition(session.session_id, to=AuthSessionStatus.AUTHENTICATED)
    return {"status": "authenticated", "provider": provider.provider_id, "token_response": payload}


__all__ = [
    "BoundServer",
    "CallbackResult",
    "CallbackServerAlreadyRunning",
    "CallbackServerNotRunning",
    "default_callback_handler",
    "callback_server_status",
    "exchange_code_for_token",
    "start_callback_server",
    "stop_callback_server",
]
