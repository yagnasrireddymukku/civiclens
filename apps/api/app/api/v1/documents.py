"""GET /api/v1/documents, GET /api/v1/documents/{slug} — see docs/API.md
§17 for the pagination/filtering conventions and docs/DATABASE.md §14
for the underlying schema. Route handlers here only translate between
HTTP and `app.documents.service` plus map ORM rows to response schemas —
no query logic lives in this file. Mirrors `app/api/v1/schemes.py`
exactly.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.documents import service
from app.documents.schemas import (
    ApplicationMethodSummary,
    CivicDocumentRefSummary,
    DepartmentSummary,
    DocumentDetail,
    DocumentListItem,
    DocumentListQueryParams,
    DocumentListResponse,
    OrganizationSummary,
    PaginationMeta,
    RequiredBySummary,
    RequirementSummary,
    ServiceRefSummary,
    SourceSummary,
    SupportingDocumentSummary,
)
from app.documents.service import DocumentRow
from app.services.service import is_publicly_visible as is_service_publicly_visible

router = APIRouter(tags=["documents"])


def _document_list_item(row: DocumentRow) -> DocumentListItem:
    document = row.document
    return DocumentListItem(
        slug=document.slug,
        name=document.name,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        short_description=document.short_description,
        document_type=document.document_type,
        category=document.category,
        delivery_mode=document.delivery_mode,
        state=row.state_name,
        district=row.district_name,
        status=document.status,
        verification_status=document.verification_status,
        last_verified=document.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    params: Annotated[DocumentListQueryParams, Query()],
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    result = service.list_documents(
        db,
        state_id=params.state_id,
        district_id=params.district_id,
        organization_id=params.organization_id,
        department_id=params.department_id,
        document_type=params.document_type,
        category=params.category,
        delivery_mode=params.delivery_mode,
        status=params.status,
        date_from=params.date_from,
        date_to=params.date_to,
        page=params.page,
        page_size=params.page_size,
    )
    return DocumentListResponse(
        results=[_document_list_item(row) for row in result.rows],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
    )


@router.get("/documents/{slug}", response_model=DocumentDetail)
def get_document(slug: str, db: Session = Depends(get_db)) -> DocumentDetail:
    row = service.get_document_by_slug(db, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    document = row.document
    required_by = service.get_required_by(db, document.id)

    return DocumentDetail(
        slug=document.slug,
        name=document.name,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        short_description=document.short_description,
        description=document.description,
        document_type=document.document_type,
        category=document.category,
        purpose=document.purpose,
        delivery_mode=document.delivery_mode,
        state=row.state_name,
        district=row.district_name,
        official_document_url=document.official_document_url,
        application_url=document.application_url,
        fee_summary=document.fee_summary,
        processing_time_summary=document.processing_time_summary,
        validity_summary=document.validity_summary,
        renewal_summary=document.renewal_summary,
        status=document.status,
        verification_status=document.verification_status,
        last_verified=document.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
        requirements=[
            RequirementSummary(
                requirement_type=requirement.requirement_type,
                description=requirement.description,
                min_value=requirement.min_value,
                max_value=requirement.max_value,
            )
            for requirement in document.requirements
        ],
        supporting_documents=[
            SupportingDocumentSummary(
                name=supporting.name,
                description=supporting.description,
                is_mandatory=supporting.is_mandatory,
                civic_document=(
                    CivicDocumentRefSummary(
                        slug=supporting.civic_document.slug, name=supporting.civic_document.name
                    )
                    if supporting.civic_document is not None
                    else None
                ),
            )
            for supporting in document.supporting_documents
        ],
        application_methods=[
            ApplicationMethodSummary(
                channel_type=method.channel_type,
                url=method.url,
                instructions=method.instructions,
            )
            for method in document.application_methods
        ],
        # Never surface an "obtained through" service that isn't itself
        # publicly visible — a document's trust boundary doesn't extend
        # to the service it links to (matches Scheme's identical
        # `related_services` rule, Phase 8).
        service=(
            ServiceRefSummary(slug=document.service.slug, name=document.service.name)
            if document.service is not None and is_service_publicly_visible(document.service)
            else None
        ),
        required_by=[
            RequiredBySummary(entity_type=entry.entity_type, slug=entry.slug, name=entry.name)
            for entry in required_by
        ],
    )
