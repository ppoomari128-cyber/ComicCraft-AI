from __future__ import annotations

import os

from app.config import get_settings
from app.schemas import ComicOutline, PanelOutline


def _fallback_outline(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
    panels_per_comic: int | None = None,
) -> ComicOutline:
    """
    
    """

    settings = get_settings()

    panel_count = (
        panels_per_comic
        if panels_per_comic is not None
        else settings.panels_per_comic
    )

    panel_count = max(1, min(int(panel_count), 5))

    prompt_hint = (
        story_prompt.strip()
        if story_prompt
        else "A heroic journey"
    )

    prompt_summary = (
        prompt_hint[:120]
        if len(prompt_hint) > 120
        else prompt_hint
    )

    character = character_name.strip() or "Hero"
    location = setting.strip() or "a mysterious world"
    story_tone = tone.strip() or "adventurous"
    style = art_style.strip() or "cinematic comic-book"

    panels: list[PanelOutline] = []

    for index in range(1, panel_count + 1):

        if index == 1:
            action = (
                f"{character} begins the journey in {location}, "
                f"discovering the first clue connected to the story."
            )

        elif index == panel_count:
            action = (
                f"{character} reaches the final moment of the journey "
                f"and resolves the main conflict."
            )

        else:
            action = (
                f"{character} continues through {location}, "
                f"facing a new challenge that moves the story forward."
            )

        title = (
            f"{character} at {location} - Panel {index}"
        )

        scene_description = (
            f"{action} "
            f"The mood is {story_tone}. "
            f"The scene follows the story idea "
            f"\"{prompt_summary}\" and is illustrated in {style} style."
        )

        image_prompt = (
            f"Comic book panel showing {action} "
            f"Main character: {character}. "
            f"Setting: {location}. "
            f"Story idea: {prompt_summary}. "
            f"Tone: {story_tone}. "
            f"Art style: {style}. "
            "Detailed characters, expressive faces, cinematic lighting, "
            "rich environment, vibrant colors, clear composition, "
            "family-friendly, polished digital comic illustration."
        )

        panels.append(
            PanelOutline(
                panel_number=index,
                title=title,
                scene_description=scene_description,
                image_prompt=image_prompt,
            )
        )

    return ComicOutline(panels=panels)


def _get_client():
    """
    Create the Google GenAI client when an API key exists.
    """

    settings = get_settings()

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or getattr(settings, "gemini_api_key", None)
    )

    if not api_key:
        return None

    try:
        from google import genai

        return genai.Client(api_key=api_key)

    except Exception as exc:
        print(
            f"[ComicCraft] Failed to create Gemini client: {exc}"
        )
        return None


def _get_outline_model() -> str:
    """
    Resolve the Gemini model used for story-outline generation.
    """

    settings = get_settings()

    configured_model = (
        os.getenv("GEMINI_OUTLINE_MODEL")
        or getattr(
            settings,
            "gemini_outline_model",
            None,
        )
    )

    # Current general-purpose Flash model.
    return (
    configured_model.strip()
    if configured_model and configured_model.strip()
    else "gemini-3.1-flash-lite"
)


def generate_outline(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
) -> ComicOutline:
    """
    Generate a structured comic outline using Gemini.

    If Gemini fails, a deterministic local outline is returned.
    """

    settings = get_settings()

    panel_count = max(
        1,
        min(
            int(settings.panels_per_comic),
            5,
        ),
    )

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or getattr(settings, "gemini_api_key", None)
    )

    # ---------------------------------------------------------------
    # No API key -> local fallback
    # ---------------------------------------------------------------

    if not api_key:
        print(
            "[ComicCraft] GEMINI_API_KEY is missing."
        )

        return _fallback_outline(
            story_prompt,
            character_name,
            setting,
            tone,
            art_style,
            panel_count,
        )

    # ---------------------------------------------------------------
    # Create Gemini client
    # ---------------------------------------------------------------

    client = _get_client()

    if client is None:
        print(
            "[ComicCraft] Gemini client could not be created."
        )

        return _fallback_outline(
            story_prompt,
            character_name,
            setting,
            tone,
            art_style,
            panel_count,
        )

    # ---------------------------------------------------------------
    # Import Google GenAI types
    # ---------------------------------------------------------------

    try:
        from google.genai import types
    except ImportError as exc:

        print(
            "[ComicCraft] google-genai import failed:"
            f" {exc}"
        )

        return _fallback_outline(
            story_prompt,
            character_name,
            setting,
            tone,
            art_style,
            panel_count,
        )

    # ---------------------------------------------------------------
    # Build prompt
    # ---------------------------------------------------------------

    prompt = f"""
Create a complete {panel_count}-panel comic story outline.

USER STORY IDEA:
{story_prompt}

MAIN CHARACTER:
{character_name}

SETTING:
{setting}

TONE:
{tone}

ART STYLE:
{art_style}

REQUIREMENTS:

1. Return exactly {panel_count} panels.
2. Panel numbers must be 1 through {panel_count}.
3. Maintain strong story continuity.
4. Every panel must logically follow the previous panel.
5. Each panel must contain:
   - panel_number
   - title
   - scene_description
   - image_prompt
6. Every image_prompt must describe a visual scene suitable for image generation.
7. Keep the main character visually consistent.
8. Keep the setting visually consistent.
9. Make the story family-friendly.
10. Make every panel visually distinct.
11. Use concise but descriptive image prompts.
"""

    model_name = _get_outline_model()

    print()
    print("=" * 70)
    print("[ComicCraft] Gemini outline generation")
    print(f"[ComicCraft] Model: {model_name}")
    print(f"[ComicCraft] Panels: {panel_count}")
    print("=" * 70)

    # ---------------------------------------------------------------
    # Gemini request
    # ---------------------------------------------------------------

    try:

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ComicOutline,
                temperature=0.8,
            ),
        )

    except Exception as exc:

        # IMPORTANT:
        # Do not silently hide the real Gemini error.
        print()
        print(
            "[ComicCraft] Gemini outline request failed:"
        )
        print(
            f"[ComicCraft] {type(exc).__name__}: {exc}"
        )
        print(
            "[ComicCraft] Switching to local fallback."
        )

        return _fallback_outline(
            story_prompt,
            character_name,
            setting,
            tone,
            art_style,
            panel_count,
        )

    # ---------------------------------------------------------------
    # Structured parsed response
    # ---------------------------------------------------------------

    try:

        parsed = getattr(
            response,
            "parsed",
            None,
        )

        if isinstance(
            parsed,
            ComicOutline,
        ):
            print(
                "[ComicCraft] Gemini outline parsed successfully."
            )

            return parsed

        # Some SDK responses may expose a dictionary.
        if isinstance(parsed, dict):

            result = ComicOutline.model_validate(
                parsed
            )

            print(
                "[ComicCraft] Gemini dictionary parsed successfully."
            )

            return result

    except Exception as exc:

        print(
            "[ComicCraft] Failed to parse structured response:"
            f" {exc}"
        )

    # ---------------------------------------------------------------
    # JSON text fallback parsing
    # ---------------------------------------------------------------

    try:

        text = getattr(
            response,
            "text",
            None,
        )

        if isinstance(text, str) and text.strip():

            result = ComicOutline.model_validate_json(
                text
            )

            print(
                "[ComicCraft] Gemini JSON text parsed successfully."
            )

            return result

    except Exception as exc:

        print(
            "[ComicCraft] Failed to parse response text:"
            f" {exc}"
        )

    # ---------------------------------------------------------------
    # No usable response
    # ---------------------------------------------------------------

    print(
        "[ComicCraft] Gemini returned no usable outline."
    )

    return _fallback_outline(
        story_prompt,
        character_name,
        setting,
        tone,
        art_style,
        panel_count,
    )


class GeminiFlashService:
    """
    Compatibility wrapper for existing ComicCraft routes.
    """

    def __init__(
        self,
        api_key: str | None = None,
    ):
        self.api_key = api_key

    def generate_outline(
        self,
        story_prompt: str,
        character_name: str,
        setting: str,
        tone: str,
        art_style: str,
    ) -> ComicOutline:

        return generate_outline(
            story_prompt=story_prompt,
            character_name=character_name,
            setting=setting,
            tone=tone,
            art_style=art_style,
        )