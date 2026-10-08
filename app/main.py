from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app

load_dotenv(PROJECT_ROOT / ".env")

app = create_app()

BASE_DIR = PROJECT_ROOT
STATIC_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def save_metadata(comic_id: str, title: str, prompt: str, panel_count: int) -> None:
    meta_file = STATIC_DIR / f"{comic_id}.txt"
    meta_file.write_text(
        f"Title: {title}\nPrompt: {prompt}\nPanels: {panel_count}\n",
        encoding="utf-8",
    )


def generate_panel_image(prompt: str, panel_index: int, width: int = 768, height: int = 768) -> Image.Image:
    try:
        from app.services.image_generator import generate_images

        panel_prompt = f"Comic panel {panel_index + 1}: {prompt}"
        generated = generate_images(prompt, [panel_prompt], width, height)
        if generated:
            first_image = generated[0]
            if isinstance(first_image, Image.Image):
                return first_image
            if isinstance(first_image, (str, os.PathLike)):
                raw_str = str(first_image)
                candidate_paths = [
                    Path(raw_str),
                    PROJECT_ROOT / raw_str.lstrip("/\\"),
                    STATIC_DIR / "exports" / Path(raw_str).name,
                    STATIC_DIR / Path(raw_str).name,
                ]
                for p in candidate_paths:
                    if p.exists() and p.is_file():
                        return Image.open(p).convert("RGB").resize((width, height))
            if isinstance(first_image, (bytes, bytearray)):
                return Image.open(io.BytesIO(first_image)).convert("RGB").resize((width, height))
    except Exception as exc:
        print(f"[ComicCraft] Image generator notice: {exc}")

    image = Image.new("RGB", (width, height), color=(22, 22, 30))
    draw = ImageDraw.Draw(image)

    for i in range(12):
        x1 = (i * 60) % width
        y1 = (i * 40) % height
        x2 = x1 + 120
        y2 = y1 + 100
        fill = ((i * 20) % 255, 60 + (i * 15) % 120, 180 + (i * 10) % 75)
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=(255, 255, 255, 80))

    draw.text((40, 40), f"Panel {panel_index + 1}", fill=(255, 255, 255))
    draw.text((40, 90), prompt[:70], fill=(240, 240, 240))
    draw.text((40, height - 90), "ComicCraft AI", fill=(255, 255, 255))

    return image


def save_panel_image(comic_id: str, panel_index: int, image: Image.Image) -> str:
    filename = f"{comic_id}_{panel_index}.png"
    path = STATIC_DIR / filename

    image.save(path)

    # Browser-accessible URL
    return f"/static/{filename}"


def build_comic(title: str = "Demo Comic", prompt: str = "A heroic adventurer explores a mysterious realm", panel_count: int | None = None) -> list[str]:
    comic_id = "demo_comic"
    count = panel_count if panel_count is not None else int(os.getenv("PANELS_PER_COMIC", "5"))
    save_metadata(comic_id, title, prompt, count)

    paths: list[str] = []
    for i in range(count):
        image = generate_panel_image(prompt, i)
        path = save_panel_image(comic_id, i, image)

        print(f"Generated panel {i + 1}: {path}")

        paths.append(path)

    return paths


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ComicCraft AI Server & Image Generator")
    parser.add_argument("command", nargs="?", default="serve",
                        help="Action to perform: 'serve' to run the web server, or 'generate'/'image' to generate comic images")
    parser.add_argument("--prompt", "-p", type=str, default="A heroic adventurer explores a mysterious ancient realm",
                        help="Prompt for the comic")
    parser.add_argument("--title", "-t", type=str, default="ComicCraft Journey",
                        help="Title of the comic")
    parser.add_argument("--panels", "-n", type=int, default=None,
                        help="Number of panels (default: from .env or 5)")
    parser.add_argument("--host", type=str, default=None, help="Host to bind server to")
    parser.add_argument("--port", type=int, default=None, help="Port to bind server to")

    args, unknown = parser.parse_known_args()

    # If invoked with generate, image, or --generate flag
    if args.command in ("generate", "image") or "--generate" in sys.argv:
        panel_count = args.panels or int(os.getenv("PANELS_PER_COMIC", "5"))
        print("\n" + "=" * 60)
        print(" [ComicCraft AI] Generating Comic Panels")
        print(f" Title       : {args.title}")
        print(f" Prompt      : {args.prompt}")
        print(f" Panel count : {panel_count}")
        print("=" * 60 + "\n")

        images = build_comic(title=args.title, prompt=args.prompt, panel_count=panel_count)
        print("\n" + "=" * 60)
        print(f" [ComicCraft AI] Generated {len(images)} comic panel(s):")
        for idx, img in enumerate(images, start=1):
            print(f"   Panel {idx}: {img}")
        print("=" * 60 + "\n")
        return

    if os.environ.get("FLASK_ENV") == "development" or os.environ.get("DEBUG") == "1":
        port = args.port or int(os.environ.get("PORT", "5000"))
        host = args.host or "0.0.0.0"
        app.run(debug=True, host=host, port=port)
        return

    try:
        from waitress import serve
    except ImportError as exc:
        raise SystemExit(
            "Waitress is not installed. Install it with: "
            f'"{sys.executable}" -m pip install -r requirements.txt'
        ) from exc

    host = args.host or os.environ.get("HOST", "0.0.0.0")
    port = args.port or int(os.environ.get("PORT", "5000"))
    print(f"ComicCraft AI server starting on http://127.0.0.1:{port}")
    
    serve(
        app,
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()