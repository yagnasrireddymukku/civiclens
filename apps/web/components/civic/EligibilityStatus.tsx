import { Badge } from "../primitives/Badge";
import { AlertTriangleIcon, CheckCircleIcon, XCircleIcon } from "../icons";

/**
 * Mirrors the Eligibility Engine's three-state result
 * (docs/ELIGIBILITY_ENGINE.md §3: ELIGIBLE/NOT_ELIGIBLE/INCOMPLETE),
 * real as of Phase 11 (apps/web/app/[locale]/eligibility). Tone+icon
 * carry the meaning, never color alone (docs/FRONTEND.md §6).
 */
export type EligibilityStatusValue = "ELIGIBLE" | "NOT_ELIGIBLE" | "INCOMPLETE";

const TONE_AND_ICON: Record<
  EligibilityStatusValue,
  { tone: "success" | "error" | "warning"; icon: typeof CheckCircleIcon }
> = {
  ELIGIBLE: { tone: "success", icon: CheckCircleIcon },
  NOT_ELIGIBLE: { tone: "error", icon: XCircleIcon },
  INCOMPLETE: { tone: "warning", icon: AlertTriangleIcon },
};

const DEFAULT_LABELS: Record<EligibilityStatusValue, string> = {
  ELIGIBLE: "Eligible",
  NOT_ELIGIBLE: "Not eligible",
  INCOMPLETE: "Incomplete",
};

export interface EligibilityStatusProps {
  status: EligibilityStatusValue;
  /** Translated label; defaults to English so the component works
   * standalone (e.g. in tests) without requiring the i18n provider —
   * same convention as `LastVerified`'s `label` prop. */
  label?: string;
}

export function EligibilityStatus({ status, label }: EligibilityStatusProps) {
  const { tone, icon: Icon } = TONE_AND_ICON[status];
  return (
    <Badge tone={tone} icon={<Icon />}>
      {label ?? DEFAULT_LABELS[status]}
    </Badge>
  );
}
