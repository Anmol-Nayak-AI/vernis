from __future__ import annotations

import hashlib
import io
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ArtworkAsset,
    AssetFingerprint,
    EvaluationRun,
    ImageComparison,
    ModelVersion,
    VisualEmbedding,
)
from app.storage import get_asset_store

MODEL_IDENTIFIER = "vernis-visual-baseline"
MODEL_VERSION = "1.0.0"
EMBEDDING_DIMENSIONS = 96
MODEL_LIMITATIONS = [
    "The descriptor captures coarse color and spatial appearance; it is not an authorship or authenticity model.",
    "Large rotations, perspective shifts, occlusion, and material changes can reduce similarity.",
    "Pixel-change regions are sensitive to lighting, camera, crop, and viewpoint differences.",
    "All similarity and change findings require human review in their domain context.",
]


class InferenceInputError(ValueError):
    pass


@dataclass(frozen=True)
class DecodedImage:
    image: Image.Image
    sha256: str
    metadata: dict[str, Any]


def ensure_model_version(db: Session) -> ModelVersion:
    model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_identifier == MODEL_IDENTIFIER,
            ModelVersion.version == MODEL_VERSION,
        )
    )
    if model is not None:
        return model
    model = ModelVersion(
        model_identifier=MODEL_IDENTIFIER,
        version=MODEL_VERSION,
        task="image_fingerprint_embedding_comparison",
        implementation="Pillow+NumPy dHash/spatial-color descriptor/translation registration",
        status="development",
        parameters={
            "embedding_dimensions": EMBEDDING_DIMENSIONS,
            "registration_max_translation_px": 8,
            "comparison_size": 256,
        },
        limitations=MODEL_LIMITATIONS,
        evaluation_summary={},
    )
    db.add(model)
    db.flush()
    return model


def _asset_bytes(asset: ArtworkAsset) -> bytes:
    if asset.status != "ready" or not asset.object_key:
        raise InferenceInputError("The asset is not ready for inference.")
    return get_asset_store().read_bytes(asset.object_key)


def decode_asset(asset: ArtworkAsset) -> DecodedImage:
    payload = _asset_bytes(asset)
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.load()
            metadata = {
                "format": source.format,
                "mode": source.mode,
                "width": source.width,
                "height": source.height,
                "exif_tag_count": len(source.getexif()),
                "icc_profile_present": bool(source.info.get("icc_profile")),
                "dpi": list(source.info.get("dpi", ())) or None,
            }
            normalized = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InferenceInputError("The stored asset cannot be safely decoded.") from exc
    return DecodedImage(normalized, hashlib.sha256(payload).hexdigest(), metadata)


def perceptual_hash(image: Image.Image) -> str:
    gray = np.asarray(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS), dtype=np.int16)
    bits = gray[:, 1:] > gray[:, :-1]
    value = 0
    for bit in bits.ravel():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def visual_descriptor(image: Image.Image) -> list[float]:
    rgb = np.asarray(image.resize((128, 128), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    spatial: list[float] = []
    for row in range(4):
        for column in range(4):
            block = rgb[row * 32 : (row + 1) * 32, column * 32 : (column + 1) * 32]
            spatial.extend(float(value) for value in block.mean(axis=(0, 1)))
    histograms: list[float] = []
    for channel in range(3):
        histogram, _ = np.histogram(rgb[:, :, channel], bins=16, range=(0.0, 1.0), density=False)
        histograms.extend(float(value) for value in histogram / max(1, histogram.sum()))
    vector = np.asarray(spatial + histograms, dtype=np.float32)
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return [round(float(value), 8) for value in vector]


def analyze_asset(db: Session, asset: ArtworkAsset) -> tuple[AssetFingerprint, VisualEmbedding]:
    model = ensure_model_version(db)
    existing_fingerprint = db.scalar(
        select(AssetFingerprint).where(
            AssetFingerprint.asset_id == asset.id,
            AssetFingerprint.model_version_id == model.id,
        )
    )
    existing_embedding = db.scalar(
        select(VisualEmbedding).where(
            VisualEmbedding.asset_id == asset.id,
            VisualEmbedding.model_version_id == model.id,
        )
    )
    if existing_fingerprint is not None and existing_embedding is not None:
        return existing_fingerprint, existing_embedding
    decoded = decode_asset(asset)
    fingerprint = existing_fingerprint or AssetFingerprint(
        organization_id=asset.organization_id,
        asset_id=asset.id,
        model_version_id=model.id,
        cryptographic_hash=decoded.sha256,
        perceptual_hash=perceptual_hash(decoded.image),
        width=decoded.image.width,
        height=decoded.image.height,
        color_mode=decoded.image.mode,
        metadata_summary=decoded.metadata,
    )
    embedding = existing_embedding or VisualEmbedding(
        organization_id=asset.organization_id,
        asset_id=asset.id,
        model_version_id=model.id,
        embedding=visual_descriptor(decoded.image),
        dimensions=EMBEDDING_DIMENSIONS,
        norm="l2",
    )
    db.add_all([fingerprint, embedding])
    db.flush()
    return fingerprint, embedding


def hamming_similarity(left: str, right: str) -> float:
    distance = (int(left, 16) ^ int(right, 16)).bit_count()
    return 1.0 - distance / 64.0


def cosine_similarity(left: list[float], right: list[float]) -> float:
    a = np.asarray(left, dtype=np.float32)
    b = np.asarray(right, dtype=np.float32)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denominator) if denominator else 0.0


def similarity_search(db: Session, asset: ArtworkAsset, limit: int = 10) -> list[dict[str, Any]]:
    source_fingerprint, source_embedding = analyze_asset(db, asset)
    candidates = db.scalars(
        select(ArtworkAsset).where(
            ArtworkAsset.organization_id == asset.organization_id,
            ArtworkAsset.status == "ready",
            ArtworkAsset.id != asset.id,
        )
    ).all()
    matches: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_fingerprint, candidate_embedding = analyze_asset(db, candidate)
        embedding_score = cosine_similarity(source_embedding.embedding, candidate_embedding.embedding)
        hash_score = hamming_similarity(source_fingerprint.perceptual_hash, candidate_fingerprint.perceptual_hash)
        combined = 0.7 * embedding_score + 0.3 * hash_score
        matches.append(
            {
                "asset_id": str(candidate.id),
                "artwork_id": str(candidate.artwork_id),
                "embedding_similarity": round(embedding_score, 6),
                "perceptual_hash_similarity": round(hash_score, 6),
                "combined_similarity": round(combined, 6),
                "interpretation": "visual retrieval candidate; not evidence of authorship, ownership, or infringement",
            }
        )
    matches.sort(key=lambda item: item["combined_similarity"], reverse=True)
    return matches[:limit]


def _best_translation(left: np.ndarray, right: np.ndarray, maximum: int = 8) -> tuple[int, int, float]:
    best = (0, 0, math.inf)
    for y in range(-maximum, maximum + 1, 2):
        for x in range(-maximum, maximum + 1, 2):
            y0a, y1a = max(0, y), min(left.shape[0], left.shape[0] + y)
            x0a, x1a = max(0, x), min(left.shape[1], left.shape[1] + x)
            y0b, y1b = max(0, -y), min(right.shape[0], right.shape[0] - y)
            x0b, x1b = max(0, -x), min(right.shape[1], right.shape[1] - x)
            a = left[y0a:y1a, x0a:x1a]
            b = right[y0b:y1b, x0b:x1b]
            if a.size == 0 or b.size == 0:
                continue
            error = float(np.mean(np.square(a - b)))
            if error < best[2]:
                best = (x, y, error)
    return best


def compare_assets(db: Session, source: ArtworkAsset, target: ArtworkAsset) -> ImageComparison:
    if source.organization_id != target.organization_id:
        raise InferenceInputError("Cross-organization comparisons are not permitted.")
    started = time.perf_counter()
    model = ensure_model_version(db)
    source_fingerprint, source_embedding = analyze_asset(db, source)
    target_fingerprint, target_embedding = analyze_asset(db, target)
    source_image = decode_asset(source).image.resize((256, 256), Image.Resampling.LANCZOS)
    target_image = decode_asset(target).image.resize((256, 256), Image.Resampling.LANCZOS)
    source_gray = np.asarray(source_image.convert("L"), dtype=np.float32)
    target_gray = np.asarray(target_image.convert("L"), dtype=np.float32)
    offset_x, offset_y, registration_error = _best_translation(source_gray, target_gray)
    aligned = np.roll(target_gray, shift=(offset_y, offset_x), axis=(0, 1))
    delta = np.abs(source_gray - aligned)
    threshold = max(20.0, float(np.percentile(delta, 90)))
    changed = delta > threshold
    changed_ratio = float(changed.mean())
    regions: list[dict[str, Any]] = []
    coordinates = np.argwhere(changed)
    if coordinates.size:
        y_min, x_min = coordinates.min(axis=0)
        y_max, x_max = coordinates.max(axis=0)
        regions.append(
            {
                "kind": "observable_pixel_change",
                "normalized_box": [
                    round(float(x_min / 256), 5),
                    round(float(y_min / 256), 5),
                    round(float((x_max + 1) / 256), 5),
                    round(float((y_max + 1) / 256), 5),
                ],
                "pixel_fraction": round(changed_ratio, 6),
                "requires_review": True,
            }
        )
    scores = {
        "embedding_similarity": round(cosine_similarity(source_embedding.embedding, target_embedding.embedding), 6),
        "perceptual_hash_similarity": round(
            hamming_similarity(source_fingerprint.perceptual_hash, target_fingerprint.perceptual_hash), 6
        ),
        "registered_mean_absolute_pixel_difference": round(float(delta.mean()) / 255.0, 6),
        "changed_pixel_fraction": round(changed_ratio, 6),
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }
    comparison = ImageComparison(
        organization_id=source.organization_id,
        source_asset_id=source.id,
        target_asset_id=target.id,
        model_version_id=model.id,
        parameters={"resize": [256, 256], "registration_max_translation_px": 8, "change_threshold": threshold},
        scores=scores,
        alignment={"translation_x": offset_x, "translation_y": offset_y, "mean_squared_error": registration_error},
        regions=regions,
        limitations=MODEL_LIMITATIONS,
        output_artifacts=[],
        evaluation_status="unreviewed",
        processed_at=datetime.now(timezone.utc),
    )
    db.add(comparison)
    db.flush()
    return comparison


def run_baseline_evaluation(db: Session) -> EvaluationRun:
    """Run a small, reproducible synthetic smoke benchmark.

    This verifies implementation behavior; it is deliberately not presented as
    a claim about performance on real artwork or conservation imagery.
    """
    model = ensure_model_version(db)
    started = time.perf_counter()
    grid_y, grid_x = np.mgrid[0:128, 0:128]
    base_array = np.stack(
        [grid_x * 2, grid_y * 2, ((grid_x + grid_y) % 128) * 2], axis=2
    ).astype(np.uint8)
    base = Image.fromarray(base_array, mode="RGB")
    translated = Image.new("RGB", base.size, (0, 0, 0))
    translated.paste(base, (3, 2))
    color_shift = Image.fromarray(np.clip(base_array.astype(np.int16) + 6, 0, 255).astype(np.uint8), mode="RGB")
    distinct_array = np.zeros((128, 128, 3), dtype=np.uint8)
    distinct_array[:, ::8, :] = (245, 35, 35)
    distinct_array[::8, :, :] = (35, 220, 80)
    distinct = Image.fromarray(distinct_array, mode="RGB")
    pairs = [
        (base, translated, True, "translated duplicate"),
        (base, color_shift, True, "minor color shift"),
        (base, distinct, False, "different synthetic pattern"),
    ]
    predictions: list[bool] = []
    measurements: list[dict[str, Any]] = []
    for left, right, expected_duplicate, label in pairs:
        embedding_score = cosine_similarity(visual_descriptor(left), visual_descriptor(right))
        hash_score = hamming_similarity(perceptual_hash(left), perceptual_hash(right))
        combined = 0.7 * embedding_score + 0.3 * hash_score
        predicted = combined >= 0.9
        predictions.append(predicted == expected_duplicate)
        measurements.append(
            {
                "fixture": label,
                "expected_duplicate": expected_duplicate,
                "combined_similarity": round(combined, 6),
                "threshold": 0.9,
                "correct": predicted == expected_duplicate,
            }
        )
    positives = [item for item in measurements if item["expected_duplicate"]]
    negatives = [item for item in measurements if not item["expected_duplicate"]]
    run = EvaluationRun(
        model_version_id=model.id,
        fixture_name="synthetic-visual-baseline-smoke-v1",
        status="succeeded",
        sample_count=len(pairs),
        metrics={
            "duplicate_detection_accuracy": round(sum(predictions) / len(predictions), 6),
            "true_positive_rate": round(sum(item["correct"] for item in positives) / len(positives), 6),
            "false_positive_rate": round(sum(not item["correct"] for item in negatives) / len(negatives), 6),
            "latency_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "measurements": measurements,
        },
        notes=[
            "Generated synthetic fixture; no external or copyrighted dataset is bundled.",
            "This smoke benchmark is too small to validate production accuracy.",
            "Segmentation IoU is not reported because this model does not perform semantic damage segmentation.",
        ],
    )
    db.add(run)
    db.flush()
    model.evaluation_summary = {
        "latest_run_id": str(run.id),
        "fixture": run.fixture_name,
        "sample_count": run.sample_count,
        "status": "smoke_tested_not_domain_validated",
    }
    return run
