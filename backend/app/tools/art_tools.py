from langchain_core.tools import tool

from app.schemas import GenerateRequest
from app.services.image_service import generate_artwork
from app.style_catalog import ART_STYLES, detect_style_key


@tool
def generate_color_palette(mood_or_style: str) -> dict:
    """Select an authentic five-color palette for an art movement or mood."""
    style_key = detect_style_key(mood_or_style)
    style = ART_STYLES[style_key]
    return {"style_key": style_key, "mood": style["name"], "hex_codes": style["palette"]}


@tool
def calculate_grid_anchors(width: int = 2048, height: int = 1360, divisions: int = 3) -> dict:
    """Calculate compositional grid anchor coordinates."""
    safe_divisions = min(max(divisions, 2), 12)
    return {
        "canvas_size": f"{width}x{height}",
        "divisions": safe_divisions,
        "horizontal_anchors": [round((width / safe_divisions) * i, 1) for i in range(1, safe_divisions)],
        "vertical_anchors": [round((height / safe_divisions) * i, 1) for i in range(1, safe_divisions)],
    }


@tool
def generate_canvas_painting(visual_description: str, style_choice: str = "auto") -> dict:
    """Generate a high-resolution, exhibition-quality artwork and return its durable asset URL."""
    style_id = detect_style_key(style_choice) if style_choice != "auto" else "auto"
    result = generate_artwork(
        GenerateRequest(prompt=visual_description, style_id=style_id, quality="studio", variants=1)
    )
    image = result.images[0]
    return {
        "image_url": image.url,
        "style_key": result.style_id,
        "style_name": result.style_name,
        "engine": result.model,
        "description": visual_description,
        "generation_id": result.generation_id,
    }


domain_tools = [generate_color_palette, calculate_grid_anchors, generate_canvas_painting]
