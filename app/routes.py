"""Application routes for the ComicCraft UI."""

from __future__ import annotations

import importlib
import json
import os
from abc import ABC, abstractmethod
from uuid import uuid4

from flask import Blueprint, jsonify, render_template, request, send_from_directory

import app.config
from app.schemas import PromptRequest
from app.services.exporters import export_comic
from app.services.gemini_flash import generate_outline

try:
    image_generator = importlib.import_module("app.services.image_generator")
    generate_images = getattr(image_generator, "generate_images")
except (ImportError, AttributeError):  # pragma: no cover - fallback for missing backend symbol
    def generate_images(*args, **kwargs):
        """Fallback when the image generation backend is unavailable."""
        del args, kwargs
        raise RuntimeError("Image generation backend is unavailable.")

try:
    gemini_pro = importlib.import_module("app.services.gemini_pro")
    _generate_story = getattr(gemini_pro, "generate_story")
except (ImportError, AttributeError):  # pragma: no cover - fallback for missing backend symbol
    _generate_story = None


def generate_story(*args, **kwargs):
    """Wrapper to safely resolve the story generation backend."""
    if _generate_story is None:
        raise RuntimeError("Story generation backend is unavailable.")
    try:
        return _generate_story(*args, **kwargs)
    finally:
        del args, kwargs


bp = Blueprint("main", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXPORTS_DIR = os.path.join(BASE_DIR, "static", "exports")

GENERATED_COMICS = {}


class ConfigBase(ABC):
    """Abstract configuration contract used by the app."""

    @abstractmethod
    def get(self, key, default=None):
        """Return a configuration value or a default."""

    @abstractmethod
    def set(self, key, value):
        """Set a configuration value."""

    @abstractmethod
    def load(self, values=None):
        """Load values into the configuration."""

    @abstractmethod
    def save(self, path=None):
        """Persist the configuration to disk."""

    @abstractmethod
    def get_settings(self):
        """Return a snapshot of the current settings."""


class Config(ConfigBase):
    """Concrete application settings with sane defaults and persistence helpers."""

    def __init__(self, **overrides):
        self._settings = {
            "APP_NAME": "ComicCraft AI",
            "DEBUG": False,
            "SECRET_KEY": os.environ.get("SECRET_KEY", "comiccraft-dev-secret"),
            "EXPORTS_DIR": EXPORTS_DIR,
            "MAX_PANELS": 5,
            "IMAGE_WIDTH": 768,
            "IMAGE_HEIGHT": 768,
            "DEFAULT_STYLE": "cinematic comic book",
        }
        self.update(**overrides)

    def get(self, key, default=None):
        """Return a configuration value or a fallback default."""
        return self._settings.get(key, default)

    def set(self, key, value):
        """Set a configuration value and return the stored value."""
        self._settings[key] = value
        return value

    def __getitem__(self, key):
        return self._settings[key]

    def __setitem__(self, key, value):
        self._settings[key] = value

    def update(self, **kwargs):
        if kwargs:
            self._settings.update(kwargs)
        return self._settings

    def load(self, values=None):
        """Load values from a mapping, iterable pairs, or a JSON file path."""
        if values is None:
            return self.as_dict()

        if isinstance(values, str):
            with open(values, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if hasattr(loaded, "items"):
                self._settings.update(dict(loaded.items()))
            else:
                raise TypeError("Loaded JSON configuration must be an object.")
            return self.as_dict()

        if hasattr(values, "items"):
            self._settings.update(dict(values.items()))
            return self.as_dict()

        if hasattr(values, "__iter__"):
            try:
                self._settings.update(dict(values))
            except (TypeError, ValueError):
                raise TypeError("Config values must be a mapping or iterable of key/value pairs.")
            return self.as_dict()

        raise TypeError("Unsupported config payload type.")

    def save(self, path=None):
        """Persist the current settings to a JSON file and return the path."""
        target = path or os.path.join(BASE_DIR, "config.json")
        directory = os.path.dirname(target) or "."
        os.makedirs(directory, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(self._settings, handle, indent=2, sort_keys=True)
        return target

    def as_dict(self):
        return dict(self._settings)

    def get_settings(self):
        """Return a snapshot of the current settings for callers and tests."""
        return self.as_dict()


config = Config()
for name, value in {
    "Config": Config,
    "config": config,
    "get_settings": config.get_settings,
    "get": config.get,
    "set": config.set,
    "load": config.load,
    "save": config.save,
}.items():
    setattr(app.config, name, value)


@bp.route("/")
def index():
    """Render the application homepage."""
    return render_template("index.html")


@bp.route("/health")
def health():
    """Liveness endpoint for monitoring."""
    return jsonify({"status": "ok", "service": "comiccraft-ai"})


@bp.route("/generate", methods=["GET", "POST"])
def generate_comic():
    """Generate a comic with story data and panel images."""
    payload = (
        request.form.to_dict()
        if request.method == "POST" and request.form
        else request.get_json(silent=True) or {}
    )

    prompt_input = (
        payload.get("story_prompt")
        or payload.get("prompt")
        or "A curious traveler explores a hidden world."
    )

    character_name = (
        payload.get("character_name")
        or payload.get("title")
        or "Hero"
    )

    art_style = (
        payload.get("art_style")
        or payload.get("style")
        or "cinematic comic book"
    )

    try:
        panel_count = int(payload.get("panels", 5))
    except (TypeError, ValueError):
        panel_count = 5

    panel_count = max(1, min(panel_count, 5))

    request_data = {
        "story_prompt": prompt_input,
        "character_name": character_name,
        "setting": payload.get("setting", "City"),
        "tone": payload.get("tone", "adventure"),
        "art_style": art_style,
        "panels": panel_count,
    }

    try:
        model = PromptRequest(**request_data)
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400

    outline = None
    story = None
    images = []

    try:
        outline = generate_outline(
            model.story_prompt,
            model.character_name,
            model.setting,
            model.tone,
            model.art_style,
        )

        story = generate_story(
            outline,
            model.character_name,
            model.tone,
        )

        image_prompts = []
        for index, panel in enumerate(outline.panels[:panel_count], start=1):
            panel_title = getattr(panel, "title", f"Comic Panel {index}")
            panel_description = getattr(panel, "description", "")
            image_prompt = f"""
Comic panel {index} of a {panel_count}-panel story.

Main story:
{model.story_prompt}

Main character:
{model.character_name}

Setting:
{model.setting}

Tone:
{model.tone}

Art style:
{model.art_style}

Panel title:
{panel_title}

Panel description:
{panel_description}

Create a polished comic illustration with strong composition, cinematic lighting,
clear focal subject, dynamic motion, and vivid colors. Keep the scene visually
coherent, with no text captions, speech bubbles, or watermarks.
"""
            image_prompts.append(image_prompt)
    except Exception as exc:
        print("Comic generation setup error:", exc)
        return jsonify({"status": "error", "error": str(exc)}), 500

    image_backend = (
        payload.get("image_backend")
        or payload.get("backend")
        or os.getenv("IMAGE_BACKEND")
        or "hf"
    )

    try:
        images = generate_images(
            prompt=model.story_prompt,
            layout=image_prompts,
            width=768,
            height=768,
            backend=image_backend,
        )
    except Exception as exc:
        print("Image generation error:", exc)
        print("Comic generation error:", exc)
        if outline is None:
            return jsonify({"status": "error", "error": str(exc)}), 500

        comic_id = uuid4().hex
        output_path = export_comic(
            comic_id=comic_id,
            title=character_name,
            prompt=model.story_prompt,
            panels=[
                getattr(panel, "title", f"Panel {index}")
                for index, panel in enumerate(outline.panels[:panel_count], start=1)
            ],
            settings=app.config.get_settings(),
        )

        comic_data = {
            "status": "success",
            "comic_id": comic_id,
            "title": character_name,
            "story_prompt": model.story_prompt,
            "panels": panel_count,
            "outline": outline.model_dump() if outline is not None and hasattr(outline, "model_dump") else outline,
            "story": story.model_dump() if story is not None and hasattr(story, "model_dump") else story,
            "images": images,
            "output_path": output_path,
        }

        GENERATED_COMICS[comic_id] = comic_data
        return jsonify(comic_data)

    comic_id = uuid4().hex
    output_path = export_comic(
        comic_id=comic_id,
        title=character_name,
        prompt=model.story_prompt,
        panels=[
            getattr(panel, "title", f"Panel {index}")
            for index, panel in enumerate(outline.panels[:panel_count], start=1)
        ],
        settings=app.config.get_settings(),
    )

    comic_data = {
        "status": "success",
        "comic_id": comic_id,
        "title": character_name,
        "story_prompt": model.story_prompt,
        "panels": panel_count,
        "outline": outline.model_dump() if outline is not None and hasattr(outline, "model_dump") else outline,
        "story": story.model_dump() if story is not None and hasattr(story, "model_dump") else story,
        "images": images,
        "output_path": output_path,
    }

    GENERATED_COMICS[comic_id] = comic_data
    return jsonify(comic_data)


@bp.route("/preview/<comic_id>")
def preview(comic_id: str):
    """Render a preview page for a generated comic."""
    comic = GENERATED_COMICS.get(comic_id)

    if not comic:
        return "Comic not found. Please generate the comic again.", 404

    story = comic.get("story") or {}
    panels = story.get("panels", []) if isinstance(story, dict) else []
    image_paths = comic.get("images") or []

    return render_template(
        "comic_preview.html",
        comic=comic,
        comic_id=comic_id,
        title=comic.get("title", "Comic preview"),
        story=story,
        panels=panels,
        image_paths=image_paths,
    )


@bp.route("/export_success/<comic_id>")
def export_success(comic_id: str):
    """Render the export-success page for a generated comic."""
    comic = GENERATED_COMICS.get(comic_id)

    if not comic:
        return "Comic not found. Please generate the comic again.", 404

    return render_template(
        "export_success.html",
        comic=comic,
        comic_id=comic_id,
        title=comic.get("title", "Exported comic"),
    )


@bp.route("/export/<comic_id>")
def export(comic_id: str):
    """Export a generated comic to a packaged output artifact."""
    output_path = export_comic(
        comic_id=comic_id,
        title="Exported Comic",
        prompt="export request",
        panels=[],
        settings=app.config.get_settings(),
    )
    return jsonify({"status": "ok", "path": output_path})


@bp.route("/static/exports/<path:filename>")
def serve_export_image(filename):
    """Serve generated export images from the static exports folder."""
    return send_from_directory(EXPORTS_DIR, filename)