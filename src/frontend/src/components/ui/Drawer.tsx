import React, { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";

export interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  side?: "right" | "left";
  className?: string;
  width?: "sm" | "md" | "lg" | "xl";
}

export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  side = "right",
  className,
  width = "md",
}: DrawerProps) {
  useEffect(() => {
    if (!open) return;

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onOpenChange(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onOpenChange]);

  if (!open) return null;

  const widthClasses = {
    sm: "w-full sm:max-w-sm",
    md: "w-full sm:max-w-md",
    lg: "w-full sm:max-w-lg",
    xl: "w-full sm:max-w-xl",
  };

  const sideClasses = {
    right: "inset-x-0 bottom-0 max-h-[92vh] sm:max-h-full sm:inset-y-0 sm:right-0 sm:left-auto border-t sm:border-t-0 sm:border-l animate-in slide-in-from-bottom sm:slide-in-from-right",
    left: "inset-x-0 bottom-0 max-h-[92vh] sm:max-h-full sm:inset-y-0 sm:left-0 sm:right-auto border-t sm:border-t-0 sm:border-r animate-in slide-in-from-bottom sm:slide-in-from-left",
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Drawer / Bottom sheet panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : "Detail Inspector"}
        className={cn(
          "fixed z-50 flex flex-col w-full bg-[var(--bg-surface)] border-[var(--border-default)] p-4 sm:p-5 text-[var(--text-primary)] shadow-2xl duration-200 rounded-t-2xl sm:rounded-none",
          sideClasses[side],
          widthClasses[width],
          className
        )}
      >
        {/* Mobile touch grab handle */}
        <div className="w-10 h-1 rounded-full bg-[var(--border-strong)] mx-auto mb-2 shrink-0 sm:hidden" aria-hidden="true" />

        <div className="flex items-start justify-between gap-3 pb-3 sm:pb-4 border-b border-[var(--border-subtle)] shrink-0">
          <div className="space-y-1 min-w-0 flex-1">
            {title && <h2 className="text-sm sm:text-base font-semibold tracking-tight truncate">{title}</h2>}
            {description && (
              <div className="text-xs text-[var(--text-secondary)]">{description}</div>
            )}
          </div>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            aria-label="Close panel"
            className="h-8 w-8 min-w-[32px] text-[var(--text-muted)] hover:text-[var(--text-primary)] shrink-0"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto py-3 sm:py-4 text-sm min-h-0">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-2 pt-3 sm:pt-4 border-t border-[var(--border-subtle)] shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
