from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..config import settings
from ..middleware.auth import extract_token

router = APIRouter()

COOKIE_NAME = "dash_psk"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 365 days in seconds


@router.post("/api/auth/login")
async def login(request: Request, response: Response):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    psk = body.get("psk", "") if isinstance(body, dict) else ""

    if not settings.DASH_PSK:
        return {"ok": True, "message": "Auth disabled"}

    if not psk or psk != settings.DASH_PSK:
        return JSONResponse({"ok": False, "error": "Invalid access key"}, status_code=401)

    response.set_cookie(
        key=COOKIE_NAME,
        value=psk,
        max_age=COOKIE_MAX_AGE,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@router.get("/api/auth/verify")
def verify(request: Request):
    auth_enabled = bool(settings.DASH_PSK)
    if not auth_enabled:
        return {"authenticated": True, "auth_enabled": False}

    token = extract_token(request)
    authenticated = token == settings.DASH_PSK
    return {"authenticated": authenticated, "auth_enabled": True}


@router.delete("/api/auth/logout")
def logout(response: Response):
    response.set_cookie(
        key=COOKIE_NAME,
        value="",
        max_age=0,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}
