import { Badge } from "../primitives/Badge";
import { CheckCircleIcon, InfoCircleIcon } from "../icons";

/**
 * A lightweight, glanceable signal that content has traceable
 * provenance (docs/DATA_GOVERNANCE.md §3) — distinct from
 * `VerificationStatus`, which states the specific verification state of
 * one fact. `SourceBadge` is the "this has a source at all" indicator
 * used in dense listings (e.g. `SearchResultCard`); `VerificationStatus`
 * is the fuller statement used on a detail page.
 */
export type SourceBadgeKind = "official" | "verified" | "available";

const CONFIG: Record<SourceBadgeKind, { label: string; tone: "primary" | "success" | "neutral" }> =
  {
    official: { label: "Official source", tone: "primary" },
    verified: { label: "Verified", tone: "success" },
    available: { label: "Source available", tone: "neutral" },
  };

export function SourceBadge({ kind }: { kind: SourceBadgeKind }) {
  const { label, tone } = CONFIG[kind];
  const Icon = kind === "verified" ? CheckCircleIcon : InfoCircleIcon;
  return (
    <Badge tone={tone} icon={<Icon />}>
      {label}
    </Badge>
  );
}
