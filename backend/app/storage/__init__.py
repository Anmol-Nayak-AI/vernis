from app.config import settings
from app.storage.local import LocalAssetStore
from app.storage.s3 import S3AssetStore


def get_asset_store() -> LocalAssetStore | S3AssetStore:
    if settings.storage_backend == "local":
        return LocalAssetStore()
    if settings.storage_backend == "s3":
        return S3AssetStore()
    raise RuntimeError(f"Unsupported storage backend: {settings.storage_backend}")

__all__ = ["LocalAssetStore", "S3AssetStore", "get_asset_store"]
