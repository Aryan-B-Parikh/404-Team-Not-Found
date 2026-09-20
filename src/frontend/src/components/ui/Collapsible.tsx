import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";

export interface CollapsibleProps {
  /** Tier-3 summary line, always visible — e.g. "Full solver comparison · 11 metrics" */
  summary: React.ReactNode;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
  children: React.ReactNode;
}

/**
 * Density pattern (UI pass): render a compact summary line and defer the full
 * content behind one click. Nothing is removed — rendering is just deferred,
 * per the visual-density plan (tier 3 = click to expand).
 */
export function Collapsible({ summary, badge, defaultOpen = false, className, children }: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={cn("rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]", className)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-3 px-4 py-2.5 text-left cursor-pointer select-none hover:bg-[var(--bg-surface-hover)] rounded-lg transition-colors"
      >
        <span className="font-semibold text-sm flex items-center gap-2 min-w-0">{summary}</span>
        <span className="flex items-center gap-2 shrink-0">
          {badge}
          <ChevronDown className={cn("w-4 h-4 text-[var(--text-muted)] transition-transform", open && "rotate-180")} />
        </span>
      </button>
      {open && <div className="px-4 pb-4 animate-in fade-in duration-100">{children}</div>}
    </div>
  );
}
