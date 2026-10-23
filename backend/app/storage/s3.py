from __future__ import annotations

import tempfile
import uuid

import boto3
from fastapi import Request

from app.config import settings
from app.storage.local import LocalAssetStore, StoredAsset


class S3AssetStore:
    """S3-compatible private storage using the same validated intake path as local development."""

    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url or None,
            region_name=settings.storage_region,
            aws_access_key_id=settings.storage_access_key_id or None,
            aws_secret_access_key=settings.storage_secret_access_key or None,
        )

    async def receive_image(
        self,
        request: Request,
        organization_id: uuid.UUID,
        artwork_id: uuid.UUID,
        asset_id: uuid.UUID,
        expected_size: int,
        expected_mime: str,
    ) -> StoredAsset:
        # Bytes remain quarantined on local ephemeral storage until Pillow has
        # decoded them and the declared size/MIME have been verified.
        with tempfile.TemporaryDirectory(prefix="vernis-intake-") as temporary_root:
            validator = LocalAssetStore(root=temporary_root)
            stored = await validator.receive_image(
                request=request,
                organization_id=organization_id,
                artwork_id=artwork_id,
                asset_id=asset_id,
                expected_size=expected_size,
                expected_mime=expected_mime,
            )
            validated_path = validator.path_for(stored.object_key)
            self.client.upload_file(
                str(validated_path),
                settings.storage_bucket,
                stored.object_key,
                ExtraArgs={
                    "ContentType": stored.mime_type,
                    "Metadata": {"sha256": stored.sha256},
                },
            )
            return stored

    def signed_download_url(self, object_key: str, expires_in: int = 60) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.storage_bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
