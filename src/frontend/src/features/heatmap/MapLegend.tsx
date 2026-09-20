import { useState } from "react";
import { Anchor, AlertTriangle, Layers, X } from "lucide-react";

export function MapLegend() {
  const [mobileExpanded, setMobileExpanded] = useState(false);

  const scale = [
    { label: "Low", range: "0–40", color: "#2F6F86", bg: "rgba(47,111,134,0.18)" },
    { label: "Elevated", range: "40–60", color: "#B7791F", bg: "rgba(183,121,31,0.18)" },
    { label: "High", range: "60–80", color: "#C26E4A", bg: "rgba(194,110,74,0.18)" },
    { label: "Critical", range: "80+", color: "#B94A48", bg: "rgba(185,74,72,0.18)" },
  ];

  const renderLegendBody = () => (
    <>
      <div className="grid grid-cols-4 gap-1.5">
        {scale.map((s) => (
          <div key={s.label} className="flex flex-col items-center gap-1">
            <div
              className="w-full h-1.5 rounded-full"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-[10px] font-semibold" style={{ color: s.color }}>
              {s.label}
            </span>
            <span className="text-[9px] font-mono text-[var(--text-muted)]">{s.range}</span>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-[var(--border-subtle)] grid grid-cols-2 gap-2 text-[10px] text-[var(--text-secondary)]">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[var(--brand)] shrink-0" />
          <span>Container Terminal</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Anchor className="w-3 h-3 text-[var(--brand)] shrink-0" />
          <span>Anchorage Queue</span>
        </div>
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3 h-3 text-[var(--status-critical)] shrink-0" />
          <span>Anomaly Flagged</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-1 border border-dashed border-[var(--brand)] shrink-0" />
          <span>Navigation Fairway</span>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile Collapsible Legend (< 640px) */}
      <div className="absolute bottom-3 left-3 z-10 sm:hidden select-none pointer-events-auto">
        {mobileExpanded ? (
          <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]/95 backdrop-blur-xs text-xs shadow-md space-y-2 max-w-[280px]">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] border-b border-[var(--border-subtle)] pb-1">
              <span>Congestion Scale</span>
              <button
                type="button"
                onClick={() => setMobileExpanded(false)}
                aria-label="Hide legend"
                className="p-1 rounded hover:bg-[var(--bg-surface-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            {renderLegendBody()}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setMobileExpanded(true)}
            aria-label="Show map legend"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-[var(--bg-surface)]/92 border border-[var(--border-default)] text-[10px] font-semibold text-[var(--text-secondary)] shadow-xs backdrop-blur-xs hover:text-[var(--text-primary)] cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5 text-[var(--brand)]" />
            <span>Legend</span>
          </button>
        )}
      </div>

      {/* Desktop Persistent Legend (>= 640px) */}
      <div className="hidden sm:block absolute bottom-4 left-4 z-10 p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]/95 backdrop-blur-xs text-xs shadow-md space-y-2 select-none pointer-events-auto max-w-xs">
        <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] border-b border-[var(--border-subtle)] pb-1">
          <span>Congestion Scale</span>
          <span className="font-mono text-[var(--text-muted)]">0–100 Scale</span>
        </div>
        {renderLegendBody()}
      </div>
    </>
  );
}
