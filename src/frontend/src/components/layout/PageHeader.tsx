import React from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "../../lib/utils";

export interface PageHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  breadcrumbs?: string[];
  status?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  status,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[var(--border-default)]",
        className
      )}
    >
      <div className="space-y-1">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="flex items-center gap-1 text-[11px] text-[var(--text-muted)] font-medium mb-1">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb}>
                {idx > 0 && <ChevronRight className="w-3 h-3 text-[var(--border-elevated)]" />}
                <span className={idx === breadcrumbs.length - 1 ? "text-[var(--text-secondary)] font-semibold" : ""}>
                  {crumb}
                </span>
              </React.Fragment>
            ))}
          </nav>
        )}

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-[var(--text-primary)]">{title}</h1>
          {status}
        </div>

        {description && (
          <p className="text-xs text-[var(--text-secondary)] max-w-3xl">{description}</p>
        )}
      </div>

      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
