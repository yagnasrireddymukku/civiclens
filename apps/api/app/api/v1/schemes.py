"""GET /api/v1/schemes, GET /api/v1/schemes/{slug} — see docs/API.md
§15 for the pagination/filtering conventions and docs/DATABASE.md §12
for the underlying schema. Route handlers here only translate between
HTTP and `app.schemes.service` plus map ORM rows to response schemas —
no query logic lives in this file. Mirrors `app/api/v1/services.py`
exactly.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.schemes import service
from app.schemes.schemas import (
    ApplicationMethodSummary,
    BenefitSummary,
    DepartmentSummary,
    OrganizationSummary,
    PaginationMeta,
    RelatedServiceSummary,
    RequiredDocumentSummary,
    RequirementSummary,
    SchemeDetail,
    SchemeListItem,
    SchemeListQueryParams,
    SchemeListResponse,
    ScholarshipDetailSummary,
    SourceSummary,
)
from app.schemes.service import SchemeRow
from app.services.service import is_publicly_visible as is_service_publicly_visible

router = APIRouter(tags=["schemes"])


def _scheme_list_item(row: SchemeRow) -> SchemeListItem:
    scheme = row.scheme
    return SchemeListItem(
        slug=scheme.slug,
        name=scheme.name,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        short_description=scheme.short_description,
        category=scheme.category,
        state=row.state_name,
        district=row.district_name,
        status=scheme.status,
        verification_status=scheme.verification_status,
        last_verified=scheme.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
    )


@router.get("/schemes", response_model=SchemeListResponse)
def list_schemes(
    params: Annotated[SchemeListQueryParams, Query()],
    db: Session = Depends(get_db),
) -> SchemeListResponse:
    result = service.list_schemes(
        db,
        state_id=params.state_id,
        district_id=params.district_id,
        organization_id=params.organization_id,
        department_id=params.department_id,
        category=params.category,
        education_level=params.education_level,
        status=params.status,
        date_from=params.date_from,
        date_to=params.date_to,
        page=params.page,
        page_size=params.page_size,
    )
    return SchemeListResponse(
        results=[_scheme_list_item(row) for row in result.rows],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
    )


@router.get("/schemes/{slug}", response_model=SchemeDetail)
def get_scheme(slug: str, db: Session = Depends(get_db)) -> SchemeDetail:
    row = service.get_scheme_by_slug(db, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Scheme not found")

    scheme = row.scheme
    return SchemeDetail(
        slug=scheme.slug,
        name=scheme.name,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        short_description=scheme.short_description,
        description=scheme.description,
        category=scheme.category,
        target_audience=scheme.target_audience,
        state=row.state_name,
        district=row.district_name,
        official_scheme_url=scheme.official_scheme_url,
        application_url=scheme.application_url,
        status=scheme.status,
        verification_status=scheme.verification_status,
        last_verified=scheme.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
        benefits=[
            BenefitSummary(
                benefit_type=benefit.benefit_type,
                description=benefit.description,
                amount_summary=benefit.amount_summary,
                frequency_summary=benefit.frequency_summary,
            )
            for benefit in scheme.benefits
        ],
        requirements=[
            RequirementSummary(
                requirement_type=requirement.requirement_type,
                description=requirement.description,
                min_value=requirement.min_value,
                max_value=requirement.max_value,
            )
            for requirement in scheme.requirements
        ],
        required_documents=[
            RequiredDocumentSummary(
                name=document.name,
                description=document.description,
                is_mandatory=document.is_mandatory,
            )
            for document in scheme.required_documents
        ],
        application_methods=[
            ApplicationMethodSummary(
                channel_type=method.channel_type,
                url=method.url,
                instructions=method.instructions,
            )
            for method in scheme.application_methods
        ],
        # Never surface a related service that isn't itself publicly
        # visible (this phase's §28) — a scheme's provenance/publication
        # trust boundary doesn't extend to the services it links to.
        related_services=[
            RelatedServiceSummary(
                slug=related.service.slug, name=related.service.name, note=related.note
            )
            for related in scheme.related_services
            if is_service_publicly_visible(related.service)
        ],
        scholarship=(
            ScholarshipDetailSummary(
                education_level=scheme.scholarship_detail.education_level,
                course_discipline=scheme.scholarship_detail.course_discipline,
                institution_type=scheme.scholarship_detail.institution_type,
                study_mode=scheme.scholarship_detail.study_mode,
                year_of_study=scheme.scholarship_detail.year_of_study,
                minimum_percentage=scheme.scholarship_detail.minimum_percentage,
                minimum_cgpa=scheme.scholarship_detail.minimum_cgpa,
                academic_requirement_notes=scheme.scholarship_detail.academic_requirement_notes,
                application_opens=scheme.scholarship_detail.application_opens,
                application_closes=scheme.scholarship_detail.application_closes,
                correction_window_end=scheme.scholarship_detail.correction_window_end,
                academic_year=scheme.scholarship_detail.academic_year,
                renewable=scheme.scholarship_detail.renewable,
                renewal_notes=scheme.scholarship_detail.renewal_notes,
            )
            if scheme.scholarship_detail is not None
            else None
        ),
    )
