import { Badge } from "../primitives/Badge";
import { AlertTriangleIcon, CheckCircleIcon, XCircleIcon } from "../icons";

/**
 * Mirrors the Eligibility Engine's three-state result
 * (docs/ELIGIBILITY_ENGINE.md §3: ELIGIBLE/NOT_ELIGIBLE/INCOMPLETE) — no
 * engine exists yet (docs/ROADMAP.md Phase 10); this is the reusable
 * presentation it will use once it does.
 */
export type EligibilityStatusValue = "ELIGIBLE" | "NOT_ELIGIBLE" | "INCOMPLETE";

const CONFIG: Record<
  EligibilityStatusValue,
  { label: string; tone: "success" | "error" | "warning"; icon: typeof CheckCircleIcon }
> = {
  ELIGIBLE: { label: "Eligible", tone: "success", icon: CheckCircleIcon },
  NOT_ELIGIBLE: { label: "Not eligible", tone: "error", icon: XCircleIcon },
  INCOMPLETE: { label: "Incomplete", tone: "warning", icon: AlertTriangleIcon },
};

export function EligibilityStatus({ status }: { status: EligibilityStatusValue }) {
  const { label, tone, icon: Icon } = CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon />}>
      {label}
    </Badge>
  );
}
