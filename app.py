import os
from importlib.metadata import version as pkg_version

from flask import Flask, render_template


def _get_version() -> str:
    """Read version from package metadata (pyproject.toml)."""
    try:
        return pkg_version("kandidat")
    except Exception:
        return "dev"


APP_VERSION = _get_version()


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "kandidat-dev-key")  # nosec B105

    from config import FT_DATA_DIR

    app.config["FT_DATA_DIR"] = FT_DATA_DIR
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

    from services.database import init_app as db_init_app

    db_init_app(app)

    from routes import bp

    app.register_blueprint(bp)

    from api import api_bp

    app.register_blueprint(api_bp)

    from services.cibles import CATEGORY_LABELS

    @app.context_processor
    def inject_globals():
        return {"category_labels": CATEGORY_LABELS, "app_version": APP_VERSION}

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    return app


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")  # nosec B201
