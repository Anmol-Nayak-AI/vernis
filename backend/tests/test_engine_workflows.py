from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.config import settings
from app.services.investigation_crew import ENGINE_AGENT_SPECS


def test_every_engine_has_a_narrow_domain_crew() -> None:
    assert set(ENGINE_AGENT_SPECS) == {
        "artsentinel", "artshield", "conservavision", "musegraph", "artvaluate", "arttransit"
    }
    assert {engine: len(specs) for engine, specs in ENGINE_AGENT_SPECS.items()} == {
        "artsentinel": 6,
        "artshield": 5,
        "conservavision": 5,
        "musegraph": 6,
        "artvaluate": 6,
        "arttransit": 5,
    }
    assert all(len({role for role, _, _ in specs}) == len(specs) for specs in ENGINE_AGENT_SPECS.values())


def _org(client: TestClient) -> dict:
    response = client.post("/api/v1/organizations", json={"name": "Engine Lab", "slug": "engine-lab", "plan": "institution"})
    assert response.status_code == 201, response.text
    return response.json()


def _artwork(client: TestClient, organization_id: str, title: str) -> dict:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/artworks",
        json={"title": title, "artist_attribution": "Attributed Artist", "attribution_status": "claimed", "medium": "Oil"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _asset(client: TestClient, organization_id: str, artwork_id: str, color: tuple[int, int, int], name: str) -> dict:
    image = Image.new("RGB", (96, 96), color)
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 18, 76, 78), fill=(210, 170, 92))
    output = io.BytesIO()
    image.save(output, format="PNG")
    data = output.getvalue()
    intent = client.post(
        f"/api/v1/organizations/{organization_id}/assets/upload-intents",
        json={"artwork_id": artwork_id, "file_name": name, "content_type": "image/png", "size_bytes": len(data), "kind": "condition_image"},
    )
    assert intent.status_code == 201, intent.text
    response = client.put(intent.json()["upload_url"], content=data, headers={"content-type": "image/png"})
    assert response.status_code == 200, response.text
    return response.json()


def test_artsentinel_evidence_review_report_and_passport(client: TestClient) -> None:
    organization = _org(client)
    artwork = _artwork(client, organization["id"], "Provenance Study")
    evidence = client.post(
        f"/api/v1/organizations/{organization['id']}/evidence",
        json={
            "artwork_id": artwork["id"],
            "title": "Owner-supplied transfer record",
            "kind": "ownership",
            "source_authority": "Owner archive",
            "extracted_text": "The supplied record states a transfer in 1987. This statement is not independently verified.",
            "sensitivity": "restricted",
        },
    )
    assert evidence.status_code == 201, evidence.text
    investigation = client.post(
        f"/api/v1/organizations/{organization['id']}/investigations",
        json={"artwork_id": artwork["id"], "title": "Attribution and provenance review"},
    )
    assert investigation.status_code == 201, investigation.text
    case_id = investigation.json()["id"]
    assert investigation.json()["status"] == "awaiting_review"
    assert "does not authenticate" in investigation.json()["limitations"][0]

    claim = client.post(
        f"/api/v1/organizations/{organization['id']}/cases/{case_id}/claims",
        json={
            "evidence_document_id": evidence.json()["id"],
            "claim_text": "The owner supplied a record that asserts a 1987 transfer.",
            "stance": "context",
            "source_locator": "Owner-supplied transfer record, passage 1",
        },
    )
    assert claim.status_code == 201, claim.text
    provenance = client.post(
        f"/api/v1/organizations/{organization['id']}/investigations/{case_id}/provenance",
        json={
            "event_type": "transfer",
            "date_from": "1987",
            "description": "Owner-asserted transfer; pending corroboration.",
            "verification_status": "asserted",
            "evidence_document_ids": [evidence.json()["id"]],
        },
    )
    assert provenance.status_code == 201, provenance.text
    report = client.post(f"/api/v1/organizations/{organization['id']}/cases/{case_id}/reports")
    assert report.status_code == 201, report.text
    assert report.json()["content"]["claims"][0]["evidence_document_id"] == evidence.json()["id"]
    assert "not authentication" in report.json()["content"]["disclaimer"]
    review = client.post(
        f"/api/v1/organizations/{organization['id']}/cases/{case_id}/reviews",
        json={"decision": "approved", "notes": "Approved as a due-diligence record, not an authenticity opinion."},
    )
    assert review.status_code == 201, review.text
    passport = client.post(f"/api/v1/organizations/{organization['id']}/artworks/{artwork['id']}/passport")
    assert passport.status_code == 201, passport.text
    assert passport.json()["snapshot"]["engine_history"][0]["engine"] == "artsentinel"
    assert not passport.json()["snapshot"]["evidence"][0].get("extracted_text")
    assert passport.json()["snapshot"]["human_reviews"][0]["decision"] == "approved"
    assert set(passport.json()["snapshot"]) >= {
        "rights_assertions", "condition_history", "valuation_research", "collection_records",
        "collection_relationships", "shipment_history", "human_reviews",
    }
    public_export = client.get(
        f"/api/v1/organizations/{organization['id']}/artworks/{artwork['id']}/passport/export",
        params={"format": "json", "scope": "public"},
    )
    assert public_export.status_code == 200, public_export.text
    assert public_export.json()["scope"] == "public"
    assert public_export.json()["snapshot"]["evidence"] == []
    pdf_export = client.get(
        f"/api/v1/organizations/{organization['id']}/artworks/{artwork['id']}/passport/export",
        params={"format": "pdf", "scope": "internal"},
    )
    assert pdf_export.status_code == 200, pdf_export.text
    assert pdf_export.headers["content-type"] == "application/pdf"
    assert pdf_export.content.startswith(b"%PDF")

    search = client.get(
        f"/api/v1/organizations/{organization['id']}/evidence",
        params={"query": "transfer 1987", "artwork_id": artwork["id"]},
    )
    assert search.status_code == 200, search.text
    assert search.json()[0]["id"] == evidence.json()["id"]
    assert search.json()[0]["hybrid_score"] > 0
    assert "passage 1" in search.json()[0]["citation"]

    no_asset_ocr = client.post(
        f"/api/v1/organizations/{organization['id']}/evidence/{evidence.json()['id']}/extract"
    )
    assert no_asset_ocr.status_code == 422
    assert "no linked image asset" in no_asset_ocr.json()["error"]["message"]

    previous = settings.external_ai_text_enabled
    settings.external_ai_text_enabled = False
    try:
        unavailable = client.post(
            f"/api/v1/organizations/{organization['id']}/investigations/{case_id}/agent-runs",
            json={"external_ai_consent": True},
        )
        assert unavailable.status_code == 503
    finally:
        settings.external_ai_text_enabled = previous


def test_artshield_conservation_collection_valuation_and_transit(client: TestClient) -> None:
    organization = _org(client)
    artwork = _artwork(client, organization["id"], "Shared Engine Work")
    related = _artwork(client, organization["id"], "Related Work")
    before = _asset(client, organization["id"], artwork["id"], (32, 54, 88), "before.png")
    after = _asset(client, organization["id"], artwork["id"], (38, 58, 91), "after.png")
    other = _asset(client, organization["id"], related["id"], (34, 56, 89), "related.png")

    shield = client.post(
        f"/api/v1/organizations/{organization['id']}/copyright/cases",
        json={"artwork_id": artwork["id"], "title": "Authorized collection scan", "source_asset_id": before["id"]},
    )
    assert shield.status_code == 201, shield.text
    assert shield.json()["source_scope"] == "organization_index"
    assert shield.json()["match_count"] >= 1

    inspection = client.post(
        f"/api/v1/organizations/{organization['id']}/conservation/inspections",
        json={
            "artwork_id": artwork["id"], "title": "Arrival condition inspection",
            "asset_id": after["id"], "baseline_asset_id": before["id"],
            "environment": {"lighting": "gallery ambient"},
        },
    )
    assert inspection.status_code == 201, inspection.text
    assert inspection.json()["comparison_id"]
    assert "none are confirmed damage" in inspection.json()["summary"]

    first_record = client.post(
        f"/api/v1/organizations/{organization['id']}/collections/records",
        json={"artwork_id": artwork["id"], "accession_number": "EL-001", "department": "Modern", "catalog_metadata": {"credit_line": "Gift"}},
    )
    second_record = client.post(
        f"/api/v1/organizations/{organization['id']}/collections/records",
        json={"artwork_id": related["id"], "accession_number": "EL-002", "department": "Modern"},
    )
    assert first_record.status_code == 201 and second_record.status_code == 201
    relationship = client.post(
        f"/api/v1/organizations/{organization['id']}/collections/relationships",
        json={"source_record_id": first_record.json()["id"], "target_record_id": second_record.json()["id"], "relationship_type": "same_series"},
    )
    assert relationship.status_code == 201, relationship.text
    assert relationship.json()["verification_status"] == "unverified"

    valuation = client.post(
        f"/api/v1/organizations/{organization['id']}/valuations",
        json={"artwork_id": artwork["id"], "title": "Comparable research"},
    )
    assert valuation.status_code == 201
    for index, price in enumerate([100_000, 120_000, 180_000], start=1):
        comparable = client.post(
            f"/api/v1/organizations/{organization['id']}/valuations/{valuation.json()['id']}/comparables",
            json={
                "source_name": "Licensed test fixture", "source_record_id": f"fixture-{index}",
                "work_title": f"Comparable {index}", "price_minor": price, "currency": "USD",
                "license_basis": "Synthetic test fixture; not a real transaction",
            },
        )
        assert comparable.status_code == 201, comparable.text
    estimate = client.post(f"/api/v1/organizations/{organization['id']}/valuations/{valuation.json()['id']}/analyze")
    assert estimate.status_code == 201, estimate.text
    assert estimate.json()["status"] == "research_estimate"
    assert estimate.json()["estimate_mid_minor"] == 120_000

    shipment = client.post(
        f"/api/v1/organizations/{organization['id']}/shipments",
        json={
            "artwork_id": artwork["id"], "title": "Museum loan shipment", "reference": "SHIP-001",
            "origin": "Engine Lab", "destination": "Partner Museum", "pre_asset_id": before["id"],
            "arrival_asset_id": after["id"], "packaging": {"crate": "climate-buffered"},
        },
    )
    assert shipment.status_code == 201, shipment.text
    assert shipment.json()["status"] == "review"
    custody = client.post(
        f"/api/v1/organizations/{organization['id']}/shipments/{shipment.json()['id']}/custody",
        json={
            "occurred_at": datetime.now(timezone.utc).isoformat(), "event_type": "handoff",
            "custodian": "Licensed carrier", "location": "Origin loading bay",
        },
    )
    assert custody.status_code == 201, custody.text
    assert other["id"]
