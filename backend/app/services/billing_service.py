from __future__ import annotations

from fastapi import HTTPException, status

from app.auth import AuthPrincipal
from app.config import settings

PLAN_PRICES = {
    "creator": lambda: settings.stripe_price_creator,
    "studio": lambda: settings.stripe_price_studio,
    "enterprise": lambda: settings.stripe_price_enterprise,
}


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
