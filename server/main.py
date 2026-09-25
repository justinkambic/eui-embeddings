"""EUI icon search server.

Exposes:
  GET  /health            — liveness probe, no auth
  GET  /auth/login        — redirect to Google OAuth consent screen
                            (?cli_port=&state= for CLI loopback clients)
  GET  /auth/callback     — OAuth callback; hands the bearer token to the
                            browser opener via postMessage, or to a CLI via
                            redirect to http://127.0.0.1:<cli_port>/callback
  GET  /auth/status       — returns {authenticated, email} for the current token
  POST /api/icon-search   — kNN search by text or image (requires auth)
  GET  /api/versions      — list indexed EUI release tags (requires auth)
"""

from __future__ import annotations

import base64
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated, Union

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, field_validator

from . import config
from .auth import (
    cli_redirect_url,
    decode_cli_state,
    encode_cli_state,
    exchange_and_verify,
    login_url,
    make_token,
    optional_auth,
    require_auth,
)
from .es import SearchClient
from .image import normalize

_log = logging.getLogger("server")
_es: SearchClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _es
    _es = SearchClient(
        config.ES_ENDPOINT,
        config.ES_API_KEY,
        config.ES_INDEX,
        config.INFERENCE_ID,
    )
    yield
    await _es.aclose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# --- health ------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"ok": True}


# --- auth --------------------------------------------------------------------

@app.get("/auth/login")
async def auth_login(cli_port: int | None = None, state: str | None = None):
    """Redirect to Google.

    Browser clients call this with no params. CLI clients (the MCP server)
    pass `cli_port` (their loopback listener) and `state` (a random nonce);
    the callback then redirects to http://127.0.0.1:<cli_port>/callback
    with the token instead of using postMessage.
    """
    oauth_state = None
    if cli_port is not None or state is not None:
        if cli_port is None or state is None:
            raise HTTPException(status_code=400, detail="cli_port and state must be given together")
        oauth_state = encode_cli_state(cli_port, state)
    return RedirectResponse(login_url(oauth_state))


@app.get("/auth/callback")
async def auth_callback(code: str, state: str | None = None):
    cli = decode_cli_state(state)

    try:
        claims = await exchange_and_verify(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {e}")

    if claims.get("hd") != config.ALLOWED_DOMAIN:
        raise HTTPException(status_code=403, detail="Access restricted to Elastic employees")

    token = make_token(claims["email"])

    if cli:
        port, nonce = cli
        return RedirectResponse(cli_redirect_url(port, nonce, token), status_code=302)

    payload = json.dumps({"type": "auth:complete", "token": token})
    return HTMLResponse(f"""<!DOCTYPE html>
<html><body><script>
  if (window.opener) {{
    window.opener.postMessage({payload}, '*');
    window.close();
  }} else {{
    document.body.innerText = 'Authenticated. You may close this tab.';
  }}
</script></body></html>""")


@app.get("/auth/status")
async def auth_status(email: Annotated[str | None, Depends(optional_auth)]):
    return {"authenticated": email is not None, "email": email}


# --- search ------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: Union[str, dict]
    version: str | None = None
    limit: int = 12

    @field_validator("limit")
    @classmethod
    def clamp_limit(cls, v: int) -> int:
        if not 1 <= v <= 50:
            raise ValueError("limit must be between 1 and 50")
        return v


@app.post("/api/icon-search")
async def icon_search(
    body: SearchRequest,
    email: Annotated[str, Depends(require_auth)],
):
    if isinstance(body.query, str):
        vector = await _es.embed_text(body.query)
        field = "name_vector"
    else:
        raw = body.query.get("image", "")
        if "," in raw:  # strip data URI prefix if present
            raw = raw.split(",", 1)[1]
        try:
            png = normalize(base64.b64decode(raw))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
        vector = await _es.embed_image(png)
        field = "image_vector_aug_centroid"

    t0 = time.monotonic()
    hits = await _es.knn_search(
        vector, field, k=100, version=body.version, limit=body.limit
    )
    took_ms = round((time.monotonic() - t0) * 1000)
    return {"hits": hits, "took_ms": took_ms}


@app.get("/api/versions")
async def versions(email: Annotated[str, Depends(require_auth)]):
    return {"versions": await _es.indexed_versions()}
