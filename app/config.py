from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""

    # Hugging Face
    hf_api_key: str = ""

    # Gemini models
    gemini_outline_model: str = "gemini-3.1-flash-lite"
    gemini_story_model: str = "gemini-3.1-pro-preview"
    gemini_image_model: str = "gemini-2.5-flash-image"

    # Image generation
    image_backend: str = "gemini"
    hf_image_model: str = "black-forest-labs/FLUX.1-schnell"
    local_diffusion_model: str = "runwayml/stable-diffusion-v1-5"

    # Comic configuration
    panels_per_comic: int = 5
    image_width: int = 768
    image_height: int = 768

    # Output directory
    output_dir: str = "static"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()