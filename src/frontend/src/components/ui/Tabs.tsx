import React from "react";
import { cn } from "../../lib/utils";

export interface TabsContextValue {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | undefined>(undefined);

export interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({ value, onValueChange, children, className }: TabsProps) {
  return (
    <TabsContext.Provider value={{ activeTab: value, setActiveTab: onValueChange }}>
      <div className={cn("w-full space-y-4", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex items-center gap-1 p-1 rounded-lg bg-[var(--bg-surface-elevated)] border border-[var(--border-default)]",
        className
      )}
    >
      {children}
    </div>
  );
}

export interface TabTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  badge?: React.ReactNode;
}

export function TabTrigger({ value, badge, className, children, ...props }: TabTriggerProps) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error("TabTrigger must be used within Tabs");

  const isActive = context.activeTab === value;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      onClick={() => context.setActiveTab(value)}
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all select-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)]",
        isActive
          ? "bg-[var(--bg-surface)] text-[var(--text-accent)] border border-[var(--border-default)] shadow-xs font-semibold"
          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] border border-transparent",
        className
      )}
      {...props}
    >
      <span>{children}</span>
      {badge && <span className="ml-1">{badge}</span>}
    </button>
  );
}

export function TabContent({
  value,
  className,
  children,
}: {
  value: string;
  className?: string;
  children: React.ReactNode;
}) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error("TabContent must be used within Tabs");

  if (context.activeTab !== value) return null;

  return (
    <div role="tabpanel" className={cn("animate-in fade-in duration-100", className)}>
      {children}
    </div>
  );
}
