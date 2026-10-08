"""ComicCraft AI and export services."""

from __future__ import annotations


def _stub_callable(name: str):
    """Create a callable that raises a clear runtime error when a backend is unavailable."""

    def _missing(*args, **kwargs):
        raise RuntimeError(f"{name} is unavailable because a required backend dependency is missing.")

    return _missing


def _safe_import(module_name: str, symbol_name: str):
    """Import a service symbol or fall back to a stub when optional dependencies are missing."""
    try:
        module = __import__(module_name, fromlist=[symbol_name])
        return getattr(module, symbol_name)
    except Exception:  # pragma: no cover - backend is optional in minimal/dev environments
        if symbol_name.endswith("Service"):
            class _UnavailableService:
                def __init__(self, *args, **kwargs):
                    raise RuntimeError(f"{symbol_name} is unavailable because a required backend dependency is missing.")

            return _UnavailableService
        return _stub_callable(symbol_name)


ComicExporter = _safe_import("app.services.exporters", "ComicExporter")
export_comic = _safe_import("app.services.exporters", "export_comic")

GeminiFlashService = _safe_import("app.services.gemini_flash", "GeminiFlashService")
generate_outline = _safe_import("app.services.gemini_flash", "generate_outline")

GeminiProService = _safe_import("app.services.gemini_pro", "GeminiProService")
generate_story = _safe_import("app.services.gemini_pro", "generate_story")

ImageGenerator = _safe_import("app.services.image_generator", "ImageGenerator")
generate_images = _safe_import("app.services.image_generator", "generate_images")

LayoutBuilder = _safe_import("app.services.layout_builder", "LayoutBuilder")
build_layout = _safe_import("app.services.layout_builder", "build_layout")


__all__ = [
    "ComicExporter",
    "GeminiFlashService",
    "GeminiProService",
    "ImageGenerator",
    "LayoutBuilder",
    "build_layout",
    "export_comic",
    "generate_images",
    "generate_outline",
    "generate_story",
]
