import { useState, useEffect } from "react";
import { RefreshCw, MapPin, Clock, Menu, Sun, Moon, Laptop } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "../ui/Button";
import { SystemStatus } from "./SystemStatus";
import { useTheme } from "../../lib/theme";

export interface TopbarProps {
  activeTitle?: string;
  activeSubtitle?: string;
  onRefresh?: () => void;
  refreshing?: boolean;
  onToggleMobileMenu?: () => void;
  className?: string;
}

export function Topbar({
  activeTitle,
  activeSubtitle,
  onRefresh,
  refreshing = false,
  onToggleMobileMenu,
  className,
}: TopbarProps) {
  const { theme, themeMode, setThemeMode } = useTheme();
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const d = new Date();
      setTimeStr(
        d.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: true,
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header
      className={cn(
        "h-16 border-b border-[var(--border-default)] bg-[var(--bg-surface)] px-3 sm:px-6 flex items-center justify-between z-10 shrink-0 select-none",
        className
      )}
    >
      {/* Left: Operational Context & Mobile Hamburger */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {onToggleMobileMenu && (
          <button
            type="button"
            onClick={onToggleMobileMenu}
            aria-label="Open mobile navigation menu"
            className="md:hidden min-w-[36px] min-h-[36px] flex items-center justify-center rounded-md hover:bg-[var(--bg-surface-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--brand)] cursor-pointer"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <div className="min-w-0">
          <h1 className="text-sm sm:text-base md:text-lg font-semibold text-[var(--text-primary)] tracking-tight truncate max-w-[140px] xs:max-w-[200px] sm:max-w-none">
            {activeTitle || "PortFlow SBX"}
          </h1>
          {activeSubtitle && (
            <p className="text-xs text-[var(--text-secondary)] truncate hidden sm:block">{activeSubtitle}</p>
          )}
        </div>
      </div>

      {/* Right: Location, System Status, Theme Toggle, Clock, Refresh */}
      <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
        {/* Maritime Location Control (Clean, Compact, Not a bulky badge) */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
          <MapPin className="w-3.5 h-3.5 text-[var(--brand)] shrink-0" />
          <span className="font-medium">San Pedro Bay</span>
          <span className="text-[var(--text-muted)] font-mono text-[11px]">(POLB/POLA)</span>
        </div>

        {/* Operational Status Pill */}
        <SystemStatus compact />

        {/* Minimal 3-Way Theme Switcher (Dark / Light / System) */}
        <div className="flex items-center rounded-md bg-[var(--bg-surface-elevated)] p-0.5 border border-[var(--border-subtle)] text-xs">
          <button
            type="button"
            onClick={() => setThemeMode("dark")}
            title="Dark Theme"
            aria-label="Dark Theme"
            className={cn(
              "p-1.5 rounded transition-colors cursor-pointer",
              themeMode === "dark"
                ? "bg-[var(--bg-surface)] text-[var(--brand-hover)] shadow-2xs"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            )}
          >
            <Moon className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setThemeMode("light")}
            title="Light Theme"
            aria-label="Light Theme"
            className={cn(
              "p-1.5 rounded transition-colors cursor-pointer",
              themeMode === "light"
                ? "bg-[var(--bg-surface)] text-amber-500 shadow-2xs"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            )}
          >
            <Sun className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setThemeMode("system")}
            title="System Theme"
            aria-label="System Theme"
            className={cn(
              "p-1.5 rounded transition-colors cursor-pointer hidden sm:block",
              themeMode === "system"
                ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-2xs"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            )}
          >
            <Laptop className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Live Clock — Plain Operational Metadata */}
        <div className="hidden xl:flex items-center gap-1.5 text-xs text-[var(--text-muted)] font-mono tabular-nums">
          <Clock className="w-3.5 h-3.5" />
          <span>{timeStr || "—"}</span>
        </div>

        {/* Refresh Action */}
        {onRefresh && (
          <Button
            size="sm"
            variant="outline"
            onClick={onRefresh}
            loading={refreshing}
            icon={<RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />}
            aria-label="Refresh live port telemetry"
            className="px-2 sm:px-3 text-xs"
          >
            <span className="hidden sm:inline">Sync</span>
          </Button>
        )}
      </div>
    </header>
  );
}
