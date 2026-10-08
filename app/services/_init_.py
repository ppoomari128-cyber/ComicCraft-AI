"""Compatibility initializer for the service package.

This module intentionally mirrors the exports of ``app.services`` so code that
imports the underscore-named package path still receives the same public API.
"""

from app.services import (
    ComicExporter,
    GeminiFlashService,
    GeminiProService,
    ImageGenerator,
    LayoutBuilder,
    build_layout,
    export_comic,
    generate_images,
    generate_outline,
    generate_story,
)

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
