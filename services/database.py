"""Flask-SQLAlchemy database module for kandidat."""

from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

db = SQLAlchemy()

DB_FILENAME = "kandidat.db"


class Candidature(db.Model):
    __tablename__ = "candidatures"

    slug = db.Column(db.String, primary_key=True)
    entreprise = db.Column(db.String, nullable=False)
    poste = db.Column(db.String, nullable=False, default="")
    type = db.Column(db.String, nullable=False, default="offre")
    statut = db.Column(db.String, nullable=False, default="brouillon")
    date_candidature = db.Column(db.String, nullable=False, default="")
    date_relance = db.Column(db.String, nullable=False, default="")
    localisation = db.Column(db.String, nullable=False, default="")
    priorite = db.Column(db.String, nullable=False, default="moyenne")
    categorie_entreprise = db.Column(db.String, nullable=False, default="entreprise")
    cible_id = db.Column(db.Integer, db.ForeignKey("cibles.id"), nullable=False)
    tags = db.Column(db.String, nullable=False, default='["candidature"]')
    contenu = db.Column(db.Text, nullable=False, default="")
    match_score = db.Column(db.Float, nullable=True, default=None)
    match_details = db.Column(db.Text, nullable=True, default=None)

    fichiers = db.relationship("Fichier", backref="candidature", cascade="all, delete-orphan")
    cible = db.relationship("Cible", backref=db.backref("candidatures", lazy="dynamic"))


class Fichier(db.Model):
    __tablename__ = "fichiers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(
        db.String,
        db.ForeignKey("candidatures.slug", ondelete="CASCADE"),
        nullable=False,
    )
    nom = db.Column(db.String, nullable=False)
    chemin = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)

    __table_args__ = (db.UniqueConstraint("slug", "nom"),)


class HistoriqueStatut(db.Model):
    __tablename__ = "historique_statuts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(
        db.String,
        db.ForeignKey("candidatures.slug", ondelete="CASCADE"),
        nullable=False,
    )
    ancien_statut = db.Column(db.String, nullable=True)
    nouveau_statut = db.Column(db.String, nullable=False)
    date_changement = db.Column(db.String, nullable=False)
    commentaire = db.Column(db.String, nullable=True)

    candidature = db.relationship(
        "Candidature",
        backref=db.backref("historique_statuts", cascade="all, delete-orphan", lazy="dynamic"),
    )


class Cible(db.Model):
    __tablename__ = "cibles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    categorie = db.Column(db.String, nullable=False)
    nom = db.Column(db.String, nullable=False)
    contactee = db.Column(db.Integer, nullable=False, default=0)
    position = db.Column(db.Integer, nullable=False, default=0)
    url = db.Column(db.String, nullable=False, default="")
    description = db.Column(db.String, nullable=False, default="")
    email = db.Column(db.String, nullable=False, default="")
    linkedin = db.Column(db.String, nullable=False, default="")
    inscrit_plateforme = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=False, default="")

    contacts = db.relationship("Contact", backref="cible", cascade="all, delete-orphan", lazy="dynamic")

    __table_args__ = (db.UniqueConstraint("categorie", "nom"),)


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.String, nullable=False)


class Contact(db.Model):
    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cible_id = db.Column(db.Integer, db.ForeignKey("cibles.id", ondelete="CASCADE"), nullable=False)
    nom = db.Column(db.String, nullable=False)
    prenom = db.Column(db.String, nullable=False, default="")
    email = db.Column(db.String, nullable=False, default="")
    telephone = db.Column(db.String, nullable=False, default="")
    linkedin = db.Column(db.String, nullable=False, default="")
    fonction = db.Column(db.String, nullable=False, default="")


def init_app(app: Flask) -> None:
    """Initialize Flask-SQLAlchemy with the app and create all tables."""
    from config import DATABASE_URL

    if DATABASE_URL:
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    else:
        data_dir = Path(app.config["FT_DATA_DIR"])
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / DB_FILENAME
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _migrate_cibles(app)
        _migrate_candidatures_cible_id()
        _migrate_match_scoring()
        _migrate_historique_statuts()
        _migrate_historique_commentaire()
        _migrate_settings()
        _migrate_inscrit_plateforme()
        _migrate_notes()


def _get_column_names(table_name: str) -> list[str]:
    """Return column names for a table using SQLAlchemy Inspector (database-agnostic)."""
    inspector = sa_inspect(db.engine)
    return [col["name"] for col in inspector.get_columns(table_name)]


def _migrate_cibles(app: Flask) -> None:
    """Add new columns to the cibles table if they don't exist yet."""
    new_cols = [
        ("url", "TEXT NOT NULL DEFAULT ''"),
        ("description", "TEXT NOT NULL DEFAULT ''"),
        ("email", "TEXT NOT NULL DEFAULT ''"),
        ("linkedin", "TEXT NOT NULL DEFAULT ''"),
    ]
    with db.engine.connect() as conn:
        for col_name, col_def in new_cols:
            try:
                conn.execute(db.text(f"ALTER TABLE cibles ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except (OperationalError, ProgrammingError):
                conn.rollback()


def _migrate_candidatures_cible_id() -> None:
    """Add cible_id column to candidatures and backfill from company name matching."""
    cat_mapping = {
        "entreprise": "entreprises",
        "esn": "esn",
        "cabinet": "cabinets",
        "groupe": "grands-groupes",
    }
    with db.engine.connect() as conn:
        # Check if column already exists
        cols = _get_column_names("candidatures")
        if "cible_id" not in cols:
            conn.execute(db.text("ALTER TABLE candidatures ADD COLUMN cible_id INTEGER REFERENCES cibles(id)"))
            conn.commit()

        # Backfill: match by company name or auto-create cible
        rows = conn.execute(
            db.text("SELECT slug, entreprise, categorie_entreprise FROM candidatures WHERE cible_id IS NULL")
        ).fetchall()

        for slug, entreprise, cat_ent in rows:
            cible = conn.execute(db.text("SELECT id FROM cibles WHERE nom = :nom"), {"nom": entreprise}).fetchone()

            if cible is None:
                cible_cat = cat_mapping.get(cat_ent, "entreprises")
                max_pos = conn.execute(
                    db.text("SELECT COALESCE(MAX(position), -1) FROM cibles WHERE categorie = :cat"),
                    {"cat": cible_cat},
                ).fetchone()[0]
                conn.execute(
                    db.text(
                        "INSERT INTO cibles (categorie, nom, contactee, position, url, description, email) "
                        "VALUES (:cat, :nom, 1, :pos, '', '', '')"
                    ),
                    {"cat": cible_cat, "nom": entreprise, "pos": max_pos + 1},
                )
                cible = conn.execute(db.text("SELECT id FROM cibles WHERE nom = :nom"), {"nom": entreprise}).fetchone()

            if cible:
                conn.execute(
                    db.text("UPDATE candidatures SET cible_id = :cid WHERE slug = :slug"),
                    {"cid": cible[0], "slug": slug},
                )

        conn.commit()

        # Sync contactee flag: cibles with candidatures should be checked
        conn.execute(
            db.text(
                "UPDATE cibles SET contactee = 1 WHERE id IN "
                "(SELECT DISTINCT cible_id FROM candidatures WHERE cible_id IS NOT NULL)"
            )
        )
        # Cibles without candidatures that were auto-checked should be unchecked
        conn.execute(
            db.text(
                "UPDATE cibles SET contactee = 0 WHERE contactee = 1 AND id NOT IN "
                "(SELECT DISTINCT cible_id FROM candidatures WHERE cible_id IS NOT NULL)"
            )
        )
        conn.commit()


def _migrate_historique_statuts() -> None:
    """Backfill historique_statuts for candidatures that have no history yet."""
    from datetime import datetime

    candidates_without_history = Candidature.query.filter(~Candidature.historique_statuts.any()).all()
    for c in candidates_without_history:
        date = c.date_candidature + "T00:00:00" if c.date_candidature else datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        entry = HistoriqueStatut(
            slug=c.slug,
            ancien_statut=None,
            nouveau_statut=c.statut,
            date_changement=date,
        )
        db.session.add(entry)
    db.session.commit()


def _migrate_historique_commentaire() -> None:
    """Add commentaire column to historique_statuts if it doesn't exist yet."""
    cols = _get_column_names("historique_statuts")
    if "commentaire" not in cols:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE historique_statuts ADD COLUMN commentaire TEXT DEFAULT NULL"))
            conn.commit()


def _migrate_settings() -> None:
    """Ensure the settings table exists (created by db.create_all, this is a no-op safety net)."""
    db.create_all()


def _migrate_inscrit_plateforme() -> None:
    """Add inscrit_plateforme column to cibles if it doesn't exist."""
    cols = _get_column_names("cibles")
    if "inscrit_plateforme" not in cols:
        with db.engine.connect() as conn:
            try:
                conn.execute(db.text("ALTER TABLE cibles ADD COLUMN inscrit_plateforme INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
            except (OperationalError, ProgrammingError):
                conn.rollback()


def _migrate_notes() -> None:
    """Add notes column to cibles if it doesn't exist."""
    cols = _get_column_names("cibles")
    if "notes" not in cols:
        with db.engine.connect() as conn:
            try:
                conn.execute(db.text("ALTER TABLE cibles ADD COLUMN notes TEXT NOT NULL DEFAULT ''"))
                conn.commit()
            except (OperationalError, ProgrammingError):
                conn.rollback()


def _migrate_match_scoring() -> None:
    """Add match_score and match_details columns to candidatures if they don't exist yet."""
    cols = _get_column_names("candidatures")
    if "match_score" not in cols:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE candidatures ADD COLUMN match_score REAL DEFAULT NULL"))
            conn.execute(db.text("ALTER TABLE candidatures ADD COLUMN match_details TEXT DEFAULT NULL"))
            conn.commit()
