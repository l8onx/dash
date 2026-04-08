import re
from typing import Optional
from urllib.parse import quote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from ..config import settings

# Paths that are always public regardless of PSK
PUBLIC_PATHS: set[str] = {
    "/api/health",
    "/api/auth/verify",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/schema",
    "/login",
}

# Static asset extensions that must always be served unauthenticated
# (login page and SPA shell need their own assets)
_STATIC_EXTS = re.compile(r"\.(js|css|ico|png|svg|woff2?|ttf|map|json)$", re.IGNORECASE)


def extract_token(request: Request) -> Optional[str]:
    """Extract PSK from Bearer header, X-Dash-PSK header, or dash_psk cookie."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()

    psk_header = request.headers.get("x-dash-psk")
    if psk_header:
        return psk_header.strip()

    return request.cookies.get("dash_psk")


class PSKMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Auth disabled — let everything through
        if not settings.DASH_PSK:
            return await call_next(request)

        path = request.url.path

        # Always-public paths and static assets bypass auth
        if path in PUBLIC_PATHS or _STATIC_EXTS.search(path):
            return await call_next(request)

        token = extract_token(request)
        if token == settings.DASH_PSK:
            return await call_next(request)

        # API routes return 401 JSON; HTML routes redirect to /login
        if path.startswith("/api/"):
            return JSONResponse(
                {"error": "Unauthorized — valid PSK required"},
                status_code=401,
            )

        next_url = quote(path, safe="")
        return RedirectResponse(url=f"/login?next={next_url}", status_code=302)
