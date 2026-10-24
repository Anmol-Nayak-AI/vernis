from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import RequestPrincipal, get_request_principal, require_membership
from app.db.models import BillingWebhookEvent, Organization, Subscription, UsageEvent
from app.db.session import get_db
from app.services.billing_service import (
    PLAN_ENTITLEMENTS,
    create_organization_checkout,
    sync_plan_entitlements,
)

router = APIRouter(prefix="/api/v1")


class CheckoutCreate(BaseModel):
    plan: Literal["artist", "professional", "gallery", "institution", "enterprise"]


@router.get("/organizations/{organization_id}/billing", tags=["billing"])
def billing_status(
    organization_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization was not found.")
    entitlements = sync_plan_entitlements(db, organization)
    subscription = db.scalar(select(Subscription).where(Subscription.organization_id == organization_id))
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    usage = db.execute(
        select(UsageEvent.meter, func.sum(UsageEvent.quantity))
        .where(UsageEvent.organization_id == organization_id, UsageEvent.occurred_at >= month_start)
        .group_by(UsageEvent.meter)
    ).all()
    db.commit()
    return {
        "plan": organization.plan,
        "subscription": {
            "status": subscription.status if subscription else "none",
            "provider": subscription.provider if subscription else None,
            "current_period_end": subscription.current_period_end if subscription else None,
            "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False,
        },
        "entitlements": [
            {"key": row.key, "enabled": row.enabled, "limit": row.limit_value, "metadata": row.metadata_fields}
            for row in entitlements
        ],
        "usage": {meter: int(quantity or 0) for meter, quantity in usage},
        "billing_provider_configured": bool(settings.stripe_secret_key and settings.stripe_webhook_secret),
    }


@router.post("/organizations/{organization_id}/billing/checkout", tags=["billing"])
def organization_checkout(
    organization_id: uuid.UUID,
    payload: CheckoutCreate,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    require_membership(db, organization_id, principal, {"owner", "administrator"})
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization was not found.")
    return create_organization_checkout(organization, payload.plan, principal)


@router.post("/billing/webhooks/stripe", tags=["billing"], include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe webhooks are not configured.")
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe signature is required.")
    payload = await request.body()
    try:
        import stripe

        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe signature validation failed.") from exc
    event_id = str(event["id"])
    if db.scalar(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.provider == "stripe",
            BillingWebhookEvent.provider_event_id == event_id,
        )
    ):
        return {"received": True}
    record = BillingWebhookEvent(
        provider="stripe",
        provider_event_id=event_id,
        event_type=str(event["type"]),
        status="processing",
    )
    db.add(record)
    data = event["data"]["object"]
    metadata = dict(data.get("metadata") or {})
    organization_id_value = metadata.get("organization_id") or data.get("client_reference_id")
    try:
        target_organization_id = uuid.UUID(str(organization_id_value)) if organization_id_value else None
    except ValueError:
        target_organization_id = None
    if target_organization_id:
        organization = db.get(Organization, target_organization_id)
        if organization:
            plan = metadata.get("plan", organization.plan)
            if plan not in PLAN_ENTITLEMENTS:
                plan = organization.plan
            subscription = db.scalar(
                select(Subscription).where(Subscription.organization_id == target_organization_id)
            ) or Subscription(organization_id=target_organization_id, plan=plan)
            organization.plan = plan
            subscription.plan = plan
            subscription.provider_customer_id = str(data.get("customer")) if data.get("customer") else subscription.provider_customer_id
            if str(event["type"]).startswith("customer.subscription"):
                subscription.provider_subscription_id = str(data.get("id"))
                provider_status = str(data.get("status", "incomplete"))
                subscription.status = "cancelled" if provider_status == "canceled" else provider_status
                period_end = data.get("current_period_end")
                subscription.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc) if period_end else None
                subscription.cancel_at_period_end = bool(data.get("cancel_at_period_end", False))
            elif event["type"] == "checkout.session.completed":
                subscription.provider_subscription_id = str(data.get("subscription")) if data.get("subscription") else None
                subscription.status = "active"
            db.add(subscription)
            sync_plan_entitlements(db, organization)
    record.status = "processed"
    record.processed_at = datetime.now(timezone.utc)
    db.commit()
    return {"received": True}
