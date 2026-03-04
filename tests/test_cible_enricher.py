"""Tests for cible enrichment feature: enricher service, API endpoints, web routes."""

import json
from unittest.mock import MagicMock, patch

import pytest


def _can_import(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


needs_tavily = pytest.mark.skipif(
    not _can_import("tavily"),
    reason="tavily-python not installed",
)


# ──────────────────────────────────────────────────────────────
# Enricher service — JSON extraction
# ──────────────────────────────────────────────────────────────


class TestExtractJson:
    def test_valid_json(self, app):
        with app.app_context():
            from services.cible_enricher import _extract_json_from_response

            result = _extract_json_from_response('{"company": {"url": "https://example.com"}, "contacts": []}')
            assert result["company"]["url"] == "https://example.com"

    def test_json_in_code_block(self, app):
        with app.app_context():
            from services.cible_enricher import _extract_json_from_response

            text = '```json\n{"company": {"url": "https://example.com"}, "contacts": []}\n```'
            result = _extract_json_from_response(text)
            assert result["company"]["url"] == "https://example.com"

    def test_invalid_json(self, app):
        with app.app_context():
            from services.cible_enricher import _extract_json_from_response

            with pytest.raises(ValueError, match="JSON invalide"):
                _extract_json_from_response("not json at all")


# ──────────────────────────────────────────────────────────────
# Enricher service — enrich_cible (mocked Tavily + LLM)
# ──────────────────────────────────────────────────────────────


class TestEnrichCible:
    @needs_tavily
    def test_enrich_cible_success(self, app):
        with app.app_context():
            from services.settings import set_setting

            set_setting("tavily_api_key", "tvly-test-key")

            mock_tavily = MagicMock()
            mock_tavily.search.return_value = {
                "results": [{"title": "Example Corp", "url": "https://example.com", "content": "A great company."}]
            }

            mock_provider = MagicMock()
            mock_provider.complete.return_value = json.dumps(
                {
                    "company": {
                        "url": "https://example.com",
                        "linkedin": "",
                        "description": "A great company",
                        "email": "",
                    },
                    "contacts": [
                        {
                            "nom": "Dupont",
                            "prenom": "Jean",
                            "fonction": "CEO",
                            "linkedin": "",
                            "email": "",
                            "telephone": "",
                        }
                    ],
                }
            )

            with (
                patch("tavily.TavilyClient", return_value=mock_tavily),
                patch("services.cible_enricher.get_provider", return_value=mock_provider),
            ):
                from services.cible_enricher import enrich_cible

                result = enrich_cible(1)  # Groupe GBH

            assert result["cible_id"] == 1
            assert result["cible_name"] == "Groupe GBH"
            assert "suggestions" in result
            assert result["suggestions"]["company"]["url"] == "https://example.com"
            assert len(result["suggestions"]["contacts"]) == 1
            assert result["suggestions"]["contacts"][0]["nom"] == "Dupont"

    def test_enrich_cible_not_found(self, app):
        with app.app_context():
            from services.settings import set_setting

            set_setting("tavily_api_key", "tvly-test-key")

            with pytest.raises(ValueError, match="non trouvee"):
                from services.cible_enricher import enrich_cible

                enrich_cible(9999)

    def test_enrich_cible_no_tavily_key(self, app):
        with app.app_context():
            with pytest.raises(ValueError, match="Tavily"):
                from services.cible_enricher import enrich_cible

                enrich_cible(1)


# ──────────────────────────────────────────────────────────────
# Enricher service — apply_enrichment
# ──────────────────────────────────────────────────────────────


class TestApplyEnrichment:
    def test_apply_company_fields(self, app):
        with app.app_context():
            from services.cible_enricher import apply_enrichment
            from services.database import Cible, db

            result = apply_enrichment(
                1,
                {
                    "company": {"url": "https://gbh.com", "description": "Groupe diversifie"},
                    "contacts": [],
                },
            )
            assert result["company_updated"] is True
            assert result["contacts_created"] == 0

            cible = db.session.get(Cible, 1)
            assert cible.url == "https://gbh.com"
            assert cible.description == "Groupe diversifie"

    def test_apply_contacts(self, app):
        with app.app_context():
            from services.cible_enricher import apply_enrichment

            result = apply_enrichment(
                1,
                {
                    "company": {},
                    "contacts": [
                        {"nom": "Martin", "prenom": "Sophie", "fonction": "DRH", "email": "sophie@gbh.com"},
                        {"nom": "Bernard", "prenom": "Luc", "fonction": "DSI"},
                    ],
                },
            )
            assert result["company_updated"] is False
            assert result["contacts_created"] == 2

    def test_apply_empty_accepted(self, app):
        with app.app_context():
            from services.cible_enricher import apply_enrichment

            result = apply_enrichment(1, {"company": {}, "contacts": []})
            assert result["company_updated"] is False
            assert result["contacts_created"] == 0

    def test_apply_not_found(self, app):
        with app.app_context():
            from services.cible_enricher import apply_enrichment

            with pytest.raises(ValueError, match="non trouvee"):
                apply_enrichment(9999, {"company": {}, "contacts": []})

    def test_apply_skips_contacts_without_nom(self, app):
        with app.app_context():
            from services.cible_enricher import apply_enrichment

            result = apply_enrichment(
                1,
                {
                    "company": {},
                    "contacts": [
                        {"nom": "", "prenom": "Anonymous"},
                        {"nom": "Valid", "prenom": "Contact"},
                    ],
                },
            )
            assert result["contacts_created"] == 1


# ──────────────────────────────────────────────────────────────
# Enrichment API endpoints
# ──────────────────────────────────────────────────────────────


class TestEnrichmentAPI:
    @needs_tavily
    def test_enrich_api_success(self, client, app):
        with app.app_context():
            from services.settings import set_setting

            set_setting("tavily_api_key", "tvly-test-key")

        mock_tavily = MagicMock()
        mock_tavily.search.return_value = {
            "results": [{"title": "Test", "url": "https://test.com", "content": "Test company"}]
        }

        mock_provider = MagicMock()
        mock_provider.complete.return_value = json.dumps({"company": {"url": "https://test.com"}, "contacts": []})

        with (
            patch("tavily.TavilyClient", return_value=mock_tavily),
            patch("services.cible_enricher.get_provider", return_value=mock_provider),
        ):
            r = client.post("/api/cibles/1/enrich")
            assert r.status_code == 200
            data = r.get_json()["data"]
            assert data["cible_id"] == 1
            assert "suggestions" in data

    def test_enrich_api_not_found(self, client):
        r = client.post("/api/cibles/9999/enrich")
        assert r.status_code == 404

    def test_enrich_api_no_tavily(self, client):
        """Returns 400 when Tavily is not configured."""
        r = client.post("/api/cibles/1/enrich")
        assert r.status_code == 400
        assert "Tavily" in r.get_json()["error"]

    def test_apply_api_success(self, client):
        r = client.post(
            "/api/cibles/1/enrich/apply",
            json={"accepted": {"company": {"url": "https://applied.com"}, "contacts": []}},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["company_updated"] is True

    def test_apply_api_not_found(self, client):
        r = client.post(
            "/api/cibles/9999/enrich/apply",
            json={"accepted": {"company": {}, "contacts": []}},
        )
        assert r.status_code == 404

    def test_apply_api_no_body(self, client):
        r = client.post("/api/cibles/1/enrich/apply", content_type="application/json")
        assert r.status_code == 400


# ──────────────────────────────────────────────────────────────
# Tavily settings API
# ──────────────────────────────────────────────────────────────


class TestTavilySettingsAPI:
    def test_update_tavily_config(self, client):
        r = client.put("/api/settings/tavily", json={"tavily_api_key": "tvly-test-key"})
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["tavily_api_key_configured"] is True

    def test_update_tavily_config_empty(self, client):
        r = client.put("/api/settings/tavily", json={"tavily_api_key": ""})
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["tavily_api_key_configured"] is False

    def test_update_tavily_no_body(self, client):
        r = client.put("/api/settings/tavily", content_type="application/json")
        assert r.status_code == 400

    def test_settings_shows_tavily(self, client):
        r = client.get("/api/settings")
        data = r.get_json()["data"]
        assert "tavily_api_key_configured" in data


# ──────────────────────────────────────────────────────────────
# Enrichment web routes
# ──────────────────────────────────────────────────────────────


class TestEnrichmentRoutes:
    def test_enrich_loading_page(self, client):
        resp = client.get("/cible/1/enrich")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Enrichissement en cours" in html
        assert "Groupe GBH" in html

    def test_enrich_loading_page_not_found(self, client):
        resp = client.get("/cible/9999/enrich")
        assert resp.status_code == 404

    def test_enrich_preview_page(self, client):
        resp = client.get("/cible/1/enrich/preview")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Enrichissement" in html
        assert "Appliquer la selection" in html

    def test_enrich_preview_page_not_found(self, client):
        resp = client.get("/cible/9999/enrich/preview")
        assert resp.status_code == 404

    def test_cible_detail_shows_enrich_button(self, client, app):
        """Enrich button appears when both Tavily and LLM are configured."""
        with app.app_context():
            from services.settings import set_setting

            set_setting("tavily_api_key", "tvly-test-key")

        resp = client.get("/cible/1")
        html = resp.data.decode()
        assert "Enrichir via IA" in html

    def test_cible_detail_hides_enrich_without_tavily(self, client):
        """Enrich button hidden when Tavily is not configured."""
        resp = client.get("/cible/1")
        html = resp.data.decode()
        assert "Enrichir via IA" not in html

    def test_settings_page_shows_tavily(self, client):
        resp = client.get("/settings")
        html = resp.data.decode()
        assert "Tavily" in html
        assert "Recherche web" in html

    def test_tavily_settings_route(self, client):
        resp = client.post(
            "/settings/tavily",
            data={"tavily_api_key": "tvly-new-key"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Parametres" in html
