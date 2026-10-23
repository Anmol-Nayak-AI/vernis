from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import Header, HTTPException, status

from app.config import settings


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: Optional[str] = None
    email: Optional[str] = None
    app_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def authenticated(self) -> bool:
        return self.user_id is not None


def _verify_access_token(token: str) -> AuthPrincipal:
    if not settings.supabase_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is not configured on the server.")

    try:
        import jwt

        issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
        jwks_client = jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=issuer,
            options={"require": ["exp", "sub"]},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.") from exc

    return AuthPrincipal(
        user_id=claims.get("sub"),
        email=claims.get("email"),
        app_metadata=claims.get("app_metadata") or {},
    )


def get_current_user(authorization: Optional[str] = Header(default=None)) -> AuthPrincipal:
    if not authorization:
        if settings.auth_required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required.")
        return AuthPrincipal()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Use a Bearer access token.")
    return _verify_access_token(token)


def require_user(authorization: Optional[str] = Header(default=None)) -> AuthPrincipal:
    principal = get_current_user(authorization)
    if not principal.authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required.")
    return principal
