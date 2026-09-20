import React from "react";
import { AlertOctagon, Anchor } from "lucide-react";
import type { EnrichedTerminal } from "./types";

export interface TerminalMarkerProps {
  terminal: EnrichedTerminal;
  isSelected: boolean;
  onClick: () => void;
}

export function TerminalMarker({
  terminal,
  isSelected,
  onClick,
}: TerminalMarkerProps) {
  const getSeverityColor = (score: number) => {
    if (score >= 80) return { bg: "var(--status-critical)", border: "var(--status-critical-border)", text: "#ffffff" };
    if (score >= 60) return { bg: "var(--status-high)", border: "var(--status-high-border)", text: "#ffffff" };
    if (score >= 40) return { bg: "var(--status-warning)", border: "var(--status-warning-border)", text: "#ffffff" };
    return { bg: "var(--brand)", border: "var(--brand-border)", text: "#ffffff" };
  };

  const colors = getSeverityColor(terminal.current_index);

  return (
    <div
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`group cursor-pointer transform -translate-x-1/2 -translate-y-full transition-all duration-150 select-none ${
        isSelected ? "scale-105 z-30" : "hover:scale-102 z-20"
      }`}
    >
      <div
        className={`flex items-center gap-2 px-2.5 py-1 rounded-md shadow-sm transition-all ${
          isSelected
            ? "ring-2 ring-[var(--brand)] ring-offset-2 ring-offset-[var(--bg-app)] bg-[var(--bg-surface)] border border-[var(--brand)] shadow-md"
            : "bg-[var(--bg-surface)] border border-[var(--border-default)] hover:border-[var(--brand-border)]"
        }`}
      >
        <div className="flex items-center gap-1.5">
          <Anchor className="w-3 h-3 text-[var(--brand)] shrink-0" />
          <span className="font-semibold text-xs text-[var(--text-primary)] tracking-wide">
            {terminal.code}
          </span>
          <span className="text-[10px] text-[var(--text-muted)] font-mono">
            {terminal.pier}
          </span>
        </div>

        <span
          className="px-1.5 py-0.5 rounded font-mono font-bold text-[10px] shadow-2xs leading-none"
          style={{ backgroundColor: colors.bg, color: colors.text }}
        >
          {terminal.current_index.toFixed(1)}
        </span>

        {terminal.has_anomaly && (
          <span title="Anomaly Flagged by Isolation Forest" className="shrink-0">
            <AlertOctagon className="w-3 h-3 text-[var(--status-critical)]" />
          </span>
        )}
      </div>

      {/* Subtle bottom indicator pin */}
      <div
        className={`w-0 h-0 mx-auto border-x-4 border-x-transparent border-t-5 ${
          isSelected ? "border-t-[var(--brand)]" : "border-t-[var(--border-default)]"
        }`}
      />
    </div>
  );
}
