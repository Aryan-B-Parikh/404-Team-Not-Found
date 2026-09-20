import React from "react";
import { Inbox } from "lucide-react";
import { cn } from "../../lib/utils";

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title = "No operational data available",
  description = "There are currently no records matching the selected parameters.",
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center border border-dashed border-[var(--border-default)] rounded-lg bg-[var(--bg-surface)]/50",
        className
      )}
    >
      <div className="w-10 h-10 rounded-full bg-[var(--bg-surface-elevated)] border border-[var(--border-default)] flex items-center justify-center text-[var(--text-secondary)] mb-3">
        {icon || <Inbox className="w-5 h-5" />}
      </div>
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">{title}</h3>
      <p className="text-xs text-[var(--text-secondary)] max-w-sm mb-4">{description}</p>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
