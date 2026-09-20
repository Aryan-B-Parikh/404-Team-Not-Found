import React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "neutral" | "info" | "success" | "warning" | "critical" | "accent" | "outline";
  size?: "xs" | "sm" | "md";
  dot?: boolean;
}

export function Badge({
  className,
  variant = "neutral",
  size = "sm",
  dot = false,
  children,
  ...props
}: BadgeProps) {
  const variants = {
    neutral:
      "bg-[var(--bg-surface-elevated)] text-[var(--text-secondary)] border-[var(--border-default)]",
    info:
      "bg-[var(--status-info-bg)] text-[var(--status-info)] border-[var(--status-info-border)]",
    success:
      "bg-[var(--status-success-bg)] text-[var(--status-success)] border-[var(--status-success-border)]",
    warning:
      "bg-[var(--status-warning-bg)] text-[var(--status-warning)] border-[var(--status-warning-border)]",
    critical:
      "bg-[var(--status-critical-bg)] text-[var(--status-critical)] border-[var(--status-critical-border)]",
    accent:
      "bg-[var(--brand-soft)] text-[var(--text-accent)] border-[var(--brand-border)]",
    outline:
      "bg-transparent text-[var(--text-secondary)] border-[var(--border-default)]",
  };

  const dotColors = {
    neutral: "bg-[var(--text-muted)]",
    info: "bg-[var(--status-info)]",
    success: "bg-[var(--status-success)]",
    warning: "bg-[var(--status-warning)]",
    critical: "bg-[var(--status-critical)]",
    accent: "bg-[var(--brand)]",
    outline: "bg-[var(--text-muted)]",
  };

  const sizes = {
    xs: "px-1.5 py-0.5 text-[10px] rounded",
    sm: "px-2 py-0.5 text-[11px] rounded-md gap-1.5 font-medium",
    md: "px-2.5 py-1 text-xs rounded-md gap-1.5 font-medium",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center border font-medium uppercase tracking-wider select-none shrink-0",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dotColors[variant])} />}
      {children}
    </span>
  );
}
