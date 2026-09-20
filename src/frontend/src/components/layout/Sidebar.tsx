import React from "react";
import { LayoutDashboard, Activity, TrendingUp, Ship, Route, CalendarRange, GitCompare, Database, Bot, Anchor, ChevronLeft, ChevronRight, X } from "lucide-react";
import { cn } from "../../lib/utils";

export interface NavItem { id: string; label: string; icon: React.ComponentType<{ className?: string }>; badge?: string; phaseBadge?: string; }
export interface NavSection { title: string; items: NavItem[]; }

export const NAV_SECTIONS: NavSection[] = [
  { title: "COMMAND", items: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "congestion", label: "Congestion", icon: Activity },
    { id: "forecast", label: "Forecast", icon: TrendingUp },
  ]},
  { title: "OPERATIONS", items: [
    { id: "berth", label: "Berths & Cranes", icon: Ship },
    { id: "routing", label: "Routing", icon: Route },
    { id: "plan", label: "72-Hour Plan", icon: CalendarRange },
  ]},
  { title: "ANALYSIS", items: [
    { id: "scenarios", label: "Scenarios", icon: GitCompare, badge: "P3" },
    { id: "quality", label: "Data Quality", icon: Database },
  ]},
  { title: "AI", items: [{ id: "bob", label: "Bob AI", icon: Bot, badge: "MCP" }] },
];

export interface SidebarProps { activeTab: string; onSelectTab: (id: string) => void; collapsed?: boolean; onToggleCollapse?: () => void; onCloseMobile?: () => void; className?: string; }

export function Sidebar({ activeTab, onSelectTab, collapsed = false, onToggleCollapse, onCloseMobile, className }: SidebarProps) {
  return (
    <aside className={cn("flex flex-col border-r border-[var(--border-default)] bg-[var(--bg-sidebar)] select-none transition-[width] duration-200 shrink-0 z-20", collapsed ? "w-[68px]" : "w-60 lg:w-64", className)}>
      <div className={cn("h-16 flex items-center border-b border-[var(--border-subtle)] relative", collapsed ? "justify-center px-0" : "justify-between px-4")}>
        {collapsed ? (
          <div className="flex items-center justify-center w-full relative">
            <button type="button" onClick={onToggleCollapse} aria-label="PortPulse AI — Expand sidebar" title="PortPulse AI (Click to expand)" className="w-10 h-10 rounded-lg bg-[var(--nav-active-bg)] border border-[var(--brand-border)] flex items-center justify-center cursor-pointer transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)]"><Anchor className="w-5 h-5 text-[var(--nav-active-icon)] shrink-0" /></button>
            {onToggleCollapse && <button type="button" onClick={onToggleCollapse} aria-label="Expand sidebar" title="Expand sidebar" className="absolute -right-3 top-2.5 w-5 h-5 rounded-full bg-[var(--bg-surface-elevated)] border border-[var(--border-strong)] shadow-xs flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--brand)] transition-all z-30 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)] cursor-pointer"><ChevronRight className="w-3 h-3" /></button>}
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 overflow-hidden min-w-0">
              <div className="w-8 h-8 rounded-lg bg-[var(--nav-active-bg)] border border-[var(--brand-border)] flex items-center justify-center shrink-0"><Anchor className="w-4 h-4 text-[var(--nav-active-icon)] shrink-0" /></div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5 font-bold tracking-wider text-sm text-[var(--text-primary)] leading-none"><span>PORTPULSE</span><span className="text-[10px] px-1 py-0.2 rounded font-mono font-semibold bg-[var(--brand)] text-white">AI</span></div>
                <span className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-medium mt-1 truncate">Port Operations Intelligence</span>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              {onCloseMobile && <button type="button" onClick={onCloseMobile} aria-label="Close navigation menu" className="md:hidden min-w-[36px] min-h-[36px] flex items-center justify-center rounded-md hover:bg-[var(--bg-surface-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)] cursor-pointer"><X className="w-5 h-5" /></button>}
              {onToggleCollapse && <button type="button" onClick={onToggleCollapse} aria-label="Collapse sidebar" title="Collapse sidebar" className="hidden md:flex p-1.5 rounded hover:bg-[var(--bg-surface-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)] cursor-pointer"><ChevronLeft className="w-4 h-4" /></button>}
            </div>
          </>
        )}
      </div>
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        {NAV_SECTIONS.map((section) => <div key={section.title} className="space-y-1">
          {!collapsed ? <div className="px-2.5 py-1 text-[10px] font-bold tracking-wider uppercase text-[var(--text-muted)]">{section.title}</div> : <div className="h-1.5" />}
          {section.items.map((item) => {
            const Icon = item.icon; const isActive = activeTab === item.id;
            return <button key={item.id} type="button" onClick={() => onSelectTab(item.id)} title={collapsed ? item.label : undefined} aria-label={item.label} aria-current={isActive ? "page" : undefined} className={cn("w-full flex items-center rounded-md text-xs font-medium transition-all group focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)] text-left cursor-pointer", collapsed ? "justify-center px-0 py-2.5" : "gap-2.5 px-2.5 py-2", isActive ? "bg-[var(--nav-active-bg)] text-[var(--nav-active-text)] font-semibold shadow-2xs" : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] border border-transparent")}>
              <Icon className={cn("w-4 h-4 shrink-0 transition-colors", isActive ? "text-[var(--nav-active-icon)]" : "text-[var(--text-muted)] group-hover:text-[var(--text-primary)]")} />
              {!collapsed && <div className="flex items-center justify-between flex-1 min-w-0"><span className="truncate">{item.label}</span>{item.badge && <span className="text-[10px] px-1.5 py-0.2 rounded font-mono font-medium bg-[var(--brand-soft)] text-[var(--text-accent)] border border-[var(--brand-border)]">{item.badge}</span>}{item.phaseBadge && <span className="text-[9px] px-1 py-0.2 rounded font-mono text-[var(--text-muted)] bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)]">{item.phaseBadge}</span>}</div>}
            </button>;
          })}
        </div>)}
      </div>
      {!collapsed && <div className="p-3 border-t border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)]/40 text-[11px] space-y-1"><div className="font-medium text-[var(--text-secondary)]">Scope: San Pedro Bay</div><div className="text-[10px] text-[var(--text-muted)]">LBCT · ITS · PCT · TTI</div></div>}
    </aside>
  );
}
