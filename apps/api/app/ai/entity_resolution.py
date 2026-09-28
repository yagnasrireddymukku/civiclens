"""Resolves an optional `(entity_type, entity_slug)` request hint to an
entity id — reused when a citizen asks a question while viewing a
specific job/service/scheme/document page, so that entity's own chunk is
always included in retrieval even if the free-text question doesn't
literally match its title (see `app.ai.service.answer_question`).

Same cross-module-read pattern `app.eligibility.service.resolve_entity`
already established, extended to the fourth entity type (`document`)
Eligibility deliberately excludes but Civic AI does not — a document is
a perfectly good thing to ask an explanatory question about, even though
it isn't something a citizen is "eligible" for.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.enums import AIEntityType
from app.documents import service as documents_service
from app.jobs import service as jobs_service
from app.schemes import service as schemes_service
from app.services import service as services_service


@dataclass(frozen=True, slots=True)
class ResolvedAIEntity:
    entity_type: AIEntityType
    entity_id: uuid.UUID
    slug: str


def resolve_entity(
    session: Session, entity_type: AIEntityType, slug: str
) -> ResolvedAIEntity | None:
    """`None` for an entity that doesn't exist *or* isn't publicly
    visible — the same "don't distinguish the two" convention every
    domain's own `get_*_by_slug` already follows."""

    if entity_type == AIEntityType.JOB:
        job_row = jobs_service.get_job_by_slug(session, slug)
        return None if job_row is None else ResolvedAIEntity(entity_type, job_row.job.id, slug)
    if entity_type == AIEntityType.SERVICE:
        service_row = services_service.get_service_by_slug(session, slug)
        return (
            None
            if service_row is None
            else ResolvedAIEntity(entity_type, service_row.service.id, slug)
        )
    if entity_type == AIEntityType.SCHEME:
        scheme_row = schemes_service.get_scheme_by_slug(session, slug)
        return (
            None
            if scheme_row is None
            else ResolvedAIEntity(entity_type, scheme_row.scheme.id, slug)
        )
    if entity_type == AIEntityType.DOCUMENT:
        document_row = documents_service.get_document_by_slug(session, slug)
        return (
            None
            if document_row is None
            else ResolvedAIEntity(entity_type, document_row.document.id, slug)
        )
    raise AssertionError(f"unreachable entity_type {entity_type}")  # pragma: no cover
