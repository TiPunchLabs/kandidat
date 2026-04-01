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
