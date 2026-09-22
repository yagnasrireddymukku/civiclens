"""GET /api/v1/services, GET /api/v1/services/{slug} — see docs/API.md
§14 for the pagination/filtering conventions and docs/DATABASE.md §10
for the underlying schema. Route handlers here only translate between
HTTP and `app.services.service` plus map ORM rows to response schemas —
no query logic lives in this file. Mirrors `app/api/v1/jobs.py` exactly.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.services import service
from app.services.schemas import (
    ApplicationMethodSummary,
    DepartmentSummary,
    OrganizationSummary,
    PaginationMeta,
    RequiredDocumentSummary,
    RequirementSummary,
    ServiceDetail,
    ServiceListItem,
    ServiceListQueryParams,
    ServiceListResponse,
    SourceSummary,
)
from app.services.service import ServiceRow

router = APIRouter(tags=["services"])


def _service_list_item(row: ServiceRow) -> ServiceListItem:
    svc = row.service
    return ServiceListItem(
        slug=svc.slug,
        name=svc.name,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        short_description=svc.short_description,
        category=svc.category,
        service_type=svc.service_type,
        delivery_mode=svc.delivery_mode,
        state=row.state_name,
        district=row.district_name,
        status=svc.status,
        verification_status=svc.verification_status,
        last_verified=svc.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
    )


@router.get("/services", response_model=ServiceListResponse)
def list_services(
    params: Annotated[ServiceListQueryParams, Query()],
    db: Session = Depends(get_db),
) -> ServiceListResponse:
    result = service.list_services(
        db,
        state_id=params.state_id,
        district_id=params.district_id,
        organization_id=params.organization_id,
        department_id=params.department_id,
        category=params.category,
        delivery_mode=params.delivery_mode,
        status=params.status,
        date_from=params.date_from,
        date_to=params.date_to,
        page=params.page,
        page_size=params.page_size,
    )
    return ServiceListResponse(
        results=[_service_list_item(row) for row in result.rows],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
    )


@router.get("/services/{slug}", response_model=ServiceDetail)
def get_service(slug: str, db: Session = Depends(get_db)) -> ServiceDetail:
    row = service.get_service_by_slug(db, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Service not found")

    svc = row.service
    return ServiceDetail(
        slug=svc.slug,
        name=svc.name,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        short_description=svc.short_description,
        description=svc.description,
        category=svc.category,
        service_type=svc.service_type,
        target_audience=svc.target_audience,
        delivery_mode=svc.delivery_mode,
        state=row.state_name,
        district=row.district_name,
        official_service_url=svc.official_service_url,
        application_url=svc.application_url,
        fee_summary=svc.fee_summary,
        processing_time_summary=svc.processing_time_summary,
        location_summary=svc.location_summary,
        status=svc.status,
        verification_status=svc.verification_status,
        last_verified=svc.last_verified_at,
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
            for requirement in svc.requirements
        ],
        required_documents=[
            RequiredDocumentSummary(
                name=document.name,
                description=document.description,
                is_mandatory=document.is_mandatory,
            )
            for document in svc.required_documents
        ],
        application_methods=[
            ApplicationMethodSummary(
                channel_type=method.channel_type,
                url=method.url,
                instructions=method.instructions,
            )
            for method in svc.application_methods
        ],
    )
