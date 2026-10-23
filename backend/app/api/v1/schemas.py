from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    plan: Literal["artist", "professional", "gallery", "institution", "enterprise"] = "artist"


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    role: str


class ArtworkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    artist_attribution: str | None = Field(default=None, max_length=240)
    attribution_status: Literal["claimed", "verified", "disputed", "unknown"] = "unknown"
    creation_year_from: int | None = Field(default=None, ge=-50000, le=3000)
    creation_year_to: int | None = Field(default=None, ge=-50000, le=3000)
    date_precision: Literal["exact", "year", "range", "circa", "unknown"] = "unknown"
    medium: str | None = Field(default=None, max_length=320)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    description: str | None = Field(default=None, max_length=10000)
    current_custody: str | None = Field(default=None, max_length=320)

    @model_validator(mode="after")
    def validate_year_range(self) -> "ArtworkCreate":
        if self.creation_year_from is not None and self.creation_year_to is not None:
            if self.creation_year_to < self.creation_year_from:
                raise ValueError("creation_year_to cannot precede creation_year_from")
        return self


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    original_name: str
    verified_mime_type: str | None
    size_bytes: int
    sha256: str | None
    status: str
    is_primary: bool
    created_at: datetime


class ArtworkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    artist_attribution: str | None
    attribution_status: str
    creation_year_from: int | None
    creation_year_to: int | None
    date_precision: str
    medium: str | None
    dimensions: dict[str, Any]
    description: str | None
    current_custody: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    assets: list[AssetRead] = Field(default_factory=list)


class ArtworkPage(BaseModel):
    items: list[ArtworkRead]
    page: int
    page_size: int
    total: int


class UploadIntentCreate(BaseModel):
    artwork_id: uuid.UUID
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=128)
    size_bytes: int = Field(gt=0)
    kind: Literal["primary_image", "detail_image", "document", "condition_image"] = "primary_image"


class UploadIntentRead(BaseModel):
    asset_id: uuid.UUID
    upload_url: str
    method: Literal["PUT"] = "PUT"
    expires_at: datetime
    max_bytes: int


class DownloadRead(BaseModel):
    url: str
    expires_in: int


class CommandCenterRead(BaseModel):
    registered_artworks: int
    active_jobs: int
    pending_reviews: int
    potential_copyright_matches: int
    condition_alerts: int
    active_shipments: int
    collection_completeness: int | None
    onboarding_complete: bool
