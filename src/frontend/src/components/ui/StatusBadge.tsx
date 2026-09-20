import { cn } from "../../lib/utils";
import { CheckCircle2, AlertTriangle, AlertOctagon, Clock, Anchor, Ship, Database, Radio, HelpCircle } from "lucide-react";

export type OperationalStatus =
  | "OPERATIONAL"
  | "HEALTHY"
  | "WARNING"
  | "ELEVATED"
  | "HIGH"
  | "CRITICAL"
  | "CRIT"
  | "WAITING"
  | "ANCHORAGE"
  | "INBOUND"
  | "BERTHED"
  | "ASSIGNED"
  | "FEASIBLE"
  | "DEMO"
  | "DEMO_AIS"
  | "CONNECTING"
  | "UNAVAILABLE"
  | "OFFLINE";

export interface StatusBadgeProps {
  status: string;
  label?: string;
  size?: "xs" | "sm" | "md";
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({
  status,
  label,
  size = "sm",
  className,
  showIcon = true,
}: StatusBadgeProps) {
  const norm = status?.toUpperCase() || "UNKNOWN";

  let variantClass = "bg-[var(--bg-surface-elevated)] text-[var(--text-secondary)] border-[var(--border-default)]";
  let dotColor = "bg-[var(--text-muted)]";
  let Icon = HelpCircle;

  switch (norm) {
    case "OPERATIONAL":
    case "HEALTHY":
      variantClass = "bg-[var(--status-success-bg)] text-[var(--status-success)] border-[var(--status-success-border)]";
      dotColor = "bg-[var(--status-success)]";
      Icon = CheckCircle2;
      break;

    case "WARNING":
    case "ELEVATED":
      variantClass = "bg-[var(--status-warning-bg)] text-[var(--status-warning)] border-[var(--status-warning-border)]";
      dotColor = "bg-[var(--status-warning)]";
      Icon = AlertTriangle;
      break;

    case "HIGH":
      variantClass = "bg-[var(--status-high-bg)] text-[var(--status-high)] border-[var(--status-high-border)]";
      dotColor = "bg-[var(--status-high)]";
      Icon = AlertTriangle;
      break;

    case "CRITICAL":
    case "CRIT":
      variantClass = "bg-[var(--status-critical-bg)] text-[var(--status-critical)] border-[var(--status-critical-border)]";
      dotColor = "bg-[var(--status-critical)]";
      Icon = AlertOctagon;
      break;

    case "WAITING":
    case "ANCHORAGE":
      variantClass = "bg-[var(--status-info-bg)] text-[var(--status-info)] border-[var(--status-info-border)]";
      dotColor = "bg-[var(--status-info)]";
      Icon = Anchor;
      break;

    case "INBOUND":
      variantClass = "bg-[var(--status-info-bg)] text-[var(--status-info)] border-[var(--status-info-border)]";
      dotColor = "bg-[var(--status-info)]";
      Icon = Ship;
      break;

    case "ASSIGNED":
    case "BERTHED":
    case "FEASIBLE":
      variantClass = "bg-[var(--brand-soft)] text-[var(--text-accent)] border-[var(--brand-border)]";
      dotColor = "bg-[var(--brand)]";
      Icon = Clock;
      break;

    case "DEMO":
    case "DEMO_AIS":
      variantClass = "bg-[var(--brand-soft)] text-[var(--text-secondary)] border-[var(--border-default)]";
      dotColor = "bg-[var(--brand)]";
      Icon = Database;
      break;

    case "CONNECTING":
      variantClass = "bg-[var(--status-info-bg)] text-[var(--status-info)] border-[var(--status-info-border)]";
      dotColor = "bg-[var(--status-info)] animate-pulse";
      Icon = Radio;
      break;

    case "UNAVAILABLE":
    case "OFFLINE":
      variantClass = "bg-[var(--status-critical-bg)] text-[var(--status-critical)] border-[var(--status-critical-border)]";
      dotColor = "bg-[var(--status-critical)]";
      Icon = AlertOctagon;
      break;
  }

  const sizes = {
    xs: "px-1.5 py-0.5 text-[10px] gap-1 rounded",
    sm: "px-2 py-0.5 text-[11px] gap-1.5 rounded-md font-medium",
    md: "px-2.5 py-1 text-xs gap-1.5 rounded-md font-medium",
  };

  const iconSizes = {
    xs: "w-2.5 h-2.5",
    sm: "w-3 h-3",
    md: "w-3.5 h-3.5",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center border select-none shrink-0 tracking-wider uppercase",
        variantClass,
        sizes[size],
        className
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dotColor)} />
      {showIcon && <Icon className={cn("shrink-0", iconSizes[size])} />}
      <span>{label || status}</span>
    </span>
  );
}
