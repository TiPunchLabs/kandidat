"""API endpoints for cibles, search, stats, and dashboard."""

import logging

from flask import jsonify, request
from pydantic import ValidationError

from api import api_bp
from services.candidature import (
    CATEGORIES,
    CIBLE_TO_CANDIDATURE_CATEGORIE,
    PRIORITES,
    STATUS_TRANSITIONS,
    STATUTS,
    TYPES,
    list_candidatures,
)
from services.cibles import (
    create_cible,
    create_contact,
    delete_cible,
    delete_contact,
    get_cible_detail,
    load_cibles,
    reorder_cibles,
    toggle_cible,
    update_cible,
    update_contact,
)
from services.dashboard import regenerate_dashboard
from services.schemas import CibleCreate, CibleResponse, CibleUpdate, ContactCreate, ContactUpdate
from services.search import search_candidatures

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


@api_bp.route("/enums", methods=["GET"])
@api_bp.doc(tags=["Statistiques"], summary="Get all enum values and status transitions")
def api_enums():
    """Return all enum values, status transitions, and category mappings."""
    from services.cibles import CATEGORIES as CIBLE_CATEGORIES

    return jsonify(
        {
            "data": {
                "statuts": STATUTS,
                "types": TYPES,
                "priorites": PRIORITES,
                "categories_candidature": CATEGORIES,
                "categories_cible": list(CIBLE_CATEGORIES),
                "status_transitions": {k: sorted(v) for k, v in STATUS_TRANSITIONS.items()},
                "cible_to_candidature_mapping": CIBLE_TO_CANDIDATURE_CATEGORIE,
            }
        }
    )


# ---------------------------------------------------------------------------
# Cibles
# ---------------------------------------------------------------------------


@api_bp.route("/cibles", methods=["GET"])
@api_bp.doc(tags=["Cibles"], summary="List all cibles grouped by category")
def api_cibles():
    """List all cibles grouped by category."""
    try:
        data = load_cibles()
        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles", methods=["POST"])
@api_bp.doc(tags=["Cibles"], summary="Create a new cible")
def api_cibles_create():
    """Create a new cible."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    try:
        payload = CibleCreate(**body)
    except ValidationError as e:
        return jsonify({"error": e.errors()[0]["msg"]}), 400

    try:
        cible = create_cible(
            payload.nom,
            payload.categorie,
            url=payload.url,
            description=payload.description,
            email=payload.email,
            linkedin=payload.linkedin,
        )
        resp = CibleResponse(
            id=cible.id,
            nom=cible.nom,
            categorie=cible.categorie,
            contactee=bool(cible.contactee),
            position=cible.position,
            url=cible.url,
            description=cible.description,
            email=cible.email,
            linkedin=cible.linkedin,
            inscrit_plateforme=bool(cible.inscrit_plateforme),
        )
        return jsonify({"data": resp.model_dump()}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/<int:cible_id>", methods=["PUT"])
@api_bp.doc(tags=["Cibles"], summary="Update a cible")
def api_cibles_update(cible_id):
    """Update a cible."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    try:
        payload = CibleUpdate(**body)
    except ValidationError as e:
        return jsonify({"error": e.errors()[0]["msg"]}), 400

    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not fields:
        return jsonify({"error": "no fields to update"}), 400

    try:
        cible = update_cible(cible_id, **fields)
        if cible is None:
            return jsonify({"error": "cible not found"}), 404
        resp = CibleResponse(
            id=cible.id,
            nom=cible.nom,
            categorie=cible.categorie,
            contactee=bool(cible.contactee),
            position=cible.position,
            url=cible.url,
            description=cible.description,
            email=cible.email,
            linkedin=cible.linkedin,
            inscrit_plateforme=bool(cible.inscrit_plateforme),
        )
        return jsonify({"data": resp.model_dump()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/<int:cible_id>", methods=["DELETE"])
@api_bp.doc(tags=["Cibles"], summary="Delete a cible")
def api_cibles_delete(cible_id):
    """Delete a cible (cascades to linked candidatures and their files)."""
    try:
        success = delete_cible(cible_id)
        if not success:
            return jsonify({"error": "cible not found"}), 404
        return jsonify({"data": {"deleted": True}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/reorder", methods=["POST"])
@api_bp.doc(tags=["Cibles"], summary="Reorder cibles within a category")
def api_cibles_reorder():
    """Reorder cibles within a category."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    categorie = body.get("categorie", "")
    ordered_ids = body.get("ordered_ids", [])

    if not categorie or not ordered_ids:
        return jsonify({"error": "categorie and ordered_ids are required"}), 400

    try:
        reorder_cibles(categorie, ordered_ids)
        return jsonify({"data": {"reordered": True}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/toggle", methods=["POST"])
@api_bp.doc(tags=["Cibles"], summary="Toggle a cible contacted status")
def api_cibles_toggle():
    """Toggle a company's contacted status."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    nom = body.get("nom", "").strip() if body.get("nom") else ""
    if not nom:
        return jsonify({"error": "nom is required"}), 400

    contactee = body.get("contactee")
    if contactee is None:
        return jsonify({"error": "contactee is required"}), 400

    try:
        result = toggle_cible(nom, bool(contactee))
        if result is False:
            return jsonify({"error": "company not found"}), 404
        if result is None:
            return jsonify({"error": "cible verrouillee par des candidatures existantes"}), 409
        return jsonify({"data": {"nom": nom, "contactee": bool(contactee)}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/<int:cible_id>/toggle-inscription", methods=["POST"])
@api_bp.doc(tags=["Cibles"], summary="Toggle platform registration for a cabinet")
def api_cible_toggle_inscription(cible_id):
    """Toggle inscrit_plateforme for a cabinet cible."""
    from services.cibles import toggle_inscription_plateforme

    result = toggle_inscription_plateforme(cible_id)
    if result is None:
        return jsonify({"error": "cible not found"}), 404
    if isinstance(result, str):
        return jsonify({"error": result}), 400

    resp = CibleResponse(
        id=result.id,
        nom=result.nom,
        categorie=result.categorie,
        contactee=bool(result.contactee),
        position=result.position,
        url=result.url,
        description=result.description,
        email=result.email,
        linkedin=result.linkedin,
        inscrit_plateforme=bool(result.inscrit_plateforme),
    )
    return jsonify({"data": resp.model_dump()})


# ---------------------------------------------------------------------------
# Cible detail + Contacts
# ---------------------------------------------------------------------------


@api_bp.route("/cibles/<int:cible_id>/detail", methods=["GET"])
@api_bp.doc(tags=["Cibles"], summary="Get cible detail with contacts and candidatures")
def api_cible_detail(cible_id):
    """Get a cible with its contacts and linked candidatures."""
    try:
        data = get_cible_detail(cible_id)
        if data is None:
            return jsonify({"error": "cible not found"}), 404
        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/<int:cible_id>/contacts", methods=["POST"])
@api_bp.doc(tags=["Contacts"], summary="Create a contact for a cible")
def api_contact_create(cible_id):
    """Create a new contact for a cible."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    try:
        payload = ContactCreate(**body)
    except ValidationError as e:
        return jsonify({"error": e.errors()[0]["msg"]}), 400

    try:
        contact = create_contact(
            cible_id,
            nom=payload.nom,
            prenom=payload.prenom,
            email=payload.email,
            telephone=payload.telephone,
            linkedin=payload.linkedin,
            fonction=payload.fonction,
        )
        if contact is None:
            return jsonify({"error": "cible not found"}), 404
        return jsonify(
            {
                "data": {
                    "id": contact.id,
                    "nom": contact.nom,
                    "prenom": contact.prenom,
                    "email": contact.email,
                    "telephone": contact.telephone,
                    "linkedin": contact.linkedin,
                    "fonction": contact.fonction,
                }
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/<int:cible_id>/contacts/<int:contact_id>", methods=["PUT"])
@api_bp.doc(tags=["Contacts"], summary="Update a contact")
def api_contact_update(cible_id, contact_id):
    """Update a contact."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    try:
        payload = ContactUpdate(**body)
    except ValidationError as e:
        return jsonify({"error": e.errors()[0]["msg"]}), 400

    fields = payload.non_null_fields()
    if not fields:
        return jsonify({"error": "no fields to update"}), 400

    try:
        contact = update_contact(contact_id, **fields)
        if contact is None:
            return jsonify({"error": "contact not found"}), 404
        return jsonify(
            {
                "data": {
                    "id": contact.id,
                    "nom": contact.nom,
                    "prenom": contact.prenom,
                    "email": contact.email,
                    "telephone": contact.telephone,
                    "linkedin": contact.linkedin,
                    "fonction": contact.fonction,
                }
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/cibles/<int:cible_id>/contacts/<int:contact_id>", methods=["DELETE"])
@api_bp.doc(tags=["Contacts"], summary="Delete a contact")
def api_contact_delete(cible_id, contact_id):
    """Delete a contact."""
    try:
        success = delete_contact(contact_id)
        if not success:
            return jsonify({"error": "contact not found"}), 404
        return jsonify({"data": {"deleted": True}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@api_bp.route("/search", methods=["GET"])
@api_bp.doc(tags=["Recherche"], summary="Full-text search across candidatures")
def api_search():
    """Full-text search across candidatures."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    try:
        results = search_candidatures(query)
        return jsonify({"data": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@api_bp.route("/stats", methods=["GET"])
@api_bp.doc(tags=["Statistiques"], summary="Get statistics by statut, type, priorite, categorie")
def api_stats():
    """Statistics: counts by statut, type, priorite, categorie + timeline."""
    try:
        candidatures = list_candidatures()

        by_statut = {s: sum(1 for c in candidatures if c.get("statut") == s) for s in STATUTS}
        by_type = {t: sum(1 for c in candidatures if c.get("type") == t) for t in TYPES}
        by_priorite = {p: sum(1 for c in candidatures if c.get("priorite") == p) for p in PRIORITES}
        by_categorie = {
            cat: sum(1 for c in candidatures if c.get("categorie_entreprise", "entreprise") == cat)
            for cat in CATEGORIES
        }

        timeline = sorted(
            [c for c in candidatures if c.get("date_candidature")],
            key=lambda c: c["date_candidature"],
        )

        return jsonify(
            {
                "data": {
                    "total": len(candidatures),
                    "by_statut": by_statut,
                    "by_type": by_type,
                    "by_priorite": by_priorite,
                    "by_categorie": by_categorie,
                    "timeline": timeline,
                }
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Dashboard regeneration
# ---------------------------------------------------------------------------


@api_bp.route("/dashboard/regenerate", methods=["POST"])
@api_bp.doc(tags=["Statistiques"], summary="Regenerate Obsidian dashboard")
def api_dashboard_regenerate():
    """Regenerate 00-Dashboard.md."""
    try:
        regenerate_dashboard()
        return jsonify({"data": {"message": "Dashboard regenerated successfully"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Cible enrichment (Tavily + LLM)
# ---------------------------------------------------------------------------


@api_bp.route("/cibles/<int:cible_id>/enrich", methods=["POST"])
@api_bp.doc(tags=["Enrichissement"], summary="Trigger AI enrichment for a cible")
def api_cible_enrich(cible_id):
    """Trigger AI enrichment for a cible: web search + LLM extraction."""
    data = get_cible_detail(cible_id)
    if data is None:
        return jsonify({"error": "cible not found"}), 404

    try:
        from services.cible_enricher import enrich_cible

        result = enrich_cible(cible_id)
        return jsonify({"data": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except (ConnectionError, TimeoutError) as e:
        return jsonify({"error": str(e)}), 503
    except Exception:
        logger.exception("Error enriching cible %s", cible_id)
        return jsonify({"error": "Erreur interne du serveur"}), 500


@api_bp.route("/cibles/<int:cible_id>/enrich/apply", methods=["POST"])
@api_bp.doc(tags=["Enrichissement"], summary="Apply selected enrichment suggestions")
def api_cible_enrich_apply(cible_id):
    """Apply selected enrichment suggestions."""
    data = get_cible_detail(cible_id)
    if data is None:
        return jsonify({"error": "cible not found"}), 404

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    accepted = body.get("accepted", body)

    try:
        from services.cible_enricher import apply_enrichment

        result = apply_enrichment(cible_id, accepted)
        return jsonify({"data": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Error applying enrichment for cible %s", cible_id)
        return jsonify({"error": "Erreur interne du serveur"}), 500
