import React from "react";
import { ResponsiveContainer } from "recharts";
import { cn } from "../../lib/utils";

export interface ChartContainerProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  height?: number | string;
  minHeight?: number;
  className?: string;
  children: React.ReactElement;
}

export function ChartContainer({
  title,
  subtitle,
  action,
  height = 300,
  minHeight = 220,
  className,
  children,
}: ChartContainerProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 space-y-3",
        className
      )}
    >
      {(title || subtitle || action) && (
        <div className="flex items-start justify-between gap-4 pb-2 border-b border-[var(--border-subtle)]">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-[var(--text-secondary)]">{subtitle}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div style={{ height, minHeight }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
