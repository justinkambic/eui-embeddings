"""Google OAuth flow and bearer-token verification.

Flow:
  1. Browser opens /auth/login in a popup.
  2. Google redirects to /auth/callback with an authorization code.
  3. Server exchanges the code for an ID token, verifies hd == elastic.co,
     then signs a short-lived token and passes it to the opener via postMessage.
  4. The <IconSearch /> component stores the token in sessionStorage and
     includes it as a Bearer token on all /api/* requests.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from . import config

_signer = TimestampSigner(config.TOKEN_SECRET)
_bearer = HTTPBearer(auto_error=False)

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SCOPES = "openid email profile"


def _redirect_uri() -> str:
    return f"{config.SERVER_BASE_URL}/auth/callback"


def login_url() -> str:
    params = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_and_verify(code: str) -> dict:
    """Exchange an authorization code for an ID token and verify it."""
    async with httpx.AsyncClient() as client:
        r = await client.post(_GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
        })
        r.raise_for_status()

    # verify_oauth2_token uses requests (sync) for Google's public key fetch —
    # acceptable overhead on the auth path which is infrequent.
    return id_token.verify_oauth2_token(
        r.json()["id_token"],
        google_requests.Request(),
        config.GOOGLE_CLIENT_ID,
    )


def make_token(email: str) -> str:
    """Return a signed, timestamped token encoding the user's email."""
    return _signer.sign(email).decode()


def _unsign_token(raw: str) -> str:
    try:
        return _signer.unsign(raw, max_age=config.TOKEN_MAX_AGE_S).decode()
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired — please sign in again")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_auth(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """FastAPI dependency — returns the authenticated email or raises 401."""
    if not creds:
        raise HTTPException(status_code=401, detail="Bearer token required")
    return _unsign_token(creds.credentials)


def optional_auth(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str | None:
    """FastAPI dependency — returns email if authenticated, None otherwise."""
    if not creds:
        return None
    try:
        return _unsign_token(creds.credentials)
    except HTTPException:
        return None
