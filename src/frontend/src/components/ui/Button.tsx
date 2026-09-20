import React, { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "destructive" | "accent";
  size?: "xs" | "sm" | "md" | "lg" | "icon";
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "secondary", size = "sm", loading = false, disabled, children, icon, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg-app)] disabled:opacity-50 disabled:pointer-events-none select-none cursor-pointer";

    const variants = {
      primary:
        "bg-[var(--brand)] text-white hover:bg-[var(--brand-hover)] border border-[var(--brand-border)] shadow-xs font-semibold",
      secondary:
        "bg-[var(--bg-surface-elevated)] text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border-default)] hover:border-[var(--border-elevated)] shadow-xs",
      outline:
        "bg-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border-default)] hover:border-[var(--border-elevated)]",
      ghost:
        "bg-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] border border-transparent",
      destructive:
        "bg-[var(--status-critical-bg)] text-[var(--status-critical)] hover:bg-[var(--status-critical)]/20 border border-[var(--status-critical-border)]",
      accent:
        "bg-[var(--brand-soft)] text-[var(--text-accent)] hover:bg-[var(--brand-soft)]/80 border border-[var(--brand-border)]",
    };

    const sizes = {
      xs: "h-7 px-2.5 text-xs rounded",
      sm: "h-8 px-3 text-xs rounded-md gap-1.5",
      md: "h-9 px-4 text-sm rounded-md gap-2",
      lg: "h-10 px-5 text-sm rounded-md gap-2.5",
      icon: "h-8 w-8 rounded-md p-0",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
        ) : icon ? (
          <span className="shrink-0">{icon}</span>
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
