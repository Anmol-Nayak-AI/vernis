from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    ArtworkCreate,
    ArtworkPage,
    ArtworkRead,
    AssetRead,
    CommandCenterRead,
    DownloadRead,
    OrganizationCreate,
    OrganizationRead,
    UploadIntentCreate,
    UploadIntentRead,
)
from app.config import settings
from app.core.security import RequestPrincipal, ensure_user, get_request_principal, require_membership
from app.db.models import (
    Artwork,
    ArtworkAsset,
    AuditEvent,
    Job,
    Organization,
    OrganizationMembership,
    UploadIntent,
)
from app.db.session import get_db
from app.storage import S3AssetStore, get_asset_store
from app.storage.local import new_upload_token, token_hash

router = APIRouter(prefix="/api/v1")
EDITOR_ROLES = {"owner", "administrator", "investigator", "conservator", "analyst"}


def _artwork_read(db: Session, artwork: Artwork) -> ArtworkRead:
    assets = db.scalars(
        select(ArtworkAsset)
        .where(
            ArtworkAsset.organization_id == artwork.organization_id,
            ArtworkAsset.artwork_id == artwork.id,
        )
        .order_by(ArtworkAsset.created_at.desc())
    ).all()
    return ArtworkRead.model_validate(artwork).model_copy(
        update={"assets": [AssetRead.model_validate(asset) for asset in assets]}
    )


def _audit(
    db: Session,
    organization_id: uuid.UUID,
    principal: RequestPrincipal,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    request: Request,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            organization_id=organization_id,
            actor_id=principal.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request.headers.get("x-request-id"),
            payload=payload or {},
        )
    )


@router.get("/health/live", tags=["health"])
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": "0.2.0"}


@router.get("/health/ready", tags=["health"])
def health_ready(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("select 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "unavailable"}
    return {"status": "ready", "database": "available"}


@router.get("/organizations", response_model=list[OrganizationRead], tags=["organizations"])
def list_organizations(
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> list[OrganizationRead]:
    rows = db.execute(
        select(Organization, OrganizationMembership.role)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Organization.id,
        )
        .where(OrganizationMembership.user_id == principal.user_id)
        .order_by(Organization.name)
    ).all()
    return [
        OrganizationRead(id=organization.id, name=organization.name, slug=organization.slug, plan=organization.plan, role=role)
        for organization, role in rows
    ]


@router.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    tags=["organizations"],
)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> OrganizationRead:
    ensure_user(db, principal)
    organization = Organization(
        name=payload.name.strip(),
        slug=payload.slug,
        plan=payload.plan,
        created_by=principal.user_id,
    )
    db.add(organization)
    try:
        db.flush()
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=principal.user_id,
            role="owner",
        )
        db.add(membership)
        _audit(db, organization.id, principal, "organization.created", "organization", organization.id, request)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug is already in use.") from exc
    return OrganizationRead(id=organization.id, name=organization.name, slug=organization.slug, plan=organization.plan, role="owner")


@router.get(
    "/organizations/{organization_id}/command-center",
    response_model=CommandCenterRead,
    tags=["command-center"],
)
def command_center(
    organization_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> CommandCenterRead:
    require_membership(db, organization_id, principal)
    artwork_count = db.scalar(select(func.count()).select_from(Artwork).where(Artwork.organization_id == organization_id)) or 0
    active_jobs = db.scalar(
        select(func.count())
        .select_from(Job)
        .where(Job.organization_id == organization_id, Job.status.in_(["queued", "running", "awaiting_review"]))
    ) or 0
    return CommandCenterRead(
        registered_artworks=artwork_count,
        active_jobs=active_jobs,
        pending_reviews=0,
        potential_copyright_matches=0,
        condition_alerts=0,
        active_shipments=0,
        collection_completeness=None,
        onboarding_complete=artwork_count > 0,
    )


@router.get(
    "/organizations/{organization_id}/artworks",
    response_model=ArtworkPage,
    tags=["artworks"],
)
def list_artworks(
    organization_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    query: str | None = Query(default=None, max_length=200),
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> ArtworkPage:
    require_membership(db, organization_id, principal)
    filters = [Artwork.organization_id == organization_id]
    if query:
        filters.append(Artwork.title.ilike(f"%{query.strip()}%"))
    total = db.scalar(select(func.count()).select_from(Artwork).where(*filters)) or 0
    artworks = db.scalars(
        select(Artwork)
        .where(*filters)
        .order_by(Artwork.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ArtworkPage(
        items=[_artwork_read(db, artwork) for artwork in artworks],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/organizations/{organization_id}/artworks",
    response_model=ArtworkRead,
    status_code=status.HTTP_201_CREATED,
    tags=["artworks"],
)
def create_artwork(
    organization_id: uuid.UUID,
    payload: ArtworkCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> ArtworkRead:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    artwork = Artwork(
        organization_id=organization_id,
        created_by=principal.user_id,
        **payload.model_dump(),
    )
    db.add(artwork)
    db.flush()
    _audit(db, organization_id, principal, "artwork.created", "artwork", artwork.id, request)
    db.commit()
    return _artwork_read(db, artwork)


@router.get(
    "/organizations/{organization_id}/artworks/{artwork_id}",
    response_model=ArtworkRead,
    tags=["artworks"],
)
def get_artwork(
    organization_id: uuid.UUID,
    artwork_id: uuid.UUID,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> ArtworkRead:
    require_membership(db, organization_id, principal)
    artwork = db.scalar(
        select(Artwork).where(Artwork.organization_id == organization_id, Artwork.id == artwork_id)
    )
    if artwork is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artwork was not found.")
    return _artwork_read(db, artwork)


@router.post(
    "/organizations/{organization_id}/assets/upload-intents",
    response_model=UploadIntentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["assets"],
)
def create_upload_intent(
    organization_id: uuid.UUID,
    payload: UploadIntentCreate,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> UploadIntentRead:
    require_membership(db, organization_id, principal, EDITOR_ROLES)
    if payload.size_bytes > settings.upload_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds the organization upload limit.")
    artwork = db.scalar(
        select(Artwork).where(Artwork.organization_id == organization_id, Artwork.id == payload.artwork_id)
    )
    if artwork is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artwork was not found.")
    raw_token = new_upload_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.upload_intent_ttl_seconds)
    asset = ArtworkAsset(
        organization_id=organization_id,
        artwork_id=artwork.id,
        kind=payload.kind,
        original_name=payload.file_name,
        declared_mime_type=payload.content_type,
        size_bytes=payload.size_bytes,
        status="pending",
        is_primary=payload.kind == "primary_image",
        uploaded_by=principal.user_id,
    )
    db.add(asset)
    db.flush()
    db.add(
        UploadIntent(
            organization_id=organization_id,
            asset_id=asset.id,
            token_hash=token_hash(raw_token),
            expected_size=payload.size_bytes,
            expected_mime_type=payload.content_type,
            expires_at=expires_at,
            created_by=principal.user_id,
        )
    )
    _audit(db, organization_id, principal, "asset.upload_intent_created", "asset", asset.id, request)
    db.commit()
    upload_path = request.url_for("upload_asset_content", token=raw_token).path
    return UploadIntentRead(
        asset_id=asset.id,
        upload_url=upload_path,
        expires_at=expires_at,
        max_bytes=settings.upload_max_bytes,
    )


@router.put("/assets/uploads/{token}", response_model=AssetRead, tags=["assets"], name="upload_asset_content")
async def upload_asset_content(token: str, request: Request, db: Session = Depends(get_db)) -> AssetRead:
    intent = db.scalar(select(UploadIntent).where(UploadIntent.token_hash == token_hash(token)))
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload intent was not found.")
    expires_at = intent.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if intent.used_at or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Upload intent is expired or already used.")
    asset = db.get(ArtworkAsset, intent.asset_id)
    if asset is None or asset.organization_id != intent.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset was not found.")
    asset.status = "quarantined"
    db.commit()
    try:
        stored = await get_asset_store().receive_image(
            request=request,
            organization_id=asset.organization_id,
            artwork_id=asset.artwork_id,
            asset_id=asset.id,
            expected_size=intent.expected_size,
            expected_mime=intent.expected_mime_type,
        )
    except HTTPException as exc:
        asset.status = "rejected"
        asset.rejection_reason = str(exc.detail)[:320]
        intent.used_at = datetime.now(timezone.utc)
        db.add(
            Job(
                organization_id=asset.organization_id,
                kind="asset_intake",
                status="failed",
                progress=100,
                requested_by=intent.created_by,
                parameters={"asset_id": str(asset.id)},
                error_code="upload_validation_failed",
            )
        )
        db.commit()
        raise
    asset.object_key = stored.object_key
    asset.size_bytes = stored.size_bytes
    asset.sha256 = stored.sha256
    asset.verified_mime_type = stored.mime_type
    asset.status = "ready"
    intent.used_at = datetime.now(timezone.utc)
    db.add(
        Job(
            organization_id=asset.organization_id,
            kind="asset_intake",
            status="succeeded",
            progress=100,
            requested_by=intent.created_by,
            parameters={"asset_id": str(asset.id), "sha256": stored.sha256},
        )
    )
    db.add(
        AuditEvent(
            organization_id=asset.organization_id,
            actor_id=intent.created_by,
            action="asset.ready",
            entity_type="asset",
            entity_id=asset.id,
            request_id=request.headers.get("x-request-id"),
            payload={"sha256": stored.sha256, "verified_mime_type": stored.mime_type},
        )
    )
    db.commit()
    return AssetRead.model_validate(asset)


@router.get(
    "/organizations/{organization_id}/assets/{asset_id}/download",
    response_model=DownloadRead,
    tags=["assets"],
)
def create_download_url(
    organization_id: uuid.UUID,
    asset_id: uuid.UUID,
    request: Request,
    principal: RequestPrincipal = Depends(get_request_principal),
    db: Session = Depends(get_db),
) -> DownloadRead:
    require_membership(db, organization_id, principal)
    asset = db.scalar(
        select(ArtworkAsset).where(
            ArtworkAsset.organization_id == organization_id,
            ArtworkAsset.id == asset_id,
            ArtworkAsset.status == "ready",
        )
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset was not found.")
    expires_in = 300
    token = jwt.encode(
        {
            "asset_id": str(asset.id),
            "organization_id": str(organization_id),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            "aud": "vernis-asset-download",
        },
        settings.storage_signing_secret,
        algorithm="HS256",
    )
    path = request.url_for("download_asset_content", asset_id=asset.id).path
    return DownloadRead(url=f"{path}?token={token}", expires_in=expires_in)


@router.get(
    "/assets/{asset_id}/content",
    tags=["assets"],
    name="download_asset_content",
    response_model=None,
)
def download_asset_content(
    asset_id: uuid.UUID,
    token: str,
    db: Session = Depends(get_db),
) -> FileResponse | RedirectResponse:
    try:
        claims = jwt.decode(
            token,
            settings.storage_signing_secret,
            algorithms=["HS256"],
            audience="vernis-asset-download",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Download link is invalid or expired.") from exc
    if claims.get("asset_id") != str(asset_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Download link does not match this asset.")
    asset = db.get(ArtworkAsset, asset_id)
    if asset is None or asset.status != "ready" or asset.object_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset was not found.")
    if claims.get("organization_id") != str(asset.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Download link has the wrong organization scope.")
    store = get_asset_store()
    if isinstance(store, S3AssetStore):
        return RedirectResponse(store.signed_download_url(asset.object_key), status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    path = store.path_for(asset.object_key)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset bytes are unavailable.")
    return FileResponse(path, media_type=asset.verified_mime_type, filename=asset.original_name)
