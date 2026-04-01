"""Tests for match scoring feature."""

import json

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
