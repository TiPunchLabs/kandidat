"""Tests for the REST API endpoints."""

import io
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Candidatures CRUD
# ──────────────────────────────────────────────────────────────


class TestListCandidatures:
    def test_list_all(self, client):
        r = client.get("/api/candidatures")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) == 3
        slugs = [c["slug"] for c in data]
        assert "acme-corp" in slugs

    def test_filter_by_statut(self, client):
        r = client.get("/api/candidatures?statut=envoyee")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) == 1
        assert data[0]["slug"] == "acme-corp"

    def test_filter_by_type(self, client):
        r = client.get("/api/candidatures?type=spontanee")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) == 1
        assert data[0]["slug"] == "beta-inc"

    def test_filter_by_priorite(self, client):
        r = client.get("/api/candidatures?priorite=haute")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) == 2

    def test_filter_by_categorie(self, client):
        r = client.get("/api/candidatures?categorie=cabinet")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) == 1
        assert data[0]["slug"] == "gamma-sa"

    def test_filter_invalid_statut(self, client):
        r = client.get("/api/candidatures?statut=invalide")
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_filter_no_results(self, client):
        r = client.get("/api/candidatures?statut=acceptee")
        assert r.status_code == 200
        assert r.get_json()["data"] == []


class TestGetCandidature:
    def test_get_existing(self, client):
        r = client.get("/api/candidatures/acme-corp")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["entreprise"] == "ACME Corp"
        assert data["slug"] == "acme-corp"
        assert len(data["fichiers"]) == 4

    def test_get_includes_cible(self, client):
        r = client.get("/api/candidatures/acme-corp")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["cible_id"] == 4
        assert data["cible"]["nom"] == "Orange Caraibe"
        assert data["cible"]["categorie"] == "entreprises"

    def test_get_not_found(self, client):
        r = client.get("/api/candidatures/inexistant")
        assert r.status_code == 404
        assert "error" in r.get_json()


class TestCreateCandidature:
    def test_create_basic(self, client, app):
        r = client.post(
            "/api/candidatures",
            json={"entreprise": "Nouvelle Corp", "poste": "SRE", "cible_id": 4},
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["slug"] == "nouvelle-corp"
        assert data["entreprise"] == "Nouvelle Corp"
        assert data["statut"] == "brouillon"
        assert data["cible_id"] == 4
        assert data["cible"]["nom"] == "Orange Caraibe"

    def test_create_with_contenu(self, client, app):
        r = client.post(
            "/api/candidatures",
            json={"entreprise": "Contenu API Corp", "cible_id": 4, "contenu": "# API Notes"},
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["contenu"] == "# API Notes"

    def test_create_missing_entreprise(self, client):
        r = client.post("/api/candidatures", json={"poste": "SRE", "cible_id": 4})
        assert r.status_code == 400

    def test_create_missing_cible_id(self, client):
        r = client.post("/api/candidatures", json={"entreprise": "No Cible Corp"})
        assert r.status_code == 400

    def test_create_invalid_cible(self, client):
        r = client.post("/api/candidatures", json={"entreprise": "Bad Cible Corp", "cible_id": 9999})
        assert r.status_code == 400
        assert "not found" in r.get_json()["error"]

    def test_create_empty_body(self, client):
        r = client.post("/api/candidatures", content_type="application/json")
        assert r.status_code == 400

    def test_create_duplicate(self, client):
        r = client.post("/api/candidatures", json={"entreprise": "ACME Corp", "cible_id": 4})
        assert r.status_code == 400
        assert "exists" in r.get_json()["error"]


class TestUpdateCandidature:
    def test_update_statut(self, client):
        # acme-corp is "envoyee", valid transition -> "relancee"
        r = client.put(
            "/api/candidatures/acme-corp",
            json={"statut": "relancee"},
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["statut"] == "relancee"

    def test_update_invalid_transition(self, client):
        # acme-corp is "envoyee", cannot go to "acceptee"
        r = client.put(
            "/api/candidatures/acme-corp",
            json={"statut": "acceptee"},
        )
        assert r.status_code == 400
        assert "Transition" in r.get_json()["error"]

    def test_update_priorite(self, client):
        r = client.put(
            "/api/candidatures/beta-inc",
            json={"priorite": "haute"},
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["priorite"] == "haute"

    def test_update_not_found(self, client):
        r = client.put("/api/candidatures/inexistant", json={"priorite": "haute"})
        assert r.status_code == 404

    def test_update_empty_body(self, client):
        r = client.put(
            "/api/candidatures/acme-corp",
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_update_no_fields(self, client):
        r = client.put("/api/candidatures/acme-corp", json={})
        assert r.status_code == 400

    def test_update_contenu(self, client):
        r = client.put(
            "/api/candidatures/acme-corp",
            json={"contenu": "# Notes\n\nUpdated via API"},
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["contenu"] == "# Notes\n\nUpdated via API"

    def test_update_contenu_empty(self, client):
        r = client.put(
            "/api/candidatures/acme-corp",
            json={"contenu": ""},
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["contenu"] == ""


class TestDeleteCandidature:
    def test_delete_existing(self, client):
        r = client.delete("/api/candidatures/beta-inc")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["deleted"] is True
        # Verify it's gone
        r2 = client.get("/api/candidatures/beta-inc")
        assert r2.status_code == 404

    def test_delete_removes_files_from_disk(self, client, data_dir):
        r = client.delete("/api/candidatures/acme-corp")
        assert r.status_code == 200
        assert not (data_dir / "candidatures" / "acme-corp").exists()

    def test_delete_not_found(self, client):
        r = client.delete("/api/candidatures/inexistant")
        assert r.status_code == 404


class TestHistoriqueAPI:
    def test_get_historique_200(self, client):
        """GET /api/candidatures/<slug>/historique returns history."""
        r = client.get("/api/candidatures/gamma-sa/historique")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) == 4
        assert data[0]["ancien_statut"] is None
        assert data[0]["nouveau_statut"] == "brouillon"
        assert data[-1]["nouveau_statut"] == "entretien"

    def test_get_historique_404(self, client):
        """GET /api/candidatures/<slug>/historique returns 404 for unknown slug."""
        r = client.get("/api/candidatures/inexistant/historique")
        assert r.status_code == 404

    def test_put_statut_creates_historique_entry(self, client):
        """PUT statut change creates a new historique entry."""
        # acme-corp: envoyee -> relancee
        client.put("/api/candidatures/acme-corp", json={"statut": "relancee"})
        r = client.get("/api/candidatures/acme-corp/historique")
        data = r.get_json()["data"]
        last = data[-1]
        assert last["ancien_statut"] == "envoyee"
        assert last["nouveau_statut"] == "relancee"


class TestPatchHistorique:
    def test_api_patch_historique_commentaire(self, client):
        """PATCH updates commentaire and returns correct data."""
        # Get first historique entry id for acme-corp
        r = client.get("/api/candidatures/acme-corp/historique")
        entries = r.get_json()["data"]
        entry_id = entries[0]["id"]

        r = client.patch(
            f"/api/candidatures/acme-corp/historique/{entry_id}",
            json={"commentaire": "API test"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["commentaire"] == "API test"
        assert data["id"] == entry_id

        # Verify via GET
        r2 = client.get("/api/candidatures/acme-corp/historique")
        entry = next(e for e in r2.get_json()["data"] if e["id"] == entry_id)
        assert entry["commentaire"] == "API test"

    def test_api_patch_historique_not_found(self, client):
        """PATCH returns 404 for unknown historique_id or unknown slug."""
        r = client.patch(
            "/api/candidatures/acme-corp/historique/99999",
            json={"commentaire": "test"},
        )
        assert r.status_code == 404

        r2 = client.patch(
            "/api/candidatures/nonexistent/historique/1",
            json={"commentaire": "test"},
        )
        assert r2.status_code == 404

    def test_api_patch_historique_too_long(self, client):
        """PATCH returns 400 for commentaire > 1000 chars."""
        r = client.get("/api/candidatures/acme-corp/historique")
        entry_id = r.get_json()["data"][0]["id"]

        r = client.patch(
            f"/api/candidatures/acme-corp/historique/{entry_id}",
            json={"commentaire": "x" * 1001},
        )
        assert r.status_code == 400
        assert "1000" in r.get_json()["error"]

    def test_api_patch_historique_no_body(self, client):
        """PATCH without JSON body returns 400."""
        r = client.get("/api/candidatures/acme-corp/historique")
        entry_id = r.get_json()["data"][0]["id"]

        r = client.patch(
            f"/api/candidatures/acme-corp/historique/{entry_id}",
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_api_patch_historique_whitespace_becomes_null(self, client):
        """PATCH with whitespace-only commentaire stores NULL."""
        r = client.get("/api/candidatures/acme-corp/historique")
        entry_id = r.get_json()["data"][0]["id"]

        r = client.patch(
            f"/api/candidatures/acme-corp/historique/{entry_id}",
            json={"commentaire": "   "},
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["commentaire"] is None

    def test_api_get_historique_includes_commentaire(self, client):
        """GET historique returns entries with commentaire field (non-regression)."""
        r = client.get("/api/candidatures/acme-corp/historique")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) >= 1
        # All entries should have the commentaire key
        for entry in data:
            assert "commentaire" in entry

    def test_api_get_historique_includes_commentaire_html(self, client):
        """GET historique returns commentaire_html for each entry."""
        # First set a commentaire with markdown
        r = client.get("/api/candidatures/acme-corp/historique")
        entry_id = r.get_json()["data"][0]["id"]
        client.patch(
            f"/api/candidatures/acme-corp/historique/{entry_id}",
            json={"commentaire": "**bold** text"},
        )

        r = client.get("/api/candidatures/acme-corp/historique")
        data = r.get_json()["data"]
        entry = next(e for e in data if e["id"] == entry_id)
        assert "commentaire_html" in entry
        assert "<strong>bold</strong>" in entry["commentaire_html"]

    def test_api_get_historique_null_commentaire_html(self, client):
        """GET historique returns null commentaire_html when commentaire is None."""
        r = client.get("/api/candidatures/acme-corp/historique")
        data = r.get_json()["data"]
        # Initial entry has no commentaire
        entry = data[0]
        assert entry["commentaire_html"] is None

    def test_api_patch_historique_returns_commentaire_html(self, client):
        """PATCH returns commentaire_html with rendered markdown."""
        r = client.get("/api/candidatures/acme-corp/historique")
        entry_id = r.get_json()["data"][0]["id"]

        r = client.patch(
            f"/api/candidatures/acme-corp/historique/{entry_id}",
            json={"commentaire": "**test** markdown"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "commentaire_html" in data
        assert "<strong>test</strong>" in data["commentaire_html"]

    def test_api_patch_historique_null_commentaire_html(self, client):
        """PATCH with empty commentaire returns null commentaire_html."""
        r = client.get("/api/candidatures/acme-corp/historique")
        entry_id = r.get_json()["data"][0]["id"]

        r = client.patch(
            f"/api/candidatures/acme-corp/historique/{entry_id}",
            json={"commentaire": ""},
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["commentaire_html"] is None


class TestArchiveCandidature:
    def test_archive_via_update(self, client):
        """Archiving is done via PUT with statut=archivee."""
        r = client.put("/api/candidatures/acme-corp", json={"statut": "archivee"})
        assert r.status_code == 200
        assert r.get_json()["data"]["statut"] == "archivee"

    def test_archive_terminal(self, client):
        """An archived candidature cannot transition to another status."""
        client.put("/api/candidatures/acme-corp", json={"statut": "archivee"})
        r = client.put("/api/candidatures/acme-corp", json={"statut": "envoyee"})
        assert r.status_code == 400
        assert "Transition" in r.get_json()["error"]


# ──────────────────────────────────────────────────────────────
# Cibles
# ──────────────────────────────────────────────────────────────


class TestCibles:
    def test_list_cibles(self, client):
        r = client.get("/api/cibles")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "grands-groupes" in data
        assert "entreprises" in data
        assert "cabinets" in data
        assert len(data["grands-groupes"]) == 3
        assert len(data["entreprises"]) == 3
        assert len(data["cabinets"]) == 2

    def test_toggle_cible(self, client):
        r = client.post(
            "/api/cibles/4/toggle",
            json={"contactee": True},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["contactee"] is True

    def test_toggle_cible_not_found(self, client):
        r = client.post(
            "/api/cibles/9999/toggle",
            json={"contactee": True},
        )
        assert r.status_code == 404

    def test_toggle_cible_missing_contactee(self, client):
        r = client.post("/api/cibles/4/toggle", json={})
        assert r.status_code == 400

    def test_toggle_cible_no_body(self, client):
        r = client.post("/api/cibles/4/toggle", content_type="application/json")
        assert r.status_code == 400

    def test_toggle_locked_by_candidature(self, client):
        """Cannot uncheck a cible that has linked candidatures."""
        r = client.post("/api/cibles/4/toggle", json={"contactee": False})
        assert r.status_code == 409
        assert "verrouillee" in r.get_json()["error"]

    def test_cible_unchecked_after_last_candidature_deleted(self, client, app):
        """Cible is auto-unchecked when its last candidature is deleted."""
        # Orange Caraibe (cible_id=4) is linked to acme-corp only
        client.delete("/api/candidatures/acme-corp")
        with app.app_context():
            from services.database import Cible, db

            cible = db.session.get(Cible, 4)
            assert cible.contactee == 0

    def test_delete_cible_cascades_candidatures(self, client, app, data_dir):
        """Deleting a cible cascades to its linked candidatures and files."""
        # cible_id=4 (Orange Caraibe) is linked to acme-corp
        r = client.delete("/api/cibles/4")
        assert r.status_code == 200
        assert r.get_json()["data"]["deleted"] is True

        # Candidature acme-corp should be gone
        r2 = client.get("/api/candidatures/acme-corp")
        assert r2.status_code == 404

        # Files on disk should be removed
        assert not (data_dir / "candidatures" / "acme-corp").exists()

    def test_cible_response_includes_inscrit_plateforme(self, client):
        r = client.get("/api/cibles")
        data = r.get_json()["data"]
        cabinets = data["cabinets"]
        assert len(cabinets) > 0
        assert "inscrit_plateforme" in cabinets[0]
        assert cabinets[0]["inscrit_plateforme"] is False

    def test_create_cible_with_inscrit_plateforme(self, client):
        resp = client.post(
            "/api/cibles",
            json={
                "nom": "Test Cabinet",
                "categorie": "cabinets",
                "inscrit_plateforme": True,
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["inscrit_plateforme"] is True

    def test_update_cible_notes(self, client):
        r = client.put("/api/cibles/4", json={"notes": "## Test notes\n- item 1"})
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["notes"] == "## Test notes\n- item 1"

    def test_cible_detail_includes_notes(self, client):
        client.put("/api/cibles/4", json={"notes": "Some notes"})
        r = client.get("/api/cibles/4/detail")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["notes"] == "Some notes"

    def test_create_cible_with_notes(self, client):
        r = client.post("/api/cibles", json={"nom": "NotesCorp", "categorie": "entreprises", "notes": "Initial note"})
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["notes"] == "Initial note"


class TestCibleExportCSV:
    """Tests for GET /api/cibles/export."""

    def test_export_csv_valid_category(self, client):
        r = client.get("/api/cibles/export?categorie=entreprises")
        assert r.status_code == 200
        assert r.content_type == "text/csv; charset=utf-8"
        assert "cibles-entreprises.csv" in r.headers["Content-Disposition"]
        lines = r.data.decode("utf-8").strip().splitlines()
        assert lines[0] == "nom,url,email,linkedin,contactee,inscrit_plateforme"
        assert len(lines) == 4  # header + 3 entreprises

    def test_export_csv_boolean_values(self, client):
        r = client.get("/api/cibles/export?categorie=grands-groupes")
        lines = r.data.decode("utf-8").strip().splitlines()
        # Groupe SAFO is contactee=1 (position=1, second data row)
        assert "Oui" in lines[2]
        # Groupe GBH is contactee=0 (position=0, first data row)
        assert "Non" in lines[1]

    def test_export_csv_invalid_category(self, client):
        r = client.get("/api/cibles/export?categorie=invalid")
        assert r.status_code == 400

    def test_export_csv_missing_category(self, client):
        r = client.get("/api/cibles/export")
        assert r.status_code == 400

    def test_export_csv_empty_category(self, client):
        r = client.get("/api/cibles/export?categorie=organisations")
        assert r.status_code == 200
        lines = r.data.decode("utf-8").strip().splitlines()
        assert len(lines) == 1  # header only


class TestCibleInscriptionToggle:
    """Tests for POST /api/cibles/<id>/toggle-inscription."""

    def test_toggle_inscription_on(self, client):
        resp = client.post("/api/cibles/7/toggle-inscription")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["inscrit_plateforme"] is True

    def test_toggle_inscription_off(self, client):
        client.post("/api/cibles/7/toggle-inscription")
        resp = client.post("/api/cibles/7/toggle-inscription")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["inscrit_plateforme"] is False

    def test_toggle_inscription_non_cabinet_rejected(self, client):
        resp = client.post("/api/cibles/4/toggle-inscription")
        assert resp.status_code == 400
        assert "cabinets" in resp.get_json()["error"].lower()

    def test_toggle_inscription_not_found(self, client):
        resp = client.post("/api/cibles/999/toggle-inscription")
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────
# Cible Detail + Contacts API
# ──────────────────────────────────────────────────────────────


class TestCibleDetailAPI:
    def test_get_cible_detail(self, client):
        r = client.get("/api/cibles/4/detail")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["nom"] == "Orange Caraibe"
        assert len(data["contacts"]) == 2
        assert data["contacts"][0]["nom"] == "Dupont"
        assert len(data["candidatures"]) >= 1

    def test_get_cible_detail_404(self, client):
        r = client.get("/api/cibles/9999/detail")
        assert r.status_code == 404


class TestContactAPI:
    def test_create_contact(self, client):
        r = client.post(
            "/api/cibles/4/contacts",
            json={"nom": "APIContact", "prenom": "Test", "email": "api@test.com", "fonction": "Dev"},
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["nom"] == "APIContact"
        assert data["prenom"] == "Test"
        assert data["email"] == "api@test.com"

    def test_create_contact_missing_nom(self, client):
        r = client.post("/api/cibles/4/contacts", json={"prenom": "Test"})
        assert r.status_code == 400

    def test_create_contact_cible_404(self, client):
        r = client.post("/api/cibles/9999/contacts", json={"nom": "Test"})
        assert r.status_code == 404

    def test_create_contact_no_body(self, client):
        r = client.post("/api/cibles/4/contacts", content_type="application/json")
        assert r.status_code == 400

    def test_update_contact(self, client):
        r = client.put(
            "/api/cibles/4/contacts/1",
            json={"fonction": "CEO"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["fonction"] == "CEO"

    def test_update_contact_no_fields(self, client):
        r = client.put("/api/cibles/4/contacts/1", json={})
        assert r.status_code == 400

    def test_update_contact_404(self, client):
        r = client.put("/api/cibles/4/contacts/9999", json={"nom": "Test"})
        assert r.status_code == 404

    def test_delete_contact(self, client):
        r = client.delete("/api/cibles/4/contacts/1")
        assert r.status_code == 200
        assert r.get_json()["data"]["deleted"] is True
        # Verify gone
        r2 = client.delete("/api/cibles/4/contacts/1")
        assert r2.status_code == 404

    def test_delete_contact_404(self, client):
        r = client.delete("/api/cibles/4/contacts/9999")
        assert r.status_code == 404

    def test_update_contact_wrong_cible(self, client):
        """PUT returns 404 when contact does not belong to the given cible."""
        # Contact 1 (Jean Dupont) belongs to cible 4, not cible 7
        r = client.put("/api/cibles/7/contacts/1", json={"nom": "Hacked"})
        assert r.status_code == 404
        assert "error" in r.get_json()

    def test_delete_contact_wrong_cible(self, client):
        """DELETE returns 404 when contact does not belong to the given cible."""
        # Contact 1 (Jean Dupont) belongs to cible 4, not cible 7
        r = client.delete("/api/cibles/7/contacts/1")
        assert r.status_code == 404
        assert "error" in r.get_json()


# ──────────────────────────────────────────────────────────────
# Search
# ──────────────────────────────────────────────────────────────


class TestSearch:
    def test_search_db_content(self, client):
        r = client.get("/api/search?q=ACME")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) >= 1
        assert any(res["slug"] == "acme-corp" for res in data)

    def test_search_file_content(self, client):
        r = client.get("/api/search?q=DevOps")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) >= 1

    def test_search_missing_query(self, client):
        r = client.get("/api/search")
        assert r.status_code == 400

    def test_search_empty_query(self, client):
        r = client.get("/api/search?q=")
        assert r.status_code == 400

    def test_search_no_results(self, client):
        r = client.get("/api/search?q=zzzznotfound")
        assert r.status_code == 200
        assert r.get_json()["data"] == []


# ──────────────────────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────────────────────


class TestStats:
    def test_stats_structure(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["total"] == 3
        assert "by_statut" in data
        assert "by_type" in data
        assert "by_priorite" in data
        assert "by_categorie" in data
        assert "timeline" in data

    def test_stats_counts(self, client):
        r = client.get("/api/stats")
        data = r.get_json()["data"]
        assert data["by_statut"]["envoyee"] == 1
        assert data["by_statut"]["entretien"] == 1
        assert data["by_statut"]["brouillon"] == 1
        assert data["by_type"]["offre"] == 2
        assert data["by_type"]["spontanee"] == 1

    def test_stats_timeline(self, client):
        r = client.get("/api/stats")
        data = r.get_json()["data"]
        timeline = data["timeline"]
        # Only candidatures with date_candidature set
        assert len(timeline) == 2
        # Should be sorted by date
        assert timeline[0]["date_candidature"] <= timeline[1]["date_candidature"]


# ──────────────────────────────────────────────────────────────
# Dashboard regeneration
# ──────────────────────────────────────────────────────────────


class TestDashboardRegenerate:
    def test_regenerate(self, client, data_dir):
        r = client.post("/api/dashboard/regenerate")
        assert r.status_code == 200
        msg = r.get_json()["data"]["message"].lower()
        assert "regenerated" in msg or "success" in msg
        # Check file was created
        dashboard = data_dir / "00-Dashboard.md"
        assert dashboard.exists()


# ──────────────────────────────────────────────────────────────
# Fichiers API
# ──────────────────────────────────────────────────────────────


class TestFichiersAPI:
    def test_upload_fichier(self, client, app, data_dir):
        """POST /api/candidatures/<slug>/fichiers uploads a file."""
        file_data = (io.BytesIO(b"# API Upload\n\nContent"), "api-upload.md")
        r = client.post(
            "/api/candidatures/acme-corp/fichiers",
            data={"file": file_data},
            content_type="multipart/form-data",
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert data["nom"] == "api-upload.md"
        assert data["type"] == "markdown"

        # Verify file on disk
        uploaded = Path(data_dir) / "candidatures" / "acme-corp" / "api-upload.md"
        assert uploaded.is_file()

    def test_upload_invalid_ext(self, client):
        """Uploading a disallowed extension returns 400."""
        file_data = (io.BytesIO(b"binary"), "bad.exe")
        r = client.post(
            "/api/candidatures/acme-corp/fichiers",
            data={"file": file_data},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400
        assert "non autorisee" in r.get_json()["error"]

    def test_upload_no_file(self, client):
        """Uploading without a file returns 400."""
        r = client.post(
            "/api/candidatures/acme-corp/fichiers",
            content_type="multipart/form-data",
        )
        assert r.status_code == 400

    def test_upload_candidature_not_found(self, client):
        """Uploading to a non-existent candidature returns 404."""
        file_data = (io.BytesIO(b"content"), "test.md")
        r = client.post(
            "/api/candidatures/inexistant/fichiers",
            data={"file": file_data},
            content_type="multipart/form-data",
        )
        assert r.status_code == 404

    def test_delete_fichier(self, client, app, data_dir):
        """DELETE /api/candidatures/<slug>/fichiers/<filename> removes the file."""
        file_path = Path(data_dir) / "candidatures" / "acme-corp" / "contrat.pdf"
        assert file_path.is_file()

        r = client.delete("/api/candidatures/acme-corp/fichiers/contrat.pdf")
        assert r.status_code == 200
        assert r.get_json()["data"]["deleted"] is True

        # Verify file removed from disk
        assert not file_path.is_file()

        # Verify DB entry removed
        with app.app_context():
            from services.database import Fichier

            f = Fichier.query.filter_by(slug="acme-corp", nom="contrat.pdf").first()
            assert f is None

    def test_delete_fichier_not_found(self, client):
        """Deleting a non-existent file returns 404."""
        r = client.delete("/api/candidatures/acme-corp/fichiers/inexistant.pdf")
        assert r.status_code == 404

    def test_delete_fichier_candidature_not_found(self, client):
        """Deleting from a non-existent candidature returns 404."""
        r = client.delete("/api/candidatures/inexistant/fichiers/test.md")
        assert r.status_code == 404

    def test_download_fichier(self, client):
        """GET /api/candidatures/<slug>/fichiers/<filename>/download returns the file."""
        r = client.get("/api/candidatures/acme-corp/fichiers/contrat.pdf/download")
        assert r.status_code == 200
        assert b"%PDF" in r.data
        assert "attachment" in r.headers.get("Content-Disposition", "")

    def test_download_subdir(self, client):
        """Download a file in a subdirectory."""
        r = client.get("/api/candidatures/acme-corp/fichiers/coaching/phase1.md/download")
        assert r.status_code == 200
        assert b"Phase 1" in r.data

    def test_download_not_found(self, client):
        """Downloading a non-existent file returns 404."""
        r = client.get("/api/candidatures/acme-corp/fichiers/inexistant.pdf/download")
        assert r.status_code == 404
