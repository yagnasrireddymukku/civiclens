import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { EducationLevel, EligibilityAttribute, EligibilityEntityType } from "@civiclens/types";
import { LastVerified, SourceBadge, VerificationStatus } from "@/components/civic";
import { Container } from "@/components/layout";
import { Breadcrumb } from "@/components/navigation";
import type { AppLocale } from "@/i18n/routing";
import { getEligibilityCriteria } from "@/lib/eligibility";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { EligibilityForm } from "./EligibilityForm";
import styles from "./page.module.css";

// The URL segment (lowercase, matching every other domain's route
// style, e.g. /jobs/[slug]) mapped to the API's uppercase
// `EligibilityEntityType` — validated here so an arbitrary path segment
// never reaches the backend as a query parameter.
const ENTITY_TYPE_BY_SEGMENT: Record<string, EligibilityEntityType> = {
  job: "JOB",
  scheme: "SCHEME",
  service: "SERVICE",
};

interface EligibilityPageProps {
  params: Promise<{ locale: string; entityType: string; slug: string }>;
}

function resolveEntityType(segment: string): EligibilityEntityType | null {
  return ENTITY_TYPE_BY_SEGMENT[segment] ?? null;
}

export async function generateMetadata({ params }: EligibilityPageProps): Promise<Metadata> {
  const { locale, entityType: segment, slug } = await params;
  const entityType = resolveEntityType(segment);
  const path = `/eligibility/${segment}/${slug}`;

  if (entityType === null) {
    return {
      ...buildLocaleAwareMetadata({ locale: locale as AppLocale, path, description: "Not found." }),
      robots: { index: false, follow: false },
    };
  }

  const result = await getEligibilityCriteria(entityType, slug);
  if (!result.reachable || result.data === null) {
    // See apps/web/app/[locale]/documents/[slug]/page.tsx's identical
    // note on notFound() and the [locale] routing 404-status limitation.
    return {
      ...buildLocaleAwareMetadata({ locale: locale as AppLocale, path, description: "Not found." }),
      robots: { index: false, follow: false },
    };
  }

  const { entity, supported } = result.data;
  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path,
    title: `Eligibility — ${entity.name}`,
    description: supported
      ? `Check whether you meet the published eligibility criteria for ${entity.name}.`
      : `No verified eligibility criteria are available for ${entity.name} yet.`,
  });
}

export default async function EligibilityPage({ params }: EligibilityPageProps) {
  const { locale, entityType: segment, slug } = await params;
  setRequestLocale(locale);

  const entityType = resolveEntityType(segment);
  if (entityType === null) {
    notFound();
  }

  const [t, tSchemes, result] = await Promise.all([
    getTranslations("Eligibility"),
    getTranslations("Schemes"),
    getEligibilityCriteria(entityType, slug),
  ]);

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

  const criteria = result.data;
  const entityTypeLabels: Record<EligibilityEntityType, string> = {
    JOB: t("entityTypeJob"),
    SCHEME: t("entityTypeScheme"),
    SERVICE: t("entityTypeService"),
  };
  const attributeLabels: Record<EligibilityAttribute, string> = {
    AGE: t("attributeAge"),
    INCOME_ANNUAL: t("attributeIncomeAnnual"),
    EDUCATION_LEVEL: t("attributeEducationLevel"),
    ACADEMIC_PERCENTAGE: t("attributeAcademicPercentage"),
    ACADEMIC_CGPA: t("attributeAcademicCgpa"),
    RESIDENCE_STATE: t("attributeResidenceState"),
    CATEGORY: t("attributeCategory"),
  };
  const educationLevelLabels: Record<EducationLevel, string> = {
    SCHOOL: tSchemes("educationLevelSchool"),
    INTERMEDIATE: tSchemes("educationLevelIntermediate"),
    DIPLOMA: tSchemes("educationLevelDiploma"),
    UNDERGRADUATE: tSchemes("educationLevelUndergraduate"),
    POSTGRADUATE: tSchemes("educationLevelPostgraduate"),
    DOCTORAL: tSchemes("educationLevelDoctoral"),
    PROFESSIONAL: tSchemes("educationLevelProfessional"),
    VOCATIONAL: tSchemes("educationLevelVocational"),
    OTHER: tSchemes("educationLevelOther"),
  };

  return (
    <Container>
      <div className={styles.page}>
        <Breadcrumb
          items={[
            { label: "CivicLens", href: "/" },
            { label: entityTypeLabels[entityType] },
            { label: criteria.entity.name },
          ]}
        />

        <header className={styles.header}>
          <p className={styles.eyebrow}>{t("pageEyebrow")}</p>
          <h1 className={styles.title}>{criteria.entity.name}</h1>
          <p className={styles.disclaimer}>{t("disclaimer")}</p>
        </header>

        {!criteria.supported ? (
          <p className={styles.notSupported}>{t("notSupportedMessage")}</p>
        ) : (
          <>
            <section className={styles.section} aria-labelledby="criteria-heading">
              <h2 id="criteria-heading" className={styles.sectionHeading}>
                {t("sectionCriteria")}
              </h2>
              <ul className={styles.factItemList}>
                {criteria.criteria.map((criterion) => (
                  <li key={criterion.attribute}>
                    {criterion.description ??
                      `${attributeLabels[criterion.attribute]} ${criterion.expected}`}
                  </li>
                ))}
              </ul>
              {criteria.source && (
                <div className={styles.badges}>
                  {criteria.verification_status && (
                    <VerificationStatus status={criteria.verification_status} />
                  )}
                  {criteria.last_verified && (
                    <LastVerified date={new Date(criteria.last_verified)} locale={locale} />
                  )}
                  <SourceBadge
                    kind={criteria.verification_status === "VERIFIED" ? "verified" : "available"}
                  />
                </div>
              )}
            </section>

            <EligibilityForm
              entityType={entityType}
              entitySlug={slug}
              locale={locale}
              criteria={criteria.criteria}
              attributeLabels={attributeLabels}
              educationLevelLabels={educationLevelLabels}
              labels={{
                submit: t("submitButton"),
                resultHeading: t("sectionResult"),
                outcomeEligible: t("outcomeEligible"),
                outcomeNotEligible: t("outcomeNotEligible"),
                outcomeIncomplete: t("outcomeIncomplete"),
                statusPass: t("statusPass"),
                statusFail: t("statusFail"),
                statusUnknown: t("statusUnknown"),
                fieldAge: t("fieldAgeLabel"),
                fieldIncome: t("fieldIncomeLabel"),
                fieldEducationLevel: t("fieldEducationLevelLabel"),
                fieldPercentage: t("fieldPercentageLabel"),
                fieldCgpa: t("fieldCgpaLabel"),
                fieldState: t("fieldStateLabel"),
                fieldCategory: t("fieldCategoryLabel"),
                errorGeneric: t("errorGeneric"),
                loading: t("loadingLabel"),
                explainWithAI: t("explainWithAI"),
                explainWithAILoading: t("explainWithAILoading"),
                explainWithAIHeading: t("explainWithAIHeading"),
                explainWithAIError: t("explainWithAIError"),
              }}
            />
          </>
        )}
      </div>
    </Container>
  );
}
