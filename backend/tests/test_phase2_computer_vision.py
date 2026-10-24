from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw


def _organization(client: TestClient, slug: str = "visual-lab") -> dict:
    response = client.post("/api/v1/organizations", json={"name": "Visual Lab", "slug": slug, "plan": "institution"})
    assert response.status_code == 201, response.text
    return response.json()


def _artwork(client: TestClient, organization_id: str, title: str) -> dict:
    response = client.post(f"/api/v1/organizations/{organization_id}/artworks", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


def _upload(client: TestClient, organization_id: str, artwork_id: str, image: Image.Image, name: str) -> dict:
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    payload = stream.getvalue()
    intent = client.post(
        f"/api/v1/organizations/{organization_id}/assets/upload-intents",
        json={
            "artwork_id": artwork_id,
            "file_name": name,
            "content_type": "image/png",
            "size_bytes": len(payload),
            "kind": "primary_image",
        },
    )
    assert intent.status_code == 201, intent.text
    response = client.put(intent.json()["upload_url"], content=payload, headers={"content-type": "image/png"})
    assert response.status_code == 200, response.text
    return response.json()


def test_real_fingerprint_similarity_and_registered_comparison(client: TestClient) -> None:
    organization = _organization(client)
    first_artwork = _artwork(client, organization["id"], "Study A")
    second_artwork = _artwork(client, organization["id"], "Study A detail")
    base = Image.new("RGB", (96, 96), (42, 68, 104))
    draw = ImageDraw.Draw(base)
    draw.rectangle((18, 22, 72, 76), fill=(204, 146, 75))
    shifted = Image.new("RGB", (96, 96), (42, 68, 104))
    shifted.paste(base.crop((10, 10, 86, 86)), (12, 11))
    first = _upload(client, organization["id"], first_artwork["id"], base, "study-a.png")
    second = _upload(client, organization["id"], second_artwork["id"], shifted, "study-a-shifted.png")

    analysis = client.post(
        f"/api/v1/organizations/{organization['id']}/forensics/assets/{first['id']}/analyze"
    )
    assert analysis.status_code == 202, analysis.text
    assert analysis.json()["fingerprint"]["perceptual_hash"]
    assert analysis.json()["embedding"]["dimensions"] == 96

    similar = client.get(
        f"/api/v1/organizations/{organization['id']}/forensics/assets/{first['id']}/similar"
    )
    assert similar.status_code == 200, similar.text
    assert similar.json()["matches"][0]["asset_id"] == second["id"]
    assert similar.json()["matches"][0]["combined_similarity"] > 0

    comparison = client.post(
        f"/api/v1/organizations/{organization['id']}/forensics/comparisons",
        json={"source_asset_id": first["id"], "target_asset_id": second["id"]},
    )
    assert comparison.status_code == 201, comparison.text
    assert comparison.json()["alignment"]["translation_x"] is not None
    assert comparison.json()["scores"]["latency_ms"] >= 0
    assert comparison.json()["evaluation_status"] == "unreviewed"
    assert comparison.json()["limitations"]


def test_evaluation_is_labeled_synthetic_and_not_domain_validation(client: TestClient) -> None:
    organization = _organization(client, "evaluation-lab")
    response = client.post(
        f"/api/v1/organizations/{organization['id']}/forensics/evaluations/baseline"
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["sample_count"] == 3
    assert "duplicate_detection_accuracy" in result["metrics"]
    assert any("synthetic" in note.lower() for note in result["notes"])
    models = client.get(f"/api/v1/organizations/{organization['id']}/forensics/models")
    assert models.status_code == 200
    assert models.json()[0]["status"] == "development"
    assert models.json()[0]["evaluation_summary"]["status"] == "smoke_tested_not_domain_validated"
