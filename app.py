import os
from importlib.metadata import version as pkg_version

from apiflask import APIFlask
from flask import render_template


def _get_version() -> str:
    """Read version from package metadata (pyproject.toml)."""
    try:
        return pkg_version("kandidat")
    except Exception:
        return "dev"


APP_VERSION = _get_version()


def create_app() -> APIFlask:
    app = APIFlask(
        __name__,
        title="kandidat API",
        version=APP_VERSION,
        docs_path="/docs",
        spec_path="/openapi.json",
        docs_ui="swagger-ui",
        json_errors=False,
    )
    app.secret_key = os.environ.get("SECRET_KEY", "kandidat-dev-key")  # nosec B105

    # OpenAPI metadata
    app.config["DESCRIPTION"] = "API REST pour la gestion de candidatures, cibles, contacts et fichiers."
    app.config["TAGS"] = [
        {"name": "Candidatures", "description": "CRUD candidatures et historique de statuts"},
        {"name": "Fichiers", "description": "Upload, download et suppression de fichiers"},
        {"name": "CV", "description": "Adaptation et conversion de CV via LLM"},
        {"name": "Cibles", "description": "Gestion des entreprises cibles"},
        {"name": "Contacts", "description": "Gestion des contacts par cible"},
        {"name": "Enrichissement", "description": "Enrichissement IA des cibles (Tavily + LLM)"},
        {"name": "Recherche", "description": "Recherche plein texte"},
        {"name": "Statistiques", "description": "Statistiques et enums"},
        {"name": "Settings", "description": "Configuration (LLM, CV reference, Tavily)"},
    ]

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

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")  # nosec B201
