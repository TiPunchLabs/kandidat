"""Seed the dev database with realistic sample data.

Usage:
    KANDIDAT_ENV=dev uv run python seed_dev.py [--force]

Options:
    --force    Drop and recreate all tables before seeding.
"""

import json
import shutil
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app
from services.database import Candidature, Cible, Contact, Fichier, HistoriqueStatut, db

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

CIBLES = [
    # grands-groupes
    {
        "categorie": "grands-groupes",
        "nom": "Groupe GBH",
        "contactee": 1,
        "position": 0,
        "url": "https://www.gbh.fr",
        "description": "Groupe de distribution et automobile aux Antilles-Guyane",
        "email": "recrutement@gbh.fr",
    },
    {
        "categorie": "grands-groupes",
        "nom": "Groupe SAFO",
        "contactee": 1,
        "position": 1,
        "url": "https://www.safo.fr",
        "description": "Distribution automobile et BTP en Guadeloupe",
        "email": "rh@safo.fr",
    },
    {
        "categorie": "grands-groupes",
        "nom": "Groupe BARBOTTEAU",
        "contactee": 0,
        "position": 2,
        "url": "",
        "description": "Groupe diversifie Guadeloupe",
        "email": "",
    },
    # entreprises
    {
        "categorie": "entreprises",
        "nom": "Orange Caraibe",
        "contactee": 1,
        "position": 0,
        "url": "https://www.orange.gp",
        "description": "Operateur telecom Antilles-Guyane",
        "email": "recrutement@orange.gp",
    },
    {
        "categorie": "entreprises",
        "nom": "Digicel",
        "contactee": 1,
        "position": 1,
        "url": "https://www.digicelgroup.com",
        "description": "Operateur telecom Caraibe",
        "email": "careers@digicelgroup.com",
    },
    {
        "categorie": "entreprises",
        "nom": "Karibea Hotels",
        "contactee": 0,
        "position": 2,
        "url": "https://www.karibea.com",
        "description": "Chaine hoteliere Antilles",
        "email": "",
    },
    {
        "categorie": "entreprises",
        "nom": "Soguafi",
        "contactee": 0,
        "position": 3,
        "url": "",
        "description": "Distribution automobile Guadeloupe",
        "email": "",
    },
    # esn
    {
        "categorie": "esn",
        "nom": "Sopra Steria",
        "contactee": 1,
        "position": 0,
        "url": "https://www.soprasteria.com",
        "description": "ESN et conseil en transformation digitale",
        "email": "recrutement@soprasteria.com",
    },
    {
        "categorie": "esn",
        "nom": "CGI",
        "contactee": 1,
        "position": 1,
        "url": "https://www.cgi.com",
        "description": "Services IT et consulting",
        "email": "",
    },
    {
        "categorie": "esn",
        "nom": "Capgemini",
        "contactee": 0,
        "position": 2,
        "url": "https://www.capgemini.com",
        "description": "Conseil, services informatiques et ingenierie",
        "email": "",
    },
    {
        "categorie": "esn",
        "nom": "Atos",
        "contactee": 1,
        "position": 3,
        "url": "https://www.atos.net",
        "description": "Services numeriques et cloud",
        "email": "",
    },
    # cabinets
    {
        "categorie": "cabinets",
        "nom": "LHH",
        "contactee": 1,
        "position": 0,
        "url": "https://www.lhh.com",
        "description": "Cabinet de conseil RH et outplacement",
        "email": "contact@lhh.com",
    },
    {
        "categorie": "cabinets",
        "nom": "Michael Page",
        "contactee": 1,
        "position": 1,
        "url": "https://www.michaelpage.fr",
        "description": "Cabinet de recrutement IT",
        "email": "",
    },
    {
        "categorie": "cabinets",
        "nom": "Hays",
        "contactee": 1,
        "position": 2,
        "url": "https://www.hays.fr",
        "description": "Cabinet de recrutement specialise",
        "email": "",
    },
]

# cible_id references the auto-incremented IDs above (1-based)
CANDIDATURES = [
    # brouillon (2)
    {
        "slug": "capgemini-devops",
        "entreprise": "Capgemini",
        "poste": "DevOps Engineer",
        "type": "offre",
        "statut": "brouillon",
        "date_candidature": "",
        "localisation": "Paris - Remote",
        "priorite": "moyenne",
        "categorie_entreprise": "esn",
        "cible_id": 10,
        "tags": ["candidature", "devops"],
        "contenu": "# Capgemini — DevOps Engineer\n\nPoste vu sur LinkedIn. Stack : Kubernetes, Terraform, AWS.\n\n## Notes\n- Verifier les conditions de teletravail\n- Preparer le CV oriente cloud",
    },
    {
        "slug": "karibea-sysadmin",
        "entreprise": "Karibea Hotels",
        "poste": "Administrateur Systemes",
        "type": "spontanee",
        "statut": "brouillon",
        "date_candidature": "",
        "localisation": "Guadeloupe",
        "priorite": "basse",
        "categorie_entreprise": "entreprise",
        "cible_id": 6,
        "tags": ["candidature", "sysadmin"],
        "contenu": "# Karibea Hotels — Sysadmin\n\nCandidature spontanee. Infrastructure hoteliere multi-sites.",
    },
    # envoyee (2)
    {
        "slug": "orange-sre",
        "entreprise": "Orange Caraibe",
        "poste": "Site Reliability Engineer",
        "type": "offre",
        "statut": "envoyee",
        "date_candidature": "2026-01-15",
        "localisation": "Guadeloupe",
        "priorite": "haute",
        "categorie_entreprise": "entreprise",
        "cible_id": 4,
        "tags": ["candidature", "sre", "telecom"],
        "contenu": "# Orange Caraibe — SRE\n\nOffre publiee sur le site Orange Emploi.\n\n## Stack technique\n- Prometheus / Grafana\n- Ansible\n- Linux RHEL\n\n## Suivi\n- CV envoye le 15/01/2026\n- Contact : Jean Dupont (DRH)",
    },
    {
        "slug": "cgi-cloud",
        "entreprise": "CGI",
        "poste": "Cloud Architect",
        "type": "offre",
        "statut": "envoyee",
        "date_candidature": "2026-01-20",
        "localisation": "Paris",
        "priorite": "haute",
        "categorie_entreprise": "esn",
        "cible_id": 9,
        "tags": ["candidature", "cloud", "architecture"],
        "contenu": "# CGI — Cloud Architect\n\nPoste base a Paris, client grand compte bancaire.\n\n## Competences requises\n- AWS / Azure\n- Terraform, CloudFormation\n- Architecture micro-services",
    },
    # relancee (1)
    {
        "slug": "sopra-data",
        "entreprise": "Sopra Steria",
        "poste": "Data Engineer",
        "type": "offre",
        "statut": "relancee",
        "date_candidature": "2025-12-10",
        "date_relance": "2026-01-10",
        "localisation": "Toulouse",
        "priorite": "moyenne",
        "categorie_entreprise": "esn",
        "cible_id": 8,
        "tags": ["candidature", "data"],
        "contenu": "# Sopra Steria — Data Engineer\n\nOffre sur Welcome to the Jungle.\n\n## Suivi\n- Candidature envoyee le 10/12/2025\n- Relance email le 10/01/2026, sans reponse pour le moment",
    },
    # entretien (2)
    {
        "slug": "gbh-devops",
        "entreprise": "Groupe GBH",
        "poste": "DevOps Lead",
        "type": "offre",
        "statut": "entretien",
        "date_candidature": "2025-11-20",
        "date_relance": "2025-12-15",
        "localisation": "Fort-de-France",
        "priorite": "haute",
        "categorie_entreprise": "groupe",
        "cible_id": 1,
        "tags": ["candidature", "devops", "lead"],
        "contenu": "# Groupe GBH — DevOps Lead\n\nPoste de responsable DevOps pour la DSI groupe.\n\n## Entretiens\n- 1er entretien RH le 10/01/2026 : OK\n- 2eme entretien technique prevu le 25/01/2026\n\n## Notes\n- Equipe de 5 personnes\n- Migration vers le cloud en cours",
    },
    {
        "slug": "digicel-infra",
        "entreprise": "Digicel",
        "poste": "Infrastructure Manager",
        "type": "offre",
        "statut": "entretien",
        "date_candidature": "2025-12-01",
        "date_relance": "2026-01-05",
        "localisation": "Guadeloupe",
        "priorite": "haute",
        "categorie_entreprise": "entreprise",
        "cible_id": 5,
        "tags": ["candidature", "infrastructure", "management"],
        "contenu": "# Digicel — Infrastructure Manager\n\nPoste de management de l'equipe infra.\n\n## Entretien\n- Entretien avec le CTO le 15/01/2026\n- Attente de retour",
    },
    # acceptee (1)
    {
        "slug": "hays-consultant",
        "entreprise": "Hays",
        "poste": "Consultant DevOps",
        "type": "offre",
        "statut": "acceptee",
        "date_candidature": "2025-10-15",
        "date_relance": "",
        "localisation": "Paris - Hybride",
        "priorite": "haute",
        "categorie_entreprise": "cabinet",
        "cible_id": 14,
        "tags": ["candidature", "consulting", "devops"],
        "contenu": "# Hays — Consultant DevOps\n\nMission via Hays pour un client dans le secteur energie.\n\n## Resultat\n- Proposition recue le 20/01/2026\n- TJM negocie\n- Debut prevu mars 2026",
    },
    # refusee (1)
    {
        "slug": "atos-sre",
        "entreprise": "Atos",
        "poste": "SRE Senior",
        "type": "offre",
        "statut": "refusee",
        "date_candidature": "2025-11-01",
        "date_relance": "2025-12-01",
        "localisation": "Lyon",
        "priorite": "moyenne",
        "categorie_entreprise": "esn",
        "cible_id": 11,
        "tags": ["candidature", "sre"],
        "contenu": "# Atos — SRE Senior\n\n## Motif de refus\n- Profil juge trop senior pour le poste\n- Feedback recu le 15/01/2026",
    },
    # sans-reponse (1)
    {
        "slug": "michael-page-devops",
        "entreprise": "Michael Page",
        "poste": "DevOps Engineer",
        "type": "offre",
        "statut": "sans-reponse",
        "date_candidature": "2025-10-20",
        "date_relance": "2025-11-20",
        "localisation": "Paris",
        "priorite": "basse",
        "categorie_entreprise": "cabinet",
        "cible_id": 13,
        "tags": ["candidature", "devops"],
        "contenu": "# Michael Page — DevOps Engineer\n\nAucune reponse malgre la relance.\nClassee sans reponse apres 2 mois.",
    },
    # archivee (2)
    {
        "slug": "safo-admin",
        "entreprise": "Groupe SAFO",
        "poste": "Administrateur Systemes et Reseaux",
        "type": "spontanee",
        "statut": "archivee",
        "date_candidature": "2025-09-01",
        "date_relance": "2025-10-01",
        "localisation": "Guadeloupe",
        "priorite": "moyenne",
        "categorie_entreprise": "groupe",
        "cible_id": 2,
        "tags": ["candidature", "sysadmin"],
        "contenu": "# Groupe SAFO — Admin Sys\n\nCandidature spontanee refusee.\nPas de poste ouvert actuellement.",
    },
    {
        "slug": "lhh-coach",
        "entreprise": "LHH",
        "poste": "Coach Technique DevOps",
        "type": "offre",
        "statut": "archivee",
        "date_candidature": "2025-08-15",
        "localisation": "Remote",
        "priorite": "basse",
        "categorie_entreprise": "cabinet",
        "cible_id": 12,
        "tags": ["candidature", "coaching"],
        "contenu": "# LHH — Coach Technique\n\nMission terminee. Bonne experience.\nArchivee apres fin de mission.",
    },
]

# History entries following the state machine for each candidature
HISTORIQUE = [
    # capgemini-devops: brouillon
    ("capgemini-devops", None, "brouillon", "2026-02-10T09:00:00"),
    # karibea-sysadmin: brouillon
    ("karibea-sysadmin", None, "brouillon", "2026-02-15T14:00:00"),
    # orange-sre: brouillon -> envoyee
    ("orange-sre", None, "brouillon", "2026-01-14T10:00:00"),
    ("orange-sre", "brouillon", "envoyee", "2026-01-15T08:30:00"),
    # cgi-cloud: brouillon -> envoyee
    ("cgi-cloud", None, "brouillon", "2026-01-18T16:00:00"),
    ("cgi-cloud", "brouillon", "envoyee", "2026-01-20T09:00:00"),
    # sopra-data: brouillon -> envoyee -> relancee
    ("sopra-data", None, "brouillon", "2025-12-09T11:00:00"),
    ("sopra-data", "brouillon", "envoyee", "2025-12-10T08:00:00"),
    ("sopra-data", "envoyee", "relancee", "2026-01-10T10:00:00"),
    # gbh-devops: brouillon -> envoyee -> relancee -> entretien
    ("gbh-devops", None, "brouillon", "2025-11-19T09:00:00"),
    ("gbh-devops", "brouillon", "envoyee", "2025-11-20T08:30:00"),
    ("gbh-devops", "envoyee", "relancee", "2025-12-15T10:00:00"),
    ("gbh-devops", "relancee", "entretien", "2026-01-08T14:00:00"),
    # digicel-infra: brouillon -> envoyee -> relancee -> entretien
    ("digicel-infra", None, "brouillon", "2025-11-30T10:00:00"),
    ("digicel-infra", "brouillon", "envoyee", "2025-12-01T09:00:00"),
    ("digicel-infra", "envoyee", "relancee", "2026-01-05T11:00:00"),
    ("digicel-infra", "relancee", "entretien", "2026-01-12T15:00:00"),
    # hays-consultant: brouillon -> envoyee -> entretien -> acceptee
    ("hays-consultant", None, "brouillon", "2025-10-14T09:00:00"),
    ("hays-consultant", "brouillon", "envoyee", "2025-10-15T08:00:00"),
    ("hays-consultant", "envoyee", "entretien", "2025-11-10T14:00:00"),
    ("hays-consultant", "entretien", "acceptee", "2026-01-20T16:00:00"),
    # atos-sre: brouillon -> envoyee -> relancee -> entretien -> refusee
    ("atos-sre", None, "brouillon", "2025-10-31T10:00:00"),
    ("atos-sre", "brouillon", "envoyee", "2025-11-01T08:00:00"),
    ("atos-sre", "envoyee", "relancee", "2025-12-01T09:00:00"),
    ("atos-sre", "relancee", "entretien", "2025-12-20T14:00:00"),
    ("atos-sre", "entretien", "refusee", "2026-01-15T11:00:00"),
    # michael-page-devops: brouillon -> envoyee -> relancee -> sans-reponse
    ("michael-page-devops", None, "brouillon", "2025-10-19T10:00:00"),
    ("michael-page-devops", "brouillon", "envoyee", "2025-10-20T09:00:00"),
    ("michael-page-devops", "envoyee", "relancee", "2025-11-20T10:00:00"),
    ("michael-page-devops", "relancee", "sans-reponse", "2025-12-20T10:00:00"),
    # safo-admin: brouillon -> envoyee -> relancee -> refusee -> archivee
    ("safo-admin", None, "brouillon", "2025-08-31T09:00:00"),
    ("safo-admin", "brouillon", "envoyee", "2025-09-01T08:00:00"),
    ("safo-admin", "envoyee", "relancee", "2025-10-01T10:00:00"),
    ("safo-admin", "relancee", "refusee", "2025-10-20T14:00:00"),
    ("safo-admin", "refusee", "archivee", "2025-11-01T09:00:00"),
    # lhh-coach: brouillon -> envoyee -> entretien -> acceptee -> archivee
    ("lhh-coach", None, "brouillon", "2025-08-14T09:00:00"),
    ("lhh-coach", "brouillon", "envoyee", "2025-08-15T08:00:00"),
    ("lhh-coach", "envoyee", "entretien", "2025-09-05T14:00:00"),
    ("lhh-coach", "entretien", "acceptee", "2025-09-20T16:00:00"),
    ("lhh-coach", "acceptee", "archivee", "2025-12-31T18:00:00"),
]

CONTACTS = [
    # Orange Caraibe (cible_id=4)
    {
        "cible_id": 4,
        "nom": "Dupont",
        "prenom": "Jean",
        "email": "jean.dupont@orange.gp",
        "telephone": "0590 12 34 56",
        "fonction": "DRH",
        "linkedin": "",
    },
    {
        "cible_id": 4,
        "nom": "Martin",
        "prenom": "Marie",
        "email": "marie.martin@orange.gp",
        "telephone": "",
        "fonction": "Tech Lead",
        "linkedin": "https://linkedin.com/in/marie-martin",
    },
    # Digicel (cible_id=5)
    {
        "cible_id": 5,
        "nom": "Joseph",
        "prenom": "Marc",
        "email": "marc.joseph@digicelgroup.com",
        "telephone": "0690 98 76 54",
        "fonction": "CTO",
        "linkedin": "https://linkedin.com/in/marc-joseph",
    },
    # Groupe GBH (cible_id=1)
    {
        "cible_id": 1,
        "nom": "Clery",
        "prenom": "Sophie",
        "email": "sophie.clery@gbh.fr",
        "telephone": "0596 71 23 45",
        "fonction": "Responsable DSI",
        "linkedin": "",
    },
    {
        "cible_id": 1,
        "nom": "Riviere",
        "prenom": "Thomas",
        "email": "thomas.riviere@gbh.fr",
        "telephone": "",
        "fonction": "DevOps Lead",
        "linkedin": "https://linkedin.com/in/thomas-riviere",
    },
    # Sopra Steria (cible_id=8)
    {
        "cible_id": 8,
        "nom": "Lemoine",
        "prenom": "Claire",
        "email": "claire.lemoine@soprasteria.com",
        "telephone": "",
        "fonction": "Manager Recrutement",
        "linkedin": "",
    },
    # Hays (cible_id=14)
    {
        "cible_id": 14,
        "nom": "Berthier",
        "prenom": "Lucas",
        "email": "lucas.berthier@hays.fr",
        "telephone": "01 42 56 78 90",
        "fonction": "Consultant IT",
        "linkedin": "https://linkedin.com/in/lucas-berthier",
    },
]

# Sample files on disk for candidatures that have progressed
FILES_ON_DISK = {
    "orange-sre": {
        "offre.md": "# SRE — Orange Caraibe\n\n## Description du poste\nRejoignez l'equipe SRE d'Orange Caraibe.\n\n## Missions\n- Monitoring et alerting (Prometheus, Grafana)\n- Automatisation (Ansible, Terraform)\n- Gestion des incidents\n\n## Profil\n- 5 ans d'experience en production\n- Linux, Docker, Kubernetes\n- Bon relationnel",
        "lm.md": "# Lettre de motivation — Orange Caraibe\n\nMadame, Monsieur,\n\nPassionne par les infrastructures resilientes et fort de mon experience en DevOps...\n\nCordialement,\nXavier Gueret",
    },
    "cgi-cloud": {
        "offre.md": "# Cloud Architect — CGI\n\n## Contexte\nClient grand compte bancaire, migration cloud.\n\n## Competences\n- AWS, Azure\n- Terraform, CloudFormation\n- Architecture micro-services\n- Securite cloud (IAM, VPC)",
    },
    "gbh-devops": {
        "offre.md": "# DevOps Lead — Groupe GBH\n\n## Mission\nPiloter la transformation DevOps de la DSI groupe.\n\n## Responsabilites\n- Management equipe DevOps (5 personnes)\n- CI/CD (GitLab CI)\n- Infrastructure as Code\n- Migration cloud",
        "lm.md": "# Lettre de motivation — Groupe GBH\n\nMadame, Monsieur,\n\nVotre projet de transformation numerique correspond...\n\nCordialement,\nXavier Gueret",
        "notes-entretien.md": "# Notes entretien GBH\n\n## Entretien 1 — RH (10/01/2026)\n- Ambiance positive\n- Questions sur le management\n- Salaire : fourchette OK\n\n## A preparer pour entretien 2\n- Cas pratique CI/CD\n- Architecture cible cloud",
    },
    "digicel-infra": {
        "offre.md": "# Infrastructure Manager — Digicel\n\n## Poste\nManagement de l'equipe infrastructure reseau et systemes.\n\n## Environnement\n- Datacenter multi-sites Caraibe\n- VMware, Cisco, Fortinet\n- Equipe de 8 personnes",
    },
    "hays-consultant": {
        "offre.md": "# Consultant DevOps — Hays\n\n## Mission\nIntervention chez un client secteur energie.\n\n## Stack\n- Kubernetes, Docker\n- Terraform, Ansible\n- AWS\n- GitLab CI/CD",
        "proposition.md": "# Proposition commerciale Hays\n\n- TJM : 550 EUR\n- Duree : 6 mois renouvelable\n- Debut : mars 2026\n- Lieu : Paris + 2j remote",
    },
    "sopra-data": {
        "offre.md": "# Data Engineer — Sopra Steria\n\n## Description\nConception de pipelines data pour un client retail.\n\n## Stack\n- Python, Spark\n- Airflow\n- AWS (S3, Glue, Redshift)\n- dbt",
    },
    "atos-sre": {
        "offre.md": "# SRE Senior — Atos\n\n## Description\nIntegrer l'equipe SRE pour un client telecom.\n\n## Stack\n- Kubernetes, Helm\n- Datadog\n- Terraform",
    },
}

# Fichier DB records matching the files on disk
FICHIERS = [
    {"slug": "orange-sre", "nom": "offre.md", "chemin": "candidatures/orange-sre/offre.md", "type": "markdown"},
    {"slug": "orange-sre", "nom": "lm.md", "chemin": "candidatures/orange-sre/lm.md", "type": "markdown"},
    {"slug": "cgi-cloud", "nom": "offre.md", "chemin": "candidatures/cgi-cloud/offre.md", "type": "markdown"},
    {"slug": "gbh-devops", "nom": "offre.md", "chemin": "candidatures/gbh-devops/offre.md", "type": "markdown"},
    {"slug": "gbh-devops", "nom": "lm.md", "chemin": "candidatures/gbh-devops/lm.md", "type": "markdown"},
    {
        "slug": "gbh-devops",
        "nom": "notes-entretien.md",
        "chemin": "candidatures/gbh-devops/notes-entretien.md",
        "type": "markdown",
    },
    {"slug": "digicel-infra", "nom": "offre.md", "chemin": "candidatures/digicel-infra/offre.md", "type": "markdown"},
    {
        "slug": "hays-consultant",
        "nom": "offre.md",
        "chemin": "candidatures/hays-consultant/offre.md",
        "type": "markdown",
    },
    {
        "slug": "hays-consultant",
        "nom": "proposition.md",
        "chemin": "candidatures/hays-consultant/proposition.md",
        "type": "markdown",
    },
    {"slug": "sopra-data", "nom": "offre.md", "chemin": "candidatures/sopra-data/offre.md", "type": "markdown"},
    {"slug": "atos-sre", "nom": "offre.md", "chemin": "candidatures/atos-sre/offre.md", "type": "markdown"},
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


def create_files_on_disk(data_dir: Path) -> None:
    """Create candidature directories and sample files on disk."""
    cand_root = data_dir / "candidatures"
    if cand_root.exists():
        shutil.rmtree(cand_root)
    cand_root.mkdir(parents=True, exist_ok=True)

    # Create a directory for every candidature (even without files)
    for c in CANDIDATURES:
        (cand_root / c["slug"]).mkdir(exist_ok=True)

    # Write sample files
    for slug, files in FILES_ON_DISK.items():
        slug_dir = cand_root / slug
        for filename, content in files.items():
            (slug_dir / filename).write_text(content, encoding="utf-8")


def seed_database(force: bool = False) -> None:
    """Seed all tables with dev data."""
    if force:
        db.drop_all()
        db.create_all()
        print("  Tables recreees (--force)")

    # Cibles
    for data in CIBLES:
        db.session.add(Cible(**data))
    db.session.commit()
    print(f"  {len(CIBLES)} cibles inserees")

    # Candidatures
    for data in CANDIDATURES:
        row = dict(data)
        row["tags"] = json.dumps(row["tags"])
        row.setdefault("date_relance", "")
        db.session.add(Candidature(**row))
    db.session.commit()
    print(f"  {len(CANDIDATURES)} candidatures inserees")

    # Fichiers
    for data in FICHIERS:
        db.session.add(Fichier(**data))
    db.session.commit()
    print(f"  {len(FICHIERS)} fichiers inseres")

    # Historique statuts
    for slug, ancien, nouveau, date in HISTORIQUE:
        db.session.add(
            HistoriqueStatut(
                slug=slug,
                ancien_statut=ancien,
                nouveau_statut=nouveau,
                date_changement=date,
            )
        )
    db.session.commit()
    print(f"  {len(HISTORIQUE)} entrees historique inserees")

    # Contacts
    for data in CONTACTS:
        db.session.add(Contact(**data))
    db.session.commit()
    print(f"  {len(CONTACTS)} contacts inseres")


def main() -> None:
    force = "--force" in sys.argv

    app = create_app()

    data_dir = Path(app.config["FT_DATA_DIR"])
    print(f"Seed dev -> {data_dir}")

    if not str(data_dir).endswith("/dev") and "dev" not in str(data_dir):
        print("ERREUR: KANDIDAT_ENV ne semble pas etre 'dev'.")
        print("Usage: KANDIDAT_ENV=dev uv run python seed_dev.py [--force]")
        sys.exit(1)

    # Fichiers sur disque
    print("Creation des fichiers sur disque...")
    create_files_on_disk(data_dir)

    # Base de donnees
    print("Seed de la base de donnees...")
    with app.app_context():
        existing = Candidature.query.count()
        if existing > 0 and not force:
            print(f"  La base contient deja {existing} candidatures.")
            print("  Utilisez --force pour tout reinitialiser.")
            sys.exit(1)
        seed_database(force=force)

    print("Done.")


if __name__ == "__main__":
    main()
