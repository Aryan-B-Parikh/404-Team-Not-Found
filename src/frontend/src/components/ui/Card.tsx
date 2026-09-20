import React from "react";
import { cn } from "../../lib/utils";

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  variant?: "default" | "elevated" | "interactive";
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  status?: React.ReactNode;
}

export function Card({
  className,
  variant = "default",
  title,
  description,
  action,
  status,
  children,
  ...props
}: CardProps) {
  const variantStyles = {
    default: "bg-[var(--bg-surface)] border-[var(--border-default)]",
    elevated: "bg-[var(--bg-surface-elevated)] border-[var(--border-subtle)]",
    interactive:
      "bg-[var(--bg-surface)] border-[var(--border-default)] hover:border-[var(--border-elevated)] hover:bg-[var(--bg-surface-hover)] transition-all cursor-pointer",
  };

  const hasHeader = Boolean(title || description || action || status);

  return (
    <div
      className={cn(
        "border rounded-lg p-3.5 sm:p-4 text-[var(--text-primary)] shadow-xs transition-colors",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {hasHeader && (
        <div className="flex items-start justify-between gap-4 pb-3 border-b border-[var(--border-subtle)] mb-3">
          <div className="space-y-1">
            {title && (
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
                  {title}
                </h3>
                {status}
              </div>
            )}
            {description && (
              <p className="text-xs text-[var(--text-secondary)]">{description}</p>
            )}
          </div>
          {action && <div className="flex items-center gap-2 shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex items-start justify-between gap-4 pb-3 border-b border-[var(--border-subtle)] mb-3", className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn("text-sm font-semibold text-[var(--text-primary)] tracking-tight", className)} {...props}>
      {children}
    </h3>
  );
}

export function CardDescription({ className, children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn("text-xs text-[var(--text-secondary)]", className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("space-y-3", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("pt-3 mt-3 border-t border-[var(--border-subtle)] flex items-center justify-between text-xs text-[var(--text-muted)]", className)} {...props}>
      {children}
    </div>
  );
}
