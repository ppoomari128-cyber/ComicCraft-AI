from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING, Any, cast

import app.config


def get_settings():
    """Compatibility wrapper for tests and callers expecting a module-level settings accessor."""
    return app.config.get_settings()


if TYPE_CHECKING:
    from app.schemas import ComicOutline, ComicStory, PanelStory


def _schema_types() -> tuple[type[Any], type[Any], type[Any]]:
    """Import schema models lazily to avoid circular type initialization."""
    from app.schemas import ComicOutline, ComicStory, PanelStory

    return ComicOutline, ComicStory, PanelStory


def _coerce_outline(outline: "ComicOutline | dict | list | None") -> "ComicOutline":
    """Normalize outline-like values into a ComicOutline instance."""
    ComicOutline, _, _ = _schema_types()

    def _normalize_panel(panel: object, index: int) -> dict:
        if isinstance(panel, dict):
            normalized = dict(panel)
            number = normalized.get("panel_number", index + 1)
            normalized.setdefault("panel_number", number)
            normalized.setdefault("title", f"Panel {number}")
            normalized.setdefault("scene_description", normalized.get("description") or "")
            normalized.setdefault("image_prompt", normalized.get("image_prompt") or normalized.get("scene_description") or "A cinematic comic panel")
            return normalized
        model_dump = getattr(panel, "model_dump", None)
        if callable(model_dump):
            try:
                return _normalize_panel(model_dump(), index)
            except Exception:
                pass
        return {
            "panel_number": index + 1,
            "title": f"Panel {index + 1}",
            "scene_description": "A cinematic comic panel.",
            "image_prompt": "A cinematic comic panel.",
        }

    if outline is None:
        return ComicOutline(panels=[])

    if isinstance(outline, ComicOutline):
        return cast("ComicOutline", outline)

    if isinstance(outline, dict):
        panels = outline.get("panels", []) if isinstance(outline.get("panels", []), list) else [outline]
        normalized_panels = [_normalize_panel(panel, index) for index, panel in enumerate(panels)]
        try:
            return ComicOutline.model_validate({"panels": normalized_panels})
        except Exception:
            return ComicOutline(panels=[])

    if isinstance(outline, list):
        normalized_panels = [_normalize_panel(panel, index) for index, panel in enumerate(outline)]
        try:
            return ComicOutline.model_validate({"panels": normalized_panels})
        except Exception:
            return ComicOutline(panels=[])

    if hasattr(outline, "model_dump"):
        try:
            return _coerce_outline(outline.model_dump())
        except Exception:
            pass

    return ComicOutline(panels=[])


def _coerce_outline_panels(outline: "ComicOutline | dict | list | None") -> list:
    """Return outline panels in a shape that is safe for fallback story generation."""
    normalized_outline = _coerce_outline(outline)
    panels = getattr(normalized_outline, "panels", []) or []
    if isinstance(panels, dict):
        panels = panels.get("panels", [])
    return list(panels)


def _fallback_story(
    outline: "ComicOutline | dict | list | None",
    character_name: str,
    tone: str,
) -> "ComicStory":
    """Create a local story when Gemini is unavailable."""
    _, ComicStory, PanelStory = _schema_types()

    tone_label = (tone or "adventure").strip().lower() or "adventure"
    tone_label = tone_label.replace("-", " ")

    narration_templates = [
        f"{character_name} begins the {tone_label} journey with courage and determination.",
        f"{character_name} discovers something unexpected and the {tone_label} mood deepens around them.",
        f"{character_name} faces a difficult challenge but keeps moving forward with resolve.",
        f"{character_name} finds a way to overcome the obstacle and adapt to the changing scene.",
        f"{character_name} finishes the {tone_label} adventure with a hopeful new beginning.",
    ]

    dialogue_templates = [
        [
            f"{character_name}: Let's begin this {tone_label} adventure!",
            "Narrator: A new journey starts.",
        ],
        [
            f"{character_name}: Something feels different here.",
            f"Narrator: The {tone_label} tension grows as the path changes.",
        ],
        [
            f"{character_name}: We cannot give up now.",
            f"Narrator: Courage becomes the key to this {tone_label} moment.",
        ],
        [
            f"{character_name}: We made it!",
            f"Narrator: The hardest part is finally over in this {tone_label} chapter.",
        ],
        [
            f"{character_name}: This is only the beginning.",
            f"Narrator: A new {tone_label} adventure waits beyond the horizon.",
        ],
    ]

    panels: list[PanelStory] = []
    for panel in _coerce_outline_panels(outline):
        if isinstance(panel, dict):
            number = panel.get("panel_number", 1)
            scene = panel.get("scene_description") or panel.get("description") or ""
        else:
            number = getattr(panel, "panel_number", 1)
            scene = getattr(panel, "scene_description", "") or getattr(panel, "description", "") or ""

        if not isinstance(scene, str):
            scene = str(scene)
        scene = scene.strip()

        index = min(int(number) - 1, len(narration_templates) - 1)

        narration = narration_templates[index]
        dialogue = dialogue_templates[index]

        caption = f"Panel {number}: {scene[:100]}" if scene else f"Panel {number}: {character_name} continues the story."

        panels.append(
            PanelStory(
                panel_number=number,
                narration=narration,
                dialogue=dialogue,
                caption=caption,
            )
        )

    return ComicStory(panels=panels)


def _get_setting(key: str, default=None):
    settings = app.config.get_settings()
    if isinstance(settings, dict):
        return settings.get(key, default)
    return getattr(settings, key, default)


def _get_client():
    """Create a Gemini client when an API key is available."""
    api_key = os.getenv("GEMINI_API_KEY") or _get_setting("gemini_api_key")
    if not api_key:
        return None

    try:
        from google import genai

        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _coerce_story_payload(payload):
    """Normalize Gemini story payloads from dict, model, or JSON text into a ComicStory."""
    _, ComicStory, _ = _schema_types()

    if payload is None:
        return None

    if isinstance(payload, ComicStory):
        return payload

    if isinstance(payload, dict):
        return ComicStory.model_validate(payload)

    if hasattr(payload, "model_dump"):
        model_dump = getattr(payload, "model_dump", None)
        if callable(model_dump):
            return ComicStory.model_validate(model_dump())

    if isinstance(payload, list):
        return ComicStory.model_validate({"panels": payload})

    return None


def generate_story(
    outline: ComicOutline,
    character_name: str,
    tone: str,
) -> ComicStory:
    """Generate the comic story, falling back to local narration when the API is unavailable."""
    _, ComicStory, _ = _schema_types()
    api_key = os.getenv("GEMINI_API_KEY") or _get_setting("gemini_api_key")
    if not api_key:
        return _fallback_story(outline, character_name, tone)

    try:
        from google.genai import types

        client = _get_client()
        if client is None:
            raise RuntimeError("Google GenAI client unavailable")

        prompt = f"""
Create a complete story for a comic with a strong narrative arc.

CHARACTER:
{character_name}

TONE:
{tone}

OUTLINE:
{outline.model_dump_json()}

Requirements:
1. Return a story with one panel entry per panel in the outline.
2. Keep panel numbers aligned with the outline.
3. Each panel needs: panel_number, narration, dialogue, and caption.
4. Write vivid but concise narration and friendly dialogue.
5. Keep the story family-friendly.
"""

        config = None
        if types is not None and hasattr(types, "GenerateContentConfig"):
            try:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ComicStory,
                    temperature=0.7,
                )
            except TypeError:
                config = types.GenerateContentConfig(
                    response_schema=ComicStory,
                    temperature=0.7,
                )

        story_model = os.getenv("GEMINI_STORY_MODEL") or _get_setting("gemini_story_model", "gemini-2.5-pro")
        response = client.models.generate_content(
            model=story_model,
            contents=prompt,
            config=config,
        )

        parsed_story = _coerce_story_payload(getattr(response, "parsed", None))
        if parsed_story is not None:
            return parsed_story

        text = getattr(response, "text", None)
        if isinstance(text, str):
            try:
                return ComicStory.model_validate_json(text)
            except Exception:
                import json

                loaded = json.loads(text)
                story = _coerce_story_payload(loaded)
                if story is not None:
                    return story

        raise ValueError("Gemini returned no usable story payload.")
    except Exception as error:
        print("generate_story error:", error)
        return _fallback_story(outline, character_name, tone)


class GeminiProService:
    """Compatibility wrapper for story generation."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def generate_story(
        self,
        outline: ComicOutline,
        character_name: str,
        tone: str,
    ) -> ComicStory:
        return generate_story(
            outline,
            character_name,
            tone,
        )