import hashlib

from fastapi import Request

CREATOR_COOKIE = "pws_creator"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_creator(request: Request) -> str | None:
    """Hash of the anonymous creator cookie, if the browser has one."""
    token = request.cookies.get(CREATOR_COOKIE)
    return hash_token(token) if token else None


def client_ip(request: Request) -> str:
    if request.app.state.settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
