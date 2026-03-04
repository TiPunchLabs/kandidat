import json
import logging
import re
import shutil
import unicodedata
from pathlib import Path

import markdown as md
from sqlalchemy.orm import joinedload

from services.database import Candidature, Cible, HistoriqueStatut, db
from services.schemas import CandidatureCreate, CandidatureResponse

logger = logging.getLogger(__name__)

STATUTS = ["brouillon", "envoyee", "relancee", "entretien", "acceptee", "refusee", "sans-reponse", "archivee"]
TYPES = ["offre", "spontanee"]
PRIORITES = ["haute", "moyenne", "basse"]
CATEGORIES = ["entreprise", "esn", "cabinet", "groupe", "organisation"]

# Mapping from cible.categorie to candidature.categorie_entreprise
CIBLE_TO_CANDIDATURE_CATEGORIE = {
    "grands-groupes": "groupe",
    "entreprises": "entreprise",
    "cabinets": "cabinet",
    "esn": "esn",
    "organisations": "organisation",
}

# Allowed status transitions: current -> set of valid next statuses
STATUS_TRANSITIONS = {
    "brouillon": {"envoyee", "archivee"},
    "envoyee": {"relancee", "sans-reponse", "archivee"},
    "relancee": {"entretien", "sans-reponse", "archivee"},
    "entretien": {"acceptee", "refusee", "archivee"},
    "acceptee": {"archivee"},
    "refusee": {"archivee"},
    "sans-reponse": {"archivee"},
    "archivee": set(),
}


def _data_dir() -> Path:
    from flask import current_app

    return Path(current_app.config["FT_DATA_DIR"])


def _candidatures_dir() -> Path:
    return _data_dir() / "candidatures"


def to_kebab_case(name: str) -> str:
    """Convert a name to kebab-case: normalize unicode, remove accents, lowercase, hyphens."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lower)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def render_markdown(content: str) -> str:
    """Convert markdown to HTML. Raw HTML in the source is escaped by the markdown library's default."""
    return md.markdown(content, extensions=["tables", "fenced_code"])


def validate_status(current: str, new: str) -> bool:
    """Check if the status transition is allowed."""
    if current == new:
        return True
    allowed = STATUS_TRANSITIONS.get(current, set())
    return new in allowed


def load_candidature(slug: str) -> dict | None:
    """Load a single candidature by slug. Returns None if not found."""
    obj = Candidature.query.options(joinedload(Candidature.cible)).filter_by(slug=slug).first()
    if obj is None:
        return None
    return CandidatureResponse.from_orm(obj).model_dump()


def list_candidatures() -> list[dict]:
    """List all candidatures ordered by slug."""
    rows = Candidature.query.options(joinedload(Candidature.cible)).order_by(Candidature.slug).all()
    return [CandidatureResponse.from_orm(obj).model_dump() for obj in rows]


def update_candidature(slug: str, fields: dict, commentaire: str | None = None) -> bool:
    """Update fields for a candidature. Returns True on success."""
    obj = db.session.get(Candidature, slug)
    if obj is None:
        return False

    # Whitelist of updatable fields
    allowed_fields = {
        "entreprise",
        "poste",
        "type",
        "statut",
        "date_candidature",
        "date_relance",
        "localisation",
        "priorite",
        "categorie_entreprise",
        "contenu",
    }

    old_statut = obj.statut
    updated = False
    for key, value in fields.items():
        if key in allowed_fields:
            setattr(obj, key, value)
            updated = True

    # Record status change in historique if statut actually changed
    if "statut" in fields and fields["statut"] != old_statut:
        from datetime import datetime

        # Strip commentaire; treat whitespace-only as None
        clean_comment = commentaire.strip() if commentaire else None
        if clean_comment == "":
            clean_comment = None

        db.session.add(
            HistoriqueStatut(
                slug=slug,
                ancien_statut=old_statut,
                nouveau_statut=fields["statut"],
                date_changement=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                commentaire=clean_comment,
            )
        )

    if updated:
        db.session.commit()

    return True


def create_candidature(data: dict) -> str:
    """Create a new candidature. Returns the slug. Raises ValueError/FileExistsError."""
    # Validate with Pydantic
    schema = CandidatureCreate(**data)
    entreprise = schema.entreprise

    slug = to_kebab_case(entreprise)
    if not slug:
        raise ValueError("Invalid entreprise name")

    # Check for duplicate in DB
    existing = db.session.get(Candidature, slug)
    if existing is not None:
        raise FileExistsError(f"Candidature '{slug}' already exists")

    # Validate cible exists
    cible = db.session.get(Cible, schema.cible_id)
    if cible is None:
        raise ValueError(f"Cible with id {schema.cible_id} not found")

    # Derive categorie_entreprise from cible
    categorie = CIBLE_TO_CANDIDATURE_CATEGORIE.get(cible.categorie, "entreprise")

    from datetime import date

    obj = Candidature(
        slug=slug,
        entreprise=entreprise,
        poste=schema.poste,
        type=schema.type,
        statut="brouillon",
        date_candidature=str(date.today()),
        date_relance="",
        localisation=schema.localisation,
        priorite=schema.priorite,
        categorie_entreprise=categorie,
        cible_id=schema.cible_id,
        tags=json.dumps(["candidature"]),
        contenu=schema.contenu,
    )
    db.session.add(obj)

    # Record initial status in historique
    from datetime import datetime

    db.session.add(
        HistoriqueStatut(
            slug=slug,
            ancien_statut=None,
            nouveau_statut="brouillon",
            date_changement=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
    )

    # Auto-mark cible as contactee
    cible.contactee = 1

    db.session.commit()

    # Create directory for future files
    cand_dir = _candidatures_dir() / slug
    cand_dir.mkdir(parents=True, exist_ok=True)

    return slug


def load_historique(slug: str) -> list[dict]:
    """Load status history for a candidature, ordered chronologically."""
    entries = HistoriqueStatut.query.filter_by(slug=slug).order_by(HistoriqueStatut.date_changement.asc()).all()
    return [
        {
            "id": e.id,
            "ancien_statut": e.ancien_statut,
            "nouveau_statut": e.nouveau_statut,
            "date_changement": e.date_changement,
            "commentaire": e.commentaire,
        }
        for e in entries
    ]


def delete_candidature(slug: str) -> bool:
    """Delete a candidature, its fichiers (DB) and its directory on disk.

    Returns True if deleted, False if not found.
    """
    obj = db.session.get(Candidature, slug)
    if obj is None:
        return False

    # Remove directory from disk (includes all files)
    cand_dir = _candidatures_dir() / slug
    if cand_dir.is_dir():
        shutil.rmtree(cand_dir)

    # DB cascade handles fichiers via relationship cascade="all, delete-orphan"
    cible_id = obj.cible_id
    db.session.delete(obj)
    db.session.flush()

    # If the cible has no more candidatures, uncheck it
    if cible_id:
        remaining = Candidature.query.filter_by(cible_id=cible_id).count()
        if remaining == 0:
            cible = db.session.get(Cible, cible_id)
            if cible:
                cible.contactee = 0

    db.session.commit()
    return True
