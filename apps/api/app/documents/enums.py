"""Documents & Certificates domain enums — see docs/DATABASE.md §14.

`RequirementType`/`ApplicationChannelType`/`DeliveryMode` are NOT
redefined here — Documents import the shared vocabulary directly from
`app.requirements.enums`, the same way Schemes/Services do. This is the
*third* real consumer of `RequirementType`/`ApplicationChannelType`
(after Services, Schemes) and the *second* of `DeliveryMode` (after
Services) — see that module's docstring for the extraction history.

`DocumentType`/`DocumentCategory` are two separate controlled taxonomies
(this phase's §6/§7), deliberately not collapsed into one: `DocumentType`
is a broad classification of the *kind of official record* (certificate,
identity document, permit, ...) while `DocumentCategory` is the *subject
matter* (residence, income, social category, ...) — a "Residence
Certificate" is `DocumentType.CERTIFICATE` + `DocumentCategory.RESIDENCE`,
distinct axes the same way `Job.employment_type` and `Job.category` are.
"""

import enum


class DocumentType(enum.StrEnum):
    CERTIFICATE = "CERTIFICATE"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    RECORD = "RECORD"
    PERMIT = "PERMIT"
    LICENSE = "LICENSE"
    REGISTRATION = "REGISTRATION"
    OTHER = "OTHER"


class DocumentCategory(enum.StrEnum):
    PERSONAL = "PERSONAL"
    IDENTITY = "IDENTITY"
    RESIDENCE = "RESIDENCE"
    INCOME = "INCOME"
    SOCIAL_CATEGORY = "SOCIAL_CATEGORY"
    EDUCATION = "EDUCATION"
    BIRTH_DEATH = "BIRTH_DEATH"
    DISABILITY = "DISABILITY"
    LAND_REVENUE = "LAND_REVENUE"
    EMPLOYMENT = "EMPLOYMENT"
    BUSINESS = "BUSINESS"
    FAMILY = "FAMILY"
    OTHER = "OTHER"


class DocumentPublicationStatus(enum.StrEnum):
    """Deliberately its own type, not shared with `ServicePublicationStatus`/
    `SchemePublicationStatus`/`JobPublicationStatus` even though all four
    have identical values — same domain-scoping reasoning as every prior
    phase's identical decision (see `app.services.enums`'s docstring)."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
