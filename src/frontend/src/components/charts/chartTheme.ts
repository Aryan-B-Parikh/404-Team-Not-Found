// Operational Recharts styling tokens matching the maritime command center design system

export const chartTheme = {
  colors: {
    brand: "#176B87",         // Ocean Blue primary
    oceanBlue: "#176B87",
    oceanBlueDark: "#4C91A8",
    steelBlue: "#2F6F86",     // Steel Blue secondary
    mutedBlue: "#4C8194",     // Muted Blue forecast
    uncertaintyBand: "rgba(23, 107, 135, 0.12)",
    accent: "var(--brand)",
    accentBg: "var(--brand-soft)",
    forecast: "#4C8194",
    forecastBand: "rgba(76, 129, 148, 0.14)",
    baseline: "#71818A",      // Muted slate baseline
    success: "#2F7D65",       // Restrained green
    warning: "#B7791F",       // Restrained amber
    high: "#C26E4A",          // Restrained terracotta
    critical: "#B94A48",      // Restrained red
    info: "#3B6F8F",          // Steel blue info
    grid: "var(--border-subtle)",
    axis: "var(--border-default)",
    tickText: "var(--text-muted)",
  },
  typography: {
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontSize: 11,
    tickFontSize: 10,
  },
  grid: {
    stroke: "var(--border-subtle, #1C2630)",
    strokeDasharray: "3 3",
  },
  axis: {
    stroke: "var(--border-default, #26313D)",
    tick: { fill: "var(--text-muted, #74808C)", fontSize: 10 },
  },
  tooltipContentStyle: {
    backgroundColor: "var(--bg-surface-elevated, #171F29)",
    borderColor: "var(--border-default, #26313D)",
    borderRadius: "8px",
    boxShadow: "0 4px 14px rgba(0, 0, 0, 0.35)",
    color: "var(--text-primary, #E7EDF3)",
    fontSize: "12px",
    padding: "8px 12px",
  },
  tooltipItemStyle: {
    color: "var(--text-primary, #E7EDF3)",
    fontSize: "11px",
    padding: "2px 0",
  },
};

