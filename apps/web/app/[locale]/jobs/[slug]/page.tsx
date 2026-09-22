import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { NotificationSummary } from "@civiclens/types";
import { LastVerified, SourceBadge, VerificationStatus } from "@/components/civic";
import { Container } from "@/components/layout";
import { Breadcrumb } from "@/components/navigation";
import { ExternalLinkIcon } from "@/components/icons";
import type { AppLocale } from "@/i18n/routing";
import { getJobBySlug } from "@/lib/jobs";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { humanizeEnumValue } from "@/lib/format";
import styles from "./page.module.css";

interface JobDetailPageProps {
  params: Promise<{ locale: string; slug: string }>;
}

export async function generateMetadata({ params }: JobDetailPageProps): Promise<Metadata> {
  const { locale, slug } = await params;
  const result = await getJobBySlug(slug);

  if (!result.reachable || result.data === null) {
    // notFound() in the page body renders the right content but, per a
    // known limitation already documented for this project's [locale]
    // routing (see docs/ROADMAP.md Phase 4's design-system-page note),
    // doesn't reliably set a 404 HTTP status here. `noindex` is the
    // mitigation available at this layer, so a nonexistent/unpublished
    // job is never presented to a crawler as indexable content — this
    // phase's explicit "do not generate SEO pages for nonexistent jobs"
    // requirement, given the status-code fix itself is out of scope.
    return {
      ...buildLocaleAwareMetadata({
        locale: locale as AppLocale,
        path: `/jobs/${slug}`,
        description: "Job not found.",
      }),
      robots: { index: false, follow: false },
    };
  }

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: `/jobs/${slug}`,
    title: result.data.title,
    description: result.data.summary ?? result.data.title,
  });
}

function formatDate(value: string | null, locale: string): string | null {
  if (!value) return null;
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric" }).format(
    new Date(value),
  );
}

function jobPostingJsonLd(
  job: { title: string; organization: { name: string }; qualificationSummary: string | null },
  notification: NotificationSummary | undefined,
): Record<string, unknown> {
  // Only fields backed by real, sourced data are included — no
  // schema.org field is guessed to fill out the shape (docs/SEO.md).
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    hiringOrganization: { "@type": "Organization", name: job.organization.name },
  };
  if (job.qualificationSummary) jsonLd.qualifications = job.qualificationSummary;
  if (notification?.published_date) jsonLd.datePosted = notification.published_date;
  if (notification?.application_end) jsonLd.validThrough = notification.application_end;
  return jsonLd;
}

export default async function JobDetailPage({ params }: JobDetailPageProps) {
  const { locale, slug } = await params;
  setRequestLocale(locale);

  const [t, result] = await Promise.all([getTranslations("Jobs"), getJobBySlug(slug)]);

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

  const job = result.data;
  const latestNotification = job.notifications.at(-1);

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "CivicLens", item: `/${locale}` },
      { "@type": "ListItem", position: 2, name: t("listTitle"), item: `/${locale}/jobs` },
      { "@type": "ListItem", position: 3, name: job.title },
    ],
  };

  return (
    <Container>
      <div className={styles.page}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(
              jobPostingJsonLd(
                {
                  title: job.title,
                  organization: job.organization,
                  qualificationSummary: job.qualification_summary,
                },
                latestNotification,
              ),
            ),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
        />

        <Breadcrumb
          items={[
            { label: "CivicLens", href: "/" },
            { label: t("listTitle"), href: "/jobs" },
            { label: job.title },
          ]}
        />

        <header className={styles.header}>
          <h1 className={styles.title}>{job.title}</h1>
          <p className={styles.subtitle}>
            {job.organization.name}
            {job.department && ` · ${job.department.name}`}
            {job.category && ` · ${humanizeEnumValue(job.category)}`}
          </p>
          <div className={styles.badges}>
            <VerificationStatus status={job.verification_status} />
            {job.last_verified && (
              <LastVerified date={new Date(job.last_verified)} locale={locale} />
            )}
          </div>
        </header>

        <section className={styles.section} aria-labelledby="overview-heading">
          <h2 id="overview-heading" className={styles.sectionHeading}>
            {t("sectionOverview")}
          </h2>
          <p>{job.description ?? job.summary}</p>
        </section>

        <section className={styles.section} aria-labelledby="eligibility-heading">
          <h2 id="eligibility-heading" className={styles.sectionHeading}>
            {t("sectionEligibility")}
          </h2>
          <dl className={styles.factList}>
            {job.min_age !== null && job.max_age !== null && (
              <div className={styles.fact}>
                <dt>{t("ageRange", { min: job.min_age, max: job.max_age })}</dt>
              </div>
            )}
            {job.min_age !== null && job.max_age === null && (
              <div className={styles.fact}>
                <dt>{t("ageMinOnly", { min: job.min_age })}</dt>
              </div>
            )}
            {job.min_age === null && job.max_age !== null && (
              <div className={styles.fact}>
                <dt>{t("ageMaxOnly", { max: job.max_age })}</dt>
              </div>
            )}
            {job.qualification_summary && (
              <div className={styles.fact}>
                <dt>{t("qualification")}</dt>
                <dd>{job.qualification_summary}</dd>
              </div>
            )}
            {job.experience_summary && (
              <div className={styles.fact}>
                <dt>{t("experience")}</dt>
                <dd>{job.experience_summary}</dd>
              </div>
            )}
          </dl>
        </section>

        <section className={styles.section} aria-labelledby="salary-heading">
          <h2 id="salary-heading" className={styles.sectionHeading}>
            {t("sectionSalary")}
          </h2>
          <p>{job.salary_summary ?? "—"}</p>
        </section>

        {job.notifications.length === 0 ? (
          <p className={styles.prompt}>{t("noNotificationsYet")}</p>
        ) : (
          job.notifications.map((notification, index) => (
            <div key={notification.notification_number ?? index} className={styles.notification}>
              <section className={styles.section} aria-labelledby={`dates-heading-${index}`}>
                <h2 id={`dates-heading-${index}`} className={styles.sectionHeading}>
                  {t("sectionImportantDates")}
                  {notification.notification_number && ` (${notification.notification_number})`}
                </h2>
                <dl className={styles.factList}>
                  {formatDate(notification.published_date, locale) && (
                    <div className={styles.fact}>
                      <dt>{t("datePublished")}</dt>
                      <dd>{formatDate(notification.published_date, locale)}</dd>
                    </div>
                  )}
                  {formatDate(notification.application_start, locale) && (
                    <div className={styles.fact}>
                      <dt>{t("dateApplicationStart")}</dt>
                      <dd>{formatDate(notification.application_start, locale)}</dd>
                    </div>
                  )}
                  {formatDate(notification.application_end, locale) && (
                    <div className={styles.fact}>
                      <dt>{t("dateApplicationEnd")}</dt>
                      <dd>{formatDate(notification.application_end, locale)}</dd>
                    </div>
                  )}
                  {formatDate(notification.correction_window_end, locale) && (
                    <div className={styles.fact}>
                      <dt>{t("dateCorrectionWindow")}</dt>
                      <dd>{formatDate(notification.correction_window_end, locale)}</dd>
                    </div>
                  )}
                  {formatDate(notification.exam_date, locale) && (
                    <div className={styles.fact}>
                      <dt>{t("dateExam")}</dt>
                      <dd>{formatDate(notification.exam_date, locale)}</dd>
                    </div>
                  )}
                </dl>
              </section>

              {notification.vacancies.length > 0 && (
                <section className={styles.section} aria-labelledby={`vacancies-heading-${index}`}>
                  <h2 id={`vacancies-heading-${index}`} className={styles.sectionHeading}>
                    {t("sectionVacancies")}
                    {notification.total_vacancies !== null &&
                      ` — ${t("totalVacancies", { count: notification.total_vacancies })}`}
                  </h2>
                  <ul className={styles.vacancyList}>
                    {notification.vacancies.map((vacancy, vacancyIndex) => (
                      <li key={vacancyIndex}>
                        {vacancy.post_name}
                        {vacancy.vacancy_count !== null && ` — ${vacancy.vacancy_count}`}
                        {vacancy.location && ` (${vacancy.location})`}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section className={styles.section} aria-labelledby={`application-heading-${index}`}>
                <h2 id={`application-heading-${index}`} className={styles.sectionHeading}>
                  {t("sectionApplication")}
                </h2>
                <div className={styles.links}>
                  {notification.official_application_url && (
                    <a
                      href={notification.official_application_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.officialLink}
                    >
                      {t("officialApplicationLink")}
                      <ExternalLinkIcon className={styles.linkIcon} />
                    </a>
                  )}
                  {notification.official_notification_url && (
                    <a
                      href={notification.official_notification_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.officialLink}
                    >
                      {t("officialNotificationLink")}
                      <ExternalLinkIcon className={styles.linkIcon} />
                    </a>
                  )}
                </div>
              </section>

              <section className={styles.section} aria-labelledby={`verification-heading-${index}`}>
                <h2 id={`verification-heading-${index}`} className={styles.sectionHeading}>
                  {t("sectionVerification")}
                </h2>
                <div className={styles.badges}>
                  <SourceBadge
                    kind={
                      notification.verification_status === "VERIFIED" ? "verified" : "available"
                    }
                  />
                  {notification.last_verified && (
                    <LastVerified date={new Date(notification.last_verified)} locale={locale} />
                  )}
                  <span className={styles.sourceOrganization}>
                    {notification.source.organization}
                  </span>
                </div>
              </section>
            </div>
          ))
        )}
      </div>
    </Container>
  );
}
