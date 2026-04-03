"""Tests for services/settings.py: get, set, get_all, upload_cv, get_cv_html."""

import pytest

from services.database import Setting, db
from services.settings import (
    get_all_settings,
    get_cv_reference_html,
    get_setting,
    set_setting,
    upload_cv_reference,
)

# ---------------------------------------------------------------------------
# get_setting
# ---------------------------------------------------------------------------


class TestGetSetting:
    def test_returns_value_for_existing_key(self, app, data_dir):
        with app.app_context():
            value = get_setting("llm_provider")
            assert value == "ollama"

    def test_returns_none_for_missing_key(self, app, data_dir):
        with app.app_context():
            value = get_setting("nonexistent_key")
            assert value is None

    def test_returns_cv_reference_html(self, app, data_dir):
        with app.app_context():
            value = get_setting("cv_reference_html")
            assert value is not None
            assert "<h1>Mon CV</h1>" in value

    def test_returns_ollama_url(self, app, data_dir):
        with app.app_context():
            value = get_setting("llm_ollama_url")
            assert value == "http://localhost:11434"


# ---------------------------------------------------------------------------
# set_setting
# ---------------------------------------------------------------------------


class TestSetSetting:
    def test_creates_new_setting(self, app, data_dir):
        with app.app_context():
            result = set_setting("new_key", "new_value")
            assert result is not None
            assert isinstance(result, Setting)
            assert get_setting("new_key") == "new_value"

    def test_updates_existing_setting(self, app, data_dir):
        with app.app_context():
            set_setting("llm_provider", "claude")
            assert get_setting("llm_provider") == "claude"

    def test_updates_updated_at_timestamp(self, app, data_dir):
        with app.app_context():
            set_setting("llm_provider", "claude")
            result = db.session.get(Setting, "llm_provider")
            # updated_at should be a valid ISO timestamp string
            assert result.updated_at is not None
            assert "T" in result.updated_at

    def test_persists_to_db(self, app, data_dir):
        with app.app_context():
            set_setting("persist_test", "hello")
            fetched = db.session.get(Setting, "persist_test")
            assert fetched is not None
            assert fetched.value == "hello"


# ---------------------------------------------------------------------------
# get_all_settings
# ---------------------------------------------------------------------------


class TestGetAllSettings:
    def test_returns_dict(self, app, data_dir):
        with app.app_context():
            result = get_all_settings()
            assert isinstance(result, dict)

    def test_contains_seeded_keys(self, app, data_dir):
        with app.app_context():
            result = get_all_settings()
            assert "llm_provider" in result
            assert "cv_reference_html" in result
            assert "llm_ollama_url" in result
            assert "llm_ollama_model" in result

    def test_values_are_strings(self, app, data_dir):
        with app.app_context():
            result = get_all_settings()
            for value in result.values():
                assert isinstance(value, str)

    def test_empty_settings_returns_empty_dict(self, app, data_dir):
        with app.app_context():
            Setting.query.delete()
            db.session.commit()
            result = get_all_settings()
            assert result == {}


# ---------------------------------------------------------------------------
# upload_cv_reference
# ---------------------------------------------------------------------------


class TestUploadCvReference:
    def test_stores_html_content(self, app, data_dir):
        with app.app_context():
            html = "<html><body><p>New CV content</p></body></html>"
            upload_cv_reference(html)
            assert get_setting("cv_reference_html") == html

    def test_sets_date_setting(self, app, data_dir):
        with app.app_context():
            upload_cv_reference("<p>Test CV</p>")
            date_value = get_setting("cv_reference_date")
            assert date_value is not None
            assert "T" in date_value  # ISO 8601 format

    def test_replaces_existing_cv(self, app, data_dir):
        with app.app_context():
            upload_cv_reference("<p>First CV</p>")
            upload_cv_reference("<p>Second CV</p>")
            assert get_setting("cv_reference_html") == "<p>Second CV</p>"

    def test_raises_on_empty_content(self, app, data_dir):
        with app.app_context():
            with pytest.raises(ValueError):
                upload_cv_reference("")

    def test_raises_on_whitespace_only_content(self, app, data_dir):
        with app.app_context():
            with pytest.raises(ValueError):
                upload_cv_reference("   \n  ")


# ---------------------------------------------------------------------------
# get_cv_reference_html
# ---------------------------------------------------------------------------


class TestGetCvReferenceHtml:
    def test_returns_stored_html(self, app, data_dir):
        with app.app_context():
            html = get_cv_reference_html()
            assert html is not None
            assert "<h1>Mon CV</h1>" in html

    def test_returns_none_when_not_set(self, app, data_dir):
        with app.app_context():
            Setting.query.filter_by(key="cv_reference_html").delete()
            db.session.commit()
            html = get_cv_reference_html()
            assert html is None

    def test_returns_updated_html_after_upload(self, app, data_dir):
        with app.app_context():
            new_html = "<html><body><h1>Updated CV</h1></body></html>"
            upload_cv_reference(new_html)
            assert get_cv_reference_html() == new_html
