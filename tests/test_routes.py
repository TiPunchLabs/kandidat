"""Tests for Flask routes: dashboard, detail, update, create, cibles, search, fichiers."""

import io
from pathlib import Path

# ---------------------------------------------------------------------------
# GET / (Dashboard)
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_status(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_dashboard_shows_candidatures(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert "ACME Corp" in html
        assert "Beta Inc" in html
        assert "Gamma SA" in html

    def test_dashboard_excludes_empty_dir(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert "empty-dir" not in html

    def test_dashboard_shows_categorie_filter(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert "filter-categorie" in html

    def test_dashboard_shows_categorie_data(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert 'data-categorie="entreprise"' in html


# ---------------------------------------------------------------------------
# GET /candidature/<slug> (Detail)
# ---------------------------------------------------------------------------


class TestDetail:
    def test_detail_status(self, client):
        resp = client.get("/candidature/acme-corp")
        assert resp.status_code == 200

    def test_detail_shows_info(self, client):
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert "ACME Corp" in html
        assert "DevOps Engineer" in html

    def test_detail_shows_files(self, client):
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert "offre.md" in html
        assert "lm.md" in html

    def test_detail_404_nonexistent(self, client):
        resp = client.get("/candidature/nonexistent")
        assert resp.status_code == 404

    def test_detail_shows_historique(self, client):
        """Detail page shows the status history timeline."""
        resp = client.get("/candidature/gamma-sa")
        html = resp.data.decode()
        assert "Historique des statuts" in html
        assert "timeline" in html
        assert "brouillon" in html
        assert "entretien" in html

    def test_detail_shows_commentaire_indicator(self, client, app):
        """Detail page shows comment indicator when historique has commentaire."""
        # Change status with a commentaire
        client.post(
            "/candidature/acme-corp/update",
            data={"statut": "relancee", "commentaire": "Relance par email"},
        )
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert "timeline-comment-indicator" in html

    def test_detail_contenu_card_always_visible(self, client):
        """Detail page always shows the Contenu card with inline editor."""
        resp = client.get("/candidature/beta-inc")
        html = resp.data.decode()
        assert 'id="contenu-card"' in html
        assert 'id="contenu-display"' in html
        assert 'id="contenu-editor"' in html

    def test_detail_contenu_card_with_content(self, client, app):
        """Detail page includes raw contenu in the inline editor textarea."""
        with app.app_context():
            from services.candidature import update_candidature

            update_candidature("acme-corp", {"contenu": "**Important** notes"})
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert 'id="contenu-card"' in html
        assert "**Important** notes" in html

    def test_detail_contenu_inline_editor(self, client):
        """Detail page shows the inline contenu editor elements."""
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert 'id="contenu-display"' in html
        assert 'id="contenu-editor"' in html

    def test_detail_historique_has_commentaire_html(self, client, app):
        """Timeline items include data-commentaire-html attribute."""
        # Add a comment with markdown
        client.post(
            "/candidature/acme-corp/update",
            data={"statut": "relancee", "commentaire": "**test**"},
        )
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert "data-commentaire-html=" in html

    def test_detail_has_separate_commentaire_card(self, client):
        """Detail page has a separate commentaire card (hidden by default)."""
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert 'id="commentaire-card"' in html
        assert 'id="commentaire-card-body"' in html


# ---------------------------------------------------------------------------
# POST /candidature/<slug>/update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_update_redirects(self, client):
        resp = client.post(
            "/candidature/acme-corp/update",
            data={
                "statut": "relancee",
            },
        )
        assert resp.status_code == 302
        assert "/candidature/acme-corp" in resp.headers["Location"]

    def test_update_changes_statut(self, client, app, data_dir):
        client.post(
            "/candidature/acme-corp/update",
            data={
                "statut": "relancee",
            },
        )
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("acme-corp")
            assert c["statut"] == "relancee"

    def test_update_invalid_statut(self, client):
        resp = client.post(
            "/candidature/acme-corp/update",
            data={
                "statut": "invalid",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "invalide" in html.lower()

    def test_update_404_nonexistent(self, client):
        resp = client.post(
            "/candidature/nonexistent/update",
            data={
                "statut": "envoyee",
            },
        )
        assert resp.status_code == 404

    def test_update_categorie(self, client, app, data_dir):
        client.post(
            "/candidature/acme-corp/update",
            data={
                "categorie_entreprise": "esn",
            },
        )
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("acme-corp")
            assert c["categorie_entreprise"] == "esn"

    def test_update_invalid_categorie(self, client):
        resp = client.post(
            "/candidature/acme-corp/update",
            data={
                "categorie_entreprise": "invalid",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "invalide" in html.lower()

    def test_update_statut_with_commentaire(self, client, app):
        """POST with statut change and commentaire saves the commentaire in historique."""
        client.post(
            "/candidature/acme-corp/update",
            data={"statut": "relancee", "commentaire": "Test commentaire"},
        )
        with app.app_context():
            from services.candidature import load_historique

            hist = load_historique("acme-corp")
            last = hist[-1]
            assert last["nouveau_statut"] == "relancee"
            assert last["commentaire"] == "Test commentaire"

    def test_update_statut_without_commentaire(self, client, app):
        """POST with statut change and no commentaire stores None (non-regression)."""
        client.post(
            "/candidature/acme-corp/update",
            data={"statut": "relancee"},
        )
        with app.app_context():
            from services.candidature import load_historique

            hist = load_historique("acme-corp")
            last = hist[-1]
            assert last["nouveau_statut"] == "relancee"
            assert last["commentaire"] is None

    def test_update_no_statut_change_ignores_commentaire(self, client, app):
        """POST without statut change does not create new historique even with commentaire."""
        with app.app_context():
            from services.candidature import load_historique

            before_count = len(load_historique("acme-corp"))

        client.post(
            "/candidature/acme-corp/update",
            data={"priorite": "haute", "commentaire": "Should be ignored"},
        )
        with app.app_context():
            from services.candidature import load_historique

            after_count = len(load_historique("acme-corp"))
            assert after_count == before_count

    def test_update_date(self, client, app, data_dir):
        client.post(
            "/candidature/acme-corp/update",
            data={
                "date_relance": "2025-11-01",
            },
        )
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("acme-corp")
            assert c["date_relance"] == "2025-11-01"


# ---------------------------------------------------------------------------
# GET /candidature/new
# ---------------------------------------------------------------------------


class TestCreateForm:
    def test_create_form_status(self, client):
        resp = client.get("/candidature/new")
        assert resp.status_code == 200

    def test_create_form_has_fields(self, client):
        resp = client.get("/candidature/new")
        html = resp.data.decode()
        assert "entreprise" in html.lower()

    def test_create_form_has_cible_dropdown(self, client):
        resp = client.get("/candidature/new")
        html = resp.data.decode()
        assert "cible_id" in html
        assert "Orange Caraibe" in html
        assert "Sopra Steria" in html

    def test_create_form_without_cible_id(self, client):
        """GET /candidature/new without cible_id shows the cible dropdown (non-regression)."""
        resp = client.get("/candidature/new")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "<select" in html
        assert "Choisir une cible" in html

    def test_create_form_with_valid_cible_id(self, client):
        """GET /candidature/new?cible_id=4 pre-fills entreprise and locks cible."""
        resp = client.get("/candidature/new?cible_id=4")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Orange Caraibe" in html
        assert 'type="hidden"' in html
        assert 'value="4"' in html

    def test_create_form_with_invalid_cible_id(self, client):
        """GET /candidature/new?cible_id=999 redirects with error."""
        resp = client.get("/candidature/new?cible_id=999")
        assert resp.status_code == 302
        assert "/cibles" in resp.headers["Location"]

    def test_create_form_with_non_integer_cible_id(self, client):
        """GET /candidature/new?cible_id=abc redirects with error."""
        resp = client.get("/candidature/new?cible_id=abc")
        assert resp.status_code == 302
        assert "/cibles" in resp.headers["Location"]

    def test_create_form_has_breadcrumb(self, client):
        """Create form has a breadcrumb for navigation consistency."""
        resp = client.get("/candidature/new")
        html = resp.data.decode()
        assert "breadcrumb" in html
        assert "Dashboard" in html

    def test_create_form_has_contenu_textarea(self, client):
        """Create form has a contenu textarea for markdown content."""
        resp = client.get("/candidature/new")
        html = resp.data.decode()
        assert 'name="contenu"' in html

    def test_create_form_has_page_header(self, client):
        """Create form uses page-header for design consistency."""
        resp = client.get("/candidature/new")
        html = resp.data.decode()
        assert "page-header" in html


# ---------------------------------------------------------------------------
# POST /candidature/new
# ---------------------------------------------------------------------------


class TestCreateSubmit:
    def test_create_redirects(self, client):
        resp = client.post(
            "/candidature/new",
            data={
                "entreprise": "New Corp",
                "poste": "SRE",
                "type": "offre",
                "priorite": "haute",
                "cible_id": "4",
            },
        )
        assert resp.status_code == 302
        assert "/candidature/new-corp" in resp.headers["Location"]

    def test_create_persists(self, client, app, data_dir):
        client.post(
            "/candidature/new",
            data={
                "entreprise": "Persist Corp",
                "type": "spontanee",
                "priorite": "moyenne",
                "cible_id": "4",
            },
        )
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("persist-corp")
            assert c is not None
            assert c["entreprise"] == "Persist Corp"
            assert c["type"] == "spontanee"
            assert c["statut"] == "brouillon"

    def test_create_with_contenu(self, client, app, data_dir):
        """POST with contenu saves the markdown content."""
        client.post(
            "/candidature/new",
            data={
                "entreprise": "Contenu Corp",
                "type": "offre",
                "priorite": "moyenne",
                "cible_id": "4",
                "contenu": "# Notes\n\nImportant info",
            },
        )
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("contenu-corp")
            assert c is not None
            assert c["contenu"] == "# Notes\n\nImportant info"

    def test_create_derives_categorie_from_cible(self, client, app, data_dir):
        """categorie_entreprise is derived from the cible, not from form data."""
        client.post(
            "/candidature/new",
            data={
                "entreprise": "Cat Route Corp",
                "type": "offre",
                "priorite": "moyenne",
                "cible_id": "7",  # Alpha Conseil (cabinets) -> cabinet
            },
        )
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("cat-route-corp")
            assert c is not None
            assert c["categorie_entreprise"] == "cabinet"

    def test_create_missing_entreprise(self, client):
        resp = client.post(
            "/candidature/new",
            data={
                "entreprise": "",
                "type": "offre",
                "priorite": "haute",
                "cible_id": "4",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "requis" in html.lower()

    def test_create_missing_cible(self, client):
        """Missing cible_id redirects with error."""
        resp = client.post(
            "/candidature/new",
            data={
                "entreprise": "No Cible Corp",
                "type": "offre",
                "priorite": "haute",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "cible" in html.lower()

    def test_create_submit_from_cible(self, client, app):
        """POST with cible_id creates candidature linked to the correct cible."""
        resp = client.post(
            "/candidature/new",
            data={
                "entreprise": "Orange Caraibe",
                "type": "spontanee",
                "priorite": "haute",
                "cible_id": "4",
            },
        )
        assert resp.status_code == 302
        assert "/candidature/orange-caraibe" in resp.headers["Location"]
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("orange-caraibe")
            assert c is not None
            assert c["entreprise"] == "Orange Caraibe"
            assert c["cible_id"] == 4

    def test_create_submit_error_preserves_cible_id(self, client):
        """POST with cible_id but empty entreprise preserves cible_id in redirect."""
        resp = client.post(
            "/candidature/new",
            data={
                "entreprise": "",
                "type": "offre",
                "priorite": "haute",
                "cible_id": "4",
            },
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "/candidature/new" in location
        assert "cible_id=4" in location

    def test_create_duplicate(self, client):
        # First create
        client.post(
            "/candidature/new",
            data={
                "entreprise": "Dup Corp",
                "type": "offre",
                "priorite": "haute",
                "cible_id": "4",
            },
        )
        # Second create with same name
        resp = client.post(
            "/candidature/new",
            data={
                "entreprise": "Dup Corp",
                "type": "offre",
                "priorite": "haute",
                "cible_id": "4",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "existe deja" in html.lower()


# ---------------------------------------------------------------------------
# Fiche cible + Contacts
# ---------------------------------------------------------------------------


class TestCibleDetail:
    def test_cible_detail_status(self, client):
        resp = client.get("/cible/4")
        assert resp.status_code == 200

    def test_cible_detail_shows_info(self, client):
        resp = client.get("/cible/4")
        html = resp.data.decode()
        assert "Orange Caraibe" in html

    def test_cible_detail_shows_contacts(self, client):
        resp = client.get("/cible/4")
        html = resp.data.decode()
        assert "Jean" in html
        assert "Dupont" in html
        assert "Marie" in html

    def test_cible_detail_shows_candidatures(self, client):
        resp = client.get("/cible/4")
        html = resp.data.decode()
        assert "ACME Corp" in html

    def test_cible_detail_404(self, client):
        resp = client.get("/cible/9999")
        assert resp.status_code == 404

    def test_cible_detail_shows_inscription_badge_for_cabinet(self, client):
        resp = client.get("/cible/7")  # Alpha Conseil (cabinet)
        assert resp.status_code == 200
        assert b"Inscription plateforme" in resp.data
        assert b"Non inscrit" in resp.data

    def test_cible_detail_hides_inscription_badge_for_non_cabinet(self, client):
        resp = client.get("/cible/4")  # Orange Caraibe (entreprise)
        assert resp.status_code == 200
        assert b"Inscription plateforme" not in resp.data


class TestCibleEdit:
    def test_edit_cible_from_detail(self, client, app):
        resp = client.post(
            "/cible/4/edit",
            data={"nom": "Orange Caraibe Modifie", "description": "Nouvelle description"},
        )
        assert resp.status_code == 302
        assert "/cible/4" in resp.headers["Location"]
        with app.app_context():
            from services.database import Cible, db

            cible = db.session.get(Cible, 4)
            assert cible.nom == "Orange Caraibe Modifie"
            assert cible.description == "Nouvelle description"

    def test_edit_cible_404(self, client):
        resp = client.post("/cible/9999/edit", data={"nom": "Test"})
        assert resp.status_code == 404

    def test_delete_cible_from_detail(self, client):
        resp = client.post("/cible/1/delete")
        assert resp.status_code == 302
        assert "/cibles" in resp.headers["Location"]

    def test_delete_cible_404(self, client):
        resp = client.post("/cible/9999/delete")
        assert resp.status_code == 404


class TestContactCRUD:
    def test_add_contact(self, client, app):
        resp = client.post(
            "/cible/4/contact/add",
            data={"nom": "Nouveau", "prenom": "Contact", "email": "new@test.com", "fonction": "Manager"},
        )
        assert resp.status_code == 302
        assert "/cible/4" in resp.headers["Location"]
        # Verify in DB
        with app.app_context():
            from services.database import Contact

            c = Contact.query.filter_by(nom="Nouveau").first()
            assert c is not None
            assert c.prenom == "Contact"
            assert c.email == "new@test.com"

    def test_add_contact_missing_nom(self, client):
        resp = client.post(
            "/cible/4/contact/add",
            data={"nom": "", "prenom": "Test"},
            follow_redirects=True,
        )
        html = resp.data.decode()
        assert "requis" in html.lower()

    def test_add_contact_cible_404(self, client):
        resp = client.post("/cible/9999/contact/add", data={"nom": "Test"})
        assert resp.status_code == 404

    def test_edit_contact(self, client, app):
        resp = client.post(
            "/cible/4/contact/1/edit",
            data={"fonction": "Directeur"},
        )
        assert resp.status_code == 302
        with app.app_context():
            from services.database import Contact, db

            c = db.session.get(Contact, 1)
            assert c.fonction == "Directeur"

    def test_edit_contact_404(self, client):
        resp = client.post("/cible/4/contact/9999/edit", data={"nom": "Test"})
        assert resp.status_code == 404

    def test_delete_contact(self, client, app):
        resp = client.post("/cible/4/contact/1/delete")
        assert resp.status_code == 302
        with app.app_context():
            from services.database import Contact, db

            c = db.session.get(Contact, 1)
            assert c is None

    def test_delete_contact_404(self, client):
        resp = client.post("/cible/4/contact/9999/delete")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_stats_status(self, client):
        resp = client.get("/stats")
        assert resp.status_code == 200

    def test_stats_shows_categorie(self, client):
        resp = client.get("/stats")
        html = resp.data.decode()
        assert "Par categorie" in html

    def test_stats_shows_categorie_values(self, client):
        resp = client.get("/stats")
        html = resp.data.decode()
        assert "entreprise" in html
        assert "esn" in html
        assert "cabinet" in html


# ---------------------------------------------------------------------------
# GET /cibles
# ---------------------------------------------------------------------------


class TestCibles:
    def test_cibles_status(self, client):
        resp = client.get("/cibles")
        assert resp.status_code == 200

    def test_cibles_shows_companies(self, client):
        resp = client.get("/cibles")
        html = resp.data.decode()
        assert "Groupe GBH" in html
        assert "Orange Caraibe" in html
        assert "Alpha Conseil" in html


# ---------------------------------------------------------------------------
# POST /cibles/toggle
# ---------------------------------------------------------------------------


class TestCiblesToggle:
    def test_toggle_success(self, client):
        # Groupe GBH has cible_id=1
        resp = client.post(
            "/cibles/toggle",
            data={
                "cible_id": "1",
                "checked": "true",
            },
        )
        assert resp.status_code == 200
        assert resp.json["ok"] is True

    def test_toggle_missing_cible_id(self, client):
        resp = client.post(
            "/cibles/toggle",
            data={
                "checked": "true",
            },
        )
        assert resp.status_code == 400

    def test_toggle_unknown_cible_id(self, client):
        resp = client.post(
            "/cibles/toggle",
            data={
                "cible_id": "9999",
                "checked": "true",
            },
        )
        assert resp.status_code == 404

    def test_toggle_locked_by_candidature(self, client):
        """Cannot uncheck a cible that has linked candidatures."""
        # Orange Caraibe (cible_id=4) is linked to acme-corp
        resp = client.post(
            "/cibles/toggle",
            data={
                "cible_id": "4",
                "checked": "false",
            },
        )
        assert resp.status_code == 409
        assert "verrouillee" in resp.json["error"]


# ---------------------------------------------------------------------------
# GET /search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_status(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200

    def test_search_no_query(self, client):
        resp = client.get("/search")
        html = resp.data.decode()
        assert "Recherche" in html

    def test_search_with_results(self, client):
        resp = client.get("/search?q=ACME")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "acme-corp" in html

    def test_search_no_results(self, client):
        resp = client.get("/search?q=zzzznonexistentzzzz")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Aucun resultat" in html


# ---------------------------------------------------------------------------
# Fichiers: view, upload, delete, download
# ---------------------------------------------------------------------------


class TestFichiers:
    def test_fichier_view_markdown(self, client):
        """Markdown files are rendered as HTML."""
        resp = client.get("/candidature/acme-corp/fichier/offre.md")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Offre DevOps" in html

    def test_fichier_view_subdir(self, client):
        """Files in subdirectories are accessible via path: parameter."""
        resp = client.get("/candidature/acme-corp/fichier/coaching/phase1.md")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Phase 1" in html

    def test_fichier_download(self, client):
        """Binary files can be downloaded."""
        resp = client.get("/candidature/acme-corp/fichier/contrat.pdf/download")
        assert resp.status_code == 200
        assert b"%PDF" in resp.data
        assert "attachment" in resp.headers.get("Content-Disposition", "")

    def test_fichier_upload(self, client, app, data_dir):
        """Upload a file and verify it appears in DB and on disk."""
        file_data = (io.BytesIO(b"# New File\n\nContent"), "nouveau.md")
        resp = client.post(
            "/candidature/acme-corp/upload",
            data={"file": file_data},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "nouveau.md" in html

        # Verify file on disk
        uploaded = Path(data_dir) / "candidatures" / "acme-corp" / "nouveau.md"
        assert uploaded.is_file()
        assert uploaded.read_text(encoding="utf-8") == "# New File\n\nContent"

        # Verify DB entry
        with app.app_context():
            from services.database import Fichier

            f = Fichier.query.filter_by(slug="acme-corp", nom="nouveau.md").first()
            assert f is not None
            assert f.type == "markdown"

    def test_fichier_upload_invalid_ext(self, client):
        """Uploading a file with a disallowed extension is rejected."""
        file_data = (io.BytesIO(b"malicious"), "virus.exe")
        resp = client.post(
            "/candidature/acme-corp/upload",
            data={"file": file_data},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "non autorisee" in html

    def test_fichier_delete(self, client, app, data_dir):
        """Deleting a file removes it from DB and disk."""
        # Verify file exists before
        file_path = Path(data_dir) / "candidatures" / "acme-corp" / "contrat.pdf"
        assert file_path.is_file()

        resp = client.post(
            "/candidature/acme-corp/fichier/contrat.pdf/delete",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "supprime" in html.lower()

        # Verify file removed from disk
        assert not file_path.is_file()

        # Verify DB entry removed
        with app.app_context():
            from services.database import Fichier

            f = Fichier.query.filter_by(slug="acme-corp", nom="contrat.pdf").first()
            assert f is None

    def test_fichier_404(self, client):
        """Requesting a non-existent file returns 404."""
        resp = client.get("/candidature/acme-corp/fichier/inexistant.md")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /candidature/<slug>/delete
# ---------------------------------------------------------------------------


class TestCandidatureDelete:
    def test_delete_redirects_to_dashboard(self, client):
        resp = client.post("/candidature/beta-inc/delete")
        assert resp.status_code == 302
        assert "/" == resp.headers["Location"] or "dashboard" in resp.headers["Location"].lower()

    def test_delete_removes_from_db(self, client, app):
        client.post("/candidature/beta-inc/delete")
        with app.app_context():
            from services.candidature import load_candidature

            assert load_candidature("beta-inc") is None

    def test_delete_removes_files_from_disk(self, client, data_dir):
        client.post("/candidature/acme-corp/delete")
        assert not (data_dir / "candidatures" / "acme-corp").exists()

    def test_delete_404_nonexistent(self, client):
        resp = client.post("/candidature/nonexistent/delete")
        assert resp.status_code == 404

    def test_delete_flash_message(self, client):
        resp = client.post("/candidature/beta-inc/delete", follow_redirects=True)
        html = resp.data.decode()
        assert "supprimee" in html.lower()


# ---------------------------------------------------------------------------
# POST /candidature/<slug>/archive
# ---------------------------------------------------------------------------


class TestCandidatureArchive:
    def test_archive_redirects_to_dashboard(self, client):
        resp = client.post("/candidature/acme-corp/archive")
        assert resp.status_code == 302

    def test_archive_changes_statut(self, client, app):
        client.post("/candidature/acme-corp/archive")
        with app.app_context():
            from services.candidature import load_candidature

            c = load_candidature("acme-corp")
            assert c["statut"] == "archivee"

    def test_archive_preserves_files(self, client, data_dir):
        client.post("/candidature/acme-corp/archive")
        assert (data_dir / "candidatures" / "acme-corp" / "offre.md").is_file()

    def test_archive_404_nonexistent(self, client):
        resp = client.post("/candidature/nonexistent/archive")
        assert resp.status_code == 404

    def test_archive_flash_message(self, client):
        resp = client.post("/candidature/acme-corp/archive", follow_redirects=True)
        html = resp.data.decode()
        assert "archivee" in html.lower()

    def test_dashboard_includes_archived_in_dom(self, client):
        """Archived candidatures are present in the DOM (hidden client-side by JS)."""
        client.post("/candidature/acme-corp/archive")
        resp = client.get("/")
        html = resp.data.decode()
        # Row is in the HTML so JS can show it when filtering by "archivee"
        assert 'data-statut="archivee"' in html
