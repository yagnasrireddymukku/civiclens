import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type {
  ApplicationChannelType,
  EducationLevel,
  SchemeDetail,
  StudyMode,
} from "@civiclens/types";
import { LastVerified, SourceBadge, VerificationStatus } from "@/components/civic";
import { Container } from "@/components/layout";
import { Breadcrumb } from "@/components/navigation";
import { ExternalLinkIcon } from "@/components/icons";
import { TrackButton } from "@/components/tracking";
import type { AppLocale } from "@/i18n/routing";
import { getSchemeBySlug } from "@/lib/schemes";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import styles from "./page.module.css";

interface SchemeDetailPageProps {
  params: Promise<{ locale: string; slug: string }>;
}

export async function generateMetadata({ params }: SchemeDetailPageProps): Promise<Metadata> {
  const { locale, slug } = await params;
  const result = await getSchemeBySlug(slug);

  if (!result.reachable || result.data === null) {
    // See apps/web/app/[locale]/services/[slug]/page.tsx's identical
    // note: notFound() renders the right content but doesn't reliably
    // set a 404 HTTP status under this project's [locale] routing (a
    // known, disclosed Next.js limitation, docs/ROADMAP.md Phase 4).
    // `noindex` is the mitigation available at this layer — preserved
    // here rather than reinvented.
    return {
      ...buildLocaleAwareMetadata({
        locale: locale as AppLocale,
        path: `/schemes/${slug}`,
        description: "Scheme not found.",
      }),
      robots: { index: false, follow: false },
    };
  }

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: `/schemes/${slug}`,
    title: result.data.name,
    description: result.data.short_description ?? result.data.name,
  });
}

// schema.org's own documentation of GovernmentService lists benefit
// programs ("food stamps, veterans benefits, etc.") as a direct
// example of the type — so, like Services, this is a genuine fit
// judged by real documented properties, not a name that merely sounds
// plausible (docs/SEO.md §6). `offers`/`Offer.price` is deliberately
// NOT used for benefit amounts: this project never states a real
// figure a source doesn't provide, and `Offer.price` implies a
// definite price schema.org readers would expect to be exact.
function governmentServiceJsonLd(scheme: SchemeDetail): Record<string, unknown> {
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "GovernmentService",
    name: scheme.name,
    provider: { "@type": "GovernmentOrganization", name: scheme.organization.name },
    serviceType: scheme.category,
  };
  if (scheme.short_description) jsonLd.description = scheme.short_description;
  if (scheme.state) jsonLd.areaServed = { "@type": "State", name: scheme.state };
  if (scheme.target_audience) {
    jsonLd.audience = { "@type": "Audience", audienceType: scheme.target_audience };
  }
  const channelsWithUrls = scheme.application_methods.filter((method) => method.url);
  if (channelsWithUrls.length > 0) {
    jsonLd.availableChannel = channelsWithUrls.map((method) => ({
      "@type": "ServiceChannel",
      serviceUrl: method.url,
    }));
  }
  return jsonLd;
}

export default async function SchemeDetailPage({ params }: SchemeDetailPageProps) {
  const { locale, slug } = await params;
  setRequestLocale(locale);

  const [t, result] = await Promise.all([getTranslations("Schemes"), getSchemeBySlug(slug)]);

  if (!result.reachable) {
    return (
      <Container>
        <div className={styles.page}>
          <p className={styles.errorText}>{result.error}</p>
        </div>
      </Container>
    );
  }
  if (result.data === null) {
    notFound();
  }

  const scheme = result.data;

  const channelLabels: Record<ApplicationChannelType, string> = {
    ONLINE: t("channelOnline"),
    OFFLINE: t("channelOffline"),
    MOBILE_APP: t("channelMobileApp"),
    MEESEVA: t("channelMeeseva"),
    DEPARTMENT_PORTAL: t("channelDepartmentPortal"),
    SERVICE_CENTER: t("channelServiceCenter"),
    IN_PERSON: t("channelInPerson"),
    OTHER: t("channelOther"),
  };

  const educationLevelLabels: Record<EducationLevel, string> = {
    SCHOOL: t("educationLevelSchool"),
    INTERMEDIATE: t("educationLevelIntermediate"),
    DIPLOMA: t("educationLevelDiploma"),
    UNDERGRADUATE: t("educationLevelUndergraduate"),
    POSTGRADUATE: t("educationLevelPostgraduate"),
    DOCTORAL: t("educationLevelDoctoral"),
    PROFESSIONAL: t("educationLevelProfessional"),
    VOCATIONAL: t("educationLevelVocational"),
    OTHER: t("educationLevelOther"),
  };

  const studyModeLabels: Record<StudyMode, string> = {
    FULL_TIME: t("studyModeFullTime"),
    PART_TIME: t("studyModePartTime"),
    DISTANCE: t("studyModeDistance"),
    ONLINE: t("studyModeOnline"),
    OTHER: t("studyModeOther"),
  };

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "CivicLens", item: `/${locale}` },
      { "@type": "ListItem", position: 2, name: t("listTitle"), item: `/${locale}/schemes` },
      { "@type": "ListItem", position: 3, name: scheme.name },
    ],
  };

  return (
    <Container>
      <div className={styles.page}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(governmentServiceJsonLd(scheme)) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
        />

        <Breadcrumb
          items={[
            { label: "CivicLens", href: "/" },
            { label: t("listTitle"), href: "/schemes" },
            { label: scheme.name },
          ]}
        />

        <header className={styles.header}>
          <h1 className={styles.title}>{scheme.name}</h1>
          <p className={styles.subtitle}>
            {scheme.organization.name}
            {scheme.department && ` · ${scheme.department.name}`}
          </p>
          <div className={styles.badges}>
            <VerificationStatus status={scheme.verification_status} />
            {scheme.last_verified && (
              <LastVerified date={new Date(scheme.last_verified)} locale={locale} />
            )}
          </div>
          <TrackButton entityType="scheme" entitySlug={scheme.slug} />
        </header>

        <section className={styles.section} aria-labelledby="overview-heading">
          <h2 id="overview-heading" className={styles.sectionHeading}>
            {t("sectionOverview")}
          </h2>
          <p>{scheme.description ?? scheme.short_description}</p>
        </section>

        {scheme.target_audience && (
          <section className={styles.section} aria-labelledby="audience-heading">
            <h2 id="audience-heading" className={styles.sectionHeading}>
              {t("sectionWhoCanBenefit")}
            </h2>
            <p>{scheme.target_audience}</p>
          </section>
        )}

        {scheme.benefits.length > 0 && (
          <section className={styles.section} aria-labelledby="benefits-heading">
            <h2 id="benefits-heading" className={styles.sectionHeading}>
              {t("sectionBenefits")}
            </h2>
            <ul className={styles.factItemList}>
              {scheme.benefits.map((benefit, index) => (
                <li key={index}>
                  {benefit.description}
                  {benefit.amount_summary && ` — ${benefit.amount_summary}`}
                  {benefit.frequency_summary && ` (${benefit.frequency_summary})`}
                </li>
              ))}
            </ul>
          </section>
        )}

        {scheme.scholarship && (
          <section className={styles.section} aria-labelledby="scholarship-heading">
            <h2 id="scholarship-heading" className={styles.sectionHeading}>
              {t("sectionScholarshipDetails")}
            </h2>
            <ul className={styles.factItemList}>
              {scheme.scholarship.education_level && (
                <li>
                  {t("scholarshipEducationLevel")}:{" "}
                  {educationLevelLabels[scheme.scholarship.education_level]}
                </li>
              )}
              {scheme.scholarship.course_discipline && (
                <li>
                  {t("scholarshipCourseDiscipline")}: {scheme.scholarship.course_discipline}
                </li>
              )}
              {scheme.scholarship.institution_type && (
                <li>
                  {t("scholarshipInstitutionType")}: {scheme.scholarship.institution_type}
                </li>
              )}
              {scheme.scholarship.study_mode && (
                <li>
                  {t("scholarshipStudyMode")}: {studyModeLabels[scheme.scholarship.study_mode]}
                </li>
              )}
              {scheme.scholarship.year_of_study && (
                <li>
                  {t("scholarshipYearOfStudy")}: {scheme.scholarship.year_of_study}
                </li>
              )}
              {scheme.scholarship.minimum_percentage !== null && (
                <li>
                  {t("scholarshipMinimumPercentage")}: {scheme.scholarship.minimum_percentage}%
                </li>
              )}
              {scheme.scholarship.minimum_cgpa !== null && (
                <li>
                  {t("scholarshipMinimumCgpa")}: {scheme.scholarship.minimum_cgpa}
                </li>
              )}
              {scheme.scholarship.academic_requirement_notes && (
                <li>{scheme.scholarship.academic_requirement_notes}</li>
              )}
              {scheme.scholarship.academic_year && (
                <li>
                  {t("scholarshipAcademicYear")}: {scheme.scholarship.academic_year}
                </li>
              )}
              <li>
                {t("scholarshipRenewable")}:{" "}
                {scheme.scholarship.renewable
                  ? t("scholarshipRenewableYes")
                  : t("scholarshipRenewableNo")}
                {scheme.scholarship.renewable &&
                  scheme.scholarship.renewal_notes &&
                  ` — ${scheme.scholarship.renewal_notes}`}
              </li>
            </ul>
            {(scheme.scholarship.application_opens ||
              scheme.scholarship.application_closes ||
              scheme.scholarship.correction_window_end) && (
              <div className={styles.badges}>
                {scheme.scholarship.application_opens && (
                  <LastVerified
                    date={new Date(scheme.scholarship.application_opens)}
                    locale={locale}
                    label={t("scholarshipApplicationOpens")}
                  />
                )}
                {scheme.scholarship.application_closes && (
                  <LastVerified
                    date={new Date(scheme.scholarship.application_closes)}
                    locale={locale}
                    label={t("scholarshipApplicationCloses")}
                  />
                )}
                {scheme.scholarship.correction_window_end && (
                  <LastVerified
                    date={new Date(scheme.scholarship.correction_window_end)}
                    locale={locale}
                    label={t("scholarshipCorrectionWindowEnd")}
                  />
                )}
              </div>
            )}
          </section>
        )}

        {scheme.requirements.length > 0 && (
          <section className={styles.section} aria-labelledby="eligibility-heading">
            <h2 id="eligibility-heading" className={styles.sectionHeading}>
              {t("sectionEligibility")}
            </h2>
            <ul className={styles.factItemList}>
              {scheme.requirements.map((requirement, index) => (
                <li key={index}>{requirement.description}</li>
              ))}
            </ul>
          </section>
        )}

        {scheme.required_documents.length > 0 && (
          <section className={styles.section} aria-labelledby="documents-heading">
            <h2 id="documents-heading" className={styles.sectionHeading}>
              {t("sectionRequiredDocuments")}
            </h2>
            <ul className={styles.factItemList}>
              {scheme.required_documents.map((document, index) => (
                <li key={index}>
                  {document.name}
                  {" — "}
                  <span className={styles.mandatoryTag}>
                    {document.is_mandatory ? t("mandatoryLabel") : t("optionalLabel")}
                  </span>
                  {document.description && `: ${document.description}`}
                </li>
              ))}
            </ul>
          </section>
        )}

        {scheme.application_methods.length > 0 && (
          <section className={styles.section} aria-labelledby="application-methods-heading">
            <h2 id="application-methods-heading" className={styles.sectionHeading}>
              {t("sectionApplicationMethods")}
            </h2>
            <ul className={styles.factItemList}>
              {scheme.application_methods.map((method, index) => (
                <li key={index}>
                  {channelLabels[method.channel_type]}
                  {method.instructions && ` — ${method.instructions}`}
                  {method.url && (
                    <>
                      {" "}
                      <a
                        href={method.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.officialLink}
                      >
                        {t("sectionOfficialApplication")}
                        <ExternalLinkIcon className={styles.linkIcon} />
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {scheme.related_services.length > 0 && (
          <section className={styles.section} aria-labelledby="related-services-heading">
            <h2 id="related-services-heading" className={styles.sectionHeading}>
              {t("sectionRelatedServices")}
            </h2>
            <ul className={styles.factItemList}>
              {scheme.related_services.map((related, index) => (
                <li key={index}>
                  {related.name}
                  {related.note && ` — ${related.note}`}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className={styles.section} aria-labelledby="verification-heading">
          <h2 id="verification-heading" className={styles.sectionHeading}>
            {t("sectionVerification")}
          </h2>
          <div className={styles.badges}>
            <SourceBadge
              kind={scheme.verification_status === "VERIFIED" ? "verified" : "available"}
            />
            {scheme.last_verified && (
              <LastVerified date={new Date(scheme.last_verified)} locale={locale} />
            )}
            <span className={styles.sourceOrganization}>{scheme.source.organization}</span>
            {scheme.official_scheme_url && (
              <a
                href={scheme.official_scheme_url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.officialLink}
              >
                {t("sectionOfficialSource")}
                <ExternalLinkIcon className={styles.linkIcon} />
              </a>
            )}
          </div>
        </section>
      </div>
    </Container>
  );
}
