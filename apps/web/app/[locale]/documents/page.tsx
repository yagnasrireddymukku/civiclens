import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { DocumentCategory, DocumentType } from "@civiclens/types";
import { Alert } from "@/components/feedback";
import { InformationCard, SourceBadge } from "@/components/civic";
import { Container } from "@/components/layout";
import { Link } from "@/i18n/navigation";
import type { AppLocale } from "@/i18n/routing";
import { getDocuments } from "@/lib/documents";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { toSourceBadgeKind } from "@/lib/verificationBadge";
import { DocumentControls } from "./DocumentControls";
import styles from "./page.module.css";

const DOCUMENT_TYPES: DocumentType[] = [
  "CERTIFICATE",
  "IDENTITY_DOCUMENT",
  "RECORD",
  "PERMIT",
  "LICENSE",
  "REGISTRATION",
  "OTHER",
];

const DOCUMENT_CATEGORIES: DocumentCategory[] = [
  "PERSONAL",
  "IDENTITY",
  "RESIDENCE",
  "INCOME",
  "SOCIAL_CATEGORY",
  "EDUCATION",
  "BIRTH_DEATH",
  "DISABILITY",
  "LAND_REVENUE",
  "EMPLOYMENT",
  "BUSINESS",
  "FAMILY",
  "OTHER",
];

interface DocumentsPageProps {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ document_type?: string; category?: string; page?: string }>;
}

export async function generateMetadata({ params }: DocumentsPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Documents" });

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: "/documents",
    title: t("listTitle"),
    description: t("devDataBody"),
  });
}

function isDocumentType(value: string | undefined): value is DocumentType {
  return value !== undefined && (DOCUMENT_TYPES as string[]).includes(value);
}

function isDocumentCategory(value: string | undefined): value is DocumentCategory {
  return value !== undefined && (DOCUMENT_CATEGORIES as string[]).includes(value);
}

export default async function DocumentsPage({ params, searchParams }: DocumentsPageProps) {
  const { locale } = await params;
  const {
    document_type: documentTypeParam,
    category: categoryParam,
    page: pageParam,
  } = await searchParams;
  setRequestLocale(locale);

  const documentType = isDocumentType(documentTypeParam) ? documentTypeParam : undefined;
  const category = isDocumentCategory(categoryParam) ? categoryParam : undefined;
  const page = Math.max(1, Number.parseInt(pageParam ?? "1", 10) || 1);

  const [t, result] = await Promise.all([
    getTranslations("Documents"),
    getDocuments({ page, documentType, category }),
  ]);

  const documentTypeLabels: Record<DocumentType, string> = {
    CERTIFICATE: t("typeCertificate"),
    IDENTITY_DOCUMENT: t("typeIdentityDocument"),
    RECORD: t("typeRecord"),
    PERMIT: t("typePermit"),
    LICENSE: t("typeLicense"),
    REGISTRATION: t("typeRegistration"),
    OTHER: t("typeOther"),
  };

  const categoryLabels: Record<DocumentCategory, string> = {
    PERSONAL: t("categoryPersonal"),
    IDENTITY: t("categoryIdentity"),
    RESIDENCE: t("categoryResidence"),
    INCOME: t("categoryIncome"),
    SOCIAL_CATEGORY: t("categorySocialCategory"),
    EDUCATION: t("categoryEducation"),
    BIRTH_DEATH: t("categoryBirthDeath"),
    DISABILITY: t("categoryDisability"),
    LAND_REVENUE: t("categoryLandRevenue"),
    EMPLOYMENT: t("categoryEmployment"),
    BUSINESS: t("categoryBusiness"),
    FAMILY: t("categoryFamily"),
    OTHER: t("categoryOther"),
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
            <DocumentControls
              documentType={documentType}
              category={category}
              documentTypeLabel={t("filterTypeLabel")}
              categoryLabel={t("filterCategoryLabel")}
              allLabel={t("filterAll")}
              documentTypeLabels={documentTypeLabels}
              categoryLabels={categoryLabels}
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
                {result.data.results.map((document) => (
                  <li key={document.slug}>
                    <InformationCard
                      eyebrow={document.organization.name}
                      title={document.name}
                      description={document.short_description ?? ""}
                      meta={[
                        document.district
                          ? `${document.district}, ${document.state}`
                          : document.state,
                        categoryLabels[document.category],
                      ].filter((value): value is string => Boolean(value))}
                      badges={
                        <SourceBadge kind={toSourceBadgeKind(document.verification_status)} />
                      }
                      href={`/documents/${document.slug}`}
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
