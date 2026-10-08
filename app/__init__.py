from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "comiccraft-dev")
    app.config["OUTPUT_DIR"] = os.getenv("OUTPUT_DIR", "static")

    from app.routes import bp

    app.register_blueprint(bp)

    return app
