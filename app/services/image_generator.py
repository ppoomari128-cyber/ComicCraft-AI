"""Image generation service for ComicCraft AI.

Primary image generator:
    Google Gemini image model

Fallbacks:
    Hugging Face Inference Providers
    Local ComicCraft placeholder image

The service keeps the same generate_images() interface used by routes.py.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings as _get_runtime_settings


# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


# -------------------------------------------------------------------
# Export directory
# -------------------------------------------------------------------

EXPORT_DIR = PROJECT_ROOT / "static" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# Settings compatibility
# -------------------------------------------------------------------

def get_settings():
    return _get_runtime_settings()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _coerce_prompt(
    prompt: str | None,
    fallback: str,
) -> str:
    """Clean and limit a prompt."""

    text = (prompt or "").strip()

    if not text:
        text = fallback.strip()

    return " ".join(text.split())[:4000]


def _safe_filename(filename: str) -> str:
    """Create a safe filename."""

    base = Path(filename).name or "comic-panel.png"

    safe = "".join(
        ch if ch.isalnum() or ch in "._-"
        else "_"
        for ch in base
    )

    return safe or "comic-panel.png"


def _public_export_url(filename: str) -> str:
    """Return browser URL for generated image."""

    output_dir = (
        getattr(get_settings(), "output_dir", None)
        or "static"
    )

    output_dir = str(output_dir).strip().strip("/")

    if output_dir and output_dir != "static":
        return f"/{output_dir}/{filename}"

    return f"/static/exports/{filename}"


# -------------------------------------------------------------------
# Gemini settings
# -------------------------------------------------------------------

def _get_gemini_api_key() -> str:
    """Get Gemini API key."""

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or getattr(get_settings(), "gemini_api_key", None)
        or getattr(get_settings(), "google_api_key", None)
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from the environment."
        )

    return str(api_key).strip()


def _get_gemini_model() -> str:
    """Get Gemini image model."""

    model = (
        os.getenv("GEMINI_IMAGE_MODEL")
        or getattr(get_settings(), "gemini_image_model", None)
        or "gemini-2.5-flash-image"
    )

    return str(model).strip()


# -------------------------------------------------------------------
# Hugging Face settings
# -------------------------------------------------------------------

def _get_hf_token() -> str:
    """Get Hugging Face token."""

    token = (
        os.getenv("HF_API_KEY")
        or os.getenv("HF_TOKEN")
        or getattr(get_settings(), "hf_api_key", None)
    )

    if not token or not str(token).strip():
        raise RuntimeError(
            "HF_API_KEY is missing from the .env file. Please add your Hugging Face token in .env."
        )

    return str(token).strip()


def _get_hf_model() -> str:
    """Get Hugging Face image model."""

    model = (
        os.getenv("HF_IMAGE_MODEL")
        or "black-forest-labs/FLUX.1-schnell"
    )

    return str(model).strip()


# -------------------------------------------------------------------
# Build comic prompt
# -------------------------------------------------------------------

def _build_comic_prompt(prompt: str) -> str:
    """Convert panel description into a stronger image prompt."""

    safe_prompt = _coerce_prompt(
        prompt,
        "A cinematic adventure comic panel."
    )

    return f"""
Create one finished high-quality comic-book illustration.

Scene:
{safe_prompt}

Visual style:
- professional comic book artwork
- cinematic composition
- polished digital illustration
- expressive characters
- clean detailed line art
- vibrant colors
- detailed environment
- strong foreground and background depth
- cinematic lighting
- clear focal subject
- family-friendly
- visually appealing
- coherent character design

Important:
- one complete comic panel
- no speech bubbles
- no captions
- no written text
- no watermark
- no logo
- no borders
""".strip()


# -------------------------------------------------------------------
# Gemini image generation
# -------------------------------------------------------------------

def _generate_with_gemini(
    prompt: str,
    filename: str,
    width: int = 768,
    height: int = 768,
) -> str:
    """Generate one real image using the Gemini image model."""

    try:
        from google import genai
    except ImportError as error:
        raise RuntimeError(
            "google-genai is not installed. "
            "Run: python -m pip install google-genai"
        ) from error

    api_key = _get_gemini_api_key()
    model_name = _get_gemini_model()
    full_prompt = _build_comic_prompt(prompt)

    print()
    print("=" * 70)
    print("[ComicCraft] Generating REAL AI image")
    print("[ComicCraft] Provider : Gemini")
    print(f"[ComicCraft] Model    : {model_name}")
    print(f"[ComicCraft] File     : {filename}")
    print("=" * 70)

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config={
                "response_modalities": ["TEXT", "IMAGE"],
            },
        )
    except Exception as error:
        error_text = str(error)
        print(f"[ComicCraft] Gemini generation failed: {error_text}")
        raise RuntimeError(
            f"Gemini image generation failed: {error_text}"
        ) from error

    image_bytes = None

    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", []) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is not None:
                image_bytes = getattr(inline_data, "data", None)
                if image_bytes:
                    break
        if image_bytes:
            break

    if not image_bytes:
        raise RuntimeError("Gemini returned no image data.")

    output_path = EXPORT_DIR / _safe_filename(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    if not output_path.exists():
        raise RuntimeError("Generated image file was not created.")

    if output_path.stat().st_size == 0:
        raise RuntimeError("Generated image file is empty.")

    print("[ComicCraft] AI image saved successfully:")
    print(f"[ComicCraft] {output_path}")
    print(f"[ComicCraft] Size: {output_path.stat().st_size} bytes")

    return _public_export_url(output_path.name)


# -------------------------------------------------------------------
# Hugging Face image generation
# -------------------------------------------------------------------

def _generate_with_huggingface(
    prompt: str,
    filename: str,
    width: int = 768,
    height: int = 768,
) -> str:
    """Generate one real image using Hugging Face."""

    try:
        from huggingface_hub import InferenceClient
    except ImportError as error:
        raise RuntimeError(
            "huggingface_hub is not installed. "
            "Run: python -m pip install -U huggingface_hub"
        ) from error

    token = _get_hf_token()
    model_name = _get_hf_model()

    full_prompt = _build_comic_prompt(prompt)

    print()
    print("=" * 70)
    print("[ComicCraft] Generating REAL AI image")
    print("[ComicCraft] Provider : Hugging Face")
    print(f"[ComicCraft] Model    : {model_name}")
    print(f"[ComicCraft] File     : {filename}")
    print("=" * 70)

    import io

    kwargs: dict[str, Any] = {}
    if "flux" in model_name.lower():
        kwargs["num_inference_steps"] = 4

    preferred_provider = os.getenv("HF_PROVIDER", "hf-inference").strip()
    providers_to_try = [preferred_provider]
    for alt in ("hf-inference", "auto", None):
        if alt not in providers_to_try:
            providers_to_try.append(alt)

    image = None
    last_error: Exception | None = None

    for prov in providers_to_try:
        try:
            client = InferenceClient(
                token=token,
                provider=prov,
            )
            image = client.text_to_image(
                prompt=full_prompt,
                model=model_name,
                width=width,
                height=height,
                **kwargs,
            )
            if image is not None:
                break
        except Exception as error:
            last_error = error
            print(f"[ComicCraft] Hugging Face attempt with provider={prov} notice: {error}")

    if image is None:
        error_text = str(last_error or "Unknown error")
        print(f"[ComicCraft] Hugging Face generation failed: {error_text}")
        raise RuntimeError(
            f"Hugging Face image generation failed: {error_text}"
        ) from last_error

    output_path = EXPORT_DIR / _safe_filename(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(image, bytes):
        image = Image.open(io.BytesIO(image)).convert("RGB")
    elif not isinstance(image, Image.Image):
        try:
            image = Image.open(io.BytesIO(image)).convert("RGB")
        except Exception:
            pass

    image.save(output_path, format="PNG")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Generated image file is empty or missing.")

    print(
        "[ComicCraft] AI image saved successfully:"
    )

    print(
        f"[ComicCraft] {output_path}"
    )

    print(
        f"[ComicCraft] Size: "
        f"{output_path.stat().st_size} bytes"
    )

    return _public_export_url(
        output_path.name
    )


# -------------------------------------------------------------------
# Free AI image generation (Zero-cost fallback)
# -------------------------------------------------------------------

def _generate_with_free_ai(
    prompt: str,
    filename: str,
    width: int = 768,
    height: int = 768,
) -> str:
    """Generate one real image using high-speed free AI generator with automatic retries."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        raise RuntimeError("Skip remote network call during unit tests")

    import io
    import time
    import urllib.parse
    import requests

    # Extract the concise scene description to prevent oversized URLs
    scene = prompt
    if "Scene:" in prompt:
        scene = prompt.split("Scene:", 1)[1]
    if "Visual style:" in scene:
        scene = scene.split("Visual style:", 1)[0]
    if "Panel description:" in scene:
        scene = scene.split("Panel description:", 1)[1]
    if "Create a polished" in scene:
        scene = scene.split("Create a polished", 1)[0]

    scene_clean = " ".join(scene.split())[:180].strip("., -")
    if not scene_clean:
        scene_clean = "comic book character in dynamic adventure scene"

    full_query = f"comic book art style, {scene_clean}, vivid colors, cinematic lighting"
    encoded = urllib.parse.quote(full_query)
    url = f"https://image.pollinations.ai/prompt/{encoded}"

    print()
    print("=" * 70)
    print("[ComicCraft] Generating REAL AI image")
    print("[ComicCraft] Provider : Free AI Image Engine")
    print(f"[ComicCraft] Prompt   : {scene_clean}")
    print(f"[ComicCraft] File     : {filename}")
    print("=" * 70)

    last_error = None
    resp = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "ComicCraftAI/1.0"},
                timeout=40,
            )
            resp.raise_for_status()
            if len(resp.content) > 1000:
                break
        except Exception as err:
            last_error = err
            print(f"[ComicCraft] Attempt {attempt} notice: {err}. Retrying...")
            time.sleep(2)

    if resp is None or not resp.ok or len(resp.content) <= 1000:
        raise RuntimeError(f"Free AI generator failed after 3 attempts: {last_error}")

    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    if img.size != (width, height):
        img = img.resize((width, height), Image.Resampling.LANCZOS)

    output_path = EXPORT_DIR / _safe_filename(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Free AI image file was not created properly.")

    print("[ComicCraft] AI image saved successfully:")
    print(f"[ComicCraft] {output_path}")
    print(f"[ComicCraft] Size: {output_path.stat().st_size} bytes")

    return _public_export_url(output_path.name)


# -------------------------------------------------------------------
# Local fallback image
# -------------------------------------------------------------------

def _load_font(size: int):
    """Try to load a common font."""

    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(
                    font_path,
                    size,
                )
        except Exception:
            pass

    return ImageFont.load_default()


def _build_placeholder_text(prompt: str) -> str:
    """Build a short summary snippet matching the panel mockup."""

    meta = _coerce_prompt(prompt, "Comic panel")

    match = re.search(
        r"Comic panel\s+(\d+)\s+of a\s+(\d+)-panel story\.?\s*(?:Main story:\s*(.*))?",
        meta,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        panel_no, total_panels, story = match.groups()
        story = re.sub(r"\s+", " ", (story or "")).strip()
        if story:
            story_summary = story[:110]
            if len(story) > 110:
                story_summary += "..."
            return (
                f"Comic panel {panel_no} of a {total_panels}-panel story. "
                f"Main story: {story_summary}"
            )
        return f"Comic panel {panel_no} of a {total_panels}-panel story."

    if "Main story:" in meta:
        story = meta.split("Main story:", 1)[1].strip()
        story = re.sub(r"\s+", " ", story)
        if len(story) > 120:
            story = story[:117] + "..."
        return story

    return meta[:120] + ("..." if len(meta) > 120 else "")


def _create_placeholder_image(
    filename: str,
    prompt: str,
    width: int = 768,
    height: int = 768,
) -> str:
    """Create a local comic-style fallback image."""

    output_path = EXPORT_DIR / _safe_filename(filename)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGB",
        (width, height),
        (11, 17, 28),
    )

    draw = ImageDraw.Draw(image)

    # Outer white frame
    draw.rectangle(
        [0, 0, width - 1, height - 1],
        outline=(255, 255, 255),
        width=8,
    )

    panel_w = 150
    panel_h = 150
    panel_gap = 42
    start_x = 58
    start_y = 255
    panels = 6

    for i in range(panels):
        x = start_x + (i % 3) * (panel_w + panel_gap)
        y = start_y + (i // 3) * (panel_h + panel_gap)
        draw.rectangle(
            [x, y, x + panel_w, y + panel_h],
            outline=(170, 177, 198),
            width=2,
        )

    title_font = _load_font(46)
    heading_font = _load_font(28)
    body_font = _load_font(18)

    draw.text(
        (45, 35),
        "COMICCRAFT AI",
        font=title_font,
        fill=(255, 255, 255),
    )

    draw.text(
        (45, 104),
        "AI Comic Panel",
        font=heading_font,
        fill=(220, 220, 225),
    )

    placeholder_text = _build_placeholder_text(prompt)
    draw.text(
        (45, 138),
        placeholder_text,
        font=body_font,
        fill=(200, 204, 220),
    )

    image.save(
        output_path,
        format="PNG",
    )

    return _public_export_url(
        output_path.name
    )


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def generate_images(
    prompt: str,
    layout: list[str] | None = None,
    width: int = 768,
    height: int = 768,
    **kwargs: Any,
) -> list[str]:
    """
    Generate multiple comic panels.

    Primary:
        Google Gemini AI image generation.

    Fallbacks:
        Hugging Face AI image generation.
        Local ComicCraft placeholder.

    Returns:
        List of browser image URLs.
    """

    # ---------------------------------------------------------------
    # Panel prompts
    # ---------------------------------------------------------------

    prompts = layout or []

    if not prompts:
        prompts = [prompt]

    image_urls: list[str] = []

    # ---------------------------------------------------------------
    # Generate each panel
    # ---------------------------------------------------------------

    for index, panel_prompt in enumerate(
        prompts,
        start=1,
    ):

        filename = (
            f"panel-{index}-{width}x{height}.png"
        )

        print()
        print(
            f"[ComicCraft] "
            f"Generating panel "
            f"{index}/{len(prompts)}..."
        )

        # -----------------------------------------------------------
        # Try Gemini, then Hugging Face, then placeholder fallback
        # -----------------------------------------------------------

        backend = (
            kwargs.get("backend")
            or kwargs.get("image_backend")
            or os.getenv("IMAGE_BACKEND")
            or "gemini"
        ).lower()
        image_url = None
        provider = None

        if backend == "hf":
            try:
                image_url = _generate_with_huggingface(
                    prompt=panel_prompt,
                    filename=filename,
                    width=width,
                    height=height,
                )
                provider = "Hugging Face"
            except Exception as hf_error:
                print(
                    f"[ComicCraft] Hugging Face failed for panel {index}: {hf_error}"
                )

        if not image_url:
            try:
                image_url = _generate_with_gemini(
                    prompt=panel_prompt,
                    filename=filename,
                    width=width,
                    height=height,
                )
                provider = "Gemini"
            except Exception as gemini_error:
                print(
                    f"[ComicCraft] Gemini failed for panel {index}: {gemini_error}"
                )

        if not image_url and backend != "hf":
            try:
                image_url = _generate_with_huggingface(
                    prompt=panel_prompt,
                    filename=filename,
                    width=width,
                    height=height,
                )
                provider = "Hugging Face"
            except Exception:
                pass

        if not image_url:
            try:
                image_url = _generate_with_free_ai(
                    prompt=panel_prompt,
                    filename=filename,
                    width=width,
                    height=height,
                )
                provider = "Free AI"
            except Exception as free_error:
                print(
                    f"[ComicCraft] Free AI generator failed for panel {index}: {free_error}"
                )

        if not image_url:
            print(f"[ComicCraft] Creating fallback panel {index}...")
            image_url = _create_placeholder_image(
                filename=filename,
                prompt=panel_prompt,
                width=width,
                height=height,
            )
            provider = "placeholder"

        print(
            f"[ComicCraft] Panel {index} generated using {provider}."
        )

        image_urls.append(
            image_url
        )

    print()
    print(
        f"[ComicCraft] Generated "
        f"{len(image_urls)} panel image(s)."
    )

    return image_urls


# -------------------------------------------------------------------
# Optional single image helper
# -------------------------------------------------------------------

def generate_image(
    prompt: str,
    filename: str = "comic_panel.png",
    width: int = 768,
    height: int = 768,
    **kwargs: Any,
) -> str:
    """Generate one comic image."""

    backend = (
        kwargs.get("backend")
        or kwargs.get("image_backend")
        or os.getenv("IMAGE_BACKEND")
        or "gemini"
    ).lower()
    if backend == "hf":
        try:
            return _generate_with_huggingface(
                prompt=prompt,
                filename=filename,
                width=width,
                height=height,
            )
        except Exception as error:
            print(f"[ComicCraft] HF single-image failed: {error}")

    try:
        return _generate_with_gemini(
            prompt=prompt,
            filename=filename,
            width=width,
            height=height,
        )
    except Exception as error:
        print(
            f"[ComicCraft] Gemini single-image generation failed: {error}"
        )

    if backend != "hf":
        try:
            return _generate_with_huggingface(
                prompt=prompt,
                filename=filename,
                width=width,
                height=height,
            )
        except Exception:
            pass

    try:
        return _generate_with_free_ai(
            prompt=prompt,
            filename=filename,
            width=width,
            height=height,
        )
    except Exception:
        pass

    return _create_placeholder_image(
        filename=filename,
        prompt=prompt,
        width=width,
        height=height,
        )