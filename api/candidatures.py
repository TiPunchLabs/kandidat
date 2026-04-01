import logging

from flask import jsonify, request, send_file
from pydantic import ValidationError

from services.candidature import (
    CATEGORIES,
    PRIORITES,
    STATUTS,
    TYPES,
    create_candidature,
    delete_candidature,
    list_candidatures,
    load_candidature,
    load_historique,
    render_markdown,
    update_candidature,
    validate_status,
)
from services.database import HistoriqueStatut, db
from services.fichiers import delete_fichier, get_fichier_path, upload_fichier
from services.schemas import CandidatureUpdate

from . import api_bp

logger = logging.getLogger(__name__)


@api_bp.route("/candidatures", methods=["GET"])
@api_bp.doc(tags=["Candidatures"], summary="List candidatures")
def api_list_candidatures():
    """List candidatures with optional filters: statut, type, priorite, categorie."""
    try:
        candidatures = list_candidatures()

        statut = request.args.get("statut")
        if statut:
            if statut not in STATUTS:
                return jsonify({"error": f"Statut invalide: {statut}"}), 400
            candidatures = [c for c in candidatures if c.get("statut") == statut]

        ctype = request.args.get("type")
        if ctype:
            if ctype not in TYPES:
                return jsonify({"error": f"Type invalide: {ctype}"}), 400
            candidatures = [c for c in candidatures if c.get("type") == ctype]

        priorite = request.args.get("priorite")
        if priorite:
            if priorite not in PRIORITES:
                return jsonify({"error": f"Priorite invalide: {priorite}"}), 400
            candidatures = [c for c in candidatures if c.get("priorite") == priorite]

        categorie = request.args.get("categorie")
        if categorie:
            if categorie not in CATEGORIES:
                return jsonify({"error": f"Categorie invalide: {categorie}"}), 400
            candidatures = [c for c in candidatures if c.get("categorie_entreprise") == categorie]

        return jsonify({"data": candidatures}), 200
    except Exception:
        logger.exception("Error listing candidatures")
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>", methods=["GET"])
@api_bp.doc(tags=["Candidatures"], summary="Get candidature by slug")
def api_get_candidature(slug):
    """Get a single candidature by slug, including associated files."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404
        return jsonify({"data": c}), 200
    except Exception:
        logger.exception("Error loading candidature %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures", methods=["POST"])
@api_bp.doc(tags=["Candidatures"], summary="Create a new candidature")
def api_create_candidature():
    """Create a new candidature from JSON body."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Corps JSON requis"}), 400

        slug = create_candidature(data)
        c = load_candidature(slug)
        return jsonify({"data": c}), 201
    except (ValidationError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except FileExistsError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Error creating candidature")
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>", methods=["PUT"])
@api_bp.doc(tags=["Candidatures"], summary="Update a candidature")
def api_update_candidature(slug):
    """Partial update of a candidature."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Corps JSON requis"}), 400

        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        # Validate with Pydantic schema
        try:
            schema = CandidatureUpdate(**data)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

        fields = schema.non_null_fields()
        if not fields:
            return jsonify({"error": "Aucun champ a mettre a jour"}), 400

        # Validate status transition if statut is being changed
        if "statut" in fields:
            new_statut = fields["statut"]
            if new_statut not in STATUTS:
                return jsonify({"error": f"Statut invalide: {new_statut}"}), 400
            if not validate_status(c["statut"], new_statut):
                return jsonify({"error": f"Transition de statut non autorisee: {c['statut']} -> {new_statut}"}), 400

        # Validate enum fields
        if "type" in fields and fields["type"] not in TYPES:
            return jsonify({"error": f"Type invalide: {fields['type']}"}), 400
        if "priorite" in fields and fields["priorite"] not in PRIORITES:
            return jsonify({"error": f"Priorite invalide: {fields['priorite']}"}), 400
        if "categorie_entreprise" in fields and fields["categorie_entreprise"] not in CATEGORIES:
            return jsonify({"error": f"Categorie invalide: {fields['categorie_entreprise']}"}), 400

        commentaire = data.get("commentaire")
        update_candidature(slug, fields, commentaire=commentaire)
        updated = load_candidature(slug)
        return jsonify({"data": updated}), 200
    except Exception:
        logger.exception("Error updating candidature %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>", methods=["DELETE"])
@api_bp.doc(tags=["Candidatures"], summary="Delete a candidature")
def api_delete_candidature(slug):
    """Delete a candidature (DB + files on disk)."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        delete_candidature(slug)
        return jsonify({"data": {"slug": slug, "deleted": True}}), 200
    except Exception:
        logger.exception("Error deleting candidature %s", slug)
        db.session.rollback()
        return jsonify({"error": "Erreur interne du serveur"}), 500


# ---------------------------------------------------------------------------
# Historique statuts
# ---------------------------------------------------------------------------


@api_bp.route("/candidatures/<slug>/historique", methods=["GET"])
@api_bp.doc(tags=["Candidatures"], summary="Get status history for a candidature")
def api_get_historique(slug):
    """Get status history for a candidature."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404
        historique = load_historique(slug)
        for h in historique:
            h["commentaire_html"] = render_markdown(h["commentaire"]) if h["commentaire"] else None
        return jsonify({"data": historique}), 200
    except Exception:
        logger.exception("Error loading historique for %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>/historique/<int:historique_id>", methods=["PATCH"])
@api_bp.doc(tags=["Candidatures"], summary="Update a historique entry comment")
def api_patch_historique(slug, historique_id):
    """Update the commentaire of an existing historique entry."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        entry = HistoriqueStatut.query.filter_by(id=historique_id, slug=slug).first()
        if entry is None:
            return jsonify({"error": "Entree d'historique introuvable"}), 404

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Corps JSON requis"}), 400

        commentaire = data.get("commentaire", "")
        if isinstance(commentaire, str):
            commentaire = commentaire.strip()
        else:
            commentaire = ""

        if len(commentaire) > 1000:
            return jsonify({"error": "Le commentaire ne doit pas depasser 1000 caracteres"}), 400

        entry.commentaire = commentaire if commentaire else None
        db.session.commit()

        return jsonify(
            {
                "data": {
                    "id": entry.id,
                    "ancien_statut": entry.ancien_statut,
                    "nouveau_statut": entry.nouveau_statut,
                    "date_changement": entry.date_changement,
                    "commentaire": entry.commentaire,
                    "commentaire_html": render_markdown(entry.commentaire) if entry.commentaire else None,
                }
            }
        ), 200
    except Exception:
        logger.exception("Error patching historique %s for %s", historique_id, slug)
        db.session.rollback()
        return jsonify({"error": "Erreur interne du serveur"}), 500


# ---------------------------------------------------------------------------
# Fichiers endpoints
# ---------------------------------------------------------------------------


@api_bp.route("/candidatures/<slug>/fichiers", methods=["POST"])
@api_bp.doc(tags=["Fichiers"], summary="Upload a file for a candidature")
def api_upload_fichier(slug):
    """Upload a file for a candidature (multipart/form-data)."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        file = request.files.get("file")
        if file is None or file.filename == "":
            return jsonify({"error": "Aucun fichier fourni"}), 400

        fichier = upload_fichier(slug, file)
        return jsonify({"data": {"nom": fichier.nom, "chemin": fichier.chemin, "type": fichier.type}}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Error uploading file for %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>/fichiers/<path:filename>", methods=["DELETE"])
@api_bp.doc(tags=["Fichiers"], summary="Delete a file from a candidature")
def api_delete_fichier(slug, filename):
    """Delete a file from a candidature."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        success = delete_fichier(slug, filename)
        if not success:
            return jsonify({"error": f"Fichier '{filename}' non trouve"}), 404

        return jsonify({"data": {"deleted": True}}), 200
    except Exception:
        logger.exception("Error deleting file %s for %s", filename, slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>/fichiers/<path:filename>/download")
@api_bp.doc(tags=["Fichiers"], summary="Download a file from a candidature")
def api_download_fichier(slug, filename):
    """Download a file from a candidature."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        file_path = get_fichier_path(slug, filename)
        if file_path is None:
            return jsonify({"error": f"Fichier '{filename}' non trouve"}), 404

        return send_file(file_path, as_attachment=True)
    except Exception:
        logger.exception("Error downloading file %s for %s", filename, slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


# ---------------------------------------------------------------------------
# CV adaptation
# ---------------------------------------------------------------------------


@api_bp.route("/candidatures/<slug>/cv/adapt", methods=["POST"])
@api_bp.doc(tags=["CV"], summary="Adapt CV via LLM")
def api_adapt_cv(slug):
    """POST /api/candidatures/<slug>/cv/adapt — Adapt CV via LLM, return adapted HTML."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        data = request.get_json(silent=True) or {}
        cv_source = data.get("cv_source", "auto")

        from services.cv_adapter import adapt_cv

        result = adapt_cv(slug, cv_source=cv_source)
        return jsonify({"data": result}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except TimeoutError as e:
        return jsonify({"error": str(e)}), 504
    except Exception:
        logger.exception("Error adapting CV for %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>/cv/save", methods=["POST"])
@api_bp.doc(tags=["CV"], summary="Save adapted CV as PDF + DOCX")
def api_save_cv(slug):
    """POST /api/candidatures/<slug>/cv/save — Save adapted CV as PDF + DOCX."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        data = request.get_json(silent=True)
        if not data or not data.get("adapted_html"):
            return jsonify({"error": "Contenu HTML adapte requis"}), 400

        from services.cv_adapter import save_adapted_cv

        files = save_adapted_cv(slug, data["adapted_html"])
        return jsonify({"data": {"files": files}}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Error saving adapted CV for %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>/match", methods=["POST"])
@api_bp.doc(tags=["Match"], summary="Evaluate CV-offer match via LLM")
def api_evaluate_match(slug):
    """POST /api/candidatures/<slug>/match — Evaluate match percentage via LLM."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        from services.match_evaluator import evaluate_match

        result = evaluate_match(slug)
        return jsonify({"data": result}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except TimeoutError as e:
        return jsonify({"error": str(e)}), 504
    except Exception:
        logger.exception("Error evaluating match for %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/candidatures/<slug>/cv/convert", methods=["POST"])
@api_bp.doc(tags=["CV"], summary="Convert CV to PDF + DOCX without LLM")
def api_convert_cv(slug):
    """POST /api/candidatures/<slug>/cv/convert — Direct HTML to PDF+DOCX, no LLM."""
    try:
        c = load_candidature(slug)
        if c is None:
            return jsonify({"error": f"Candidature '{slug}' non trouvee"}), 404

        data = request.get_json(silent=True) or {}
        cv_source = data.get("cv_source", "global")

        from services.cv_adapter import resolve_cv_html
        from services.cv_converter import save_cv_files

        if cv_source == "candidature":
            from services.database import Fichier

            html_fichier = Fichier.query.filter_by(slug=slug, type="html").first()
            if not html_fichier:
                return jsonify({"error": "Aucun fichier HTML trouve pour cette candidature"}), 400
            from pathlib import Path

            from flask import current_app

            data_dir = Path(current_app.config["FT_DATA_DIR"])
            file_path = data_dir / html_fichier.chemin
            if not file_path.is_file():
                return jsonify({"error": "Fichier CV introuvable sur le disque"}), 400
            cv_html = file_path.read_text(encoding="utf-8")
        else:
            cv_html = resolve_cv_html(slug)
            if not cv_html:
                return jsonify({"error": "Aucun CV de reference configure"}), 400

        files = save_cv_files(cv_html, slug, prefix="cv")
        return jsonify({"data": {"files": files}}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Error converting CV for %s", slug)
        return jsonify({"error": "Erreur interne du serveur"}), 500
