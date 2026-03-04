"""Cibles (target companies) management via Flask-SQLAlchemy."""

import shutil

from services.database import Candidature, Cible, Contact, db
from services.schemas import CibleResponse, ContactResponse

CATEGORIES = ("grands-groupes", "esn", "entreprises", "cabinets", "organisations")

CATEGORY_LABELS = {
    "grands-groupes": "Grands groupes",
    "esn": "ESN",
    "entreprises": "Entreprises",
    "cabinets": "Cabinets de recrutement",
    "organisations": "Administrations & Associations",
}


def load_cibles() -> dict[str, list[dict]]:
    """Load all cibles grouped by category.

    Returns a dict with keys: 'grands-groupes', 'entreprises', 'cabinets'.
    Each value is a list of dicts with id, nom, categorie, contactee, position.
    """
    rows = Cible.query.order_by(Cible.categorie, Cible.position).all()

    categories: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}

    for row in rows:
        cat = row.categorie
        if cat in categories:
            resp = CibleResponse(
                id=row.id,
                nom=row.nom,
                categorie=row.categorie,
                contactee=bool(row.contactee),
                position=row.position,
                url=row.url,
                description=row.description,
                email=row.email,
                linkedin=row.linkedin,
            )
            data = resp.model_dump()
            data["candidatures_count"] = Candidature.query.filter(
                Candidature.cible_id == row.id, Candidature.statut != "archivee"
            ).count()
            categories[cat].append(data)

    return categories


def list_all_cibles() -> list[dict]:
    """Return a flat list of all cibles, ordered by categorie then nom (for dropdowns)."""
    rows = Cible.query.order_by(Cible.categorie, Cible.nom).all()
    return [
        CibleResponse(
            id=row.id,
            nom=row.nom,
            categorie=row.categorie,
            contactee=bool(row.contactee),
            position=row.position,
            url=row.url,
            description=row.description,
            email=row.email,
            linkedin=row.linkedin,
        ).model_dump()
        for row in rows
    ]


def get_cible(cible_id: int) -> Cible | None:
    """Get a single cible by id."""
    return db.session.get(Cible, cible_id)


def create_cible(
    nom: str, categorie: str, url: str = "", description: str = "", email: str = "", linkedin: str = ""
) -> Cible:
    """Create a new cible at the last position in its category."""
    max_pos = db.session.query(db.func.max(Cible.position)).filter_by(categorie=categorie).scalar()
    position = (max_pos or 0) + 1

    cible = Cible(
        nom=nom,
        categorie=categorie,
        contactee=0,
        position=position,
        url=url,
        description=description,
        email=email,
        linkedin=linkedin,
    )
    db.session.add(cible)
    db.session.commit()
    return cible


def update_cible(cible_id: int, **fields) -> Cible | None:
    """Update a cible's fields. Returns the updated cible or None."""
    cible = db.session.get(Cible, cible_id)
    if cible is None:
        return None

    for key, value in fields.items():
        if key == "contactee":
            cible.contactee = 1 if value else 0
        elif hasattr(cible, key):
            setattr(cible, key, value)

    db.session.commit()
    return cible


def delete_cible(cible_id: int) -> bool:
    """Delete a cible, cascading to all linked candidatures (fichiers on disk + DB)."""
    from pathlib import Path

    from flask import current_app

    cible = db.session.get(Cible, cible_id)
    if cible is None:
        return False

    # Cascade: delete all candidatures linked to this cible
    candidatures = Candidature.query.filter_by(cible_id=cible_id).all()
    data_dir = Path(current_app.config["FT_DATA_DIR"])
    for cand in candidatures:
        # Remove candidature directory from disk (includes all files)
        cand_dir = data_dir / "candidatures" / cand.slug
        if cand_dir.is_dir():
            shutil.rmtree(cand_dir)
        db.session.delete(cand)

    cat = cible.categorie
    pos = cible.position
    db.session.delete(cible)

    # Shift positions down for items after the deleted one
    Cible.query.filter(Cible.categorie == cat, Cible.position > pos).update({Cible.position: Cible.position - 1})

    db.session.commit()
    return True


def reorder_cibles(categorie: str, ordered_ids: list[int]) -> bool:
    """Reorder cibles within a category based on the given id order."""
    for pos, cible_id in enumerate(ordered_ids, start=1):
        cible = db.session.get(Cible, cible_id)
        if cible and cible.categorie == categorie:
            cible.position = pos
    db.session.commit()
    return True


def toggle_cible(company: str, checked: bool) -> bool | None:
    """Toggle a company's contacted status.

    Returns True on success, False if not found, None if locked by candidatures.
    """
    cible = Cible.query.filter_by(nom=company).first()
    if cible is None:
        return False

    # Cannot uncheck a cible that has active (non-archived) candidatures
    if (
        not checked
        and Candidature.query.filter(Candidature.cible_id == cible.id, Candidature.statut != "archivee").count() > 0
    ):
        return None

    cible.contactee = 1 if checked else 0
    db.session.commit()
    return True


def get_cible_detail(cible_id: int) -> dict | None:
    """Return a cible with its contacts and linked candidatures."""
    cible = db.session.get(Cible, cible_id)
    if cible is None:
        return None

    contacts = [
        ContactResponse(
            id=c.id,
            nom=c.nom,
            prenom=c.prenom,
            email=c.email,
            telephone=c.telephone,
            linkedin=c.linkedin,
            fonction=c.fonction,
        ).model_dump()
        for c in cible.contacts.order_by(Contact.id).all()
    ]

    candidatures = [
        {
            "slug": c.slug,
            "entreprise": c.entreprise,
            "poste": c.poste,
            "statut": c.statut,
            "priorite": c.priorite,
        }
        for c in Candidature.query.filter_by(cible_id=cible_id).filter(Candidature.statut != "archivee").all()
    ]

    return {
        "id": cible.id,
        "nom": cible.nom,
        "categorie": cible.categorie,
        "contactee": bool(cible.contactee),
        "position": cible.position,
        "url": cible.url,
        "description": cible.description,
        "email": cible.email,
        "linkedin": cible.linkedin,
        "contacts": contacts,
        "candidatures": candidatures,
    }


def create_contact(cible_id: int, **fields) -> Contact | None:
    """Create a new contact for a cible. Returns None if cible not found."""
    cible = db.session.get(Cible, cible_id)
    if cible is None:
        return None

    contact = Contact(cible_id=cible_id, **fields)
    db.session.add(contact)
    db.session.commit()
    return contact


def update_contact(contact_id: int, **fields) -> Contact | None:
    """Update a contact's fields. Returns the updated contact or None."""
    contact = db.session.get(Contact, contact_id)
    if contact is None:
        return None

    for key, value in fields.items():
        if hasattr(contact, key):
            setattr(contact, key, value)

    db.session.commit()
    return contact


def delete_contact(contact_id: int) -> bool:
    """Delete a contact. Returns True on success, False if not found."""
    contact = db.session.get(Contact, contact_id)
    if contact is None:
        return False

    db.session.delete(contact)
    db.session.commit()
    return True
