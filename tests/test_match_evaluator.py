"""Tests for match scoring feature."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestMatchDatabaseColumns:
    """Test that match columns exist on the Candidature model."""

    def test_candidature_has_match_score_column(self, app):
        with app.app_context():
            from services.database import Candidature, db

            c = db.session.get(Candidature, "acme-corp")
            assert hasattr(c, "match_score")
            assert c.match_score is None

    def test_candidature_has_match_details_column(self, app):
        with app.app_context():
            from services.database import Candidature, db

            c = db.session.get(Candidature, "acme-corp")
            assert hasattr(c, "match_details")
            assert c.match_details is None

    def test_match_score_persists(self, app):
        with app.app_context():
            from services.database import Candidature, db

            c = db.session.get(Candidature, "acme-corp")
            c.match_score = 82.5
            c.match_details = json.dumps({
                "strengths": ["DevOps experience"],
                "weaknesses": ["No AWS"],
                "missing": ["GCP"],
            })
            db.session.commit()

            reloaded = db.session.get(Candidature, "acme-corp")
            assert reloaded.match_score == 82.5
            details = json.loads(reloaded.match_details)
            assert details["strengths"] == ["DevOps experience"]


class TestMatchSchemas:
    """Test that match fields appear in CandidatureResponse."""

    def test_response_includes_match_fields_none(self, app):
        with app.app_context():
            from services.database import Candidature, db
            from services.schemas import CandidatureResponse

            c = db.session.get(Candidature, "acme-corp")
            resp = CandidatureResponse.from_orm(c)
            assert resp.match_score is None
            assert resp.match_details is None

    def test_response_includes_match_fields_with_data(self, app):
        with app.app_context():
            import json

            from services.database import Candidature, db
            from services.schemas import CandidatureResponse

            c = db.session.get(Candidature, "acme-corp")
            c.match_score = 75.0
            c.match_details = json.dumps({"strengths": ["Python"], "weaknesses": [], "missing": []})
            db.session.commit()

            reloaded = db.session.get(Candidature, "acme-corp")
            resp = CandidatureResponse.from_orm(reloaded)
            assert resp.match_score == 75.0
            assert resp.match_details == {"strengths": ["Python"], "weaknesses": [], "missing": []}


class TestMatchEvaluator:
    """Test the match evaluation service."""

    def test_evaluate_match_returns_score_and_details(self, app):
        with app.app_context():
            from services.settings import set_setting, upload_cv_reference

            upload_cv_reference("<html><body>CV with Python, Docker, Terraform</body></html>")
            set_setting("llm_provider", "ollama")

            mock_provider = MagicMock()
            mock_provider.complete.return_value = json.dumps({
                "score": 82,
                "strengths": ["Python experience", "Docker skills"],
                "weaknesses": ["No AWS mentioned"],
                "missing": ["Kubernetes"],
            })

            with patch("services.match_evaluator.get_provider", return_value=mock_provider):
                from services.match_evaluator import evaluate_match

                result = evaluate_match("acme-corp")

            assert result["match_score"] == 82
            assert "Python experience" in result["match_details"]["strengths"]
            assert "No AWS mentioned" in result["match_details"]["weaknesses"]
            assert "Kubernetes" in result["match_details"]["missing"]

    def test_evaluate_match_persists_to_db(self, app):
        with app.app_context():
            from services.database import Candidature, db
            from services.settings import set_setting, upload_cv_reference

            upload_cv_reference("<html><body>CV content</body></html>")
            set_setting("llm_provider", "ollama")

            mock_provider = MagicMock()
            mock_provider.complete.return_value = json.dumps({
                "score": 65,
                "strengths": ["Good"],
                "weaknesses": ["Bad"],
                "missing": ["Missing"],
            })

            with patch("services.match_evaluator.get_provider", return_value=mock_provider):
                from services.match_evaluator import evaluate_match

                evaluate_match("acme-corp")

            c = db.session.get(Candidature, "acme-corp")
            assert c.match_score == 65

    def test_evaluate_match_no_cv_raises(self, app):
        with app.app_context():
            from services.database import Setting, db
            from services.match_evaluator import evaluate_match

            # Remove the seeded CV reference to simulate no CV configured
            setting = db.session.get(Setting, "cv_reference_html")
            if setting:
                db.session.delete(setting)
                db.session.commit()

            with pytest.raises(ValueError, match="CV de reference"):
                evaluate_match("acme-corp")

    def test_evaluate_match_empty_contenu_raises(self, app):
        with app.app_context():
            from services.database import Candidature, db
            from services.settings import upload_cv_reference

            upload_cv_reference("<html><body>CV</body></html>")
            c = db.session.get(Candidature, "acme-corp")
            c.contenu = ""
            db.session.commit()

            from services.match_evaluator import evaluate_match

            with pytest.raises(ValueError, match="contenu"):
                evaluate_match("acme-corp")
