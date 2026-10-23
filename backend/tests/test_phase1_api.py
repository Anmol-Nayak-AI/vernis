from __future__ import annotations

import hashlib
import io
import uuid

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.security import RequestPrincipal, ensure_user
from app.db.models import OrganizationMembership


def _create_organization(client: TestClient, slug: str = "north-gallery") -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={"name": "North Gallery", "slug": slug, "plan": "gallery"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_artwork(client: TestClient, organization_id: str) -> dict:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/artworks",
        json={
            "title": "Untitled study",
            "artist_attribution": "Claimed Artist",
            "attribution_status": "claimed",
            "creation_year_from": 1984,
            "creation_year_to": 1986,
            "date_precision": "range",
            "medium": "Oil on linen",
            "dimensions": {"height": 80, "width": 60, "unit": "cm"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_artwork_registry_enforces_tenant_and_role_boundaries(
    client: TestClient,
    db_session: Session,
    principal_state: dict[str, RequestPrincipal],
) -> None:
    organization = _create_organization(client)
    artwork = _create_artwork(client, organization["id"])

    principal_state["current"] = RequestPrincipal(
        user_id=uuid.UUID("20000000-0000-0000-0000-000000000002"),
        email="viewer@example.test",
    )
    denied = client.get(f"/api/v1/organizations/{organization['id']}/artworks/{artwork['id']}")
    assert denied.status_code == 404

    ensure_user(db_session, principal_state["current"])
    db_session.add(
        OrganizationMembership(
            organization_id=uuid.UUID(organization["id"]),
            user_id=principal_state["current"].user_id,
            role="viewer",
        )
    )
    db_session.commit()

    visible = client.get(f"/api/v1/organizations/{organization['id']}/artworks/{artwork['id']}")
    assert visible.status_code == 200
    forbidden_write = client.post(
        f"/api/v1/organizations/{organization['id']}/artworks",
        json={"title": "Viewer cannot create"},
    )
    assert forbidden_write.status_code == 403
    assert forbidden_write.json()["error"]["code"] == "http_403"
    assert forbidden_write.json()["error"]["request_id"]


def test_secure_image_upload_hashes_validates_and_uses_single_use_intent(client: TestClient) -> None:
    organization = _create_organization(client, "conservation-lab")
    artwork = _create_artwork(client, organization["id"])
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color=(126, 68, 45)).save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    intent = client.post(
        f"/api/v1/organizations/{organization['id']}/assets/upload-intents",
        json={
            "artwork_id": artwork["id"],
            "file_name": "condition.png",
            "content_type": "image/png",
            "size_bytes": len(image_bytes),
            "kind": "primary_image",
        },
    )
    assert intent.status_code == 201, intent.text
    upload = client.put(intent.json()["upload_url"], content=image_bytes, headers={"content-type": "image/png"})
    assert upload.status_code == 200, upload.text
    assert upload.json()["sha256"] == hashlib.sha256(image_bytes).hexdigest()
    assert upload.json()["status"] == "ready"

    replay = client.put(intent.json()["upload_url"], content=image_bytes, headers={"content-type": "image/png"})
    assert replay.status_code == 410

    asset_id = upload.json()["id"]
    signed = client.get(f"/api/v1/organizations/{organization['id']}/assets/{asset_id}/download")
    assert signed.status_code == 200
    downloaded = client.get(signed.json()["url"])
    assert downloaded.status_code == 200
    assert downloaded.content == image_bytes


def test_command_center_uses_real_registry_counts(client: TestClient) -> None:
    organization = _create_organization(client, "metrics-workspace")
    empty = client.get(f"/api/v1/organizations/{organization['id']}/command-center")
    assert empty.status_code == 200
    assert empty.json()["registered_artworks"] == 0
    assert empty.json()["onboarding_complete"] is False

    _create_artwork(client, organization["id"])
    populated = client.get(f"/api/v1/organizations/{organization['id']}/command-center")
    assert populated.status_code == 200
    assert populated.json()["registered_artworks"] == 1
    assert populated.json()["onboarding_complete"] is True
