from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

AspectRatio = Literal["square", "landscape", "portrait", "widescreen"]
StudioQuality = Literal["draft", "standard", "studio", "masterpiece"]
PaletteMode = Literal["artist-led", "chromatic", "earth-and-gold", "nocturne", "luminous", "unexpected"]
ArtworkPurpose = Literal["gallery-original", "fine-art-print", "editorial", "collector-series"]


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    style_id: str = Field(default="auto", max_length=80)
    secondary_style_id: Optional[str] = Field(default=None, max_length=80)
    aspect_ratio: AspectRatio = "landscape"
    quality: StudioQuality = "standard"
    variants: int = Field(default=1, ge=1, le=4)
    palette_mode: PaletteMode = "artist-led"
    artwork_purpose: ArtworkPurpose = "fine-art-print"
    originality: int = Field(default=72, ge=0, le=100)
    negative_prompt: str = Field(default="", max_length=1000)
    show_grid: bool = False
    safety_identifier: Optional[str] = Field(default=None, max_length=128)

    @field_validator("prompt", "negative_prompt")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())


class GeneratedImage(BaseModel):
    id: str
    url: str
    width: int
    height: int
    format: str
    sha256: Optional[str] = None


class GenerateResponse(BaseModel):
    generation_id: str
    images: list[GeneratedImage]
    style_id: str
    style_name: str
    palette: list[str]
    model: str
    quality: str
    aspect_ratio: str
    palette_mode: str
    artwork_purpose: str
    originality: int
    revised_prompt: str
