from __future__ import annotations

import base64
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

from openai import APITimeoutError, OpenAI

from app.config import settings
from app.schemas import GenerateRequest, GenerateResponse, GeneratedImage
from app.style_catalog import ART_STYLES, DEFAULT_STYLE_KEY, detect_style_key

logger = logging.getLogger(__name__)

MASTER_SIZE_MAP = {
    "square": ("2048x2048", 2048, 2048),
    "landscape": ("2048x1360", 2048, 1360),
    "portrait": ("1360x2048", 1360, 2048),
    "widescreen": ("2560x1440", 2560, 1440),
}
STANDARD_SIZE_MAP = {
    "square": ("1024x1024", 1024, 1024),
    "landscape": ("1536x1024", 1536, 1024),
    "portrait": ("1024x1536", 1024, 1536),
    "widescreen": ("1536x864", 1536, 864),
}
QUALITY_MAP = {"draft": "low", "standard": "medium", "studio": "high", "masterpiece": "max"}
PALETTE_DIRECTIONS = {
    "artist-led": "Let the selected medium and subject determine a sophisticated, natural color harmony.",
    "chromatic": "Use bold complementary color tension, jewel-like saturation, and carefully controlled chromatic vibration.",
    "earth-and-gold": "Build from mineral earth pigments, umber, sienna, bone black, and restrained gilded highlights.",
    "nocturne": "Use deep blue-black nocturnal values with sparse luminous accents and subtle temperature shifts in the shadows.",
    "luminous": "Favor translucent light, opalescent color relationships, glowing atmosphere, and bright but nuanced highlights.",
    "unexpected": "Create an uncommon, collectible palette with one surprising dissonant accent while preserving overall harmony.",
}
PURPOSE_DIRECTIONS = {
    "gallery-original": "Compose it as a singular gallery centerpiece with close-view material depth and a commanding silhouette.",
    "fine-art-print": "Compose for a premium archival art print with clean edge-to-edge framing, rich tonal separation, and detail that survives enlargement.",
    "editorial": "Create a memorable editorial image with an immediate visual thesis, strong negative space, and a clear focal read.",
    "collector-series": "Make it feel like one work from a coherent limited collector series: distinctive, repeatable in visual language, and unmistakably authored.",
}


class ImageGenerationError(RuntimeError):
    pass


def resolve_style(request: GenerateRequest) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    style_key = detect_style_key(request.prompt) if request.style_id == "auto" else request.style_id
    if style_key not in ART_STYLES:
        raise ValueError(f"Unknown style_id: {style_key}")
    secondary = None
    if request.secondary_style_id:
        if request.secondary_style_id not in ART_STYLES:
            raise ValueError(f"Unknown secondary_style_id: {request.secondary_style_id}")
        if request.secondary_style_id != style_key:
            secondary = ART_STYLES[request.secondary_style_id]
    return style_key, ART_STYLES.get(style_key, ART_STYLES[DEFAULT_STYLE_KEY]), secondary


def build_generation_prompt(request: GenerateRequest) -> tuple[str, str, dict[str, Any]]:
    style_key, style, secondary = resolve_style(request)
    style_direction = style["direction"]
    if secondary:
        style_direction += f"; subtly blend these secondary material qualities: {secondary['direction']}"
    if request.originality >= 82:
        originality_direction = "Push toward an unconventional interpretation, surprising composition, and rare visual motifs while keeping the subject legible."
    elif request.originality >= 55:
        originality_direction = "Balance a clear subject with original compositional decisions and a recognizably authored visual voice."
    else:
        originality_direction = "Favor classical clarity, familiar visual grammar, and restrained experimentation."
    avoid = request.negative_prompt or "watermarks, signatures, captions, borders, mockup frames, duplicated subjects, malformed anatomy, muddy colors, generic stock imagery"
    prompt = f"""Create an original, exhibition-quality artwork.

SUBJECT AND INTENT
{request.prompt}

ART DIRECTION
Primary visual language: {style['name']}.
{style_direction}.
Use this palette as a harmonic guide, not a rigid swatch set: {', '.join(style['palette'])}.
Chromatic direction: {PALETTE_DIRECTIONS[request.palette_mode]}
Originality direction: {originality_direction}

PRESENTATION INTENT
{PURPOSE_DIRECTIONS[request.artwork_purpose]}

COMPOSITION AND CRAFT
Build a deliberate focal hierarchy with foreground, middle ground, and background separation where appropriate. Preserve convincing perspective, material specificity, edge control, and intentional mark-making. Every detail must support the central idea. The result should feel authored, cohesive, and suitable for a premium gallery print—not like a template, filter, or stock image.

OUTPUT CONSTRAINTS
Fill the entire canvas. Do not render a frame, gallery wall, canvas mockup, UI, or process notes. Do not add text unless the subject explicitly asks for legible text. Avoid: {avoid}."""
    return prompt, style_key, style


def _read_field(item: Any, field: str) -> Any:
    return item.get(field) if isinstance(item, dict) else getattr(item, field, None)


def generate_artwork(request: GenerateRequest) -> GenerateResponse:
    if not settings.openai_api_key:
        raise ImageGenerationError("Image generation is not configured. Set OPENAI_API_KEY on the server.")

    prompt, style_key, style = build_generation_prompt(request)
    size_map = STANDARD_SIZE_MAP if request.quality in {"draft", "standard"} else MASTER_SIZE_MAP
    size, width, height = size_map[request.aspect_ratio]
    requested_quality = QUALITY_MAP[request.quality]
    generation_id = uuid.uuid4().hex
    output_dir = Path(settings.generated_assets_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)
    model_candidates = [settings.image_model]
    if settings.image_fallback_model and settings.image_fallback_model not in model_candidates:
        model_candidates.append(settings.image_fallback_model)

    response, used_model, last_error = None, settings.image_model, None
    for model in model_candidates:
        quality = requested_quality if "2.5" in model else (requested_quality if requested_quality != "max" else "high")
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "n": request.variants,
                "output_format": settings.image_output_format,
                "output_compression": 82,
            }
            if request.safety_identifier:
                # Kept in extra_body for compatibility with SDK releases whose
                # typed method signature predates this API field.
                kwargs["extra_body"] = {"safety_identifier": request.safety_identifier}
            response = client.images.generate(**kwargs)
            used_model = model
            break
        except Exception as exc:  # SDK exception classes differ by transport/version.
            last_error = exc
            logger.warning("Image model %s failed: %s", model, exc.__class__.__name__)
            # A timed-out render may still be running provider-side. Starting a
            # second high-resolution render would double both latency and cost.
            if isinstance(exc, APITimeoutError):
                break

    if response is None:
        raise ImageGenerationError("The image provider could not complete this generation. Please retry or choose a lower quality.") from last_error

    generated: list[GeneratedImage] = []
    extension = settings.image_output_format
    for index, item in enumerate(response.data or []):
        image_id = f"{generation_id}-{index + 1}"
        b64_data, remote_url = _read_field(item, "b64_json"), _read_field(item, "url")
        checksum = None
        if b64_data:
            file_path = output_dir / f"{image_id}.{extension}"
            image_bytes = base64.b64decode(b64_data)
            file_path.write_bytes(image_bytes)
            checksum = hashlib.sha256(image_bytes).hexdigest()
            url = f"/generated/{file_path.name}"
        elif remote_url:
            url = remote_url
        else:
            logger.error("Image provider returned an item without image data")
            continue
        generated.append(GeneratedImage(id=image_id, url=url, width=width, height=height, format=extension, sha256=checksum))

    if not generated:
        raise ImageGenerationError("The image provider returned no usable images.")

    return GenerateResponse(
        generation_id=generation_id,
        images=generated,
        style_id=style_key,
        style_name=style["name"],
        palette=style["palette"],
        model=used_model,
        quality=request.quality,
        aspect_ratio=request.aspect_ratio,
        palette_mode=request.palette_mode,
        artwork_purpose=request.artwork_purpose,
        originality=request.originality,
        revised_prompt=prompt,
    )
