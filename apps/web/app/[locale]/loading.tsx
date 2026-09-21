import { useTranslations } from "next-intl";
import { Spinner } from "@/components/primitives";
import { Container } from "@/components/layout";

export default function Loading() {
  const t = useTranslations("Loading");

  return (
    <Container>
      <div style={{ paddingBlock: "var(--space-16)" }}>
        <Spinner label={t("label")} size="lg" />
      </div>
    </Container>
  );
}
