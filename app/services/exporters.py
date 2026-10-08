"""Export support for packaged comic outputs."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def export_comic(comic_id: str, title: str, prompt: str, panels: list[str] | None, settings: object) -> str:
    """Create a simple export artifact on disk and return the path."""
    configured_dir = getattr(settings, "output_dir", "static") or "static"
    output_dir = Path(configured_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    export_target = output_dir / f"{comic_id}.txt"
    export_target.write_text(
        f"Title: {title}\nPrompt: {prompt}\nPanels: {len(panels or [])}\n",
        encoding="utf-8",
    )
    return str(export_target)


class ComicExporter:
    """Compatibility wrapper for export tasks."""

    def export_comic(self, comic_id: str, title: str, prompt: str, panels: list[str] | None, settings: object) -> str:
        return export_comic(comic_id=comic_id, title=title, prompt=prompt, panels=panels, settings=settings)
