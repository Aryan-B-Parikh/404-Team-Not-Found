import React, { forwardRef } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options?: SelectOption[];
  sizeVariant?: "xs" | "sm" | "md";
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, options, children, sizeVariant = "sm", ...props }, ref) => {
    const sizeClasses = {
      xs: "h-7 text-xs px-2.5 pr-7",
      sm: "h-8 text-xs px-3 pr-8",
      md: "h-9 text-sm px-3 pr-8",
    };

    return (
      <div className="inline-flex flex-col gap-1">
        {label && <span className="text-[11px] font-medium text-[var(--text-secondary)]">{label}</span>}
        <div className="relative inline-block w-full">
          <select
            ref={ref}
            className={cn(
              "w-full appearance-none rounded-md bg-[var(--bg-surface-elevated)] border border-[var(--border-default)] text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed",
              sizeClasses[sizeVariant],
              className
            )}
            {...props}
          >
            {options
              ? options.map((opt) => (
                  <option
                    key={opt.value}
                    value={opt.value}
                    disabled={opt.disabled}
                    className="bg-[var(--bg-surface)] text-[var(--text-primary)]"
                  >
                    {opt.label}
                  </option>
                ))
              : children}
          </select>
          <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none text-[var(--text-muted)]" />
        </div>
      </div>
    );
  }
);

Select.displayName = "Select";
