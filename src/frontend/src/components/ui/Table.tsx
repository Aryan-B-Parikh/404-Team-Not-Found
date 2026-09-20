import React from "react";
import { cn } from "../../lib/utils";

export function Table({ className, children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-x-auto rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
      <table className={cn("w-full min-w-[480px] caption-bottom text-xs", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function TableHeader({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className={cn("bg-[var(--bg-surface-elevated)]/60 border-b border-[var(--border-default)]", className)} {...props}>
      {children}
    </thead>
  );
}

export function TableBody({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody className={cn("[&_tr:last-child]:border-0", className)} {...props}>
      {children}
    </tbody>
  );
}

export function TableFooter({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tfoot className={cn("bg-[var(--bg-surface-elevated)] font-medium border-t border-[var(--border-default)]", className)} {...props}>
      {children}
    </tfoot>
  );
}

export function TableRow({ className, children, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-surface-hover)]/70 data-[state=selected]:bg-[var(--bg-surface-active)]",
        className
      )}
      {...props}
    >
      {children}
    </tr>
  );
}

export function TableHead({ className, children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "h-9 px-3 text-left align-middle font-medium text-[var(--text-muted)] text-[11px] uppercase tracking-wider",
        className
      )}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableCell({ className, children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("p-3 align-middle text-[var(--text-primary)] font-normal", className)} {...props}>
      {children}
    </td>
  );
}
