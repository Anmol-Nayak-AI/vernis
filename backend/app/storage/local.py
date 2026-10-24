from __future__ import annotations

import hashlib
import os
import secrets
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request, status
from PIL import Image, UnidentifiedImageError

from app.config import settings

ALLOWED_IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
    "TIFF": ("image/tiff", ".tif"),
}


@dataclass(frozen=True)
class StoredAsset:
    object_key: str
    size_bytes: int
    sha256: str
    mime_type: str


class LocalAssetStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.storage_root).resolve()
        self.quarantine = self.root / "quarantine"
        self.assets = self.root / "assets"
        self.quarantine.mkdir(parents=True, exist_ok=True)
        self.assets.mkdir(parents=True, exist_ok=True)

    async def receive_image(
        self,
        request: Request,
        organization_id: uuid.UUID,
        artwork_id: uuid.UUID,
        asset_id: uuid.UUID,
        expected_size: int,
        expected_mime: str,
    ) -> StoredAsset:
        digest = hashlib.sha256()
        size = 0
        fd, temporary_name = tempfile.mkstemp(prefix=f"{asset_id}-", dir=self.quarantine)
        try:
            with os.fdopen(fd, "wb") as output:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > settings.upload_max_bytes or size > expected_size:
                        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Upload is larger than declared or allowed.")
                    digest.update(chunk)
                    output.write(chunk)
            if size != expected_size:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload size does not match the intent.")
            try:
                with Image.open(temporary_name) as image:
                    image.verify()
                    image_format = image.format or ""
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is not a safely decodable image.") from exc
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Image format is not supported.")
            verified_mime, extension = ALLOWED_IMAGE_FORMATS[image_format]
            if expected_mime not in {verified_mime, "application/octet-stream"}:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Declared MIME type does not match file content.")
            relative = Path(str(organization_id)) / str(artwork_id) / f"{asset_id}{extension}"
            destination = self.assets / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temporary_name, destination)
            return StoredAsset(
                object_key=relative.as_posix(),
                size_bytes=size,
                sha256=digest.hexdigest(),
                mime_type=verified_mime,
            )
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def path_for(self, object_key: str) -> Path:
        candidate = (self.assets / object_key).resolve()
        if self.assets not in candidate.parents:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset was not found.")
        return candidate

    def read_bytes(self, object_key: str) -> bytes:
        return self.path_for(object_key).read_bytes()


def new_upload_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
