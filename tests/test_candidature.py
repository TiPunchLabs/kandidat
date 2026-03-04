"""Tests for services/candidature.py: load, list, update, create, to_kebab_case."""

import pytest

from services.candidature import (
    create_candidature,
    list_candidatures,
    load_candidature,
    load_historique,
    render_markdown,
    to_kebab_case,
    update_candidature,
)
from services.database import Cible, HistoriqueStatut, db

# ---------------------------------------------------------------------------
# to_kebab_case
# ---------------------------------------------------------------------------


class TestToKebabCase:
    def test_simple_name(self):
        assert to_kebab_case("Exelcia IT") == "exelcia-it"

    def test_accented_characters(self):
        assert to_kebab_case("Serène Up") == "serene-up"

    def test_multiple_spaces(self):
        assert to_kebab_case("Groupe   Parfait") == "groupe-parfait"

    def test_special_characters(self):
        assert to_kebab_case("CMA-CGM (France)") == "cma-cgm-france"

    def test_leading_trailing_hyphens(self):
        assert to_kebab_case("  Test Corp  ") == "test-corp"

    def test_empty_string(self):
        assert to_kebab_case("") == ""

    def test_unicode_normalization(self):
        assert to_kebab_case("Éléphant café") == "elephant-cafe"


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


class TestRenderMarkdown:
    def test_basic_rendering(self):
        result = render_markdown("**bold** text")
        assert "<strong>bold</strong>" in result
        assert "text" in result

    def test_fenced_code(self):
        result = render_markdown("```python\nprint('hello')\n```")
        assert "<code" in result
        assert "print" in result

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = render_markdown(md)
        assert "<table>" in result
        assert "<td>1</td>" in result

    def test_empty_string(self):
        result = render_markdown("")
        assert result == ""

    def test_paragraphs(self):
        result = render_markdown("Hello\n\nWorld")
        assert "<p>Hello</p>" in result
        assert "<p>World</p>" in result


# ---------------------------------------------------------------------------
# load_candidature
# ---------------------------------------------------------------------------


class TestLoadCandidature:
    def test_load_valid(self, app, data_dir):
        with app.app_context():
            c = load_candidature("acme-corp")
            assert c is not None
            assert c["slug"] == "acme-corp"
            assert c["entreprise"] == "ACME Corp"
            assert c["poste"] == "DevOps Engineer"
            assert c["type"] == "offre"
            assert c["statut"] == "envoyee"
            assert c["priorite"] == "haute"
            assert c["date_candidature"] == "2025-10-01"
            assert c["date_relance"] == ""
            assert "candidature" in c["tags"]

    def test_load_returns_categorie(self, app, data_dir):
        with app.app_context():
            c = load_candidature("acme-corp")
            assert c["categorie_entreprise"] == "entreprise"
            c2 = load_candidature("beta-inc")
            assert c2["categorie_entreprise"] == "esn"

    def test_load_returns_files(self, app, data_dir):
        with app.app_context():
            c = load_candidature("acme-corp")
            filenames = [f["nom"] for f in c["fichiers"]]
            assert "offre.md" in filenames
            assert "lm.md" in filenames

    def test_load_nonexistent(self, app, data_dir):
        with app.app_context():
            c = load_candidature("nonexistent")
            assert c is None

    def test_load_slug_not_in_db(self, app, data_dir):
        """A slug that doesn't exist in the DB returns None."""
        with app.app_context():
            c = load_candidature("not-in-db")
            assert c is None

    def test_load_minimal_candidature(self, app, data_dir):
        with app.app_context():
            c = load_candidature("beta-inc")
            assert c is not None
            assert c["entreprise"] == "Beta Inc"
            assert c["statut"] == "brouillon"
            assert c["contenu"] == ""
            assert c["fichiers"] == []

    def test_date_fields_are_strings(self, app, data_dir):
        with app.app_context():
            c = load_candidature("acme-corp")
            assert isinstance(c["date_candidature"], str)
            assert isinstance(c["date_relance"], str)


# ---------------------------------------------------------------------------
# list_candidatures
# ---------------------------------------------------------------------------


class TestListCandidatures:
    def test_list_all(self, app, data_dir):
        with app.app_context():
            results = list_candidatures()
            slugs = [c["slug"] for c in results]
            assert "acme-corp" in slugs
            assert "beta-inc" in slugs
            assert "gamma-sa" in slugs

    def test_only_db_records_returned(self, app, data_dir):
        """Only candidatures in the DB are returned (no filesystem scanning)."""
        with app.app_context():
            results = list_candidatures()
            slugs = [c["slug"] for c in results]
            assert len(slugs) == 3

    def test_empty_db_returns_empty_list(self, app, data_dir):
        """An empty candidatures table returns an empty list."""
        with app.app_context():
            from services.database import Candidature, Fichier, db

            Fichier.query.delete()
            Candidature.query.delete()
            db.session.commit()
            results = list_candidatures()
            assert results == []

    def test_returns_sorted(self, app, data_dir):
        with app.app_context():
            results = list_candidatures()
            slugs = [c["slug"] for c in results]
            assert slugs == sorted(slugs)


# ---------------------------------------------------------------------------
# update_candidature
# ---------------------------------------------------------------------------


class TestUpdateCandidature:
    def test_update_statut(self, app, data_dir):
        with app.app_context():
            success = update_candidature("acme-corp", {"statut": "relancee"})
            assert success is True
            c = load_candidature("acme-corp")
            assert c["statut"] == "relancee"

    def test_update_preserves_content(self, app, data_dir):
        with app.app_context():
            original = load_candidature("acme-corp")
            original_content = original["contenu"]
            update_candidature("acme-corp", {"priorite": "basse"})
            updated = load_candidature("acme-corp")
            assert updated["contenu"] == original_content

    def test_update_preserves_other_fields(self, app, data_dir):
        with app.app_context():
            update_candidature("acme-corp", {"priorite": "basse"})
            c = load_candidature("acme-corp")
            assert c["entreprise"] == "ACME Corp"
            assert c["poste"] == "DevOps Engineer"
            assert c["priorite"] == "basse"

    def test_update_nonexistent(self, app, data_dir):
        with app.app_context():
            success = update_candidature("nonexistent", {"statut": "envoyee"})
            assert success is False

    def test_update_date(self, app, data_dir):
        with app.app_context():
            update_candidature("acme-corp", {"date_relance": "2025-11-01"})
            c = load_candidature("acme-corp")
            assert c["date_relance"] == "2025-11-01"

    def test_update_contenu(self, app, data_dir):
        with app.app_context():
            update_candidature("acme-corp", {"contenu": "# Notes\n\nTest content"})
            c = load_candidature("acme-corp")
            assert c["contenu"] == "# Notes\n\nTest content"

    def test_update_contenu_empty(self, app, data_dir):
        with app.app_context():
            update_candidature("acme-corp", {"contenu": ""})
            c = load_candidature("acme-corp")
            assert c["contenu"] == ""


# ---------------------------------------------------------------------------
# create_candidature
# ---------------------------------------------------------------------------


class TestCreateCandidature:
    def test_create_basic(self, app, data_dir):
        with app.app_context():
            slug = create_candidature(
                {
                    "entreprise": "Test Corp",
                    "poste": "DevOps",
                    "type": "offre",
                    "priorite": "haute",
                    "cible_id": 4,
                }
            )
            assert slug == "test-corp"
            c = load_candidature("test-corp")
            assert c is not None
            assert c["entreprise"] == "Test Corp"
            assert c["statut"] == "brouillon"
            assert c["priorite"] == "haute"

    def test_create_kebab_case_slug(self, app, data_dir):
        with app.app_context():
            slug = create_candidature(
                {
                    "entreprise": "Ma Super Entreprise",
                    "type": "spontanee",
                    "priorite": "moyenne",
                    "cible_id": 4,
                }
            )
            assert slug == "ma-super-entreprise"

    def test_create_duplicate_raises(self, app, data_dir):
        with app.app_context():
            with pytest.raises(FileExistsError):
                create_candidature(
                    {
                        "entreprise": "ACME Corp",
                        "type": "offre",
                        "priorite": "haute",
                        "cible_id": 4,
                    }
                )

    def test_create_empty_name_raises(self, app, data_dir):
        with app.app_context():
            with pytest.raises(ValueError):
                create_candidature(
                    {
                        "entreprise": "",
                        "type": "offre",
                        "priorite": "haute",
                        "cible_id": 4,
                    }
                )

    def test_create_sets_date(self, app, data_dir):
        with app.app_context():
            from datetime import date

            slug = create_candidature(
                {
                    "entreprise": "Date Test",
                    "type": "offre",
                    "priorite": "moyenne",
                    "cible_id": 4,
                }
            )
            c = load_candidature(slug)
            assert c["date_candidature"] == str(date.today())

    def test_create_derives_categorie_from_cible(self, app, data_dir):
        """categorie_entreprise is derived from the cible's categorie."""
        with app.app_context():
            # cible_id=4 is Orange Caraibe (entreprises) -> categorie_entreprise=entreprise
            slug = create_candidature(
                {"entreprise": "Cat Derive Ent", "type": "offre", "priorite": "moyenne", "cible_id": 4}
            )
            c = load_candidature(slug)
            assert c["categorie_entreprise"] == "entreprise"

            # cible_id=9 is Sopra Steria (esn) -> categorie_entreprise=esn
            slug2 = create_candidature(
                {"entreprise": "Cat Derive ESN", "type": "offre", "priorite": "moyenne", "cible_id": 9}
            )
            c2 = load_candidature(slug2)
            assert c2["categorie_entreprise"] == "esn"

            # cible_id=7 is Alpha Conseil (cabinets) -> categorie_entreprise=cabinet
            slug3 = create_candidature(
                {"entreprise": "Cat Derive Cab", "type": "offre", "priorite": "moyenne", "cible_id": 7}
            )
            c3 = load_candidature(slug3)
            assert c3["categorie_entreprise"] == "cabinet"

            # cible_id=1 is Groupe GBH (grands-groupes) -> categorie_entreprise=groupe
            slug4 = create_candidature(
                {"entreprise": "Cat Derive Grp", "type": "offre", "priorite": "moyenne", "cible_id": 1}
            )
            c4 = load_candidature(slug4)
            assert c4["categorie_entreprise"] == "groupe"

    def test_create_sets_cible_contactee(self, app, data_dir):
        """Creating a candidature marks the cible as contactee."""
        with app.app_context():
            # cible_id=5 is Digicel, contactee=0 initially
            cible_before = db.session.get(Cible, 5)
            assert cible_before.contactee == 0

            create_candidature({"entreprise": "Contactee Test", "type": "offre", "priorite": "moyenne", "cible_id": 5})

            cible_after = db.session.get(Cible, 5)
            assert cible_after.contactee == 1

    def test_create_invalid_cible_raises(self, app, data_dir):
        """Creating a candidature with a non-existent cible_id raises ValueError."""
        with app.app_context():
            with pytest.raises(ValueError, match="not found"):
                create_candidature(
                    {"entreprise": "Invalid Cible", "type": "offre", "priorite": "moyenne", "cible_id": 9999}
                )

    def test_create_sets_tags(self, app, data_dir):
        with app.app_context():
            slug = create_candidature(
                {
                    "entreprise": "Tag Test",
                    "type": "offre",
                    "priorite": "moyenne",
                    "cible_id": 4,
                }
            )
            c = load_candidature(slug)
            assert "candidature" in c["tags"]

    def test_load_includes_cible(self, app, data_dir):
        """load_candidature includes cible summary with id, nom, categorie."""
        with app.app_context():
            c = load_candidature("acme-corp")
            assert c["cible_id"] == 4
            assert c["cible"] is not None
            assert c["cible"]["id"] == 4
            assert c["cible"]["nom"] == "Orange Caraibe"
            assert c["cible"]["categorie"] == "entreprises"


# ---------------------------------------------------------------------------
# Historique statuts
# ---------------------------------------------------------------------------


class TestHistoriqueStatuts:
    def test_create_records_initial_historique(self, app, data_dir):
        """Creating a candidature records an initial historique entry."""
        with app.app_context():
            slug = create_candidature(
                {"entreprise": "Hist Test", "type": "offre", "priorite": "moyenne", "cible_id": 4}
            )
            historique = load_historique(slug)
            assert len(historique) == 1
            assert historique[0]["ancien_statut"] is None
            assert historique[0]["nouveau_statut"] == "brouillon"

    def test_update_statut_records_historique(self, app, data_dir):
        """Updating the statut records a historique entry."""
        with app.app_context():
            # acme-corp: envoyee -> relancee
            update_candidature("acme-corp", {"statut": "relancee"})
            historique = load_historique("acme-corp")
            last = historique[-1]
            assert last["ancien_statut"] == "envoyee"
            assert last["nouveau_statut"] == "relancee"

    def test_update_non_statut_no_historique(self, app, data_dir):
        """Updating a non-statut field does not create a historique entry."""
        with app.app_context():
            before = load_historique("acme-corp")
            update_candidature("acme-corp", {"priorite": "basse"})
            after = load_historique("acme-corp")
            assert len(after) == len(before)

    def test_update_same_statut_no_historique(self, app, data_dir):
        """Updating to the same statut does not create a historique entry."""
        with app.app_context():
            before = load_historique("acme-corp")
            update_candidature("acme-corp", {"statut": "envoyee"})
            after = load_historique("acme-corp")
            assert len(after) == len(before)

    def test_historique_chronological_order(self, app, data_dir):
        """Historique entries are returned in chronological order."""
        with app.app_context():
            historique = load_historique("gamma-sa")
            dates = [h["date_changement"] for h in historique]
            assert dates == sorted(dates)
            assert len(historique) == 4

    def test_historique_includes_commentaire(self, app, data_dir):
        """update_candidature with commentaire stores it in historique."""
        with app.app_context():
            update_candidature("acme-corp", {"statut": "relancee"}, commentaire="Service test")
            hist = load_historique("acme-corp")
            last = hist[-1]
            assert last["commentaire"] == "Service test"

    def test_historique_strips_whitespace_commentaire(self, app, data_dir):
        """Commentaire is stripped; whitespace-only becomes None."""
        with app.app_context():
            update_candidature("acme-corp", {"statut": "relancee"}, commentaire="  spaces  ")
            hist = load_historique("acme-corp")
            last = hist[-1]
            assert last["commentaire"] == "spaces"

            # Whitespace-only should be None
            update_candidature("acme-corp", {"statut": "sans-reponse"}, commentaire="   ")
            hist2 = load_historique("acme-corp")
            last2 = hist2[-1]
            assert last2["commentaire"] is None

    def test_cascade_delete_removes_historique(self, app, data_dir):
        """Deleting a candidature cascades to its historique entries."""
        with app.app_context():
            from services.candidature import delete_candidature

            delete_candidature("gamma-sa")
            entries = HistoriqueStatut.query.filter_by(slug="gamma-sa").all()
            assert len(entries) == 0
