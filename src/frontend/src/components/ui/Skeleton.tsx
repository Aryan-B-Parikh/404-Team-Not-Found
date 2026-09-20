import React from "react";
import { cn } from "../../lib/utils";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-[var(--bg-surface-elevated)]/70 border border-[var(--border-subtle)]/40",
        className
      )}
      {...props}
    />
  );
}

export function SkeletonKpi() {
  return (
    <div className="p-3.5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] space-y-2">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-7 w-28" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="p-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-20 w-full" />
      <div className="flex gap-2 pt-2 border-t border-[var(--border-subtle)]">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-3 w-1/4" />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2">
      <div className="flex gap-4 pb-2 border-b border-[var(--border-subtle)]">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-2 border-b border-[var(--border-subtle)]/50">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3.5 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart({ height = 240 }: { height?: number }) {
  return (
    <div
      style={{ height }}
      className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 flex flex-col justify-between"
    >
      <div className="flex justify-between items-center">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-20" />
      </div>
      <div className="flex items-end justify-between gap-2 h-36 px-2">
        {Array.from({ length: 16 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1"
            style={{ height: `${25 + ((i * 17) % 65)}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between pt-2 border-t border-[var(--border-subtle)]">
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}
