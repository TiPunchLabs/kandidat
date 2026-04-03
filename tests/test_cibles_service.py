"""Tests for services/cibles.py: create, update, delete, reorder, toggle, detail, contacts."""

from services.cibles import (
    create_cible,
    create_contact,
    delete_cible,
    delete_contact,
    get_cible_detail,
    reorder_cibles,
    toggle_cible,
    update_cible,
    update_contact,
)
from services.database import Cible, Contact, db

# ---------------------------------------------------------------------------
# create_cible
# ---------------------------------------------------------------------------


class TestCreateCible:
    def test_creates_at_last_position(self, app, data_dir):
        with app.app_context():
            # "entreprises" already has positions 0, 1, 2 (ids 4, 5, 6)
            cible = create_cible(nom="New Corp", categorie="entreprises")
            assert cible is not None
            assert cible.id is not None
            assert cible.nom == "New Corp"
            assert cible.categorie == "entreprises"
            assert cible.position == 3  # max(0,1,2) + 1

    def test_creates_first_in_empty_category(self, app, data_dir):
        with app.app_context():
            cible = create_cible(nom="First Org", categorie="organisations")
            assert cible.position == 1

    def test_returns_cible_object(self, app, data_dir):
        with app.app_context():
            cible = create_cible(nom="Test ESN", categorie="esn")
            assert isinstance(cible, Cible)
            assert cible.contactee == 0

    def test_optional_fields_default_empty(self, app, data_dir):
        with app.app_context():
            cible = create_cible(nom="Bare Corp", categorie="cabinets")
            assert cible.url == ""
            assert cible.description == ""
            assert cible.email == ""
            assert cible.linkedin == ""

    def test_optional_fields_stored(self, app, data_dir):
        with app.app_context():
            cible = create_cible(
                nom="Full Corp",
                categorie="entreprises",
                url="https://example.com",
                description="A description",
                email="contact@example.com",
                linkedin="https://linkedin.com/in/full",
            )
            assert cible.url == "https://example.com"
            assert cible.description == "A description"
            assert cible.email == "contact@example.com"
            assert cible.linkedin == "https://linkedin.com/in/full"


# ---------------------------------------------------------------------------
# update_cible
# ---------------------------------------------------------------------------


class TestUpdateCible:
    def test_update_nom(self, app, data_dir):
        with app.app_context():
            result = update_cible(4, nom="Orange Updated")
            assert result is not None
            assert result.nom == "Orange Updated"

    def test_update_returns_cible(self, app, data_dir):
        with app.app_context():
            result = update_cible(5, description="New description")
            assert isinstance(result, Cible)
            assert result.description == "New description"

    def test_update_multiple_fields(self, app, data_dir):
        with app.app_context():
            result = update_cible(6, url="https://edf.fr", email="contact@edf.fr")
            assert result.url == "https://edf.fr"
            assert result.email == "contact@edf.fr"

    def test_update_contactee_boolean(self, app, data_dir):
        with app.app_context():
            result = update_cible(4, contactee=True)
            assert result.contactee == 1
            result2 = update_cible(4, contactee=False)
            assert result2.contactee == 0

    def test_update_missing_cible_returns_none(self, app, data_dir):
        with app.app_context():
            result = update_cible(9999, nom="Ghost")
            assert result is None

    def test_update_ignores_unknown_fields(self, app, data_dir):
        with app.app_context():
            # Should not raise — unknown fields are silently ignored
            result = update_cible(4, unknown_field="value")
            assert result is not None


# ---------------------------------------------------------------------------
# delete_cible
# ---------------------------------------------------------------------------


class TestDeleteCible:
    def test_delete_existing_cible(self, app, data_dir):
        with app.app_context():
            result = delete_cible(8)  # LHH — no candidatures
            assert result is True
            assert db.session.get(Cible, 8) is None

    def test_delete_missing_returns_false(self, app, data_dir):
        with app.app_context():
            result = delete_cible(9999)
            assert result is False

    def test_delete_cascades_to_candidatures(self, app, data_dir):
        with app.app_context():
            from services.database import Candidature

            # cible_id=4 has acme-corp candidature
            assert Candidature.query.filter_by(cible_id=4).count() == 1
            delete_cible(4)
            assert Candidature.query.filter_by(cible_id=4).count() == 0

    def test_delete_shifts_positions(self, app, data_dir):
        with app.app_context():
            # cabinets: id=7 pos=0, id=8 pos=1 — delete id=7
            delete_cible(7)
            lhh = db.session.get(Cible, 8)
            assert lhh.position == 0  # shifted from 1 to 0


# ---------------------------------------------------------------------------
# reorder_cibles
# ---------------------------------------------------------------------------


class TestReorderCibles:
    def test_reorder_updates_positions(self, app, data_dir):
        with app.app_context():
            # grands-groupes: 1(pos0), 2(pos1), 3(pos2) — reverse order
            result = reorder_cibles("grands-groupes", [3, 2, 1])
            assert result is True
            assert db.session.get(Cible, 3).position == 1
            assert db.session.get(Cible, 2).position == 2
            assert db.session.get(Cible, 1).position == 3

    def test_reorder_ignores_wrong_category(self, app, data_dir):
        with app.app_context():
            # id=9 is esn, not grands-groupes — should not be reordered
            original_pos = db.session.get(Cible, 9).position
            reorder_cibles("grands-groupes", [9, 1, 2, 3])
            # id=9 position should be unchanged
            assert db.session.get(Cible, 9).position == original_pos

    def test_reorder_returns_true(self, app, data_dir):
        with app.app_context():
            result = reorder_cibles("esn", [9])
            assert result is True


# ---------------------------------------------------------------------------
# toggle_cible
# ---------------------------------------------------------------------------


class TestToggleCible:
    def test_toggle_check(self, app, data_dir):
        with app.app_context():
            # id=4 (Orange Caraibe) contactee=0 initially
            result = toggle_cible(4, True)
            assert result is True
            assert db.session.get(Cible, 4).contactee == 1

    def test_toggle_uncheck(self, app, data_dir):
        with app.app_context():
            # id=2 (Groupe SAFO) contactee=1, no candidatures
            result = toggle_cible(2, False)
            assert result is True
            assert db.session.get(Cible, 2).contactee == 0

    def test_toggle_missing_returns_false(self, app, data_dir):
        with app.app_context():
            result = toggle_cible(9999, True)
            assert result is False

    def test_toggle_locked_by_active_candidature_returns_none(self, app, data_dir):
        with app.app_context():
            # First mark cible 4 as contactee, then try to uncheck
            toggle_cible(4, True)
            # acme-corp is linked to cible 4, statut=envoyee (not archivee)
            result = toggle_cible(4, False)
            assert result is None

    def test_toggle_archived_candidature_allows_uncheck(self, app, data_dir):
        with app.app_context():
            from services.candidature import update_candidature

            # Archive the acme-corp candidature so cible 4 can be unchecked
            # Transition: envoyee -> refusee -> archivee
            update_candidature("acme-corp", {"statut": "refusee"})
            update_candidature("acme-corp", {"statut": "archivee"})
            toggle_cible(4, True)
            result = toggle_cible(4, False)
            assert result is True


# ---------------------------------------------------------------------------
# get_cible_detail
# ---------------------------------------------------------------------------


class TestGetCibleDetail:
    def test_returns_dict_with_contacts_and_candidatures(self, app, data_dir):
        with app.app_context():
            detail = get_cible_detail(4)  # Orange Caraibe: 2 contacts, 1 candidature
            assert detail is not None
            assert detail["id"] == 4
            assert detail["nom"] == "Orange Caraibe"
            assert detail["categorie"] == "entreprises"
            assert len(detail["contacts"]) == 2
            assert len(detail["candidatures"]) == 1

    def test_contact_fields_present(self, app, data_dir):
        with app.app_context():
            detail = get_cible_detail(4)
            contact = detail["contacts"][0]
            assert "id" in contact
            assert "nom" in contact
            assert "prenom" in contact
            assert "email" in contact
            assert "fonction" in contact

    def test_candidature_fields_present(self, app, data_dir):
        with app.app_context():
            detail = get_cible_detail(4)
            cand = detail["candidatures"][0]
            assert cand["slug"] == "acme-corp"
            assert "statut" in cand
            assert "priorite" in cand

    def test_excludes_archived_candidatures(self, app, data_dir):
        with app.app_context():
            from services.candidature import update_candidature

            update_candidature("acme-corp", {"statut": "refusee"})
            update_candidature("acme-corp", {"statut": "archivee"})
            detail = get_cible_detail(4)
            assert len(detail["candidatures"]) == 0

    def test_missing_cible_returns_none(self, app, data_dir):
        with app.app_context():
            detail = get_cible_detail(9999)
            assert detail is None

    def test_cible_with_no_contacts(self, app, data_dir):
        with app.app_context():
            detail = get_cible_detail(5)  # Digicel — no contacts
            assert detail["contacts"] == []

    def test_contains_all_base_fields(self, app, data_dir):
        with app.app_context():
            detail = get_cible_detail(4)
            expected_fields = (
                "id",
                "nom",
                "categorie",
                "contactee",
                "position",
                "url",
                "description",
                "email",
                "linkedin",
                "inscrit_plateforme",
            )
            for field in expected_fields:
                assert field in detail


# ---------------------------------------------------------------------------
# create_contact
# ---------------------------------------------------------------------------


class TestCreateContact:
    def test_creates_contact_for_existing_cible(self, app, data_dir):
        with app.app_context():
            contact = create_contact(5, nom="Doe", prenom="John", email="john@digicel.com", fonction="CEO")
            assert contact is not None
            assert isinstance(contact, Contact)
            assert contact.nom == "Doe"
            assert contact.cible_id == 5

    def test_create_contact_missing_cible_returns_none(self, app, data_dir):
        with app.app_context():
            result = create_contact(9999, nom="Ghost", prenom="Ghost")
            assert result is None

    def test_contact_persisted_in_db(self, app, data_dir):
        with app.app_context():
            contact = create_contact(5, nom="Persisted", prenom="Test")
            contact_id = contact.id
            fetched = db.session.get(Contact, contact_id)
            assert fetched is not None
            assert fetched.nom == "Persisted"


# ---------------------------------------------------------------------------
# update_contact
# ---------------------------------------------------------------------------


class TestUpdateContact:
    def test_update_existing_contact(self, app, data_dir):
        with app.app_context():
            result = update_contact(1, nom="Dupont-Updated", fonction="CTO")
            assert result is not None
            assert result.nom == "Dupont-Updated"
            assert result.fonction == "CTO"

    def test_update_returns_contact_object(self, app, data_dir):
        with app.app_context():
            result = update_contact(2, email="new@orange.gp")
            assert isinstance(result, Contact)
            assert result.email == "new@orange.gp"

    def test_update_missing_contact_returns_none(self, app, data_dir):
        with app.app_context():
            result = update_contact(9999, nom="Ghost")
            assert result is None

    def test_update_ignores_unknown_fields(self, app, data_dir):
        with app.app_context():
            # Should not raise
            result = update_contact(1, cible_id=999)  # not in _CONTACT_UPDATE_FIELDS
            assert result is not None
            # cible_id should remain unchanged
            assert result.cible_id == 4


# ---------------------------------------------------------------------------
# delete_contact
# ---------------------------------------------------------------------------


class TestDeleteContact:
    def test_delete_existing_contact(self, app, data_dir):
        with app.app_context():
            result = delete_contact(3)  # Paul Durand, cible 7
            assert result is True
            assert db.session.get(Contact, 3) is None

    def test_delete_missing_contact_returns_false(self, app, data_dir):
        with app.app_context():
            result = delete_contact(9999)
            assert result is False

    def test_delete_removes_from_db(self, app, data_dir):
        with app.app_context():
            delete_contact(1)
            assert db.session.get(Contact, 1) is None
