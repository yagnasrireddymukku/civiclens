import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { EmploymentType } from "@civiclens/types";
import { Alert } from "@/components/feedback";
import { InformationCard, SourceBadge } from "@/components/civic";
import { Container } from "@/components/layout";
import { Link } from "@/i18n/navigation";
import type { AppLocale } from "@/i18n/routing";
import { getJobs } from "@/lib/jobs";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { toSourceBadgeKind } from "@/lib/verificationBadge";
import { JobControls } from "./JobControls";
import styles from "./page.module.css";

const EMPLOYMENT_TYPES: EmploymentType[] = ["PERMANENT", "CONTRACT", "TEMPORARY"];

interface JobsPageProps {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ employment_type?: string; page?: string }>;
}

export async function generateMetadata({ params }: JobsPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Jobs" });

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: "/jobs",
    title: t("listTitle"),
    description: t("devDataBody"),
  });
}

function isEmploymentType(value: string | undefined): value is EmploymentType {
  return value !== undefined && (EMPLOYMENT_TYPES as string[]).includes(value);
}

export default async function JobsPage({ params, searchParams }: JobsPageProps) {
  const { locale } = await params;
  const { employment_type: employmentTypeParam, page: pageParam } = await searchParams;
  setRequestLocale(locale);

  const employmentType = isEmploymentType(employmentTypeParam) ? employmentTypeParam : undefined;
  const page = Math.max(1, Number.parseInt(pageParam ?? "1", 10) || 1);

  const [t, result] = await Promise.all([
    getTranslations("Jobs"),
    getJobs({ page, employmentType }),
  ]);

  const employmentTypeLabels: Record<EmploymentType, string> = {
    PERMANENT: t("employmentTypePermanent"),
    CONTRACT: t("employmentTypeContract"),
    TEMPORARY: t("employmentTypeTemporary"),
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
            <JobControls
              employmentType={employmentType}
              employmentTypeLabel={t("filterEmploymentTypeLabel")}
              allLabel={t("filterAll")}
              employmentTypeLabels={employmentTypeLabels}
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
                {result.data.results.map((job) => (
                  <li key={job.slug}>
                    <InformationCard
                      eyebrow={job.organization.name}
                      title={job.title}
                      description={job.summary ?? ""}
                      meta={[
                        job.district ? `${job.district}, ${job.state}` : job.state,
                        job.category,
                      ].filter((value): value is string => Boolean(value))}
                      badges={<SourceBadge kind={toSourceBadgeKind(job.verification_status)} />}
                      href={`/jobs/${job.slug}`}
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
