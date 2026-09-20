import React, { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  maxWidth?: "sm" | "md" | "lg" | "xl";
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
  maxWidth = "md",
}: DialogProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  const maxWidthClasses = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-xl",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#060d19]/80 backdrop-blur-sm transition-opacity animate-in fade-in"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Dialog box */}
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          "relative z-50 w-full rounded-lg border border-[var(--border-elevated)] bg-[var(--bg-surface)] p-5 text-[var(--text-primary)] shadow-2xl animate-in zoom-in-95 duration-150",
          maxWidthClasses[maxWidth],
          className
        )}
      >
        <div className="flex items-start justify-between gap-4 pb-3 border-b border-[var(--border-subtle)]">
          <div className="space-y-1">
            {title && <h2 className="text-base font-semibold tracking-tight">{title}</h2>}
            {description && (
              <p className="text-xs text-[var(--text-secondary)]">{description}</p>
            )}
          </div>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            aria-label="Close dialog"
            className="h-7 w-7 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="py-4 text-sm">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border-subtle)]">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
