import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { DeliveryMode, ServiceCategory } from "@civiclens/types";
import { Alert } from "@/components/feedback";
import { InformationCard, SourceBadge } from "@/components/civic";
import { Container } from "@/components/layout";
import { Link } from "@/i18n/navigation";
import type { AppLocale } from "@/i18n/routing";
import { getServices } from "@/lib/services";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { toSourceBadgeKind } from "@/lib/verificationBadge";
import { ServiceControls } from "./ServiceControls";
import styles from "./page.module.css";

const SERVICE_CATEGORIES: ServiceCategory[] = [
  "CERTIFICATES",
  "DOCUMENTS",
  "WELFARE",
  "EDUCATION",
  "HEALTHCARE",
  "AGRICULTURE",
  "EMPLOYMENT",
  "BUSINESS",
  "TRANSPORT",
  "MUNICIPAL",
  "REVENUE",
  "SOCIAL_SECURITY",
  "IDENTITY",
  "UTILITIES",
  "OTHER",
];

const DELIVERY_MODES: DeliveryMode[] = ["ONLINE", "OFFLINE", "BOTH"];

interface ServicesPageProps {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ category?: string; delivery_mode?: string; page?: string }>;
}

export async function generateMetadata({ params }: ServicesPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Services" });

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: "/services",
    title: t("listTitle"),
    description: t("devDataBody"),
  });
}

function isServiceCategory(value: string | undefined): value is ServiceCategory {
  return value !== undefined && (SERVICE_CATEGORIES as string[]).includes(value);
}

function isDeliveryMode(value: string | undefined): value is DeliveryMode {
  return value !== undefined && (DELIVERY_MODES as string[]).includes(value);
}

export default async function ServicesPage({ params, searchParams }: ServicesPageProps) {
  const { locale } = await params;
  const {
    category: categoryParam,
    delivery_mode: deliveryModeParam,
    page: pageParam,
  } = await searchParams;
  setRequestLocale(locale);

  const category = isServiceCategory(categoryParam) ? categoryParam : undefined;
  const deliveryMode = isDeliveryMode(deliveryModeParam) ? deliveryModeParam : undefined;
  const page = Math.max(1, Number.parseInt(pageParam ?? "1", 10) || 1);

  const [t, result] = await Promise.all([
    getTranslations("Services"),
    getServices({ page, category, deliveryMode }),
  ]);

  const categoryLabels: Record<ServiceCategory, string> = {
    CERTIFICATES: t("categoryCertificates"),
    DOCUMENTS: t("categoryDocuments"),
    WELFARE: t("categoryWelfare"),
    EDUCATION: t("categoryEducation"),
    HEALTHCARE: t("categoryHealthcare"),
    AGRICULTURE: t("categoryAgriculture"),
    EMPLOYMENT: t("categoryEmployment"),
    BUSINESS: t("categoryBusiness"),
    TRANSPORT: t("categoryTransport"),
    MUNICIPAL: t("categoryMunicipal"),
    REVENUE: t("categoryRevenue"),
    SOCIAL_SECURITY: t("categorySocialSecurity"),
    IDENTITY: t("categoryIdentity"),
    UTILITIES: t("categoryUtilities"),
    OTHER: t("categoryOther"),
  };

  const deliveryModeLabels: Record<DeliveryMode, string> = {
    ONLINE: t("deliveryModeOnline"),
    OFFLINE: t("deliveryModeOffline"),
    BOTH: t("deliveryModeBoth"),
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
            <ServiceControls
              category={category}
              deliveryMode={deliveryMode}
              categoryLabel={t("filterCategoryLabel")}
              deliveryModeLabel={t("filterDeliveryModeLabel")}
              allLabel={t("filterAll")}
              categoryLabels={categoryLabels}
              deliveryModeLabels={deliveryModeLabels}
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
                {result.data.results.map((service) => (
                  <li key={service.slug}>
                    <InformationCard
                      eyebrow={service.organization.name}
                      title={service.name}
                      description={service.short_description ?? ""}
                      meta={[
                        service.district ? `${service.district}, ${service.state}` : service.state,
                        categoryLabels[service.category],
                      ].filter((value): value is string => Boolean(value))}
                      badges={<SourceBadge kind={toSourceBadgeKind(service.verification_status)} />}
                      href={`/services/${service.slug}`}
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
