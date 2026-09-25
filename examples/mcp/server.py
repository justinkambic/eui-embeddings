#!/usr/bin/env python3
"""MCP server exposing EUI icon search to AI assistants.

Talks to the hosted icon-search API (Cloud Run) using the same Google
OAuth identity the EUI docs search UI uses, so anyone in the Elastic org
can use it without an Elasticsearch key or a local sidecar. The intended
user flow:

    1. User pastes a screenshot of an icon into their AI chat (Claude
       Code, Cursor, etc.).
    2. The assistant sees the image and calls the `icon_search` tool
       with the image path.
    3. This server forwards to the icon-search API with a bearer token.
       On first use (or when the token expires) it opens a browser tab
       for Google sign-in and receives the token on a loopback port.
    4. The assistant gets back a ranked list with EUI prop names and
       inserts something like `<EuiIcon type="search" />` in the user's
       code.

Setup:

    .venv-mcp/bin/python examples/mcp/server.py login     # one-time sign-in
    .venv-mcp/bin/python examples/mcp/server.py status    # who am I?
    .venv-mcp/bin/python examples/mcp/server.py logout    # forget the token

Then configure your assistant's MCP client to launch this script over
stdio (see claude_code_config.example.json next to this file).

Environment:

    ICON_SEARCH_BASE_URL   API base URL. Defaults to the hosted Cloud Run
                           service. Point at http://127.0.0.1:4555 to use
                           the local Express sidecar instead (no auth).
    ICON_SEARCH_TOKEN      Bearer token override. Skips the cached token
                           and the browser flow. Mostly for CI / debugging.
    ICON_DOCS_BASE_URL     Docs page used for `view` links in results.

Tokens are cached at $XDG_CONFIG_HOME/eui-icons/tokens.json (default
~/.config/eui-icons/tokens.json), keyed by API base URL, mode 0600.

This server never sees an Elasticsearch key. The API holds it and
applies domain restriction + rate limits.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from mcp.server.fastmcp import FastMCP


# 5 MB to match the API's body cap. Anything larger is almost certainly
# not an icon screenshot anyway.
_MAX_IMAGE_BYTES = 5 * 1024 * 1024

HOSTED_API_URL = "https://eui-icon-search-1014491842772.us-central1.run.app"
HOSTED_DOCS_URL = (
    "https://eui-icon-search-docs-1014491842772.us-central1.run.app"
    "/docs/components/display/icons"
)

BASE_URL = os.environ.get("ICON_SEARCH_BASE_URL", HOSTED_API_URL).rstrip("/")
ICON_DOCS_BASE_URL = os.environ.get("ICON_DOCS_BASE_URL", HOSTED_DOCS_URL)

# How long to wait for the user to finish signing in before giving up.
LOGIN_TIMEOUT_S = float(os.environ.get("ICON_SEARCH_LOGIN_TIMEOUT_S", "180"))


mcp = FastMCP("eui-icons")


def _log(msg: str) -> None:
    # stdout is the MCP transport; everything human-facing goes to stderr.
    print(f"[eui-icons] {msg}", file=sys.stderr, flush=True)


# --- token cache -------------------------------------------------------------


def _token_file() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "eui-icons" / "tokens.json"


def _read_cache() -> dict[str, str]:
    try:
        return json.loads(_token_file().read_text())
    except (OSError, ValueError):
        return {}


def _write_cache(cache: dict[str, str]) -> None:
    p = _token_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(p)


def load_token() -> str | None:
    env = os.environ.get("ICON_SEARCH_TOKEN")
    if env:
        return env
    return _read_cache().get(BASE_URL)


def save_token(token: str) -> None:
    cache = _read_cache()
    cache[BASE_URL] = token
    _write_cache(cache)


def clear_token() -> None:
    cache = _read_cache()
    if cache.pop(BASE_URL, None) is not None:
        _write_cache(cache)


# --- browser login (loopback handoff) ---------------------------------------


class LoginError(RuntimeError):
    pass


_CALLBACK_HTML = b"""<!DOCTYPE html>
<html><body style="font-family: system-ui; padding: 2rem">
<h2>Signed in to EUI icon search.</h2>
<p>You can close this tab and go back to your AI assistant.</p>
</body></html>"""


def browser_login(timeout_s: float = LOGIN_TIMEOUT_S) -> str:
    """Open the browser for Google sign-in; return the bearer token.

    Starts a one-shot HTTP listener on 127.0.0.1:<random port>, asks the
    API to redirect there after Google authenticates the user, and waits
    for the callback carrying our nonce. Blocking; run in a thread from
    async code.
    """
    nonce = secrets.token_urlsafe(24)
    result: dict[str, str] = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
            url = urlparse(self.path)
            if url.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            qs = parse_qs(url.query)
            token = (qs.get("token") or [""])[0]
            state = (qs.get("state") or [""])[0]
            if not token or not secrets.compare_digest(state, nonce):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Login state mismatch. Please retry the sign-in.")
                return
            result["token"] = token
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_CALLBACK_HTML)
            done.set()

        def log_message(self, *_: Any) -> None:  # silence stdlib access log
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    httpd.timeout = 0.5

    login_url = f"{BASE_URL}/auth/login?{urlencode({'cli_port': port, 'state': nonce})}"
    _log("Opening your browser to sign in with Google...")
    _log(f"If it doesn't open, visit: {login_url}")
    if not webbrowser.open(login_url):
        _log("Could not launch a browser automatically.")

    end = time.monotonic() + timeout_s
    try:
        while not done.is_set() and time.monotonic() < end:
            httpd.handle_request()
    finally:
        httpd.server_close()

    if "token" not in result:
        raise LoginError(
            f"Timed out after {int(timeout_s)}s waiting for the browser sign-in to complete."
        )
    return result["token"]


# --- HTTP with auto-auth -----------------------------------------------------


def _auth_headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _request(method: str, path: str, *, timeout: float, **kw: Any) -> httpx.Response:
    """Call the API, running the browser login once if we get a 401.

    Against the unauthenticated local sidecar the first call simply
    succeeds and no login is attempted.
    """
    token = load_token()
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.request(method, f"{BASE_URL}{path}", headers=_auth_headers(token), **kw)
        if r.status_code != 401 or os.environ.get("ICON_SEARCH_TOKEN"):
            return r

        _log("Not signed in (or token expired); starting browser sign-in.")
        clear_token()
        token = await asyncio.to_thread(browser_login)
        save_token(token)
        return await client.request(
            method, f"{BASE_URL}{path}", headers=_auth_headers(token), **kw
        )


def _connection_help(detail: str) -> str:
    return (
        f"Could not reach the icon-search API at {BASE_URL}: {detail}.\n"
        "Check your network, or set ICON_SEARCH_BASE_URL to a different server "
        "(e.g. http://127.0.0.1:4555 for the local sidecar)."
    )


def _error_text(r: httpx.Response) -> str:
    try:
        detail = r.json()
    except Exception:
        detail = r.text
    if r.status_code == 401:
        return (
            f"icon-search error (HTTP 401): {detail}\n"
            "Sign in with: python examples/mcp/server.py login"
        )
    if r.status_code == 403:
        return (
            f"icon-search error (HTTP 403): {detail}\n"
            "Icon search is restricted to Elastic Google accounts."
        )
    return f"icon-search error (HTTP {r.status_code}): {detail}"


# --- response formatting ---------------------------------------------------


def _docs_link(prop_name: str) -> str:
    return f"{ICON_DOCS_BASE_URL}#icon-{prop_name}"


def _format_hits_text(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "No matching icons found."
    lines = [
        f"Top {len(hits)} candidates (scores are cosine similarity; "
        f"click `view` to see each rendered in EUI's docs):",
        "",
        "Note: in dense visual neighborhoods (ML icons, app glyphs, logos) "
        "the score gap between #1 and #10 is often <0.02 — present the "
        "full list to the user rather than committing to the top hit.",
        "",
        "| # | prop | score | version | preview | aliases |",
        "|---|---|---|---|---|---|",
    ]
    for i, hit in enumerate(hits, 1):
        prop = hit["prop_name"]
        score = hit["score"]
        version = hit["version"]
        aliases = hit.get("aliases") or []
        alias_cell = ", ".join(f"`{a}`" for a in aliases) if aliases else ""
        lines.append(
            f"| {i} | `{prop}` | {score:.3f} | {version} | "
            f"[view]({_docs_link(prop)}) | {alias_cell} |"
        )
    return "\n".join(lines)


# --- tools -------------------------------------------------------------------


@mcp.tool()
async def icon_search(
    text: str | None = None,
    image_path: str | None = None,
    image_base64: str | None = None,
    version: str | None = None,
    limit: int = 12,
) -> str:
    """Search EUI icons by text description or by image.

    Provide exactly ONE of `text`, `image_path`, or `image_base64`.

    PREFER `image_path` when the image is on disk (e.g. when the user
    pastes an image into chat — the AI client typically attaches it as a
    file path). It is more reliable than passing 7-100 KB of base64
    through tool-call argument serialization, where the bytes can get
    mangled in transit.

    The first call may open a browser tab asking the user to sign in
    with their Elastic Google account. Tell the user to complete it; the
    search continues automatically afterwards.

    Args:
        text: Free-text description, e.g. "search icon", "warning triangle",
            "trash can".
        image_path: Absolute or working-directory-relative path to an image
            file (PNG/JPG/WebP/GIF) to search for. The MCP server reads,
            base64-encodes, and forwards to the API. 5 MB max.
        image_base64: Base64-encoded image bytes. A `data:image/...;base64,`
            prefix is OK. Use this only when the image is not available
            on disk (rare).
        version: EUI release tag to search against (e.g. "v115.0.0"). When
            omitted, searches across all indexed versions.
        limit: Number of top hits to return (1..50). Defaults to 12 —
            jina-clip-v2 produces tightly-clustered scores in dense
            visual neighborhoods, so a wider list lets the user (or the
            assistant) spot the right answer beyond the literal top-1.
    """
    provided = [n for n in (text, image_path, image_base64) if n]
    if len(provided) == 0:
        return "Error: provide one of `text`, `image_path`, or `image_base64`."
    if len(provided) > 1:
        return (
            "Error: provide only ONE of `text`, `image_path`, or `image_base64`, "
            "not multiple."
        )
    if limit < 1 or limit > 50:
        return "Error: `limit` must be between 1 and 50."

    # Resolve image_path → image_base64 here, so the wire format to the
    # API is uniform and we never ship ambiguous arg combinations.
    if image_path:
        try:
            p = Path(image_path).expanduser()
        except Exception as e:
            return f"Error: invalid `image_path` ({image_path!r}): {e}"
        if not p.exists():
            return f"Error: image_path does not exist: {p}"
        if not p.is_file():
            return f"Error: image_path is not a regular file: {p}"
        size = p.stat().st_size
        if size > _MAX_IMAGE_BYTES:
            return f"Error: image at {p} is {size} bytes; max is {_MAX_IMAGE_BYTES}."
        try:
            data = p.read_bytes()
        except OSError as e:
            return f"Error: could not read {p}: {e}"
        image_base64 = base64.b64encode(data).decode("ascii")

    body: dict[str, Any] = {"limit": limit}
    if version:
        body["version"] = version
    body["query"] = text if text else {"image": image_base64}

    try:
        r = await _request("POST", "/api/icon-search", timeout=30.0, json=body)
    except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as e:
        return _connection_help(repr(e))
    except LoginError as e:
        return f"Sign-in did not complete: {e}"

    if r.status_code != 200:
        return _error_text(r)

    data = r.json()
    return _format_hits_text(data.get("hits", []))


@mcp.tool()
async def icon_versions() -> str:
    """List the EUI release tags currently indexed and searchable.

    Use this to confirm which version filter to pass to `icon_search`.
    """
    try:
        r = await _request("GET", "/api/versions", timeout=10.0)
    except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as e:
        return _connection_help(repr(e))
    except LoginError as e:
        return f"Sign-in did not complete: {e}"

    if r.status_code != 200:
        return _error_text(r)
    versions = r.json().get("versions") or []
    if not versions:
        return "No versions indexed yet. Run the ingester first."
    return "Indexed EUI versions:\n" + "\n".join(f"- {v}" for v in versions)


# --- CLI ---------------------------------------------------------------------


def _cmd_status() -> int:
    token = load_token()
    if not token:
        _log(f"Not signed in to {BASE_URL}. Run: server.py login")
        return 1
    try:
        r = httpx.get(f"{BASE_URL}/auth/status", headers=_auth_headers(token), timeout=10.0)
    except httpx.HTTPError as e:
        _log(_connection_help(repr(e)))
        return 2
    info = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code == 200 and info.get("authenticated"):
        _log(f"Signed in to {BASE_URL} as {info.get('email')}")
        return 0
    _log(f"Token for {BASE_URL} is not valid (HTTP {r.status_code}). Run: server.py login")
    return 1


def _cmd_login() -> int:
    try:
        token = browser_login()
    except LoginError as e:
        _log(str(e))
        return 1
    save_token(token)
    _log(f"Saved token to {_token_file()}")
    return _cmd_status()


def _cmd_logout() -> int:
    clear_token()
    _log(f"Forgot token for {BASE_URL}")
    return 0


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        cmd = argv[0]
        if cmd == "login":
            sys.exit(_cmd_login())
        if cmd == "logout":
            sys.exit(_cmd_logout())
        if cmd == "status":
            sys.exit(_cmd_status())
        _log(f"Unknown command {cmd!r}. Use: login | logout | status, or no args to serve MCP.")
        sys.exit(2)
    # FastMCP's run() handles stdio transport.
    mcp.run()


if __name__ == "__main__":
    main()
