"""Deterministic chunk-text construction — docs/AI_ARCHITECTURE.md §4's
"keep chunking deterministic" requirement: the same entity must always
produce the same chunk text and the same content hash.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.ai.chunking import build_chunk_text, content_hash
from app.ai.enums import AIEntityType
from app.schemes.enums import EducationLevel
from app.schemes.models import ScholarshipDetail
from tests.test_documents._helpers import (
    make_document,
    make_organization,
    make_scheme,
    make_service,
    make_source,
    make_state,
)
from tests.test_documents._helpers import (
    make_requirement as make_document_requirement,
)
from tests.test_jobs._helpers import make_job
from tests.test_schemes._helpers import make_requirement as make_scheme_requirement
from tests.test_services._helpers import make_requirement as make_service_requirement


def test_build_chunk_text_is_deterministic_for_a_job(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    first = build_chunk_text(db_session, AIEntityType.JOB, job.id)
    second = build_chunk_text(db_session, AIEntityType.JOB, job.id)

    assert first is not None
    assert first == second
    assert job.title in first
    assert content_hash(first) == content_hash(second)


def test_build_chunk_text_includes_job_age_range_and_qualification(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        min_age=18,
        max_age=30,
        qualification_summary="Bachelor's degree required.",
    )

    text = build_chunk_text(db_session, AIEntityType.JOB, job.id)

    assert text is not None
    assert "18" in text and "30" in text
    assert "Bachelor's degree required." in text


def test_build_chunk_text_returns_none_for_unknown_job(db_session: Session) -> None:
    import uuid

    assert build_chunk_text(db_session, AIEntityType.JOB, uuid.uuid4()) is None


def test_build_chunk_text_includes_service_requirements(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(db_session, organization=organization, source=source)
    make_service_requirement(
        db_session, service, description="Applicant must be a resident of Testland."
    )

    text = build_chunk_text(db_session, AIEntityType.SERVICE, service.id)

    assert text is not None
    assert "Applicant must be a resident of Testland." in text


def test_build_chunk_text_includes_scheme_benefits_and_requirements(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)
    make_scheme_requirement(db_session, scheme, description="Must be enrolled full-time.")

    text = build_chunk_text(db_session, AIEntityType.SCHEME, scheme.id)

    assert text is not None
    assert "Must be enrolled full-time." in text


def test_build_chunk_text_includes_scholarship_detail(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)
    detail = ScholarshipDetail(
        scheme_id=scheme.id,
        education_level=EducationLevel.UNDERGRADUATE,
        minimum_percentage=Decimal("60.00"),
        renewable=True,
    )
    db_session.add(detail)
    db_session.flush()
    db_session.refresh(scheme)

    text = build_chunk_text(db_session, AIEntityType.SCHEME, scheme.id)

    assert text is not None
    assert "UNDERGRADUATE" in text
    assert "60.00" in text


def test_build_chunk_text_includes_document_requirements_and_supporting_docs(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    make_document_requirement(db_session, document, description="Must show proof of address.")

    text = build_chunk_text(db_session, AIEntityType.DOCUMENT, document.id)

    assert text is not None
    assert "Must show proof of address." in text
