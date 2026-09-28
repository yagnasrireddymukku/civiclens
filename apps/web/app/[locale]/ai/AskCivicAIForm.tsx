"use client";

import type { FormEvent } from "react";
import { useId, useState } from "react";
import type { AIAskResponse } from "@civiclens/types";
import { LastVerified } from "@/components/civic/LastVerified";
import { VerificationStatus } from "@/components/civic/VerificationStatus";
import { Button, Textarea } from "@/components/primitives";
import { Link } from "@/i18n/navigation";
import { askCivicAI } from "@/lib/ai";
import styles from "./AskCivicAIForm.module.css";

const MIN_QUESTION_LENGTH = 3;
const MAX_QUESTION_LENGTH = 500;

interface FormLabels {
  questionLabel: string;
  questionHint: string;
  submit: string;
  loading: string;
  resultHeading: string;
  citationsHeading: string;
  needsReviewCaveat: string;
  statusInsufficientEvidence: string;
  statusProviderUnavailable: string;
  statusUngrounded: string;
  searchLinkLabel: string;
  errorGeneric: string;
  lastVerifiedLabel: string;
}

export interface AskCivicAIFormProps {
  locale: string;
  labels: FormLabels;
}

/**
 * The interactive half of the Civic AI page (this phase's §F). Submitted
 * questions live only in this component's local state and the one
 * outbound request — never persisted anywhere on this side either
 * (docs/AI_ARCHITECTURE.md §7, this phase's §G). No fabricated chat
 * history and no fake streaming — one question, one real answer, shown
 * only once the actual response has arrived.
 */
export function AskCivicAIForm({ locale, labels }: AskCivicAIFormProps) {
  const [question, setQuestion] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [result, setResult] = useState<AIAskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const resultHeadingId = useId();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < MIN_QUESTION_LENGTH || trimmed.length > MAX_QUESTION_LENGTH) {
      setValidationError(labels.questionHint);
      return;
    }
    setValidationError(null);
    setNetworkError(null);
    setLoading(true);
    setResult(null);

    const response = await askCivicAI(trimmed, locale);
    setLoading(false);
    if (!response.reachable) {
      setNetworkError(response.error);
      return;
    }
    setResult(response.data);
  }

  const statusMessage: Record<string, string> = {
    INSUFFICIENT_EVIDENCE: labels.statusInsufficientEvidence,
    PROVIDER_UNAVAILABLE: labels.statusProviderUnavailable,
    UNGROUNDED: labels.statusUngrounded,
  };

  return (
    <section className={styles.wrapper} aria-labelledby={resultHeadingId}>
      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <Textarea
          label={labels.questionLabel}
          hint={labels.questionHint}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          error={validationError ?? undefined}
          maxLength={MAX_QUESTION_LENGTH}
        />
        <Button type="submit" loading={loading}>
          {labels.submit}
        </Button>
      </form>

      {networkError && (
        <p role="alert" className={styles.errorText}>
          {labels.errorGeneric}: {networkError}
        </p>
      )}

      {result && (
        <div className={styles.result} role="status" aria-live="polite">
          <h2 id={resultHeadingId} className={styles.resultHeading}>
            {labels.resultHeading}
          </h2>

          {result.grounding_status === "GROUNDED" && result.answer ? (
            <>
              <p className={styles.answerText}>{result.answer}</p>
              {result.citations.length > 0 && (
                <div className={styles.citations}>
                  <h3 className={styles.citationsHeading}>{labels.citationsHeading}</h3>
                  <ul className={styles.citationList}>
                    {result.citations.map((citation) => (
                      <li key={citation.citation_id} className={styles.citationItem}>
                        <Link href={citation.route} className={styles.citationLink}>
                          {citation.title}
                        </Link>
                        <div className={styles.citationMeta}>
                          <VerificationStatus status={citation.verification_status} />
                          {citation.last_verified && (
                            <LastVerified
                              date={new Date(citation.last_verified)}
                              locale={locale}
                              label={labels.lastVerifiedLabel}
                            />
                          )}
                        </div>
                        {citation.needs_review_caveat && (
                          <p className={styles.caveat}>{labels.needsReviewCaveat}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className={styles.fallback}>
              <p>{statusMessage[result.grounding_status] ?? result.message}</p>
              <Link href="/search" className={styles.searchLink}>
                {labels.searchLinkLabel}
              </Link>
            </div>
          )}

          <p className={styles.disclaimerSmall}>{result.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
