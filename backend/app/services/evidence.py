from __future__ import annotations

import hashlib
import io
import re
import uuid
from collections import defaultdict
from typing import Any

import numpy as np
import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ArtworkAsset, EvidenceChunk, EvidenceDocument
from app.storage import get_asset_store

TEXT_EMBEDDING_MODEL = "vernis-hashed-text-embedding-1.0.0"
TEXT_EMBEDDING_DIMENSIONS = 1536
TOKEN_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)


def local_text_embedding(text: str) -> list[float]:
    """Signed feature-hash embedding used for private, CPU-only lexical retrieval."""
    vector = np.zeros(TEXT_EMBEDDING_DIMENSIONS, dtype=np.float32)
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    features = tokens + [f"{tokens[index]}::{tokens[index + 1]}" for index in range(len(tokens) - 1)]
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % TEXT_EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return [round(float(value), 8) for value in vector]


def rebuild_chunks(db: Session, evidence: EvidenceDocument) -> int:
    db.query(EvidenceChunk).filter(EvidenceChunk.evidence_document_id == evidence.id).delete()
    if not evidence.extracted_text:
        return 0
    chunks = [evidence.extracted_text[index : index + 1600] for index in range(0, len(evidence.extracted_text), 1400)]
    for ordinal, content in enumerate(chunks):
        db.add(
            EvidenceChunk(
                organization_id=evidence.organization_id,
                evidence_document_id=evidence.id,
                ordinal=ordinal,
                content=content,
                embedding=local_text_embedding(content),
                embedding_model=TEXT_EMBEDDING_MODEL,
                citation_label=f"{evidence.title} · passage {ordinal + 1}",
            )
        )
    db.flush()
    return len(chunks)


def ocr_evidence_asset(db: Session, evidence: EvidenceDocument) -> int:
    if evidence.asset_id is None:
        raise ValueError("Evidence has no linked image asset.")
    asset = db.scalar(
        select(ArtworkAsset).where(
            ArtworkAsset.organization_id == evidence.organization_id,
            ArtworkAsset.id == evidence.asset_id,
            ArtworkAsset.status == "ready",
        )
    )
    if asset is None or not asset.object_key:
        raise ValueError("Evidence image asset is not ready.")
    payload = get_asset_store().read_bytes(asset.object_key)
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.load()
            normalized = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Evidence image cannot be safely decoded for OCR.") from exc
    extracted = pytesseract.image_to_string(normalized, lang="eng", config="--psm 6").strip()
    evidence.extracted_text = extracted or None
    evidence.extraction_method = "tesseract-ocr-eng-psm6"
    evidence.metadata_fields = {
        **(evidence.metadata_fields or {}),
        "ocr_character_count": len(extracted),
        "ocr_limitations": "OCR text is machine-extracted, unverified, and may contain transcription errors.",
    }
    return rebuild_chunks(db, evidence)


def hybrid_search(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    include_restricted: bool,
    artwork_id: uuid.UUID | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    filters = [EvidenceChunk.organization_id == organization_id]
    if artwork_id is not None:
        filters.append(EvidenceDocument.artwork_id == artwork_id)
    statement = (
        select(EvidenceChunk, EvidenceDocument)
        .join(EvidenceDocument, EvidenceDocument.id == EvidenceChunk.evidence_document_id)
        .where(*filters)
    )
    if not include_restricted:
        statement = statement.where(EvidenceDocument.sensitivity != "restricted")
    rows = db.execute(statement.limit(2000)).all()
    query_vector = np.asarray(local_text_embedding(query), dtype=np.float32)
    query_tokens = {token.lower() for token in TOKEN_PATTERN.findall(query)}
    best_by_document: defaultdict[uuid.UUID, list[dict[str, Any]]] = defaultdict(list)
    for chunk, document in rows:
        vector = np.asarray(chunk.embedding or [0.0] * TEXT_EMBEDDING_DIMENSIONS, dtype=np.float32)
        cosine = float(np.dot(query_vector, vector))
        chunk_tokens = {token.lower() for token in TOKEN_PATTERN.findall(chunk.content)}
        lexical = len(query_tokens & chunk_tokens) / max(1, len(query_tokens))
        score = 0.55 * max(0.0, cosine) + 0.45 * lexical
        if score <= 0:
            continue
        best_by_document[document.id].append(
            {
                "document": document,
                "citation": chunk.citation_label,
                "excerpt": chunk.content[:500],
                "hybrid_score": round(score, 6),
                "embedding_score": round(cosine, 6),
                "lexical_score": round(lexical, 6),
            }
        )
    results: list[dict[str, Any]] = []
    for matches in best_by_document.values():
        best = max(matches, key=lambda item: item["hybrid_score"])
        results.append(best)
    results.sort(key=lambda item: item["hybrid_score"], reverse=True)
    return results[:limit]
