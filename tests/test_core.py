import importlib
from pathlib import Path

from pytest import MonkeyPatch

create_app = getattr(importlib.import_module("app"), "create_app")
from app.schemas import ComicOutline
from app.services.gemini_flash import generate_outline
from app.services.gemini_pro import generate_story


def test_app_creates_and_serves_homepage():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    assert b"ComicCraft AI" in response.data


def test_generate_endpoint_accepts_prompt(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(
        "app.routes.generate_images",
        lambda *args, **kwargs: (args, kwargs, ["/static/exports/panel-1-768x768.png"])[2],
    )
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "title": "Sky Run",
            "prompt": "A fox races across the moonlit rooftops.",
            "style": "cinematic",
            "tone": "adventure",
            "panels": "3",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["title"] == "Sky Run"
    assert payload["panels"] == 3


def test_preview_and_export_pages_render_successfully():
    from app.routes import GENERATED_COMICS

    GENERATED_COMICS.clear()
    GENERATED_COMICS["demo-comic"] = {
        "title": "Sky Run",
        "story": {
            "panels": [
                {
                    "panel_number": 1,
                    "narration": "The hero starts their journey.",
                    "dialogue": ["Hero: Let's begin!"],
                    "caption": "A brave beginning.",
                }
            ]
        },
        "images": ["/static/exports/panel-1-768x768.png"],
        "output_path": "/static/exports/demo-comic.txt",
    }

    app = create_app()
    client = app.test_client()

    preview = client.get("/preview/demo-comic")
    assert preview.status_code == 200
    assert b"Comic ID:" in preview.data

    export_page = client.get("/export_success/demo-comic")
    assert export_page.status_code == 200
    assert b"Export complete" in export_page.data


def test_generate_images_uses_gemini_image_model(monkeypatch: MonkeyPatch, tmp_path: Path):
    from types import SimpleNamespace

    from google import genai

    from app.services import image_generator

    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(
                            parts=[
                                SimpleNamespace(
                                    inline_data=SimpleNamespace(data=b"image")
                                )
                            ]
                        )
                    )
                ]
            )

    class FakeClient:
        models = FakeModels()

        def __init__(self, **kwargs):
            del kwargs

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(image_generator, "EXPORT_DIR", tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_IMAGE_MODEL", raising=False)

    result = image_generator.generate_images("A comic panel", layout=["Panel 1"])

    assert captured["model"] == "gemini-2.5-flash-image"
    assert captured["config"]["response_modalities"] == ["TEXT", "IMAGE"]
    assert result == ["/static/exports/panel-1-768x768.png"]
    assert (tmp_path / "panel-1-768x768.png").read_bytes() == b"image"


def test_generate_images_falls_back_to_placeholder(monkeypatch: MonkeyPatch, tmp_path: Path):
    from app.services import image_generator

    monkeypatch.setattr(image_generator, "EXPORT_DIR", tmp_path)
    def boom(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("API unavailable")

    monkeypatch.setattr(image_generator, "_generate_with_gemini", boom)

    result = image_generator.generate_images("A comic panel", layout=["Panel 1"])

    assert result == ["/static/exports/panel-1-768x768.png"]
    assert (tmp_path / "panel-1-768x768.png").exists()
    assert (tmp_path / "panel-1-768x768.png").stat().st_size > 0


def test_generate_images_uses_live_output_dir_setting(monkeypatch: MonkeyPatch, tmp_path: Path):
    from types import SimpleNamespace

    from google import genai

    from app.services import image_generator

    class FakeModels:
        def generate_content(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(
                            parts=[SimpleNamespace(inline_data=SimpleNamespace(data=b"image"))]
                        )
                    )
                ]
            )

    class FakeClient:
        models = FakeModels()

        def __init__(self, **kwargs):
            del kwargs

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(image_generator, "EXPORT_DIR", tmp_path)
    monkeypatch.setattr(
        image_generator,
        "get_settings",
        lambda: SimpleNamespace(output_dir="uploads"),
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    result = image_generator.generate_images("A comic panel", layout=["Panel 1"])

    assert result == ["/uploads/panel-1-768x768.png"]
    assert (tmp_path / "panel-1-768x768.png").read_bytes() == b"image"


def test_gemini_fallback_handles_api_errors(monkeypatch: MonkeyPatch):
    class FakeSettings:
        gemini_api_key = "fake-key"
        panels_per_comic = 3
        gemini_outline_model = "gemini-test"
        gemini_story_model = "gemini-test"

    class FakeClient:
        class models:
            @staticmethod
            def generate_content(*args, **kwargs):
                del args, kwargs
                raise RuntimeError("API unavailable")

    monkeypatch.setattr("app.services.gemini_flash.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.gemini_pro.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.gemini_flash._get_client", lambda: FakeClient())
    monkeypatch.setattr("app.services.gemini_pro._get_client", lambda: FakeClient())

    outline = generate_outline("a test prompt", "Nova", "moon city", "adventure", "cinematic")
    story = generate_story(outline, "Nova", "adventure")

    assert isinstance(outline, ComicOutline)
    assert outline.panels
    assert story.panels
