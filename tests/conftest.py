import json

import pytest

from services.database import Candidature, Cible, Contact, Fichier, HistoriqueStatut, Setting, db


@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory with candidature file structure on disk."""
    # Create directory structure (files on disk still needed for file_view route and search)
    cand_dir = tmp_path / "candidatures"
    cand_dir.mkdir()

    # --- acme-corp: files on disk ---
    c1 = cand_dir / "acme-corp"
    c1.mkdir()
    (c1 / "offre.md").write_text("# Offre DevOps\n\nContenu de l'offre.", encoding="utf-8")
    (c1 / "lm.md").write_text("# Lettre de motivation\n\nBonjour...", encoding="utf-8")
    # PDF file for download tests
    (c1 / "contrat.pdf").write_bytes(b"%PDF-1.4 fake pdf content for testing")
    # Subdirectory file for path: tests
    coaching_dir = c1 / "coaching"
    coaching_dir.mkdir()
    (coaching_dir / "phase1.md").write_text("# Phase 1\n\nCoaching notes.", encoding="utf-8")

    # --- beta-inc: no files ---
    c2 = cand_dir / "beta-inc"
    c2.mkdir()

    # --- gamma-sa: no files ---
    c3 = cand_dir / "gamma-sa"
    c3.mkdir()

    return tmp_path


@pytest.fixture
def app(data_dir, monkeypatch):
    """Create a Flask test app with a test-specific database.

    Both the env var AND the cached config module attribute are patched
    BEFORE create_app() so that init_app() + migrations never touch
    the prod/dev database.
    """
    monkeypatch.setenv("FT_DATA_DIR", str(data_dir))
    monkeypatch.setattr("config.FT_DATA_DIR", str(data_dir))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("config.DATABASE_URL", None)

    from app import create_app

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()
        _seed_cibles()
        _seed_candidatures()
        _seed_historique_statuts()
        _seed_contacts()
        _seed_settings()

    return app


def _seed_candidatures():
    """Insert test candidatures using ORM models."""
    candidatures = [
        Candidature(
            slug="acme-corp",
            entreprise="ACME Corp",
            poste="DevOps Engineer",
            type="offre",
            statut="envoyee",
            date_candidature="2025-10-01",
            date_relance="",
            localisation="Paris",
            priorite="haute",
            categorie_entreprise="entreprise",
            cible_id=4,  # Orange Caraibe (entreprises)
            tags=json.dumps(["candidature"]),
            contenu="# ACME Corp\n\nDescription de la candidature.",
        ),
        Candidature(
            slug="beta-inc",
            entreprise="Beta Inc",
            poste="",
            type="spontanee",
            statut="brouillon",
            date_candidature="",
            date_relance="",
            localisation="",
            priorite="moyenne",
            categorie_entreprise="esn",
            cible_id=9,  # Sopra Steria (esn)
            tags=json.dumps(["candidature"]),
            contenu="",
        ),
        Candidature(
            slug="gamma-sa",
            entreprise="Gamma SA",
            poste="SRE",
            type="offre",
            statut="entretien",
            date_candidature="2025-09-15",
            date_relance="2025-10-01",
            localisation="Guadeloupe",
            priorite="haute",
            categorie_entreprise="cabinet",
            cible_id=7,  # Alpha Conseil (cabinets)
            tags=json.dumps(["candidature"]),
            contenu="# Gamma SA\n\nNotes sur la candidature.",
        ),
    ]

    for c in candidatures:
        db.session.add(c)

    # Insert fichiers for acme-corp (the ones that exist on disk)
    fichiers = [
        Fichier(slug="acme-corp", nom="lm.md", chemin="candidatures/acme-corp/lm.md", type="markdown"),
        Fichier(slug="acme-corp", nom="offre.md", chemin="candidatures/acme-corp/offre.md", type="markdown"),
        Fichier(slug="acme-corp", nom="contrat.pdf", chemin="candidatures/acme-corp/contrat.pdf", type="pdf"),
        Fichier(
            slug="acme-corp",
            nom="coaching/phase1.md",
            chemin="candidatures/acme-corp/coaching/phase1.md",
            type="markdown",
        ),
    ]
    for f in fichiers:
        db.session.add(f)

    db.session.commit()


def _seed_cibles():
    """Insert test cibles using ORM models.

    IDs are auto-incremented:
      1=Groupe GBH, 2=Groupe SAFO, 3=Groupe BARBOTTEAU,
      4=Orange Caraibe, 5=Digicel, 6=EDF,
      7=Alpha Conseil, 8=LHH, 9=Sopra Steria
    """
    cibles = [
        Cible(categorie="grands-groupes", nom="Groupe GBH", contactee=0, position=0),
        Cible(categorie="grands-groupes", nom="Groupe SAFO", contactee=1, position=1),
        Cible(categorie="grands-groupes", nom="Groupe BARBOTTEAU", contactee=0, position=2),
        Cible(categorie="entreprises", nom="Orange Caraibe", contactee=0, position=0),
        Cible(categorie="entreprises", nom="Digicel", contactee=0, position=1),
        Cible(categorie="entreprises", nom="EDF", contactee=1, position=2),
        Cible(categorie="cabinets", nom="Alpha Conseil", contactee=0, position=0),
        Cible(categorie="cabinets", nom="LHH", contactee=0, position=1),
        Cible(categorie="esn", nom="Sopra Steria", contactee=0, position=0),
    ]
    for c in cibles:
        db.session.add(c)
    db.session.commit()


def _seed_historique_statuts():
    """Insert test historique_statuts entries."""
    entries = [
        # acme-corp: brouillon -> envoyee (2 entries)
        HistoriqueStatut(
            slug="acme-corp",
            ancien_statut=None,
            nouveau_statut="brouillon",
            date_changement="2025-10-01T00:00:00",
        ),
        HistoriqueStatut(
            slug="acme-corp",
            ancien_statut="brouillon",
            nouveau_statut="envoyee",
            date_changement="2025-10-02T10:30:00",
        ),
        # beta-inc: brouillon (1 entry)
        HistoriqueStatut(
            slug="beta-inc",
            ancien_statut=None,
            nouveau_statut="brouillon",
            date_changement="2025-10-05T00:00:00",
        ),
        # gamma-sa: brouillon -> envoyee -> relancee -> entretien (4 entries)
        HistoriqueStatut(
            slug="gamma-sa",
            ancien_statut=None,
            nouveau_statut="brouillon",
            date_changement="2025-09-15T00:00:00",
        ),
        HistoriqueStatut(
            slug="gamma-sa",
            ancien_statut="brouillon",
            nouveau_statut="envoyee",
            date_changement="2025-09-16T09:00:00",
        ),
        HistoriqueStatut(
            slug="gamma-sa",
            ancien_statut="envoyee",
            nouveau_statut="relancee",
            date_changement="2025-09-25T14:00:00",
        ),
        HistoriqueStatut(
            slug="gamma-sa",
            ancien_statut="relancee",
            nouveau_statut="entretien",
            date_changement="2025-10-01T11:00:00",
        ),
    ]
    for e in entries:
        db.session.add(e)
    db.session.commit()


def _seed_contacts():
    """Insert test contacts for cibles.

    Contact IDs are auto-incremented:
      1=Jean Dupont (cible 4), 2=Marie Martin (cible 4), 3=Paul Durand (cible 7)
    """
    contacts = [
        Contact(
            cible_id=4, nom="Dupont", prenom="Jean", email="jean@orange.gp", telephone="0590123456", fonction="DRH"
        ),
        Contact(
            cible_id=4,
            nom="Martin",
            prenom="Marie",
            email="marie@orange.gp",
            linkedin="https://linkedin.com/in/marie",
            fonction="Tech Lead",
        ),
        Contact(cible_id=7, nom="Durand", prenom="Paul", email="paul@alpha.fr", fonction="Consultant"),
    ]
    for c in contacts:
        db.session.add(c)
    db.session.commit()


def _seed_settings():
    """Insert test settings for CV reference and LLM config."""
    settings = [
        Setting(
            key="cv_reference_html",
            value="<html><body><h1>Mon CV</h1><p>Experience...</p></body></html>",
            updated_at="2026-02-21T10:00:00",
        ),
        Setting(key="cv_reference_date", value="2026-02-21T10:00:00", updated_at="2026-02-21T10:00:00"),
        Setting(key="llm_provider", value="ollama", updated_at="2026-02-21T10:00:00"),
        Setting(key="llm_ollama_url", value="http://localhost:11434", updated_at="2026-02-21T10:00:00"),
        Setting(key="llm_ollama_model", value="llama3.2", updated_at="2026-02-21T10:00:00"),
    ]
    for s in settings:
        db.session.add(s)
    db.session.commit()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()
