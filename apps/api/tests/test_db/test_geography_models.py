"""Geography model/relationship/constraint tests.

Fixture data is unambiguously fictional per docs/DATA_GOVERNANCE.md §7 /
docs/TESTING.md §15: state code "ZZ", state name "Testland" — values that
can never collide with a real Indian state.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.geography.enums import ConstituencyType, StateStatus
from app.geography.models import Constituency, District, State


def make_state(**overrides) -> State:
    defaults = dict(name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED)
    defaults.update(overrides)
    return State(**defaults)


def test_create_state_district_constituency_with_relationships(db_session: Session) -> None:
    state = make_state()
    db_session.add(state)
    db_session.flush()

    district = District(state_id=state.id, name="Sampleburg", code="SB", slug="sampleburg")
    db_session.add(district)
    db_session.flush()

    constituency = Constituency(
        state_id=state.id,
        district_id=district.id,
        type=ConstituencyType.ASSEMBLY,
        name="Test Assembly Constituency",
        slug="test-assembly-constituency",
    )
    db_session.add(constituency)
    db_session.flush()

    db_session.refresh(state)
    assert district in state.districts
    assert constituency in state.constituencies
    assert constituency.district is district


def test_state_code_must_be_unique(db_session: Session) -> None:
    db_session.add(make_state(name="Testland One"))
    db_session.flush()

    db_session.add(make_state(name="Testland Two"))  # same code "ZZ"
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_state_name_must_be_unique(db_session: Session) -> None:
    db_session.add(make_state(code="Z1"))
    db_session.flush()

    db_session.add(make_state(code="Z2"))  # same name "Testland"
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_state_slug_must_be_unique(db_session: Session) -> None:
    db_session.add(make_state(name="Testland A", code="ZA"))
    db_session.flush()

    db_session.add(make_state(name="Testland B", code="ZB"))  # same slug "testland"
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_district_code_unique_within_state_but_reusable_across_states(
    db_session: Session,
) -> None:
    state_one = make_state(name="Testland One", code="Z1", slug="testland-one")
    state_two = make_state(name="Testland Two", code="Z2", slug="testland-two")
    db_session.add_all([state_one, state_two])
    db_session.flush()

    db_session.add(District(state_id=state_one.id, name="Sampleburg", code="SB", slug="sampleburg"))
    db_session.flush()

    # Same district code "SB" in a *different* state must be allowed.
    db_session.add(District(state_id=state_two.id, name="Sampleburg", code="SB", slug="sampleburg"))
    db_session.flush()  # must not raise


def test_district_code_rejected_when_duplicated_within_same_state(db_session: Session) -> None:
    state = make_state()
    db_session.add(state)
    db_session.flush()

    db_session.add(District(state_id=state.id, name="Sampleburg", code="SB", slug="sampleburg"))
    db_session.flush()

    db_session.add(
        District(state_id=state.id, name="Sampleburg Two", code="SB", slug="sampleburg-two")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_district_requires_an_existing_state(db_session: Session) -> None:
    import uuid

    db_session.add(
        District(state_id=uuid.uuid4(), name="Orphan District", code="OD", slug="orphan-district")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_state_cascades_to_its_districts(db_session: Session) -> None:
    state = make_state()
    district = District(name="Sampleburg", code="SB", slug="sampleburg")
    state.districts.append(district)
    db_session.add(state)
    db_session.flush()
    district_id = district.id

    db_session.delete(state)
    db_session.flush()

    assert db_session.get(District, district_id) is None


def test_constituency_district_is_optional(db_session: Session) -> None:
    state = make_state()
    db_session.add(state)
    db_session.flush()

    constituency = Constituency(
        state_id=state.id,
        district_id=None,
        type=ConstituencyType.PARLIAMENTARY,
        name="Statewide Test Constituency",
        slug="statewide-test-constituency",
    )
    db_session.add(constituency)
    db_session.flush()  # must not raise — district_id is nullable

    assert constituency.district is None


def test_constituency_slug_unique_within_state_and_type_but_reusable_across_types(
    db_session: Session,
) -> None:
    state = make_state()
    db_session.add(state)
    db_session.flush()

    db_session.add(
        Constituency(
            state_id=state.id,
            type=ConstituencyType.ASSEMBLY,
            name="Test Constituency",
            slug="test-constituency",
        )
    )
    db_session.flush()

    # Same slug, same state, but a *different* type — must be allowed,
    # per docs' note that an assembly and parliamentary constituency in
    # the same state may share a name/slug.
    db_session.add(
        Constituency(
            state_id=state.id,
            type=ConstituencyType.PARLIAMENTARY,
            name="Test Constituency",
            slug="test-constituency",
        )
    )
    db_session.flush()  # must not raise

    # But the same slug + same type in the same state must be rejected.
    db_session.add(
        Constituency(
            state_id=state.id,
            type=ConstituencyType.ASSEMBLY,
            name="Test Constituency Duplicate",
            slug="test-constituency",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
