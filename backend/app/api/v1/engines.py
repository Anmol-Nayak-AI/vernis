from __future__ import annotations

import statistics
import io
import json
from html import escape
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.v1.router import EDITOR_ROLES, _audit
from app.core.security import RequestPrincipal, get_request_principal, require_membership
from app.db.models import (
    Artwork,
    ArtworkAsset,
    ArtworkPassport,
    CollectionRecord,
    CollectionRelationship,
    ConditionInspection,
    AgentRun,
    CopyrightMatch,
    CustodyEvent,
    DamageFinding,
    EngineCase,
    EvidenceClaim,
    EvidenceDocument,
    HumanReview,
    Job,
    MarketComparable,
    Organization,
    ProvenanceEvent,
    ReportVersion,
    Shipment,
    ToolExecution,
    UsageEvent,
    ValuationReport,
)
from app.db.session import get_db
from app.config import settings
from app.services.computer_vision import InferenceInputError, compare_assets, similarity_search
from app.services.billing_service import PLAN_ENTITLEMENTS
from app.services.evidence import hybrid_search, ocr_evidence_asset, rebuild_chunks

router = APIRouter(prefix="/api/v1/organizations/{organization_id}")
ENGINES = {"artsentinel", "artshield", "conservavision", "musegraph", "artvaluate", "arttransit"}
ENGINE_LIMITATIONS = {
    "artsentinel": [
        "This workflow supports due diligence and does not authenticate an artwork.",
        "Visual similarity cannot establish authorship or forgery.",
    ],
    "artshield": [
        "Visual similarity does not establish copyright ownership or infringement.",
        "No legal notice or accusation is generated automatically.",
    ],
    "conservavision": [
        "Ordinary photographs cannot reveal all material deterioration.",
        "Observable changes may be caused by lighting, camera, viewpoint, or registration error.",
        "Treatment decisions require a qualified conservator.",
    ],
    "musegraph": [
        "Extracted or imported metadata remains unverified until a cataloger reviews it.",
    ],
    "artvaluate": [
        "Research estimates are not certified appraisals or investment advice.",
        "Only user-supplied, licensed comparable records are included.",
    ],
    "arttransit": [
        "Visual change analysis does not determine when damage occurred or legal liability.",
        "Insurance claim decisions remain with qualified humans and insurers.",
    ],
}


class CaseCreate(BaseModel):
    artwork_id: uuid.UUID
    title: str = Field(min_length=1, max_length=240)
    input_data: dict[str, Any] = Field(default_factory=dict)


class EvidenceCreate(BaseModel):
    artwork_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=320)
    kind: Literal[
        "certificate", "catalog", "ownership", "rights", "condition_report", "shipment",
        "market_record", "artist_statement", "other",
    ] = "other"
    source_uri: HttpUrl | None = None
    source_authority: str | None = Field(default=None, max_length=320)
    extracted_text: str | None = Field(default=None, max_length=100_000)
    sensitivity: Literal["internal", "restricted", "public"] = "internal"
    external_ai_consent: bool = False
    metadata_fields: dict[str, Any] = Field(default_factory=dict)


class ClaimCreate(BaseModel):
    evidence_document_id: uuid.UUID | None = None
    claim_text: str = Field(min_length=2, max_length=20_000)
    stance: Literal["supports", "contradicts", "context", "unresolved"] = "unresolved"
    confidence: int | None = Field(default=None, ge=0, le=100)
    source_locator: str | None = Field(default=None, max_length=320)


class ReviewCreate(BaseModel):
    decision: Literal["approved", "changes_requested", "rejected"]
    notes: str = Field(min_length=3, max_length=20_000)


class AgentRunCreate(BaseModel):
    external_ai_consent: bool


class ProvenanceCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=80)
    date_from: str | None = Field(default=None, max_length=32)
    date_to: str | None = Field(default=None, max_length=32)
    actor_name: str | None = Field(default=None, max_length=320)
    place_name: str | None = Field(default=None, max_length=320)
    description: str = Field(min_length=2, max_length=20_000)
    verification_status: Literal["asserted", "supported", "verified", "disputed"] = "asserted"
    evidence_document_ids: list[uuid.UUID] = Field(default_factory=list)


class ShieldScanCreate(CaseCreate):
    source_asset_id: uuid.UUID


class InspectionCreate(CaseCreate):
    asset_id: uuid.UUID
    baseline_asset_id: uuid.UUID | None = None
    inspected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    environment: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=20_000)


class CollectionRecordCreate(BaseModel):
    artwork_id: uuid.UUID
    accession_number: str = Field(min_length=1, max_length=160)
    department: str | None = Field(default=None, max_length=240)
    location: str | None = Field(default=None, max_length=320)
    catalog_metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipCreate(BaseModel):
    source_record_id: uuid.UUID
    target_record_id: uuid.UUID
    relationship_type: str = Field(min_length=2, max_length=120)
    evidence_document_ids: list[uuid.UUID] = Field(default_factory=list)


class ComparableCreate(BaseModel):
    source_name: str = Field(min_length=2, max_length=240)
    source_uri: HttpUrl | None = None
    source_record_id: str = Field(min_length=1, max_length=240)
    artist_name: str | None = Field(default=None, max_length=240)
    work_title: str = Field(min_length=1, max_length=320)
    sold_at: datetime | None = None
    price_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    attributes: dict[str, Any] = Field(default_factory=dict)
    license_basis: str = Field(min_length=3, max_length=320)


class ShipmentCreate(CaseCreate):
    reference: str = Field(min_length=1, max_length=160)
    origin: str = Field(min_length=2, max_length=320)
    destination: str = Field(min_length=2, max_length=320)
    carrier: str | None = Field(default=None, max_length=320)
    packaging: dict[str, Any] = Field(default_factory=dict)
    pre_asset_id: uuid.UUID | None = None
    arrival_asset_id: uuid.UUID | None = None


class CustodyCreate(BaseModel):
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = Field(min_length=2, max_length=80)
    custodian: str = Field(min_length=2, max_length=320)
    location: str = Field(min_length=2, max_length=320)
    notes: str | None = Field(default=None, max_length=20_000)
    evidence_document_ids: list[uuid.UUID] = Field(default_factory=list)


def _artwork(db: Session, organization_id: uuid.UUID, artwork_id: uuid.UUID) -> Artwork:
    row = db.scalar(select(Artwork).where(Artwork.organization_id == organization_id, Artwork.id == artwork_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Artwork was not found.")
    return row


def _asset(db: Session, organization_id: uuid.UUID, asset_id: uuid.UUID) -> ArtworkAsset:
    row = db.scalar(
        select(ArtworkAsset).where(
            ArtworkAsset.organization_id == organization_id,
            ArtworkAsset.id == asset_id,
            ArtworkAsset.status == "ready",
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Ready asset was not found.")
    return row


def _case(db: Session, organization_id: uuid.UUID, case_id: uuid.UUID, engine: str | None = None) -> EngineCase:
    filters = [EngineCase.organization_id == organization_id, EngineCase.id == case_id]
    if engine:
        filters.append(EngineCase.engine == engine)
    row = db.scalar(select(EngineCase).where(*filters))
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow case was not found.")
    return row


def _new_case(
    db: Session,
    organization_id: uuid.UUID,
    engine: str,
    payload: CaseCreate,
    principal: RequestPrincipal,
) -> EngineCase:
    _artwork(db, organization_id, payload.artwork_id)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization was not found.")
    monthly_limit = PLAN_ENTITLEMENTS[organization.plan]["workflow_cases_monthly"]
    if monthly_limit is not None:
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        used = db.scalar(
            select(func.count()).select_from(EngineCase).where(
                EngineCase.organization_id == organization_id,
                EngineCase.created_at >= month_start,
            )
        ) or 0
        if used >= monthly_limit:
            raise HTTPException(status_code=429, detail="The organization has reached its monthly workflow entitlement.")
    row = EngineCase(
        organization_id=organization_id,
        artwork_id=payload.artwork_id,
        engine=engine,
        title=payload.title.strip(),
        input_data=payload.input_data,
        limitations=ENGINE_LIMITATIONS[engine],
        created_by=principal.user_id,
    )
    db.add(row)
    db.flush()
    db.add(
        UsageEvent(
            organization_id=organization_id,
            actor_id=principal.user_id,
            meter="workflow_case_created",
            quantity=1,
            idempotency_key=f"case-created:{row.id}",
            resource_type="engine_case",
            resource_id=row.id,
            event_metadata={"engine": engine, "plan": organization.plan},
        )
    )
    return row


def _case_payload(row: EngineCase) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "organization_id": str(row.organization_id),
        "artwork_id": str(row.artwork_id),
        "engine": row.engine,
        "title": row.title,
        "status": row.status,
        "risk_level": row.risk_level,
        "input_data": row.input_data,
        "summary": row.summary,
        "limitations": row.limitations,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/cases", tags=["engines"])
def list_cases(
    organization_id: uuid.UUID,
    engine: str | None = Query(default=None),
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    require_membership(db, organization_id, principal)
    if engine and engine not in ENGINES:
        raise HTTPException(status_code=422, detail="Unknown engine.")
    query = select(EngineCase).where(EngineCase.organization_id == organization_id)
    if engine:
        query = query.where(EngineCase.engine == engine)
    rows = db.scalars(query.order_by(EngineCase.created_at.desc()).limit(200)).all()
    return [_case_payload(row) for row in rows]


@router.get("/cases/{case_id}", tags=["engines"])
def get_case(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal)
    row = _case(db, organization_id, case_id)
    claims = db.scalars(select(EvidenceClaim).where(EvidenceClaim.case_id == row.id)).all()
    reviews = db.scalars(select(HumanReview).where(HumanReview.case_id == row.id)).all()
    reports = db.scalars(select(ReportVersion).where(ReportVersion.case_id == row.id).order_by(ReportVersion.version.desc())).all()
    return {
        **_case_payload(row),
        "claims": [
            {"id": claim.id, "claim_text": claim.claim_text, "stance": claim.stance, "confidence": claim.confidence,
             "review_status": claim.review_status, "evidence_document_id": claim.evidence_document_id,
             "source_locator": claim.source_locator}
            for claim in claims
        ],
        "reviews": [
            {"id": review.id, "decision": review.decision, "notes": review.notes,
             "reviewer_id": review.reviewer_id, "created_at": review.created_at}
            for review in reviews
        ],
        "reports": [
            {"id": report.id, "version": report.version, "title": report.title,
             "review_status": report.review_status, "created_at": report.created_at}
            for report in reports
        ],
    }


@router.post("/investigations", status_code=201, tags=["investigations"])
def create_investigation(
    organization_id: uuid.UUID,
    payload: CaseCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    row = _new_case(db, organization_id, "artsentinel", payload, principal)
    artwork_assets = db.scalars(
        select(ArtworkAsset).where(
            ArtworkAsset.organization_id == organization_id,
            ArtworkAsset.artwork_id == payload.artwork_id,
            ArtworkAsset.status == "ready",
        )
    ).all()
    visual_findings: list[dict[str, Any]] = []
    if artwork_assets:
        try:
            visual_findings = similarity_search(db, artwork_assets[0], 10)
        except InferenceInputError:
            visual_findings = []
    row.input_data = {**row.input_data, "visual_retrieval": visual_findings}
    row.status = "awaiting_review"
    row.summary = "Preliminary evidence workspace created. No authenticity determination has been made."
    _audit(db, organization_id, principal, "artsentinel.investigation_created", "engine_case", row.id, request)
    db.commit()
    return _case_payload(row)


@router.post("/investigations/{case_id}/provenance", status_code=201, tags=["investigations"])
def add_provenance_event(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    payload: ProvenanceCreate,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    case = _case(db, organization_id, case_id, "artsentinel")
    row = ProvenanceEvent(
        organization_id=organization_id,
        artwork_id=case.artwork_id,
        **payload.model_dump(exclude={"evidence_document_ids"}),
        evidence_document_ids=[str(value) for value in payload.evidence_document_ids],
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "verification_status": row.verification_status, "description": row.description}


@router.post("/investigations/{case_id}/agent-runs", status_code=202, tags=["agents"])
@router.post("/cases/{case_id}/agent-runs", status_code=202, tags=["agents"])
def start_investigation_crew(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    payload: AgentRunCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    case = _case(db, organization_id, case_id)
    if not payload.external_ai_consent:
        raise HTTPException(status_code=422, detail="Explicit external AI processing consent is required for this run.")
    if not settings.external_ai_text_enabled or not settings.crew_enabled or not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="The consent-gated CrewAI service is not configured.")
    case.input_data = {**case.input_data, "external_ai_consent": True}
    case.status = "queued"
    job = Job(
        organization_id=organization_id,
        kind=f"{case.engine}_crew",
        status="queued",
        progress=0,
        requested_by=principal.user_id,
        parameters={"case_id": str(case.id), "external_ai_consent": True},
    )
    db.add(job)
    db.flush()
    run = AgentRun(
        organization_id=organization_id,
        case_id=case.id,
        job_id=job.id,
        crew_name=f"{case.engine}_evidence_review_v1",
        status="queued",
        model_identifier=settings.crew_model,
        input_summary={"case_id": str(case.id), "text_evidence_only": True},
    )
    db.add(run)
    db.flush()
    _audit(db, organization_id, principal, f"{case.engine}.agent_run_queued", "agent_run", run.id, request)
    db.commit()
    try:
        from app.workers.celery_app import run_engine_case

        run_engine_case.delay(str(run.id))
    except Exception as exc:
        run.status = "failed"
        run.errors = [{"code": "queue_unavailable", "message": "Agent queue is unavailable."}]
        job.status = "failed"
        job.error_code = "queue_unavailable"
        case.status = "failed"
        db.commit()
        raise HTTPException(status_code=503, detail="The agent queue is unavailable.") from exc
    return {"agent_run_id": run.id, "job_id": job.id, "status": run.status, "model_identifier": run.model_identifier}


@router.get("/agents/runs", tags=["agents"])
def list_agent_runs(
    organization_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    require_membership(db, organization_id, principal)
    rows = db.scalars(
        select(AgentRun).where(AgentRun.organization_id == organization_id).order_by(AgentRun.created_at.desc()).limit(100)
    ).all()
    return [
        {"id": row.id, "case_id": row.case_id, "crew_name": row.crew_name, "status": row.status,
         "model_identifier": row.model_identifier, "token_usage": row.token_usage,
         "estimated_cost": row.estimated_cost, "errors": row.errors, "created_at": row.created_at,
         "started_at": row.started_at, "completed_at": row.completed_at}
        for row in rows
    ]


@router.get("/agents/runs/{run_id}", tags=["agents"])
def get_agent_run(
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal)
    run = db.scalar(select(AgentRun).where(AgentRun.organization_id == organization_id, AgentRun.id == run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run was not found.")
    tools = db.scalars(select(ToolExecution).where(ToolExecution.agent_run_id == run.id).order_by(ToolExecution.started_at)).all()
    return {
        "id": run.id, "case_id": run.case_id, "crew_name": run.crew_name, "status": run.status,
        "model_identifier": run.model_identifier, "input_summary": run.input_summary, "output": run.output,
        "token_usage": run.token_usage, "estimated_cost": run.estimated_cost, "errors": run.errors,
        "tool_executions": [
            {"id": tool.id, "agent_name": tool.agent_name, "tool_name": tool.tool_name,
             "status": tool.status, "input_summary": tool.input_summary,
             "output_summary": tool.output_summary, "error_code": tool.error_code,
             "started_at": tool.started_at, "completed_at": tool.completed_at}
            for tool in tools
        ],
    }


@router.post("/copyright/cases", status_code=201, tags=["copyright"])
def create_copyright_case(
    organization_id: uuid.UUID,
    payload: ShieldScanCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    source = _asset(db, organization_id, payload.source_asset_id)
    if source.artwork_id != payload.artwork_id:
        raise HTTPException(status_code=422, detail="Source asset does not belong to the selected artwork.")
    case = _new_case(db, organization_id, "artshield", payload, principal)
    candidates = similarity_search(db, source, 50)
    for candidate in candidates:
        combined = float(candidate["combined_similarity"])
        hash_score = float(candidate["perceptual_hash_similarity"])
        classification = "near_duplicate" if combined >= 0.92 and hash_score >= 0.85 else "style_similarity"
        db.add(
            CopyrightMatch(
                organization_id=organization_id,
                case_id=case.id,
                source_asset_id=source.id,
                matched_asset_id=uuid.UUID(candidate["asset_id"]),
                similarity_scores=candidate,
                source_record={"scope": "organization_index", "authorized": True},
                classification=classification,
            )
        )
    case.input_data = {
        **case.input_data,
        "visual_retrieval": candidates,
        "authorized_source_scope": "organization_index",
    }
    case.status = "awaiting_review"
    case.summary = f"{len(candidates)} candidate(s) found in the authorized organization index. Human rights review is required."
    _audit(db, organization_id, principal, "artshield.case_created", "engine_case", case.id, request)
    db.commit()
    return {**_case_payload(case), "match_count": len(candidates), "source_scope": "organization_index"}


@router.post("/conservation/inspections", status_code=201, tags=["conservation"])
def create_condition_inspection(
    organization_id: uuid.UUID,
    payload: InspectionCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    asset = _asset(db, organization_id, payload.asset_id)
    if asset.artwork_id != payload.artwork_id:
        raise HTTPException(status_code=422, detail="Inspection asset does not belong to the selected artwork.")
    case = _new_case(db, organization_id, "conservavision", payload, principal)
    inspection = ConditionInspection(
        organization_id=organization_id,
        case_id=case.id,
        asset_id=asset.id,
        inspected_at=payload.inspected_at,
        environment=payload.environment,
        notes=payload.notes,
    )
    db.add(inspection)
    db.flush()
    comparison_id = None
    findings: list[DamageFinding] = []
    if payload.baseline_asset_id:
        baseline = _asset(db, organization_id, payload.baseline_asset_id)
        if baseline.artwork_id != payload.artwork_id:
            raise HTTPException(status_code=422, detail="Baseline asset does not belong to the selected artwork.")
        comparison = compare_assets(db, baseline, asset)
        comparison_id = comparison.id
        case.input_data = {
            **case.input_data,
            "comparison": {
                "id": str(comparison.id),
                "scores": comparison.scores,
                "regions": comparison.regions,
                "limitations": comparison.limitations,
            },
        }
        for region in comparison.regions:
            finding = DamageFinding(
                organization_id=organization_id,
                inspection_id=inspection.id,
                finding_type="observable_visual_change",
                normalized_region=region["normalized_box"],
                measurements={
                    "pixel_fraction": region["pixel_fraction"],
                    "comparison_id": str(comparison.id),
                },
                confidence=None,
                limitations=comparison.limitations,
            )
            db.add(finding)
            findings.append(finding)
    case.status = "awaiting_review"
    case.summary = f"Inspection recorded with {len(findings)} observable change region(s); none are confirmed damage."
    _audit(db, organization_id, principal, "conservavision.inspection_created", "engine_case", case.id, request)
    db.commit()
    return {**_case_payload(case), "inspection_id": inspection.id, "comparison_id": comparison_id, "finding_count": len(findings)}


@router.post("/collections/records", status_code=201, tags=["collections"])
def create_collection_record(
    organization_id: uuid.UUID,
    payload: CollectionRecordCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    _artwork(db, organization_id, payload.artwork_id)
    supplied = [payload.department, payload.location, *payload.catalog_metadata.values()]
    completeness = min(100, round(sum(value not in (None, "", [], {}) for value in supplied) / max(1, len(supplied)) * 100))
    row = CollectionRecord(organization_id=organization_id, completeness_score=completeness, **payload.model_dump())
    db.add(row)
    db.flush()
    case = _new_case(
        db,
        organization_id,
        "musegraph",
        CaseCreate(artwork_id=payload.artwork_id, title=f"Catalog review · {payload.accession_number}"),
        principal,
    )
    case.status = "awaiting_review"
    case.summary = "Collection metadata is stored as supplied and remains in the catalog review queue."
    case.input_data = {
        **case.input_data,
        "collection_record_id": str(row.id),
        "completeness_score": completeness,
        "review_status": row.review_status,
    }
    _audit(db, organization_id, principal, "musegraph.record_created", "collection_record", row.id, request)
    db.commit()
    return {"id": row.id, "case_id": case.id, "completeness_score": completeness, "review_status": row.review_status}


@router.post("/collections/relationships", status_code=201, tags=["collections"])
def create_collection_relationship(
    organization_id: uuid.UUID,
    payload: RelationshipCreate,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    records = db.scalars(
        select(CollectionRecord).where(
            CollectionRecord.organization_id == organization_id,
            CollectionRecord.id.in_([payload.source_record_id, payload.target_record_id]),
        )
    ).all()
    if len(records) != 2 or payload.source_record_id == payload.target_record_id:
        raise HTTPException(status_code=422, detail="Two distinct collection records are required.")
    row = CollectionRelationship(
        organization_id=organization_id,
        **payload.model_dump(exclude={"evidence_document_ids"}),
        evidence_document_ids=[str(value) for value in payload.evidence_document_ids],
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "verification_status": row.verification_status}


@router.post("/valuations", status_code=201, tags=["valuations"])
def create_valuation_case(
    organization_id: uuid.UUID,
    payload: CaseCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    case = _new_case(db, organization_id, "artvaluate", payload, principal)
    case.summary = "No licensed comparable records have been supplied."
    _audit(db, organization_id, principal, "artvaluate.case_created", "engine_case", case.id, request)
    db.commit()
    return _case_payload(case)


@router.post("/valuations/{case_id}/comparables", status_code=201, tags=["valuations"])
def add_market_comparable(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    payload: ComparableCreate,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    _case(db, organization_id, case_id, "artvaluate")
    row = MarketComparable(
        organization_id=organization_id,
        case_id=case_id,
        **payload.model_dump(exclude={"source_uri"}),
        source_uri=str(payload.source_uri) if payload.source_uri else None,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "source_record_id": row.source_record_id, "price_minor": row.price_minor, "currency": row.currency}


@router.post("/valuations/{case_id}/analyze", status_code=201, tags=["valuations"])
def analyze_valuation(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    case = _case(db, organization_id, case_id, "artvaluate")
    rows = db.scalars(select(MarketComparable).where(MarketComparable.case_id == case.id)).all()
    currencies = {row.currency for row in rows}
    if len(rows) < 3 or len(currencies) != 1:
        report = ValuationReport(
            organization_id=organization_id,
            case_id=case.id,
            status="insufficient_market_evidence",
            methodology={"comparable_count": len(rows), "required_minimum": 3},
            limitations=["At least three licensed comparables in one currency are required.", *ENGINE_LIMITATIONS["artvaluate"]],
        )
        case.summary = "Insufficient market evidence."
    else:
        prices = sorted(row.price_minor for row in rows)
        median = round(statistics.median(prices))
        low = round(statistics.quantiles(prices, n=4, method="inclusive")[0])
        high = round(statistics.quantiles(prices, n=4, method="inclusive")[2])
        report = ValuationReport(
            organization_id=organization_id,
            case_id=case.id,
            status="research_estimate",
            currency=rows[0].currency,
            estimate_low_minor=low,
            estimate_mid_minor=median,
            estimate_high_minor=high,
            methodology={"method": "interquartile comparable range", "comparable_count": len(rows), "outlier_resistant": True},
            assumptions=["Comparable records and license statements are accurate as supplied."],
            limitations=ENGINE_LIMITATIONS["artvaluate"],
        )
        case.summary = "Comparable-based research range calculated; human appraiser review is required."
    db.add(report)
    case.input_data = {
        **case.input_data,
        "valuation": {
            "status": report.status,
            "currency": report.currency,
            "estimate_low_minor": report.estimate_low_minor,
            "estimate_mid_minor": report.estimate_mid_minor,
            "estimate_high_minor": report.estimate_high_minor,
            "methodology": report.methodology,
            "limitations": report.limitations,
        },
    }
    case.status = "awaiting_review"
    db.commit()
    return {
        "id": report.id, "status": report.status, "currency": report.currency,
        "estimate_low_minor": report.estimate_low_minor, "estimate_mid_minor": report.estimate_mid_minor,
        "estimate_high_minor": report.estimate_high_minor, "methodology": report.methodology,
        "limitations": report.limitations,
    }


@router.post("/shipments", status_code=201, tags=["shipments"])
def create_shipment(
    organization_id: uuid.UUID,
    payload: ShipmentCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    if payload.pre_asset_id:
        pre = _asset(db, organization_id, payload.pre_asset_id)
        if pre.artwork_id != payload.artwork_id:
            raise HTTPException(status_code=422, detail="Pre-shipment asset does not belong to the artwork.")
    if payload.arrival_asset_id:
        arrival = _asset(db, organization_id, payload.arrival_asset_id)
        if arrival.artwork_id != payload.artwork_id:
            raise HTTPException(status_code=422, detail="Arrival asset does not belong to the artwork.")
    case = _new_case(db, organization_id, "arttransit", payload, principal)
    shipment = Shipment(
        organization_id=organization_id,
        case_id=case.id,
        reference=payload.reference,
        origin=payload.origin,
        destination=payload.destination,
        carrier=payload.carrier,
        packaging=payload.packaging,
        pre_asset_id=payload.pre_asset_id,
        arrival_asset_id=payload.arrival_asset_id,
    )
    db.add(shipment)
    db.flush()
    comparison_id = None
    if payload.pre_asset_id and payload.arrival_asset_id:
        comparison = compare_assets(db, pre, arrival)
        comparison_id = comparison.id
        case.input_data = {
            **case.input_data,
            "comparison": {
                "id": str(comparison.id),
                "scores": comparison.scores,
                "regions": comparison.regions,
                "limitations": comparison.limitations,
            },
        }
        shipment.status = "review"
        case.status = "awaiting_review"
        case.summary = "Before/after visual comparison completed; observable changes do not determine damage or liability."
    _audit(db, organization_id, principal, "arttransit.shipment_created", "shipment", shipment.id, request)
    db.commit()
    return {"id": shipment.id, "case_id": case.id, "status": shipment.status, "comparison_id": comparison_id, "limitations": case.limitations}


@router.post("/shipments/{shipment_id}/custody", status_code=201, tags=["shipments"])
def add_custody_event(
    organization_id: uuid.UUID,
    shipment_id: uuid.UUID,
    payload: CustodyCreate,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    shipment = db.scalar(select(Shipment).where(Shipment.organization_id == organization_id, Shipment.id == shipment_id))
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment was not found.")
    row = CustodyEvent(
        organization_id=organization_id,
        shipment_id=shipment_id,
        **payload.model_dump(exclude={"evidence_document_ids"}),
        evidence_document_ids=[str(value) for value in payload.evidence_document_ids],
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "occurred_at": row.occurred_at, "event_type": row.event_type}


@router.get("/evidence", tags=["evidence"])
def search_evidence(
    organization_id: uuid.UUID,
    query: str | None = Query(default=None, max_length=200),
    artwork_id: uuid.UUID | None = None,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    membership = require_membership(db, organization_id, principal)
    filters = [EvidenceDocument.organization_id == organization_id]
    if artwork_id:
        filters.append(EvidenceDocument.artwork_id == artwork_id)
    if membership.role not in {"owner", "administrator", "investigator", "reviewer"}:
        filters.append(EvidenceDocument.sensitivity != "restricted")
    if query:
        hybrid = hybrid_search(
            db,
            organization_id,
            query,
            include_restricted=membership.role in {"owner", "administrator", "investigator", "reviewer"},
            artwork_id=artwork_id,
        )
        if hybrid:
            return [
                {
                    "id": match["document"].id,
                    "artwork_id": match["document"].artwork_id,
                    "title": match["document"].title,
                    "kind": match["document"].kind,
                    "source_uri": match["document"].source_uri,
                    "source_authority": match["document"].source_authority,
                    "verification_status": match["document"].verification_status,
                    "sensitivity": match["document"].sensitivity,
                    "citation": match["citation"],
                    "excerpt": match["excerpt"],
                    "hybrid_score": match["hybrid_score"],
                    "embedding_model": "vernis-hashed-text-embedding-1.0.0",
                }
                for match in hybrid
            ]
        term = f"%{query.strip()}%"
        filters.append(or_(EvidenceDocument.title.ilike(term), EvidenceDocument.extracted_text.ilike(term)))
    rows = db.scalars(select(EvidenceDocument).where(*filters).order_by(EvidenceDocument.created_at.desc()).limit(100)).all()
    return [
        {"id": row.id, "artwork_id": row.artwork_id, "title": row.title, "kind": row.kind,
         "source_uri": row.source_uri, "source_authority": row.source_authority,
         "verification_status": row.verification_status, "sensitivity": row.sensitivity,
         "citation": f"Evidence {str(row.id)[:8]} · {row.title}"}
        for row in rows
    ]


@router.post("/evidence", status_code=201, tags=["evidence"])
def create_evidence(
    organization_id: uuid.UUID,
    payload: EvidenceCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    _artwork(db, organization_id, payload.artwork_id)
    asset = _asset(db, organization_id, payload.asset_id) if payload.asset_id else None
    if asset and asset.artwork_id != payload.artwork_id:
        raise HTTPException(status_code=422, detail="Evidence asset does not belong to the selected artwork.")
    row = EvidenceDocument(
        organization_id=organization_id,
        created_by=principal.user_id,
        content_sha256=asset.sha256 if asset else None,
        extraction_method="user_supplied_text" if payload.extracted_text else None,
        **payload.model_dump(exclude={"source_uri"}),
        source_uri=str(payload.source_uri) if payload.source_uri else None,
    )
    db.add(row)
    db.flush()
    chunk_count = rebuild_chunks(db, row)
    _audit(db, organization_id, principal, "evidence.created", "evidence_document", row.id, request)
    db.commit()
    return {"id": row.id, "verification_status": row.verification_status, "chunk_count": chunk_count}


@router.post("/evidence/{evidence_id}/extract", status_code=202, tags=["evidence"])
def extract_evidence_text(
    organization_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    evidence = db.scalar(
        select(EvidenceDocument).where(
            EvidenceDocument.organization_id == organization_id,
            EvidenceDocument.id == evidence_id,
        )
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence document was not found.")
    job = Job(
        organization_id=organization_id,
        kind="evidence_ocr",
        status="running",
        progress=10,
        requested_by=principal.user_id,
        parameters={"evidence_document_id": str(evidence.id), "external_provider": False},
    )
    db.add(job)
    db.flush()
    try:
        chunk_count = ocr_evidence_asset(db, evidence)
    except ValueError as exc:
        job.status = "failed"
        job.progress = 100
        job.error_code = "ocr_input_error"
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job.status = "succeeded"
    job.progress = 100
    _audit(db, organization_id, principal, "evidence.ocr_completed", "evidence_document", evidence.id, request)
    db.commit()
    return {
        "job_id": job.id,
        "status": job.status,
        "extraction_method": evidence.extraction_method,
        "chunk_count": chunk_count,
        "limitations": ["OCR text is unverified and may contain transcription errors."],
    }


@router.post("/cases/{case_id}/claims", status_code=201, tags=["evidence"])
def add_evidence_claim(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    payload: ClaimCreate,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    _case(db, organization_id, case_id)
    if payload.evidence_document_id:
        evidence = db.scalar(
            select(EvidenceDocument).where(
                EvidenceDocument.organization_id == organization_id,
                EvidenceDocument.id == payload.evidence_document_id,
            )
        )
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence document was not found.")
    row = EvidenceClaim(organization_id=organization_id, case_id=case_id, **payload.model_dump())
    db.add(row)
    db.commit()
    return {"id": row.id, "review_status": row.review_status, "stance": row.stance}


@router.post("/cases/{case_id}/reviews", status_code=201, tags=["reviews"])
def review_case(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    payload: ReviewCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, {"owner", "administrator", "reviewer"})
    case = _case(db, organization_id, case_id)
    row = HumanReview(
        organization_id=organization_id,
        case_id=case.id,
        reviewer_id=principal.user_id,
        decision=payload.decision,
        notes=payload.notes,
    )
    case.status = "approved" if payload.decision == "approved" else "changes_requested"
    db.add(row)
    _audit(db, organization_id, principal, "case.reviewed", "engine_case", case.id, request, {"decision": payload.decision})
    db.commit()
    return {"id": row.id, "case_status": case.status, "decision": row.decision}


@router.post("/cases/{case_id}/reports", status_code=201, tags=["reports"])
def generate_case_report(
    organization_id: uuid.UUID,
    case_id: uuid.UUID,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES | {"reviewer"})
    case = _case(db, organization_id, case_id)
    claims = db.scalars(select(EvidenceClaim).where(EvidenceClaim.case_id == case.id)).all()
    reviews = db.scalars(select(HumanReview).where(HumanReview.case_id == case.id)).all()
    latest_agent_run = db.scalar(
        select(AgentRun)
        .where(AgentRun.case_id == case.id, AgentRun.status.in_(["succeeded", "partially_succeeded"]))
        .order_by(AgentRun.completed_at.desc())
        .limit(1)
    )
    version = (db.scalar(select(func.max(ReportVersion.version)).where(ReportVersion.case_id == case.id)) or 0) + 1
    evidence_ids = sorted({str(claim.evidence_document_id) for claim in claims if claim.evidence_document_id})
    content = {
        "case": _case_payload(case),
        "claims": [
            {"text": claim.claim_text, "stance": claim.stance, "confidence": claim.confidence,
             "review_status": claim.review_status, "evidence_document_id": str(claim.evidence_document_id) if claim.evidence_document_id else None,
             "source_locator": claim.source_locator}
            for claim in claims
        ],
        "human_reviews": [
            {"decision": review.decision, "notes": review.notes, "reviewer_id": str(review.reviewer_id)}
            for review in reviews
        ],
        "agent_review": {
            "run_id": str(latest_agent_run.id),
            "crew_name": latest_agent_run.crew_name,
            "status": latest_agent_run.status,
            "output": latest_agent_run.output,
        } if latest_agent_run else None,
        "limitations": case.limitations,
        "disclaimer": "AI-assisted and computational findings support human review; this is not authentication, legal advice, a certified appraisal, a conservation treatment decision, or an insurance determination.",
    }
    report = ReportVersion(
        organization_id=organization_id,
        case_id=case.id,
        version=version,
        title=f"{case.title} · report v{version}",
        content=content,
        evidence_document_ids=evidence_ids,
        review_status="reviewed" if case.status == "approved" else "draft",
        created_by=principal.user_id,
    )
    db.add(report)
    db.flush()
    _audit(db, organization_id, principal, "report.generated", "report_version", report.id, request)
    db.commit()
    return {"id": report.id, "version": report.version, "review_status": report.review_status, "content": report.content}


@router.post("/artworks/{artwork_id}/passport", status_code=201, tags=["passports"])
def generate_passport(
    organization_id: uuid.UUID,
    artwork_id: uuid.UUID,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_membership(db, organization_id, principal, EDITOR_ROLES | {"reviewer"})
    artwork = _artwork(db, organization_id, artwork_id)
    cases = db.scalars(select(EngineCase).where(EngineCase.organization_id == organization_id, EngineCase.artwork_id == artwork_id)).all()
    evidence = db.scalars(select(EvidenceDocument).where(EvidenceDocument.organization_id == organization_id, EvidenceDocument.artwork_id == artwork_id)).all()
    provenance = db.scalars(select(ProvenanceEvent).where(ProvenanceEvent.organization_id == organization_id, ProvenanceEvent.artwork_id == artwork_id)).all()
    case_ids = [case.id for case in cases]
    reviews = db.scalars(select(HumanReview).where(HumanReview.organization_id == organization_id, HumanReview.case_id.in_(case_ids))).all() if case_ids else []
    approved_case_ids = {review.case_id for review in reviews if review.decision == "approved"}
    rights_matches = db.scalars(select(CopyrightMatch).where(CopyrightMatch.organization_id == organization_id, CopyrightMatch.case_id.in_(case_ids))).all() if case_ids else []
    inspections = db.scalars(select(ConditionInspection).where(ConditionInspection.organization_id == organization_id, ConditionInspection.case_id.in_(case_ids))).all() if case_ids else []
    inspection_ids = [inspection.id for inspection in inspections]
    damage_findings = db.scalars(select(DamageFinding).where(DamageFinding.organization_id == organization_id, DamageFinding.inspection_id.in_(inspection_ids))).all() if inspection_ids else []
    collection_records = db.scalars(select(CollectionRecord).where(CollectionRecord.organization_id == organization_id, CollectionRecord.artwork_id == artwork_id)).all()
    collection_record_ids = [record.id for record in collection_records]
    collection_relationships = db.scalars(
        select(CollectionRelationship).where(
            CollectionRelationship.organization_id == organization_id,
            or_(
                CollectionRelationship.source_record_id.in_(collection_record_ids),
                CollectionRelationship.target_record_id.in_(collection_record_ids),
            ),
        )
    ).all() if collection_record_ids else []
    valuation_reports = db.scalars(select(ValuationReport).where(ValuationReport.organization_id == organization_id, ValuationReport.case_id.in_(case_ids))).all() if case_ids else []
    shipments = db.scalars(select(Shipment).where(Shipment.organization_id == organization_id, Shipment.case_id.in_(case_ids))).all() if case_ids else []
    shipment_ids = [shipment.id for shipment in shipments]
    custody_events = db.scalars(select(CustodyEvent).where(CustodyEvent.organization_id == organization_id, CustodyEvent.shipment_id.in_(shipment_ids))).all() if shipment_ids else []
    version = (db.scalar(select(func.max(ArtworkPassport.version)).where(ArtworkPassport.artwork_id == artwork_id)) or 0) + 1
    completeness_fields = [artwork.artist_attribution, artwork.medium, artwork.creation_year_from, evidence, provenance, reviews]
    completeness = round(sum(bool(value) for value in completeness_fields) / len(completeness_fields) * 100)
    case_summaries = [
        {"engine": case.engine, "case_id": str(case.id), "status": case.status, "summary": case.summary,
         "limitations": case.limitations, "human_reviewed": case.id in approved_case_ids}
        for case in cases
    ]
    public_case_summaries = [summary for summary in case_summaries if summary["human_reviewed"]]
    review_summaries = [
        {"case_id": str(review.case_id), "decision": review.decision, "notes": review.notes,
         "reviewer_id": str(review.reviewer_id), "reviewed_at": review.created_at.isoformat()}
        for review in reviews
    ]
    rights_summaries = [
        {"case_id": str(match.case_id), "classification": match.classification,
         "similarity_scores": match.similarity_scores, "source_record": match.source_record,
         "human_reviewed": match.case_id in approved_case_ids}
        for match in rights_matches
    ]
    condition_history = [
        {"inspection_id": str(inspection.id), "case_id": str(inspection.case_id),
         "asset_id": str(inspection.asset_id), "inspected_at": inspection.inspected_at.isoformat(),
         "environment": inspection.environment,
         "findings": [
             {"id": str(finding.id), "type": finding.finding_type, "region": finding.normalized_region,
              "measurements": finding.measurements, "review_status": finding.review_status,
              "limitations": finding.limitations}
             for finding in damage_findings if finding.inspection_id == inspection.id
         ]}
        for inspection in inspections
    ]
    collection_summaries = [
        {"record_id": str(record.id), "accession_number": record.accession_number,
         "department": record.department, "location": record.location,
         "completeness_score": record.completeness_score, "review_status": record.review_status}
        for record in collection_records
    ]
    relationship_summaries = [
        {"id": str(relationship.id), "source_record_id": str(relationship.source_record_id),
         "target_record_id": str(relationship.target_record_id), "type": relationship.relationship_type,
         "verification_status": relationship.verification_status,
         "evidence_document_ids": relationship.evidence_document_ids}
        for relationship in collection_relationships
    ]
    valuation_summaries = [
        {"case_id": str(report.case_id), "status": report.status, "currency": report.currency,
         "estimate_low_minor": report.estimate_low_minor, "estimate_mid_minor": report.estimate_mid_minor,
         "estimate_high_minor": report.estimate_high_minor, "methodology": report.methodology,
         "limitations": report.limitations, "human_reviewed": report.case_id in approved_case_ids}
        for report in valuation_reports
    ]
    shipment_summaries = [
        {"shipment_id": str(shipment.id), "case_id": str(shipment.case_id), "reference": shipment.reference,
         "origin": shipment.origin, "destination": shipment.destination, "carrier": shipment.carrier,
         "status": shipment.status, "packaging": shipment.packaging,
         "custody": [
             {"occurred_at": event.occurred_at.isoformat(), "event_type": event.event_type,
              "custodian": event.custodian, "location": event.location,
              "evidence_document_ids": event.evidence_document_ids}
             for event in custody_events if event.shipment_id == shipment.id
         ]}
        for shipment in shipments
    ]
    snapshot = {
        "schema_version": "1.0",
        "artwork": {"id": str(artwork.id), "title": artwork.title, "artist_attribution": artwork.artist_attribution,
                    "attribution_status": artwork.attribution_status, "medium": artwork.medium},
        "file_fingerprints": [asset.sha256 for asset in db.scalars(select(ArtworkAsset).where(ArtworkAsset.artwork_id == artwork.id)).all() if asset.sha256],
        "engine_history": case_summaries,
        "rights_assertions": rights_summaries,
        "condition_history": condition_history,
        "valuation_research": valuation_summaries,
        "collection_records": collection_summaries,
        "collection_relationships": relationship_summaries,
        "shipment_history": shipment_summaries,
        "human_reviews": [
            {"case_id": item["case_id"], "decision": item["decision"], "reviewed_at": item["reviewed_at"]}
            for item in review_summaries
            if item["decision"] == "approved"
        ],
        "provenance": [{"id": str(event.id), "description": event.description, "verification_status": event.verification_status,
                        "evidence_document_ids": event.evidence_document_ids} for event in provenance],
        "evidence": [{"id": str(item.id), "title": item.title, "kind": item.kind, "verification_status": item.verification_status,
                      "sensitivity": item.sensitivity} for item in evidence],
        "evidence_completeness": completeness,
    }
    public_snapshot = {
        "schema_version": "1.0",
        "artwork": snapshot["artwork"],
        "engine_history": public_case_summaries,
        "rights_assertions": [item for item in rights_summaries if item["human_reviewed"]],
        "condition_history": [item for item in condition_history if item["case_id"] in {str(value) for value in approved_case_ids}],
        "valuation_research": [item for item in valuation_summaries if item["human_reviewed"]],
        "collection_records": [item for item in collection_summaries if item["review_status"] != "needs_review"],
        "shipment_history": [item for item in shipment_summaries if item["case_id"] in {str(value) for value in approved_case_ids}],
        "human_reviews": review_summaries,
        "evidence": [{"id": str(item.id), "title": item.title, "kind": item.kind,
                      "verification_status": item.verification_status} for item in evidence if item.sensitivity == "public"],
        "evidence_completeness": completeness,
    }
    passport = ArtworkPassport(
        organization_id=organization_id,
        artwork_id=artwork_id,
        version=version,
        snapshot=snapshot,
        public_snapshot=public_snapshot,
        evidence_completeness=completeness,
    )
    db.add(passport)
    db.flush()
    _audit(db, organization_id, principal, "passport.generated", "artwork_passport", passport.id, request)
    db.commit()
    return {"id": passport.id, "version": passport.version, "evidence_completeness": completeness, "snapshot": snapshot}


@router.get("/artworks/{artwork_id}/passport/export", tags=["passports"], response_model=None)
def export_passport(
    organization_id: uuid.UUID,
    artwork_id: uuid.UUID,
    export_format: Literal["json", "pdf"] = Query(default="json", alias="format"),
    scope: Literal["internal", "public"] = "internal",
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any] | Response:
    membership = require_membership(db, organization_id, principal)
    if scope == "internal" and membership.role not in {"owner", "administrator", "investigator", "reviewer"}:
        raise HTTPException(status_code=403, detail="Internal passport exports require a privileged organization role.")
    passport = db.scalar(
        select(ArtworkPassport)
        .where(
            ArtworkPassport.organization_id == organization_id,
            ArtworkPassport.artwork_id == artwork_id,
        )
        .order_by(ArtworkPassport.version.desc())
        .limit(1)
    )
    if passport is None:
        raise HTTPException(status_code=404, detail="Artwork passport was not found.")
    snapshot = passport.public_snapshot if scope == "public" else passport.snapshot
    payload = {
        "passport_id": str(passport.id),
        "version": passport.version,
        "schema_version": passport.schema_version,
        "scope": scope,
        "snapshot": snapshot,
        "generated_at": passport.created_at.isoformat(),
    }
    if export_format == "json":
        return payload
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    stream = io.BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, title="Vernis Artwork Intelligence Passport")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Vernis Artwork Intelligence Passport", styles["Title"]),
        Paragraph(f"Version {passport.version} · {escape(scope)} scope", styles["Normal"]),
        Spacer(1, 14),
        Paragraph(escape(str(snapshot.get("artwork", {}).get("title", "Untitled artwork"))), styles["Heading2"]),
        Paragraph(
            "This evidence passport preserves source references and reviewed workflow history. It is not an authenticity certificate, legal opinion, certified appraisal, conservation prescription, or insurance determination.",
            styles["Normal"],
        ),
        Spacer(1, 14),
    ]
    for key, value in snapshot.items():
        story.append(Paragraph(escape(key.replace("_", " ").title()), styles["Heading3"]))
        story.append(Paragraph(escape(json.dumps(value, ensure_ascii=False, default=str)), styles["Code"]))
        story.append(Spacer(1, 8))
    document.build(story)
    return Response(
        content=stream.getvalue(),
        media_type="application/pdf",
        headers={"content-disposition": f'attachment; filename="vernis-passport-v{passport.version}-{scope}.pdf"'},
    )
