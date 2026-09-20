/**
 * PortPulse AI — Map Configuration
 * Geographic bounds, operational coordinates, and restrained congestion thresholds.
 */

export const MAP_CONFIG = {
  // San Pedro Bay Geography & Terminals Center (POLB & POLA)
  center: [-118.25, 33.75] as [number, number],
  defaultZoom: 11,
  minZoom: 9,
  maxZoom: 17,

  // Geographical bounds constraint around Southern California to keep operators focused
  // Wider than the tight terminal cluster so the Polaris-style basemap is useful at zoom 11.
  maxBounds: [
    [-119.25, 33.20], // Southwest coordinate
    [-117.25, 34.30], // Northeast coordinate
  ] as [[number, number], [number, number]],

  // Restrained 4-Tier Semantic Congestion Thresholds (Phase 2.5)
  thresholds: {
    low: {
      max: 40,
      label: "Low (Nominal)",
      color: "#2F6F86", // Muted steel/ocean blue
      bgLight: "#E8F1F5",
      bgDark: "rgba(47, 111, 134, 0.20)",
    },
    moderate: {
      max: 60,
      label: "Elevated",
      color: "#B7791F", // Muted amber
      bgLight: "#FBF3E3",
      bgDark: "rgba(183, 121, 31, 0.20)",
    },
    high: {
      max: 80,
      label: "High",
      color: "#C26E4A", // Warm terracotta
      bgLight: "rgba(194, 110, 74, 0.15)",
      bgDark: "rgba(194, 110, 74, 0.22)",
    },
    critical: {
      max: 100,
      label: "Critical (Severe)",
      color: "#B94A48", // Muted red
      bgLight: "#F9E9E8",
      bgDark: "rgba(185, 74, 72, 0.24)",
    },
  },

  // Navigation Fairways & Anchorage Queues
  fairwayLine: {
    color: "#3B6F8F",
    dashArray: [3, 3],
  },
};
