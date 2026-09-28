"use client";

import type { FormEvent } from "react";
import { useId, useState } from "react";
import type {
  ConditionStatus,
  EducationLevel,
  EligibilityAttribute,
  EligibilityCriterionQuestion,
  EligibilityEntityType,
  EligibilityEvaluateResponse,
} from "@civiclens/types";
import { EligibilityStatus } from "@/components/civic/EligibilityStatus";
import { Button, Input, Select } from "@/components/primitives";
import { evaluateEligibility } from "@/lib/eligibility";
import styles from "./EligibilityForm.module.css";

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

interface FormLabels {
  submit: string;
  resultHeading: string;
  outcomeEligible: string;
  outcomeNotEligible: string;
  outcomeIncomplete: string;
  statusPass: string;
  statusFail: string;
  statusUnknown: string;
  fieldAge: string;
  fieldIncome: string;
  fieldEducationLevel: string;
  fieldPercentage: string;
  fieldCgpa: string;
  fieldState: string;
  fieldCategory: string;
  errorGeneric: string;
  loading: string;
}

export interface EligibilityFormProps {
  entityType: EligibilityEntityType;
  entitySlug: string;
  criteria: EligibilityCriterionQuestion[];
  attributeLabels: Record<EligibilityAttribute, string>;
  educationLevelLabels: Record<EducationLevel, string>;
  labels: FormLabels;
}

interface FormState {
  age: string;
  income_annual: string;
  education_level: string;
  academic_percentage: string;
  academic_cgpa: string;
  residence_state_code: string;
  category: string;
}

const EMPTY_STATE: FormState = {
  age: "",
  income_annual: "",
  education_level: "",
  academic_percentage: "",
  academic_cgpa: "",
  residence_state_code: "",
  category: "",
};

const STATUS_TONE: Record<ConditionStatus, "success" | "error" | "warning"> = {
  PASS: "success",
  FAIL: "error",
  UNKNOWN: "warning",
};

/**
 * Renders only the fields this entity's rule actually asks about (this
 * phase's §F: "let users answer only the questions required by
 * supported structured criteria"). Submitted answers live only in this
 * component's local state and the one outbound request — never written
 * anywhere else, never persisted (this phase's §G).
 */
export function EligibilityForm({
  entityType,
  entitySlug,
  criteria,
  attributeLabels,
  educationLevelLabels,
  labels,
}: EligibilityFormProps) {
  const [form, setForm] = useState<FormState>(EMPTY_STATE);
  const [result, setResult] = useState<EligibilityEvaluateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultHeadingId = useId();

  const attributes = new Set(criteria.map((c) => c.attribute));

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const answers = {
      age: form.age ? Number(form.age) : null,
      income_annual: form.income_annual || null,
      education_level: (form.education_level || null) as EducationLevel | null,
      academic_percentage: form.academic_percentage || null,
      academic_cgpa: form.academic_cgpa || null,
      residence_state_code: form.residence_state_code || null,
      category: form.category || null,
    };

    const response = await evaluateEligibility(entityType, entitySlug, answers);
    setLoading(false);
    if (!response.reachable) {
      setError(response.error);
      return;
    }
    setResult(response.data);
  }

  const outcomeLabel = {
    ELIGIBLE: labels.outcomeEligible,
    NOT_ELIGIBLE: labels.outcomeNotEligible,
    INCOMPLETE: labels.outcomeIncomplete,
  };
  const statusLabel: Record<ConditionStatus, string> = {
    PASS: labels.statusPass,
    FAIL: labels.statusFail,
    UNKNOWN: labels.statusUnknown,
  };

  return (
    <section className={styles.wrapper} aria-labelledby={resultHeadingId}>
      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        {attributes.has("AGE") && (
          <Input
            type="number"
            min={0}
            max={130}
            label={labels.fieldAge}
            value={form.age}
            onChange={(e) => setForm({ ...form, age: e.target.value })}
          />
        )}
        {attributes.has("INCOME_ANNUAL") && (
          <Input
            type="number"
            min={0}
            step="0.01"
            label={labels.fieldIncome}
            value={form.income_annual}
            onChange={(e) => setForm({ ...form, income_annual: e.target.value })}
          />
        )}
        {attributes.has("EDUCATION_LEVEL") && (
          <Select
            label={labels.fieldEducationLevel}
            placeholder={labels.fieldEducationLevel}
            value={form.education_level}
            onChange={(e) => setForm({ ...form, education_level: e.target.value })}
            options={EDUCATION_LEVELS.map((level) => ({
              value: level,
              label: educationLevelLabels[level],
            }))}
          />
        )}
        {attributes.has("ACADEMIC_PERCENTAGE") && (
          <Input
            type="number"
            min={0}
            max={100}
            step="0.01"
            label={labels.fieldPercentage}
            value={form.academic_percentage}
            onChange={(e) => setForm({ ...form, academic_percentage: e.target.value })}
          />
        )}
        {attributes.has("ACADEMIC_CGPA") && (
          <Input
            type="number"
            min={0}
            max={10}
            step="0.01"
            label={labels.fieldCgpa}
            value={form.academic_cgpa}
            onChange={(e) => setForm({ ...form, academic_cgpa: e.target.value })}
          />
        )}
        {attributes.has("RESIDENCE_STATE") && (
          <Input
            type="text"
            maxLength={10}
            label={labels.fieldState}
            value={form.residence_state_code}
            onChange={(e) => setForm({ ...form, residence_state_code: e.target.value })}
          />
        )}
        {attributes.has("CATEGORY") && (
          <Input
            type="text"
            maxLength={100}
            label={labels.fieldCategory}
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          />
        )}

        <Button type="submit" loading={loading}>
          {labels.submit}
        </Button>
      </form>

      {error && (
        <p role="alert" className={styles.errorText}>
          {labels.errorGeneric}: {error}
        </p>
      )}

      {result && result.supported && result.outcome && (
        <div className={styles.result}>
          <h2 id={resultHeadingId} className={styles.resultHeading}>
            {labels.resultHeading}
          </h2>
          <EligibilityStatus status={result.outcome} label={outcomeLabel[result.outcome]} />
          <ul className={styles.conditionList}>
            {result.conditions.map((condition) => (
              <li key={condition.attribute} className={styles.conditionItem}>
                <span className={styles.conditionStatus} data-tone={STATUS_TONE[condition.status]}>
                  {statusLabel[condition.status]}
                </span>
                <span>{condition.description ?? attributeLabels[condition.attribute]}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
