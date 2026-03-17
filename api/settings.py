"""Settings API endpoints for CV reference and LLM configuration."""

from flask import jsonify, request

from api import api_bp
from services.settings import get_all_settings, get_cv_reference_html, get_setting, set_setting


@api_bp.route("/settings", methods=["GET"])
@api_bp.doc(tags=["Settings"], summary="Get all application settings")
def get_settings():
    """GET /api/settings — Get all application settings (sensitive values masked)."""
    all_settings = get_all_settings()

    data = {
        "cv_reference_configured": bool(all_settings.get("cv_reference_html")),
        "cv_reference_date": all_settings.get("cv_reference_date", ""),
        "llm_provider": all_settings.get("llm_provider", ""),
        "llm_ollama_url": all_settings.get("llm_ollama_url", "http://localhost:11434"),
        "llm_ollama_model": all_settings.get("llm_ollama_model", "llama3.2"),
        "llm_claude_model": all_settings.get("llm_claude_model", "claude-sonnet-4-20250514"),
        "llm_claude_api_key_configured": bool(all_settings.get("llm_claude_api_key")),
        "tavily_api_key_configured": bool(all_settings.get("tavily_api_key")),
    }
    return jsonify({"data": data})


@api_bp.route("/settings/cv-reference", methods=["PUT"])
@api_bp.doc(tags=["Settings"], summary="Upload or replace CV reference HTML")
def upload_cv_reference():
    """PUT /api/settings/cv-reference — Upload or replace the global CV reference HTML."""
    from services.settings import upload_cv_reference as do_upload

    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier fourni"}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.endswith(".html"):
        return jsonify({"error": "Le fichier doit etre au format HTML (.html)"}), 400

    content = file.read().decode("utf-8", errors="replace")
    if not content.strip():
        return jsonify({"error": "Le fichier HTML est vide"}), 400

    if len(content) > 10 * 1024 * 1024:
        return jsonify({"error": "Fichier trop volumineux (max 10 Mo)"}), 413

    try:
        do_upload(content)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "data": {
                "cv_reference_configured": True,
                "cv_reference_date": get_setting("cv_reference_date") or "",
            }
        }
    )


@api_bp.route("/settings/cv-reference", methods=["GET"])
@api_bp.doc(tags=["Settings"], summary="Get CV reference HTML content")
def get_cv_reference():
    """GET /api/settings/cv-reference — Get the global CV reference HTML content."""
    cv_html = get_cv_reference_html()
    if not cv_html:
        return jsonify({"error": "Aucun CV de reference configure"}), 404

    return jsonify(
        {
            "data": {
                "cv_html": cv_html,
                "cv_reference_date": get_setting("cv_reference_date") or "",
            }
        }
    )


@api_bp.route("/settings/llm", methods=["PUT"])
@api_bp.doc(tags=["Settings"], summary="Update LLM provider configuration")
def update_llm_config():
    """PUT /api/settings/llm — Update LLM provider configuration."""
    from services.schemas import LLMConfigUpdate

    data = request.get_json()
    if not data:
        return jsonify({"error": "Donnees JSON requises"}), 400

    try:
        config = LLMConfigUpdate(**data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    set_setting("llm_provider", config.provider)

    if config.provider == "ollama":
        set_setting("llm_ollama_url", config.ollama_url)
        set_setting("llm_ollama_model", config.ollama_model)
    elif config.provider == "claude":
        if config.claude_api_key:
            set_setting("llm_claude_api_key", config.claude_api_key)
        set_setting("llm_claude_model", config.claude_model)

    response = {"llm_provider": config.provider}
    if config.provider == "ollama":
        response["llm_ollama_url"] = config.ollama_url
        response["llm_ollama_model"] = config.ollama_model
    elif config.provider == "claude":
        response["llm_claude_model"] = config.claude_model

    return jsonify({"data": response})


@api_bp.route("/settings/llm/health", methods=["POST"])
@api_bp.doc(tags=["Settings"], summary="Test LLM provider connectivity")
def llm_health_check():
    """POST /api/settings/llm/health — Test connectivity to the configured LLM provider."""
    from services.llm import get_provider

    try:
        provider = get_provider()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        result = provider.health_check()
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503

    return jsonify({"data": result})


@api_bp.route("/settings/llm/models", methods=["GET"])
@api_bp.doc(tags=["Settings"], summary="List available Ollama models")
def list_ollama_models():
    """GET /api/settings/llm/models — List available models from Ollama server."""
    import httpx

    ollama_url = request.args.get("ollama_url") or get_setting("llm_ollama_url") or "http://localhost:11434"
    ollama_url = ollama_url.rstrip("/")

    try:
        response = httpx.get(f"{ollama_url}/api/tags", timeout=10)
        response.raise_for_status()
    except httpx.ConnectError:
        return jsonify({"error": f"Impossible de se connecter a Ollama sur {ollama_url}"}), 503
    except httpx.HTTPStatusError as e:
        return jsonify({"error": f"Erreur Ollama: {e.response.status_code}"}), 503

    data = response.json()
    models = [m["name"] for m in data.get("models", [])]
    return jsonify({"data": {"models": models}})


@api_bp.route("/settings/cv-reference/convert", methods=["POST"])
@api_bp.doc(tags=["Settings"], summary="Convert CV reference to PDF + DOCX")
def convert_cv_reference():
    """POST /api/settings/cv-reference/convert — Convert global CV to PDF + DOCX."""
    from services.cv_converter import html_to_docx, html_to_pdf

    cv_html = get_cv_reference_html()
    if not cv_html:
        return jsonify({"error": "Aucun CV de reference configure"}), 404

    try:
        html_to_pdf(cv_html)
        html_to_docx(cv_html)
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(
        {
            "data": {
                "pdf_generated": True,
                "docx_generated": True,
            }
        }
    )


# ---------------------------------------------------------------------------
# Tavily (web search for enrichment)
# ---------------------------------------------------------------------------


@api_bp.route("/settings/tavily", methods=["PUT"])
@api_bp.doc(tags=["Settings"], summary="Save Tavily API key")
def update_tavily_config():
    """PUT /api/settings/tavily — Save Tavily API key."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Donnees JSON requises"}), 400

    api_key = data.get("tavily_api_key", "").strip()
    if api_key:
        set_setting("tavily_api_key", api_key)

    return jsonify({"data": {"tavily_api_key_configured": bool(api_key)}})


@api_bp.route("/settings/tavily/health", methods=["POST"])
@api_bp.doc(tags=["Settings"], summary="Test Tavily API connectivity")
def tavily_health_check():
    """POST /api/settings/tavily/health — Test Tavily API connectivity."""
    from services.cible_enricher import test_tavily_connection

    try:
        result = test_tavily_connection()
        return jsonify({"data": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
