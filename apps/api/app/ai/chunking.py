"""Deterministic knowledge-chunk construction — docs/AI_ARCHITECTURE.md
§3-4, docs/DATABASE.md §16. `build_chunk_text` is a pure function of an
already-loaded ORM row (no I/O, no randomness, no wall-clock read): the
same entity always produces the same chunk text, which is what "keep
chunking deterministic" (this phase's §4) actually requires.

One chunk per entity (MVP scope, see `app.ai.models.KnowledgeChunk`'s
module docstring) — built from richer detail than
`search_documents.searchable_text` carries (that field is deliberately
thin, weighted low for full-text search, see
`app.search.models.SearchDocument`'s module docstring), so each domain
gets its own small formatter here reading the entity's full description
and structured child rows (requirements/benefits/fees/application
methods) — real content a citizen's question is actually about, not
just a search snippet.

Each formatter reads another domain's ORM models directly — the same
established cross-module-read precedent `app.eligibility.service` and
`app.documents.service.get_required_by` already use (CLAUDE.md rule 10's
carve-out for an explicit, modeled relationship); models are this
codebase's public read interface, not domain-internal state.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.ai.enums import AIEntityType
from app.documents.models import CivicDocument
from app.jobs.models import Job
from app.schemes.models import Scheme
from app.services.models import Service


def _join_sentences(*parts: str | None) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def _build_job_chunk(job: Job) -> str:
    lines = [job.title]
    if job.summary:
        lines.append(job.summary)
    if job.description:
        lines.append(job.description)
    facts = []
    if job.employment_type:
        facts.append(f"Employment type: {job.employment_type.value}.")
    if job.category:
        facts.append(f"Category: {job.category}.")
    if job.min_age is not None or job.max_age is not None:
        lo = job.min_age if job.min_age is not None else "no minimum"
        hi = job.max_age if job.max_age is not None else "no maximum"
        facts.append(f"Age range: {lo} to {hi}.")
    if job.qualification_summary:
        facts.append(f"Qualification: {job.qualification_summary}")
    if job.experience_summary:
        facts.append(f"Experience: {job.experience_summary}")
    if job.salary_summary:
        facts.append(f"Salary: {job.salary_summary}")
    lines.append(_join_sentences(*facts))
    return _join_sentences(*lines)


def _build_service_chunk(service: Service) -> str:
    lines = [service.name]
    if service.short_description:
        lines.append(service.short_description)
    if service.description:
        lines.append(service.description)
    facts = []
    if service.service_type:
        facts.append(f"Service type: {service.service_type}.")
    if service.target_audience:
        facts.append(f"For: {service.target_audience}")
    if service.delivery_mode:
        facts.append(f"Delivery mode: {service.delivery_mode.value}.")
    if service.fee_summary:
        facts.append(f"Fee: {service.fee_summary}")
    if service.processing_time_summary:
        facts.append(f"Processing time: {service.processing_time_summary}")
    lines.append(_join_sentences(*facts))
    for requirement in service.requirements:
        lines.append(f"Requirement: {requirement.description}")
    for method in service.application_methods:
        instructions = f" {method.instructions}" if method.instructions else ""
        lines.append(f"Apply via {method.channel_type.value}.{instructions}")
    return _join_sentences(*lines)


def _build_scheme_chunk(scheme: Scheme) -> str:
    lines = [scheme.name]
    if scheme.short_description:
        lines.append(scheme.short_description)
    if scheme.description:
        lines.append(scheme.description)
    if scheme.target_audience:
        lines.append(f"For: {scheme.target_audience}")
    lines.append(f"Category: {scheme.category.value}.")
    for benefit in scheme.benefits:
        amount = f" Amount: {benefit.amount_summary}." if benefit.amount_summary else ""
        lines.append(f"Benefit ({benefit.benefit_type.value}): {benefit.description}{amount}")
    for requirement in scheme.requirements:
        lines.append(f"Requirement: {requirement.description}")
    if scheme.scholarship_detail is not None:
        detail = scheme.scholarship_detail
        facts = []
        if detail.education_level:
            facts.append(f"Education level: {detail.education_level.value}.")
        if detail.minimum_percentage is not None:
            facts.append(f"Minimum percentage required: {detail.minimum_percentage}.")
        if detail.minimum_cgpa is not None:
            facts.append(f"Minimum CGPA required: {detail.minimum_cgpa}.")
        if detail.academic_requirement_notes:
            facts.append(detail.academic_requirement_notes)
        lines.append(_join_sentences(*facts))
    return _join_sentences(*lines)


def _build_document_chunk(document: CivicDocument) -> str:
    lines = [document.name]
    if document.short_description:
        lines.append(document.short_description)
    if document.description:
        lines.append(document.description)
    if document.purpose:
        lines.append(f"Purpose: {document.purpose}")
    facts = []
    if document.fee_summary:
        facts.append(f"Fee: {document.fee_summary}")
    if document.processing_time_summary:
        facts.append(f"Processing time: {document.processing_time_summary}")
    if document.validity_summary:
        facts.append(f"Validity: {document.validity_summary}")
    if document.renewal_summary:
        facts.append(f"Renewal: {document.renewal_summary}")
    lines.append(_join_sentences(*facts))
    for requirement in document.requirements:
        lines.append(f"Requirement: {requirement.description}")
    for supporting in document.supporting_documents:
        mandatory = "mandatory" if supporting.is_mandatory else "optional"
        lines.append(f"Supporting document needed ({mandatory}): {supporting.name}")
    return _join_sentences(*lines)


def build_chunk_text(
    session: Session, entity_type: AIEntityType, entity_id: uuid.UUID
) -> str | None:
    """`None` when the entity no longer exists — the caller (`app.ai.
    indexing`) treats that as "nothing to index," not an error.

    Deliberately explicit per-branch dispatch rather than a
    dict-of-(model, builder) lookup table: each domain's row has a
    different, incompatible type, which a shared dispatch dict can't
    express without erasing type information that would otherwise let
    a type checker verify each builder is only ever called with the row
    shape it actually expects."""

    if entity_type == AIEntityType.JOB:
        job = session.get(Job, entity_id)
        return _build_job_chunk(job) if job is not None else None
    if entity_type == AIEntityType.SERVICE:
        service = session.get(Service, entity_id)
        return _build_service_chunk(service) if service is not None else None
    if entity_type == AIEntityType.SCHEME:
        scheme = session.get(Scheme, entity_id)
        return _build_scheme_chunk(scheme) if scheme is not None else None
    if entity_type == AIEntityType.DOCUMENT:
        document = session.get(CivicDocument, entity_id)
        return _build_document_chunk(document) if document is not None else None
    raise AssertionError(f"unreachable entity_type {entity_type}")  # pragma: no cover


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
