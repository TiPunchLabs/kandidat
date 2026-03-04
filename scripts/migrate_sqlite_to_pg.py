"""Migrate data from SQLite (kandidat.db) to PostgreSQL.

Usage:
    DATABASE_URL=postgresql+psycopg://kandidat:kandidat@localhost:5432/kandidat \
        uv run python scripts/migrate_sqlite_to_pg.py --source data/prod/kandidat.db
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import create_app
from config import DATABASE_URL
from services.database import Candidature, Cible, Contact, Fichier, HistoriqueStatut, Setting, db


def read_sqlite(source_path: str) -> dict:
    """Read all records from SQLite database."""
    sqlite_uri = f"sqlite:///{Path(source_path).resolve()}"
    engine = create_engine(sqlite_uri)

    data = {}
    with Session(engine) as session:
        data["settings"] = [
            {"key": r.key, "value": r.value, "updated_at": r.updated_at}
            for r in session.execute(text("SELECT key, value, updated_at FROM settings")).fetchall()
        ]
        data["cibles"] = [
            {
                "id": r.id,
                "categorie": r.categorie,
                "nom": r.nom,
                "contactee": r.contactee,
                "position": r.position,
                "url": r.url,
                "description": r.description,
                "email": r.email,
                "linkedin": r.linkedin,
            }
            for r in session.execute(
                text("SELECT id, categorie, nom, contactee, position, url, description, email, linkedin FROM cibles")
            ).fetchall()
        ]
        data["contacts"] = [
            {
                "id": r.id,
                "cible_id": r.cible_id,
                "nom": r.nom,
                "prenom": r.prenom,
                "email": r.email,
                "telephone": r.telephone,
                "linkedin": r.linkedin,
                "fonction": r.fonction,
            }
            for r in session.execute(
                text("SELECT id, cible_id, nom, prenom, email, telephone, linkedin, fonction FROM contacts")
            ).fetchall()
        ]
        data["candidatures"] = [
            {
                "slug": r.slug,
                "entreprise": r.entreprise,
                "poste": r.poste,
                "type": r.type,
                "statut": r.statut,
                "date_candidature": r.date_candidature,
                "date_relance": r.date_relance,
                "localisation": r.localisation,
                "priorite": r.priorite,
                "categorie_entreprise": r.categorie_entreprise,
                "cible_id": r.cible_id,
                "tags": r.tags,
                "contenu": r.contenu,
            }
            for r in session.execute(
                text(
                    "SELECT slug, entreprise, poste, type, statut, date_candidature, date_relance, "
                    "localisation, priorite, categorie_entreprise, cible_id, tags, contenu FROM candidatures"
                )
            ).fetchall()
        ]
        data["fichiers"] = [
            {"id": r.id, "slug": r.slug, "nom": r.nom, "chemin": r.chemin, "type": r.type}
            for r in session.execute(text("SELECT id, slug, nom, chemin, type FROM fichiers")).fetchall()
        ]
        data["historique_statuts"] = [
            {
                "id": r.id,
                "slug": r.slug,
                "ancien_statut": r.ancien_statut,
                "nouveau_statut": r.nouveau_statut,
                "date_changement": r.date_changement,
                "commentaire": r.commentaire,
            }
            for r in session.execute(
                text(
                    "SELECT id, slug, ancien_statut, nouveau_statut, date_changement, commentaire "
                    "FROM historique_statuts"
                )
            ).fetchall()
        ]

    engine.dispose()
    return data


def write_pg(data: dict) -> None:
    """Write records to PostgreSQL via app ORM (merge for idempotency)."""
    # Settings
    for row in data["settings"]:
        db.session.merge(Setting(**row))
    db.session.commit()
    print(f"  Settings: {len(data['settings'])} rows")

    # Cibles
    for row in data["cibles"]:
        db.session.merge(Cible(**row))
    db.session.commit()
    print(f"  Cibles: {len(data['cibles'])} rows")

    # Contacts
    for row in data["contacts"]:
        db.session.merge(Contact(**row))
    db.session.commit()
    print(f"  Contacts: {len(data['contacts'])} rows")

    # Candidatures
    for row in data["candidatures"]:
        db.session.merge(Candidature(**row))
    db.session.commit()
    print(f"  Candidatures: {len(data['candidatures'])} rows")

    # Fichiers
    for row in data["fichiers"]:
        db.session.merge(Fichier(**row))
    db.session.commit()
    print(f"  Fichiers: {len(data['fichiers'])} rows")

    # HistoriqueStatuts
    for row in data["historique_statuts"]:
        db.session.merge(HistoriqueStatut(**row))
    db.session.commit()
    print(f"  HistoriqueStatuts: {len(data['historique_statuts'])} rows")


def reset_sequences() -> None:
    """Reset PostgreSQL sequences to max(id) + 1 for all auto-increment tables."""
    sequences = [
        ("cibles", "id"),
        ("contacts", "id"),
        ("fichiers", "id"),
        ("historique_statuts", "id"),
    ]
    with db.engine.connect() as conn:
        for table, col in sequences:
            conn.execute(
                text(f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), COALESCE(MAX({col}), 1)) FROM {table}")  # nosec B608 - table/col are hardcoded constants, not user input
            )
        conn.commit()
    print("  Sequences reset")


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL")
    parser.add_argument("--source", required=True, help="Path to SQLite database file (e.g. data/prod/kandidat.db)")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"Error: source file not found: {source}")
        sys.exit(1)

    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable must be set (target PostgreSQL)")
        sys.exit(1)

    print(f"Source: {source}")
    print(f"Target: {DATABASE_URL}")
    print()

    # Read from SQLite
    print("Reading from SQLite...")
    data = read_sqlite(str(source))
    print(
        f"  Found: {len(data['settings'])} settings, {len(data['cibles'])} cibles, "
        f"{len(data['contacts'])} contacts, {len(data['candidatures'])} candidatures, "
        f"{len(data['fichiers'])} fichiers, {len(data['historique_statuts'])} historique entries"
    )
    print()

    # Write to PostgreSQL via app context
    print("Writing to PostgreSQL...")
    app = create_app()
    with app.app_context():
        write_pg(data)
        print()
        print("Resetting sequences...")
        reset_sequences()

    print()
    print("Migration complete!")


if __name__ == "__main__":
    main()
