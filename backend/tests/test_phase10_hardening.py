from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings


def test_entitlements_usage_security_headers_and_metrics(client: TestClient) -> None:
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Hardened Workspace", "slug": "hardened-workspace", "plan": "professional"},
    )
    assert organization.status_code == 201
    organization_id = organization.json()["id"]
    artwork = client.post(
        f"/api/v1/organizations/{organization_id}/artworks",
        json={"title": "Measured work"},
    )
    assert artwork.status_code == 201
    workflow = client.post(
        f"/api/v1/organizations/{organization_id}/valuations",
        json={"artwork_id": artwork.json()["id"], "title": "Metered research"},
    )
    assert workflow.status_code == 201

    billing = client.get(f"/api/v1/organizations/{organization_id}/billing")
    assert billing.status_code == 200, billing.text
    assert billing.json()["plan"] == "professional"
    assert billing.json()["usage"]["workflow_case_created"] == 1
    limits = {row["key"]: row["limit"] for row in billing.json()["entitlements"]}
    assert limits["workflow_cases_monthly"] == 250

    original_secret = settings.stripe_secret_key
    settings.stripe_secret_key = ""
    try:
        checkout = client.post(
            f"/api/v1/organizations/{organization_id}/billing/checkout",
            json={"plan": "professional"},
        )
        assert checkout.status_code == 503
    finally:
        settings.stripe_secret_key = original_secret

    assert billing.headers["x-content-type-options"] == "nosniff"
    assert "camera=()" in billing.headers["permissions-policy"]
    assert billing.headers["x-request-id"]
    assert int(billing.headers["x-ratelimit-remaining"]) >= 0
    metrics = client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert "vernis_http_requests_total" in metrics.text
