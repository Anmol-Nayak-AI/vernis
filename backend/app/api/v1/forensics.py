from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.router import EDITOR_ROLES, _audit
from app.core.security import RequestPrincipal, get_request_principal, require_membership
from app.db.models import ArtworkAsset, ImageComparison, Job, ModelVersion
from app.db.session import get_db
from app.services.computer_vision import (
    InferenceInputError,
    analyze_asset,
    compare_assets,
    run_baseline_evaluation,
    similarity_search,
)

router = APIRouter(prefix="/api/v1")


class ComparisonCreate(BaseModel):
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID


def _asset(db: Session, organization_id: uuid.UUID, asset_id: uuid.UUID) -> ArtworkAsset:
    asset = db.scalar(
        select(ArtworkAsset).where(
            ArtworkAsset.organization_id == organization_id,
            ArtworkAsset.id == asset_id,
        )
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset was not found.")
    return asset


def _comparison_payload(comparison: ImageComparison) -> dict[str, Any]:
    return {
        "id": comparison.id,
        "source_asset_id": comparison.source_asset_id,
        "target_asset_id": comparison.target_asset_id,
        "model_version_id": comparison.model_version_id,
        "parameters": comparison.parameters,
        "scores": comparison.scores,
        "alignment": comparison.alignment,
        "regions": comparison.regions,
        "limitations": comparison.limitations,
        "output_artifacts": comparison.output_artifacts,
        "evaluation_status": comparison.evaluation_status,
        "processed_at": comparison.processed_at,
    }


@router.post(
    "/organizations/{organization_id}/forensics/assets/{asset_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["forensics"],
)
def analyze_visual_asset(
    organization_id: uuid.UUID,
    asset_id: uuid.UUID,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    asset = _asset(db, organization_id, asset_id)
    job = Job(
        organization_id=organization_id,
        kind="visual_fingerprint",
        status="running",
        progress=10,
        requested_by=principal.user_id,
        parameters={"asset_id": str(asset.id)},
    )
    db.add(job)
    db.flush()
    try:
        fingerprint, embedding = analyze_asset(db, asset)
    except InferenceInputError as exc:
        job.status = "failed"
        job.progress = 100
        job.error_code = "invalid_inference_input"
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    job.status = "succeeded"
    job.progress = 100
    _audit(db, organization_id, principal, "forensics.asset_analyzed", "asset", asset.id, request)
    db.commit()
    return {
        "job_id": job.id,
        "status": job.status,
        "input_asset_ids": [asset.id],
        "model_identifier": "vernis-visual-baseline",
        "model_version": "1.0.0",
        "fingerprint": {
            "sha256": fingerprint.cryptographic_hash,
            "perceptual_hash": fingerprint.perceptual_hash,
            "width": fingerprint.width,
            "height": fingerprint.height,
            "metadata": fingerprint.metadata_summary,
        },
        "embedding": {"id": embedding.id, "dimensions": embedding.dimensions, "norm": embedding.norm},
        "evaluation_status": "smoke_tested_not_domain_validated",
        "errors": [],
    }


@router.get("/organizations/{organization_id}/forensics/assets/{asset_id}/similar", tags=["forensics"])
def find_similar_assets(
    organization_id: uuid.UUID,
    asset_id: uuid.UUID,
    limit: int = Query(default=10, ge=1, le=50),
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal)
    asset = _asset(db, organization_id, asset_id)
    try:
        matches = similarity_search(db, asset, limit)
    except InferenceInputError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    db.commit()
    return {
        "input_asset_id": asset.id,
        "model_identifier": "vernis-visual-baseline",
        "model_version": "1.0.0",
        "matches": matches,
        "limitations": [
            "Results are restricted to this organization's indexed assets.",
            "Similarity is a retrieval signal, not a legal, attribution, or authenticity conclusion.",
        ],
    }


@router.post(
    "/organizations/{organization_id}/forensics/comparisons",
    status_code=status.HTTP_201_CREATED,
    tags=["forensics"],
)
def create_visual_comparison(
    organization_id: uuid.UUID,
    payload: ComparisonCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    source = _asset(db, organization_id, payload.source_asset_id)
    target = _asset(db, organization_id, payload.target_asset_id)
    try:
        comparison = compare_assets(db, source, target)
    except InferenceInputError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    _audit(db, organization_id, principal, "forensics.comparison_created", "image_comparison", comparison.id, request)
    db.commit()
    return _comparison_payload(comparison)


@router.get("/organizations/{organization_id}/forensics/comparisons", tags=["forensics"])
def list_visual_comparisons(
    organization_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    require_membership(db, organization_id, principal)
    rows = db.scalars(
        select(ImageComparison)
        .where(ImageComparison.organization_id == organization_id)
        .order_by(ImageComparison.processed_at.desc())
        .limit(100)
    ).all()
    return [_comparison_payload(row) for row in rows]


@router.get("/organizations/{organization_id}/forensics/models", tags=["forensics"])
def list_model_versions(
    organization_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    require_membership(db, organization_id, principal)
    models = db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all()
    return [
        {
            "id": model.id,
            "model_identifier": model.model_identifier,
            "version": model.version,
            "task": model.task,
            "implementation": model.implementation,
            "status": model.status,
            "parameters": model.parameters,
            "limitations": model.limitations,
            "evaluation_summary": model.evaluation_summary,
        }
        for model in models
    ]


@router.post(
    "/organizations/{organization_id}/forensics/evaluations/baseline",
    status_code=status.HTTP_201_CREATED,
    tags=["forensics"],
)
def evaluate_visual_baseline(
    organization_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, {"owner", "administrator"})
    run = run_baseline_evaluation(db)
    db.commit()
    return {
        "id": run.id,
        "fixture_name": run.fixture_name,
        "status": run.status,
        "sample_count": run.sample_count,
        "metrics": run.metrics,
        "notes": run.notes,
    }
