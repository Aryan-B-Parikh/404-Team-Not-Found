import React from "react";
import { cn } from "../../lib/utils";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; // 0 to 100
  max?: number;
  tone?: "accent" | "success" | "warning" | "critical" | "info" | "auto";
  size?: "xs" | "sm" | "md";
  showLabel?: boolean;
}

export function Progress({
  value,
  max = 100,
  tone = "auto",
  size = "sm",
  showLabel = false,
  className,
  ...props
}: ProgressProps) {
  const percentage = Math.min(Math.max(0, (value / max) * 100), 100);

  let selectedTone = tone;
  if (tone === "auto") {
    if (percentage > 85) selectedTone = "critical";
    else if (percentage > 70) selectedTone = "warning";
    else if (percentage > 50) selectedTone = "accent";
    else selectedTone = "success";
  }

  const toneStyles = {
    accent: "bg-[var(--accent)]",
    success: "bg-[var(--status-success)]",
    warning: "bg-[var(--status-warning)]",
    critical: "bg-[var(--status-critical)]",
    info: "bg-[var(--status-info)]",
    auto: "bg-[var(--accent)]",
  };

  const sizes = {
    xs: "h-1",
    sm: "h-1.5",
    md: "h-2.5",
  };

  return (
    <div className={cn("w-full space-y-1", className)} {...props}>
      {showLabel && (
        <div className="flex justify-between text-[11px] font-mono">
          <span className="text-[var(--text-secondary)]">Utilization</span>
          <span className="text-[var(--text-primary)] font-medium">{Math.round(percentage)}%</span>
        </div>
      )}
      <div className={cn("w-full rounded-full bg-[var(--bg-surface-elevated)] overflow-hidden border border-[var(--border-subtle)]", sizes[size])}>
        <div
          className={cn("h-full transition-all duration-300 rounded-full", toneStyles[selectedTone])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
