import { Badge } from "../primitives/Badge";
import { AlertTriangleIcon, CheckCircleIcon, InfoCircleIcon, XCircleIcon } from "../icons";

/**
 * Mirrors apps/api's VerificationStatus enum (app/sources/enums.py) and
 * docs/DATA_GOVERNANCE.md §4's four states exactly — this component
 * doesn't invent its own vocabulary. No live data flows through it yet
 * (Phase 3's `sources` module has no public read API); this is the
 * reusable presentation the future source/eligibility pages will use.
 */
export type VerificationStatusValue = "VERIFIED" | "NEEDS_REVIEW" | "EXPIRED" | "UNVERIFIED";

const CONFIG: Record<
  VerificationStatusValue,
  { label: string; tone: "success" | "warning" | "error" | "neutral"; icon: typeof CheckCircleIcon }
> = {
  VERIFIED: { label: "Verified", tone: "success", icon: CheckCircleIcon },
  NEEDS_REVIEW: { label: "Needs review", tone: "warning", icon: AlertTriangleIcon },
  EXPIRED: { label: "Expired", tone: "neutral", icon: InfoCircleIcon },
  UNVERIFIED: { label: "Unverified", tone: "error", icon: XCircleIcon },
};

export function VerificationStatus({ status }: { status: VerificationStatusValue }) {
  const { label, tone, icon: Icon } = CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon />}>
      {label}
    </Badge>
  );
}
