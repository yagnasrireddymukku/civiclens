import { Badge } from "../primitives/Badge";
import { CheckCircleIcon, ClockIcon, XCircleIcon } from "../icons";

export type DeadlineStatusValue = "OPEN" | "CLOSING_SOON" | "CLOSED" | "UPCOMING";

const CONFIG: Record<
  DeadlineStatusValue,
  { label: string; tone: "success" | "warning" | "neutral" | "info"; icon: typeof ClockIcon }
> = {
  UPCOMING: { label: "Upcoming", tone: "info", icon: ClockIcon },
  OPEN: { label: "Open", tone: "success", icon: CheckCircleIcon },
  CLOSING_SOON: { label: "Closing soon", tone: "warning", icon: ClockIcon },
  CLOSED: { label: "Closed", tone: "neutral", icon: XCircleIcon },
};

export function DeadlineBadge({ status }: { status: DeadlineStatusValue }) {
  const { label, tone, icon: Icon } = CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon />}>
      {label}
    </Badge>
  );
}
