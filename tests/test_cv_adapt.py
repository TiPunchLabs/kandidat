"""Tests for CV adaptation feature: settings service, LLM providers, CV adapter, CV converter, API & routes."""

import io
from unittest.mock import MagicMock, patch

import pytest


def _can_import(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


needs_llm_deps = pytest.mark.skipif(
    not (_can_import("httpx") and _can_import("anthropic")),
    reason="httpx or anthropic not installed",
)
needs_converter_deps = pytest.mark.skipif(
    not (_can_import("weasyprint") and _can_import("docx")),
    reason="weasyprint or python-docx not installed",
)


# ──────────────────────────────────────────────────────────────
# Settings service
# ──────────────────────────────────────────────────────────────


class TestSettingsService:
    def test_get_setting_existing(self, app):
        with app.app_context():
            from services.settings import get_setting

            val = get_setting("llm_provider")
            assert val == "ollama"

    def test_get_setting_missing(self, app):
        with app.app_context():
            from services.settings import get_setting

            val = get_setting("nonexistent_key")
            assert val is None

    def test_set_setting_create(self, app):
        with app.app_context():
            from services.settings import get_setting, set_setting

            set_setting("new_key", "new_value")
            assert get_setting("new_key") == "new_value"

    def test_set_setting_update(self, app):
        with app.app_context():
            from services.settings import get_setting, set_setting

            set_setting("llm_provider", "claude")
            assert get_setting("llm_provider") == "claude"

    def test_get_all_settings(self, app):
        with app.app_context():
            from services.settings import get_all_settings

            all_s = get_all_settings()
            assert isinstance(all_s, dict)
            assert "llm_provider" in all_s
            assert "cv_reference_html" in all_s
            assert all_s["llm_provider"] == "ollama"

    def test_upload_cv_reference(self, app):
        with app.app_context():
            from services.settings import get_cv_reference_html, upload_cv_reference

            upload_cv_reference("<html><body>New CV</body></html>")
            assert get_cv_reference_html() == "<html><body>New CV</body></html>"

    def test_upload_cv_reference_empty(self, app):
        with app.app_context():
            import pytest

            from services.settings import upload_cv_reference

            with pytest.raises(ValueError, match="vide"):
                upload_cv_reference("   ")

    def test_get_cv_reference_html(self, app):
        with app.app_context():
            from services.settings import get_cv_reference_html

            html = get_cv_reference_html()
            assert html is not None
            assert "<h1>Mon CV</h1>" in html


# ──────────────────────────────────────────────────────────────
# LLM provider factory
# ──────────────────────────────────────────────────────────────


@needs_llm_deps
class TestLLMProviderFactory:
    def test_get_provider_ollama(self, app):
        with app.app_context():
            from services.llm import get_provider
            from services.llm.ollama import OllamaProvider

            provider = get_provider()
            assert isinstance(provider, OllamaProvider)

    def test_get_provider_claude(self, app):
        with app.app_context():
            from services.llm import get_provider
            from services.llm.claude import ClaudeProvider
            from services.settings import set_setting

            set_setting("llm_provider", "claude")
            set_setting("llm_claude_api_key", "sk-ant-test-key")
            provider = get_provider()
            assert isinstance(provider, ClaudeProvider)

    def test_get_provider_unknown(self, app):
        with app.app_context():
            import pytest

            from services.llm import get_provider
            from services.settings import set_setting

            set_setting("llm_provider", "unknown")
            with pytest.raises(ValueError, match="inconnu"):
                get_provider()

    def test_get_provider_none_configured(self, app):
        with app.app_context():
            import pytest

            from services.database import Setting, db
            from services.llm import get_provider

            Setting.query.filter_by(key="llm_provider").delete()
            db.session.commit()
            with pytest.raises(ValueError, match="Aucun fournisseur"):
                get_provider()

    def test_get_provider_claude_no_api_key(self, app):
        with app.app_context():
            import pytest

            from services.llm import get_provider
            from services.settings import set_setting

            set_setting("llm_provider", "claude")
            with pytest.raises(ValueError, match="Cle API"):
                get_provider()


# ──────────────────────────────────────────────────────────────
# CV converter
# ──────────────────────────────────────────────────────────────


@needs_converter_deps
class TestCVConverter:
    def test_validate_html_valid(self, app):
        with app.app_context():
            from services.cv_converter import validate_html

            assert validate_html("<html><body>Hello</body></html>") is True

    def test_validate_html_empty(self, app):
        with app.app_context():
            from services.cv_converter import validate_html

            assert validate_html("") is False
            assert validate_html("   ") is False

    def test_validate_html_no_tags(self, app):
        with app.app_context():
            from services.cv_converter import validate_html

            assert validate_html("plain text no tags") is False

    def test_validate_html_none(self, app):
        with app.app_context():
            from services.cv_converter import validate_html

            assert validate_html(None) is False

    def test_html_to_pdf(self, app):
        with app.app_context():
            from services.cv_converter import html_to_pdf

            pdf_bytes = html_to_pdf("<html><body><h1>Test</h1></body></html>")
            assert isinstance(pdf_bytes, bytes)
            assert pdf_bytes[:4] == b"%PDF"

    def test_html_to_pdf_invalid(self, app):
        with app.app_context():
            import pytest

            from services.cv_converter import html_to_pdf

            with pytest.raises(ValueError, match="invalide"):
                html_to_pdf("")

    def test_html_to_docx(self, app):
        with app.app_context():
            from services.cv_converter import html_to_docx

            docx_bytes = html_to_docx("<html><body><h1>Title</h1><p>Content</p></body></html>")
            assert isinstance(docx_bytes, bytes)
            # DOCX files start with PK (ZIP format)
            assert docx_bytes[:2] == b"PK"

    def test_html_to_docx_invalid(self, app):
        with app.app_context():
            import pytest

            from services.cv_converter import html_to_docx

            with pytest.raises(ValueError, match="invalide"):
                html_to_docx("")

    def test_save_cv_files(self, app, data_dir):
        with app.app_context():
            from services.cv_converter import save_cv_files

            results = save_cv_files("<html><body><h1>CV</h1></body></html>", "acme-corp", prefix="cv_test")
            assert len(results) == 2
            types = {r["type"] for r in results}
            assert types == {"pdf", "docx"}

            # Verify files on disk
            for r in results:
                file_path = data_dir / "candidatures" / "acme-corp" / r["nom"]
                assert file_path.is_file()

    def test_save_cv_files_unique_naming(self, app, data_dir):
        with app.app_context():
            from services.cv_converter import save_cv_files

            # First save
            results1 = save_cv_files("<html><body>CV1</body></html>", "acme-corp", prefix="cv_dup")
            # Second save — should get _2 suffix
            results2 = save_cv_files("<html><body>CV2</body></html>", "acme-corp", prefix="cv_dup")

            names1 = {r["nom"] for r in results1}
            names2 = {r["nom"] for r in results2}
            # No overlap
            assert names1.isdisjoint(names2)
            # Second set should have _2 suffix
            assert any("_2." in n for n in names2)


# ──────────────────────────────────────────────────────────────
# CV adapter orchestrator
# ──────────────────────────────────────────────────────────────


class TestCVAdapter:
    def test_resolve_cv_html_global(self, app):
        """Without candidature-specific HTML, returns global CV reference."""
        with app.app_context():
            from services.cv_adapter import resolve_cv_html

            html = resolve_cv_html("acme-corp")
            assert html is not None
            assert "<h1>Mon CV</h1>" in html

    def test_resolve_cv_html_candidature_specific(self, app, data_dir):
        """Candidature-specific HTML file takes priority over global."""
        with app.app_context():
            from services.cv_adapter import resolve_cv_html
            from services.database import Fichier, db

            # Create an HTML file for acme-corp
            cv_dir = data_dir / "candidatures" / "acme-corp"
            cv_file = cv_dir / "cv_custom.html"
            cv_file.write_text("<html><body><h1>Custom CV</h1></body></html>", encoding="utf-8")

            fichier = Fichier(
                slug="acme-corp", nom="cv_custom.html", chemin="candidatures/acme-corp/cv_custom.html", type="html"
            )
            db.session.add(fichier)
            db.session.commit()

            html = resolve_cv_html("acme-corp")
            assert "<h1>Custom CV</h1>" in html

    def test_resolve_cv_html_no_cv(self, app):
        """Returns None when no CV is configured."""
        with app.app_context():
            from services.cv_adapter import resolve_cv_html
            from services.database import Setting, db

            Setting.query.filter_by(key="cv_reference_html").delete()
            db.session.commit()

            html = resolve_cv_html("beta-inc")
            assert html is None

    def test_build_adaptation_context(self, app):
        with app.app_context():
            from services.cv_adapter import build_adaptation_context

            ctx = build_adaptation_context("acme-corp")
            assert ctx["poste"] == "DevOps Engineer"
            assert ctx["entreprise"] == "ACME Corp"
            assert "ACME Corp" in ctx["contenu"]

    def test_build_adaptation_context_empty_contenu(self, app):
        with app.app_context():
            from services.cv_adapter import build_adaptation_context

            ctx = build_adaptation_context("beta-inc")
            assert ctx["poste"] == "(non precise)"
            assert "(aucun contenu" in ctx["contenu"]

    def test_build_adaptation_context_not_found(self, app):
        with app.app_context():
            import pytest

            from services.cv_adapter import build_adaptation_context

            with pytest.raises(ValueError, match="non trouvee"):
                build_adaptation_context("inexistant")

    def test_adapt_cv_auto_uses_global(self, app):
        """Default auto mode uses global CV when no candidature-specific file exists."""
        with app.app_context():
            mock_provider = MagicMock()
            mock_provider.adapt_cv.return_value = "<html><body><h1>Adapted</h1></body></html>"

            with patch("services.cv_adapter.get_provider", return_value=mock_provider):
                from services.cv_adapter import adapt_cv

                result = adapt_cv("acme-corp")

            assert "<h1>Adapted</h1>" in result["adapted_html"]
            assert "context" in result
            assert result["context"]["poste"] == "DevOps Engineer"
            mock_provider.adapt_cv.assert_called_once()

    def test_adapt_cv_explicit_global(self, app):
        with app.app_context():
            mock_provider = MagicMock()
            mock_provider.adapt_cv.return_value = "<html><body>Adapted</body></html>"

            with patch("services.cv_adapter.get_provider", return_value=mock_provider):
                from services.cv_adapter import adapt_cv

                result = adapt_cv("acme-corp", cv_source="global")

            assert "adapted_html" in result
            mock_provider.adapt_cv.assert_called_once()

    def test_adapt_cv_no_cv_configured(self, app):
        with app.app_context():
            import pytest

            from services.database import Setting, db

            Setting.query.filter_by(key="cv_reference_html").delete()
            db.session.commit()

            mock_provider = MagicMock()
            with patch("services.cv_adapter.get_provider", return_value=mock_provider):
                from services.cv_adapter import adapt_cv

                with pytest.raises(ValueError, match="Aucun CV"):
                    adapt_cv("acme-corp")

    def test_adapt_cv_invalid_llm_response(self, app):
        with app.app_context():
            import pytest

            mock_provider = MagicMock()
            mock_provider.adapt_cv.return_value = ""  # Empty response

            with patch("services.cv_adapter.get_provider", return_value=mock_provider):
                from services.cv_adapter import adapt_cv

                with pytest.raises(ValueError, match="invalide"):
                    adapt_cv("acme-corp")

    def test_adapt_cv_warning_on_empty_contenu(self, app):
        """When candidature has no contenu, result includes a warning."""
        with app.app_context():
            mock_provider = MagicMock()
            mock_provider.adapt_cv.return_value = "<html><body>Adapted</body></html>"

            with patch("services.cv_adapter.get_provider", return_value=mock_provider):
                from services.cv_adapter import adapt_cv

                result = adapt_cv("beta-inc")  # beta-inc has empty contenu

            assert "warning" in result
            assert "moins precis" in result["warning"]

    def test_adapt_cv_no_warning_with_contenu(self, app):
        """When candidature has contenu, no warning is returned."""
        with app.app_context():
            mock_provider = MagicMock()
            mock_provider.adapt_cv.return_value = "<html><body>Adapted</body></html>"

            with patch("services.cv_adapter.get_provider", return_value=mock_provider):
                from services.cv_adapter import adapt_cv

                result = adapt_cv("acme-corp")  # acme-corp has contenu

            assert "warning" not in result

    @needs_converter_deps
    def test_save_adapted_cv(self, app, data_dir):
        with app.app_context():
            from services.cv_adapter import save_adapted_cv

            files = save_adapted_cv("acme-corp", "<html><body><h1>Adapted CV</h1></body></html>")
            assert len(files) == 2
            types = {f["type"] for f in files}
            assert types == {"pdf", "docx"}


# ──────────────────────────────────────────────────────────────
# Settings API endpoints
# ──────────────────────────────────────────────────────────────


class TestSettingsAPI:
    def test_get_settings(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["cv_reference_configured"] is True
        assert data["llm_provider"] == "ollama"
        assert data["llm_ollama_url"] == "http://localhost:11434"
        assert data["llm_ollama_model"] == "llama3.2"

    def test_get_settings_masks_api_key(self, client):
        r = client.get("/api/settings")
        data = r.get_json()["data"]
        assert "llm_claude_api_key" not in data
        assert "llm_claude_api_key_configured" in data

    def test_upload_cv_reference(self, client):
        html_content = b"<html><body><h1>New CV</h1></body></html>"
        r = client.put(
            "/api/settings/cv-reference",
            data={"file": (io.BytesIO(html_content), "cv.html")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["cv_reference_configured"] is True

    def test_upload_cv_reference_no_file(self, client):
        r = client.put("/api/settings/cv-reference")
        assert r.status_code == 400
        assert "fichier" in r.get_json()["error"].lower()

    def test_upload_cv_reference_wrong_extension(self, client):
        r = client.put(
            "/api/settings/cv-reference",
            data={"file": (io.BytesIO(b"content"), "cv.pdf")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400
        assert "HTML" in r.get_json()["error"]

    def test_upload_cv_reference_empty(self, client):
        r = client.put(
            "/api/settings/cv-reference",
            data={"file": (io.BytesIO(b"   "), "cv.html")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400
        assert "vide" in r.get_json()["error"]

    def test_get_cv_reference(self, client):
        r = client.get("/api/settings/cv-reference")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "<h1>Mon CV</h1>" in data["cv_html"]

    def test_get_cv_reference_not_configured(self, client, app):
        with app.app_context():
            from services.database import Setting, db

            Setting.query.filter_by(key="cv_reference_html").delete()
            db.session.commit()

        r = client.get("/api/settings/cv-reference")
        assert r.status_code == 404

    def test_update_llm_config_ollama(self, client):
        r = client.put(
            "/api/settings/llm",
            json={"provider": "ollama", "ollama_url": "http://localhost:11434", "ollama_model": "mistral"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["llm_provider"] == "ollama"
        assert data["llm_ollama_model"] == "mistral"

    def test_update_llm_config_claude(self, client):
        r = client.put(
            "/api/settings/llm",
            json={"provider": "claude", "claude_api_key": "sk-ant-test", "claude_model": "claude-sonnet-4-20250514"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["llm_provider"] == "claude"

    def test_update_llm_config_no_body(self, client):
        r = client.put("/api/settings/llm", content_type="application/json")
        assert r.status_code == 400

    def test_update_llm_config_invalid_provider(self, client):
        r = client.put("/api/settings/llm", json={"provider": "invalid"})
        assert r.status_code == 400


# ──────────────────────────────────────────────────────────────
# CV Adaptation API endpoints
# ──────────────────────────────────────────────────────────────


class TestCVAdaptAPI:
    def test_adapt_cv_success(self, client, app):
        mock_provider = MagicMock()
        mock_provider.adapt_cv.return_value = "<html><body><h1>Adapted</h1></body></html>"

        with patch("services.cv_adapter.get_provider", return_value=mock_provider):
            r = client.post("/api/candidatures/acme-corp/cv/adapt", json={})
            assert r.status_code == 200
            data = r.get_json()["data"]
            assert "<h1>Adapted</h1>" in data["adapted_html"]
            assert "provider_used" in data
            assert "context" in data

    def test_adapt_cv_with_warning(self, client, app):
        mock_provider = MagicMock()
        mock_provider.adapt_cv.return_value = "<html><body>Adapted</body></html>"

        with patch("services.cv_adapter.get_provider", return_value=mock_provider):
            r = client.post("/api/candidatures/beta-inc/cv/adapt", json={})
            assert r.status_code == 200
            data = r.get_json()["data"]
            assert "warning" in data
            assert "moins precis" in data["warning"]

    def test_adapt_cv_not_found(self, client):
        r = client.post("/api/candidatures/inexistant/cv/adapt", json={})
        assert r.status_code == 404

    def test_adapt_cv_no_cv_configured(self, client, app):
        with app.app_context():
            from services.database import Setting, db

            Setting.query.filter_by(key="cv_reference_html").delete()
            db.session.commit()

        r = client.post("/api/candidatures/acme-corp/cv/adapt", json={})
        assert r.status_code == 400
        assert "CV" in r.get_json()["error"]

    @needs_converter_deps
    def test_save_adapted_cv(self, client, app, data_dir):
        r = client.post(
            "/api/candidatures/acme-corp/cv/save",
            json={"adapted_html": "<html><body><h1>Saved CV</h1></body></html>"},
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert len(data["files"]) == 2

    def test_save_adapted_cv_no_html(self, client):
        r = client.post("/api/candidatures/acme-corp/cv/save", json={})
        assert r.status_code == 400

    def test_save_adapted_cv_not_found(self, client):
        r = client.post(
            "/api/candidatures/inexistant/cv/save",
            json={"adapted_html": "<html>test</html>"},
        )
        assert r.status_code == 404

    @needs_converter_deps
    def test_convert_cv_without_llm(self, client, app, data_dir):
        r = client.post(
            "/api/candidatures/acme-corp/cv/convert",
            json={"cv_source": "global"},
        )
        assert r.status_code == 201
        data = r.get_json()["data"]
        assert len(data["files"]) == 2

    def test_convert_cv_not_found(self, client):
        r = client.post("/api/candidatures/inexistant/cv/convert", json={})
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────
# Settings web routes
# ──────────────────────────────────────────────────────────────


class TestSettingsRoutes:
    def test_settings_page(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Parametres" in html
        assert "CV de reference" in html
        assert "Fournisseur LLM" in html

    def test_settings_page_shows_cv_status(self, client):
        resp = client.get("/settings")
        html = resp.data.decode()
        assert "CV de reference configure" in html

    def test_settings_page_shows_provider(self, client):
        resp = client.get("/settings")
        html = resp.data.decode()
        assert "ollama" in html.lower()

    def test_upload_cv_reference_route(self, client):
        html_content = b"<html><body><h1>Route CV</h1></body></html>"
        resp = client.post(
            "/settings/cv-reference",
            data={"file": (io.BytesIO(html_content), "cv.html")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "mis a jour" in html.lower() or "CV de reference configure" in html

    def test_upload_cv_reference_no_file(self, client):
        resp = client.post(
            "/settings/cv-reference",
            data={},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Aucun fichier" in html

    def test_update_llm_config_route(self, client):
        resp = client.post(
            "/settings/llm",
            data={"provider": "ollama", "ollama_url": "http://localhost:11434", "ollama_model": "llama3.2"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Parametres" in html

    def test_settings_page_shows_prompts_section(self, client):
        resp = client.get("/settings")
        html = resp.data.decode()
        assert "Prompts LLM" in html
        assert "system-prompt" in html
        assert "user-prompt" in html

    def test_update_prompts_route(self, client):
        resp = client.post(
            "/settings/prompts",
            data={"system_prompt": "Custom system prompt", "user_prompt": "Custom user prompt: {cv_html}"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Prompts LLM mis a jour" in html

    def test_update_prompts_persists(self, client, app):
        client.post(
            "/settings/prompts",
            data={"system_prompt": "Persistent prompt", "user_prompt": ""},
            follow_redirects=True,
        )
        with app.app_context():
            from services.settings import get_setting

            assert get_setting("cv_adapt_system_prompt") == "Persistent prompt"

    def test_reset_prompts_to_empty(self, client, app):
        # Save custom first
        client.post(
            "/settings/prompts",
            data={"system_prompt": "Custom", "user_prompt": "Custom"},
            follow_redirects=True,
        )
        # Reset by sending empty values
        client.post(
            "/settings/prompts",
            data={"system_prompt": "", "user_prompt": ""},
            follow_redirects=True,
        )
        with app.app_context():
            from services.settings import get_setting

            # Empty string means it will fall back to default
            assert get_setting("cv_adapt_system_prompt") == ""


# ──────────────────────────────────────────────────────────────
# CV adaptation web routes
# ──────────────────────────────────────────────────────────────


class TestCVAdaptRoutes:
    def test_cv_loading_page(self, client):
        resp = client.get("/candidature/acme-corp/cv/adapt")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Adaptation en cours" in html
        assert "ACME Corp" in html
        assert "DevOps Engineer" in html

    def test_cv_loading_page_not_found(self, client):
        resp = client.get("/candidature/inexistant/cv/adapt")
        assert resp.status_code == 404

    def test_cv_preview_page(self, client):
        resp = client.get("/candidature/acme-corp/cv/preview")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Apercu du CV adapte" in html
        assert "Confirmer et sauvegarder" in html
        assert "Relancer" in html
        assert "Annuler" in html

    def test_cv_preview_page_not_found(self, client):
        resp = client.get("/candidature/inexistant/cv/preview")
        assert resp.status_code == 404

    def test_detail_shows_cv_buttons(self, client):
        """Detail page shows CV adapt button when CV reference is configured."""
        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert "Adapter mon CV" in html
        assert "Exporter en PDF/DOCX" in html

    def test_detail_hides_cv_buttons_without_reference(self, client, app):
        """Detail page hides CV buttons when no CV reference is configured."""
        with app.app_context():
            from services.database import Setting, db

            Setting.query.filter_by(key="cv_reference_html").delete()
            db.session.commit()

        resp = client.get("/candidature/acme-corp")
        html = resp.data.decode()
        assert "Adapter mon CV" not in html

    def test_nav_shows_settings_link(self, client):
        """Navigation includes link to settings page."""
        resp = client.get("/")
        html = resp.data.decode()
        assert "/settings" in html
