from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthPrincipal, get_current_user
from app.config import settings
from app.db.models import OrganizationMembership, User


@dataclass(frozen=True)
class RequestPrincipal:
    user_id: uuid.UUID
    email: str | None
    is_development: bool = False


def get_request_principal(principal: AuthPrincipal = Depends(get_current_user)) -> RequestPrincipal:
    if principal.user_id:
        try:
            return RequestPrincipal(user_id=uuid.UUID(principal.user_id), email=principal.email)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user subject.") from exc
    if settings.environment == "development" and not settings.auth_required:
        return RequestPrincipal(
            user_id=uuid.UUID(settings.development_user_id),
            email=settings.development_user_email,
            is_development=True,
        )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required.")


def ensure_user(db: Session, principal: RequestPrincipal) -> User:
    user = db.get(User, principal.user_id)
    if user is None:
        user = User(id=principal.user_id, email=principal.email, display_name=(principal.email or "Member").split("@")[0])
        db.add(user)
        db.flush()
    elif principal.email and user.email != principal.email:
        user.email = principal.email
    return user


def require_membership(
    db: Session,
    organization_id: uuid.UUID,
    principal: RequestPrincipal,
    allowed_roles: set[str] | None = None,
) -> OrganizationMembership:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == principal.user_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization was not found.")
    if allowed_roles and membership.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot perform this action.")
    return membership
