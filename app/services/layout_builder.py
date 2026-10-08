"""Comic panel layout helper functions."""

from __future__ import annotations

from collections.abc import Iterable


def _as_layout_text(item: object, index: int, fallback: str) -> str:
    """Convert one panel entry into a string-friendly layout description."""
    if isinstance(item, str):
        text = item.strip()
        return text or f"Panel {index}: {fallback}"

    if isinstance(item, dict):
        title = str(item.get("title") or item.get("name") or f"Panel {index}").strip()
        description = str(
            item.get("description")
            or item.get("scene_description")
            or item.get("image_prompt")
            or fallback
        ).strip()
        return f"{title}: {description}" if title and description else f"Panel {index}: {fallback}"

    for key in ("title", "name"):
        value = getattr(item, key, None)
        if value:
            title = str(value).strip()
            break
    else:
        title = f"Panel {index}"

    description = (
        getattr(item, "description", None)
        or getattr(item, "scene_description", None)
        or getattr(item, "image_prompt", None)
        or fallback
    )
    description_text = str(description).strip() if description is not None else fallback
    return f"{title}: {description_text}" if description_text else f"Panel {index}: {fallback}"


def build_layout(prompt: str | None, panels: int = 5, outline: Iterable[object] | None = None) -> list[str]:
    """Return a panel plan using either a prompt summary or a provided outline."""
    try:
        panel_count = max(1, int(panels or 1))
    except (TypeError, ValueError):
        panel_count = 5

    summary = str(prompt or "An unexpected journey unfolds.").strip() or "An unexpected journey unfolds."
    items: list[str] = []
    raw_outline = list(outline) if outline is not None else []

    if raw_outline:
        for index, item in enumerate(raw_outline[:panel_count], start=1):
            items.append(_as_layout_text(item, index, summary))
    else:
        items = [f"Panel {index}: {summary}" for index in range(1, panel_count + 1)]

    while len(items) < panel_count:
        items.append(f"Panel {len(items) + 1}: {summary}")

    return items[:panel_count]


class LayoutBuilder:
    """Compatibility wrapper for layout generation."""

    def build_layout(self, prompt: str | None, panels: int = 5, outline: Iterable[object] | None = None) -> list[str]:
        return build_layout(prompt=prompt, panels=panels, outline=outline)
