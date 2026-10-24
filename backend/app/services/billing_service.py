from __future__ import annotations

from fastapi import HTTPException, status

from app.auth import AuthPrincipal
from app.config import settings
from app.core.security import RequestPrincipal
from app.db.models import Entitlement, Organization
from sqlalchemy import select
from sqlalchemy.orm import Session

PLAN_PRICES = {
    "creator": lambda: settings.stripe_price_creator,
    "studio": lambda: settings.stripe_price_studio,
    "enterprise": lambda: settings.stripe_price_enterprise,
}

SAAS_PLAN_PRICES = {
    "artist": lambda: settings.stripe_price_artist or settings.stripe_price_creator,
    "professional": lambda: settings.stripe_price_professional or settings.stripe_price_studio,
    "gallery": lambda: settings.stripe_price_gallery or settings.stripe_price_studio,
    "institution": lambda: settings.stripe_price_institution or settings.stripe_price_studio,
    "enterprise": lambda: settings.stripe_price_enterprise,
}

PLAN_ENTITLEMENTS: dict[str, dict[str, int | None]] = {
    "artist": {"workflow_cases_monthly": 25, "storage_bytes": 5 * 1024**3, "members": 1},
    "professional": {"workflow_cases_monthly": 250, "storage_bytes": 50 * 1024**3, "members": 5},
    "gallery": {"workflow_cases_monthly": 1000, "storage_bytes": 250 * 1024**3, "members": 25},
    "institution": {"workflow_cases_monthly": 5000, "storage_bytes": 2 * 1024**4, "members": 100},
    "enterprise": {"workflow_cases_monthly": None, "storage_bytes": None, "members": None},
}


def sync_plan_entitlements(db: Session, organization: Organization) -> list[Entitlement]:
    configured = PLAN_ENTITLEMENTS[organization.plan]
    existing = {
        row.key: row
        for row in db.scalars(select(Entitlement).where(Entitlement.organization_id == organization.id)).all()
    }
    rows: list[Entitlement] = []
    for key, limit in configured.items():
        row = existing.get(key) or Entitlement(organization_id=organization.id, key=key)
        row.enabled = True
        row.limit_value = limit
        row.metadata_fields = {"source": "plan_catalog", "plan": organization.plan}
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def create_organization_checkout(
    organization: Organization,
    plan: str,
    principal: RequestPrincipal,
) -> dict[str, str]:
    if plan not in SAAS_PLAN_PRICES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown billing plan.")
    price_id = SAAS_PLAN_PRICES[plan]()
    if not settings.stripe_secret_key or not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"The {plan} checkout plan is not configured.",
        )
    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.frontend_url.rstrip('/')}?billing=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url.rstrip('/')}?billing=cancelled",
            customer_email=principal.email,
            client_reference_id=str(organization.id),
            metadata={
                "organization_id": str(organization.id),
                "requested_by": str(principal.user_id),
                "plan": plan,
            },
            subscription_data={"metadata": {"organization_id": str(organization.id), "plan": plan}},
            allow_promotion_codes=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The billing provider could not start checkout.",
        ) from exc
    if not checkout.url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The billing provider returned no checkout URL.",
        )
    return {"url": checkout.url, "session_id": checkout.id}


def create_checkout_session(plan: str, principal: AuthPrincipal) -> dict[str, str]:
    if plan not in PLAN_PRICES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown billing plan.")
    price_id = PLAN_PRICES[plan]()
    if not settings.stripe_secret_key or not price_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"The {plan} checkout plan is not configured yet.")

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.frontend_url.rstrip('/')}?billing=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url.rstrip('/')}?billing=cancelled",
            customer_email=principal.email,
            client_reference_id=principal.user_id,
            metadata={"user_id": principal.user_id or "", "plan": plan},
            allow_promotion_codes=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The billing provider could not start checkout.") from exc

    if not checkout.url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The billing provider returned no checkout URL.")
    return {"url": checkout.url, "session_id": checkout.id}
