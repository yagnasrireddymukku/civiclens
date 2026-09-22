import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { EducationLevel, SchemeCategory } from "@civiclens/types";
import { Alert } from "@/components/feedback";
import { InformationCard, SourceBadge } from "@/components/civic";
import { Container } from "@/components/layout";
import { Link } from "@/i18n/navigation";
import type { AppLocale } from "@/i18n/routing";
import { getSchemes } from "@/lib/schemes";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { toSourceBadgeKind } from "@/lib/verificationBadge";
import { SchemeControls } from "./SchemeControls";
import styles from "./page.module.css";

const SCHEME_CATEGORIES: SchemeCategory[] = [
  "SCHOLARSHIP",
  "PENSION",
  "SUBSIDY",
  "FINANCIAL_ASSISTANCE",
  "INSURANCE",
  "HOUSING",
  "HEALTHCARE",
  "EDUCATION",
  "AGRICULTURE",
  "EMPLOYMENT",
  "SKILL_DEVELOPMENT",
  "WOMEN_CHILD_WELFARE",
  "SOCIAL_WELFARE",
  "BUSINESS_ENTREPRENEURSHIP",
  "DISABILITY_SUPPORT",
  "OTHER",
];

const EDUCATION_LEVELS: EducationLevel[] = [
  "SCHOOL",
  "INTERMEDIATE",
  "DIPLOMA",
  "UNDERGRADUATE",
  "POSTGRADUATE",
  "DOCTORAL",
  "PROFESSIONAL",
  "VOCATIONAL",
  "OTHER",
];

interface SchemesPageProps {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ category?: string; education_level?: string; page?: string }>;
}

export async function generateMetadata({ params }: SchemesPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Schemes" });

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: "/schemes",
    title: t("listTitle"),
    description: t("devDataBody"),
  });
}

function isSchemeCategory(value: string | undefined): value is SchemeCategory {
  return value !== undefined && (SCHEME_CATEGORIES as string[]).includes(value);
}

function isEducationLevel(value: string | undefined): value is EducationLevel {
  return value !== undefined && (EDUCATION_LEVELS as string[]).includes(value);
}

export default async function SchemesPage({ params, searchParams }: SchemesPageProps) {
  const { locale } = await params;
  const {
    category: categoryParam,
    education_level: educationLevelParam,
    page: pageParam,
  } = await searchParams;
  setRequestLocale(locale);

  const category = isSchemeCategory(categoryParam) ? categoryParam : undefined;
  const educationLevel = isEducationLevel(educationLevelParam) ? educationLevelParam : undefined;
  const page = Math.max(1, Number.parseInt(pageParam ?? "1", 10) || 1);

  const [t, result] = await Promise.all([
    getTranslations("Schemes"),
    getSchemes({ page, category, educationLevel }),
  ]);

  const categoryLabels: Record<SchemeCategory, string> = {
    SCHOLARSHIP: t("categoryScholarship"),
    PENSION: t("categoryPension"),
    SUBSIDY: t("categorySubsidy"),
    FINANCIAL_ASSISTANCE: t("categoryFinancialAssistance"),
    INSURANCE: t("categoryInsurance"),
    HOUSING: t("categoryHousing"),
    HEALTHCARE: t("categoryHealthcare"),
    EDUCATION: t("categoryEducation"),
    AGRICULTURE: t("categoryAgriculture"),
    EMPLOYMENT: t("categoryEmployment"),
    SKILL_DEVELOPMENT: t("categorySkillDevelopment"),
    WOMEN_CHILD_WELFARE: t("categoryWomenChildWelfare"),
    SOCIAL_WELFARE: t("categorySocialWelfare"),
    BUSINESS_ENTREPRENEURSHIP: t("categoryBusinessEntrepreneurship"),
    DISABILITY_SUPPORT: t("categoryDisabilitySupport"),
    OTHER: t("categoryOther"),
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

  const totalPages =
    result.reachable && result.data.pagination.total_count > 0
      ? Math.ceil(result.data.pagination.total_count / result.data.pagination.page_size)
      : 0;

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("listTitle")}</h1>

        <Alert tone="info" title={t("devDataTitle")}>
          {t("devDataBody")}
        </Alert>

        <p className={styles.searchCta}>
          {t("searchCta")} <Link href="/search">{t("searchCtaLink")}</Link>
        </p>

        {result.reachable === false ? (
          <Alert tone="error" title={t("errorTitle")}>
            {result.error}
          </Alert>
        ) : (
          <>
            <SchemeControls
              category={category}
              educationLevel={educationLevel}
              categoryLabel={t("filterCategoryLabel")}
              educationLevelLabel={t("filterEducationLevelLabel")}
              allLabel={t("filterAll")}
              categoryLabels={categoryLabels}
              educationLevelLabels={educationLevelLabels}
              page={page}
              totalPages={totalPages}
            />

            <p className={styles.resultsHeading}>
              {t("resultsCount", { count: result.data.pagination.total_count })}
            </p>

            {result.data.results.length === 0 ? (
              <p className={styles.prompt}>{t("emptyBody")}</p>
            ) : (
              <ul className={styles.results}>
                {result.data.results.map((scheme) => (
                  <li key={scheme.slug}>
                    <InformationCard
                      eyebrow={scheme.organization.name}
                      title={scheme.name}
                      description={scheme.short_description ?? ""}
                      meta={[
                        scheme.district ? `${scheme.district}, ${scheme.state}` : scheme.state,
                        categoryLabels[scheme.category],
                      ].filter((value): value is string => Boolean(value))}
                      badges={<SourceBadge kind={toSourceBadgeKind(scheme.verification_status)} />}
                      href={`/schemes/${scheme.slug}`}
                    />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </Container>
  );
}
