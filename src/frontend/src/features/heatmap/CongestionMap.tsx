import React, { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { EnrichedTerminal, MapFilterState, AnchorageZone } from "./types";
import { MapLegend } from "./MapLegend";
import { useTheme } from "../../lib/theme";
import { createMaritimeMapStyle, MAP_CONFIG, defaultMapProvider } from "./map";

interface GeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: {
      type: "Point";
      coordinates: [number, number];
    };
    properties: {
      code: string;
      name: string;
      congestion: number;
      normalized: number;
    };
  }>;
}

export interface CongestionMapProps {
  terminals: EnrichedTerminal[];
  anchorages: AnchorageZone[];
  filterState: MapFilterState;
  selectedTerminal: EnrichedTerminal | null;
  onSelectTerminal: (code: string) => void;
  onResetView?: () => void;
  className?: string;
}

export function CongestionMap({
  terminals,
  anchorages,
  filterState,
  selectedTerminal,
  onSelectTerminal,
  className,
}: CongestionMapProps) {
  const { theme } = useTheme();
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [tileError, setTileError] = useState(false);

  // Initialize MapLibre
  useEffect(() => {
    if (!mapContainer.current) return;

    try {
      const initialStyle = createMaritimeMapStyle(theme);

      const map = new maplibregl.Map({
        container: mapContainer.current,
        style: initialStyle,
        center: MAP_CONFIG.center,
        zoom: MAP_CONFIG.defaultZoom,
        minZoom: MAP_CONFIG.minZoom,
        maxZoom: MAP_CONFIG.maxZoom,
        attributionControl: false,
      });

      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

      map.on("load", () => {
        setMapLoaded(true);
        setTileError(false);
      });

      map.on("error", () => {
        // Fallback: If external tile provider encounters network latency, canvas and markers still render gracefully
        setMapLoaded(true);
        setTileError(true);
      });

      const resizeObserver = new ResizeObserver(() => {
        map.resize();
      });
      resizeObserver.observe(mapContainer.current);

      mapRef.current = map;

      return () => {
        resizeObserver.disconnect();
        markersRef.current.forEach((m) => m.remove());
        markersRef.current = [];
        map.remove();
        mapRef.current = null;
      };
    } catch (err) {
      console.error("MapLibre initialization notice:", err);
      setMapLoaded(true);
    }
  }, []);

  // Update map style dynamically when user toggles Light/Dark theme
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    try {
      map.setStyle(createMaritimeMapStyle(theme), { diff: true });
    } catch {
      // ignore style diff errors
    }
  }, [theme, mapLoaded]);

  // Update Heatmap Source & Layers when terminals, mode, or layers change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const sourceId = "congestion-heatmap-source";
    const heatmapLayerId = "congestion-heatmap-layer";
    const circleLayerId = "congestion-circle-layer";

    const updateLayers = () => {
      // Build GeoJSON features from terminals
      const geojsonData: GeoJsonFeatureCollection = {
        type: "FeatureCollection",
        features: terminals.map((t) => {
          const val = filterState.mode === "FORECAST" ? t.peak_index : t.current_index;
          return {
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [t.lon, t.lat],
            },
            properties: {
              code: t.code,
              name: t.name,
              congestion: val,
              normalized: Math.min(Math.max(val / 100, 0), 1),
            },
          };
        }),
      };

      if (map.getSource(sourceId)) {
        (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(geojsonData);
      } else {
        map.addSource(sourceId, {
          type: "geojson",
          data: geojsonData,
        });

        // Restrained Heatmap Density Layer (Phase 2.5)
        map.addLayer({
          id: heatmapLayerId,
          type: "heatmap",
          source: sourceId,
          maxzoom: 15,
          paint: {
            "heatmap-weight": ["get", "normalized"],
            "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 10, 1.1, 14, 2.2],
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(9, 13, 16, 0)",
              0.2,
              "rgba(47, 111, 134, 0.35)", // Low (muted steel/ocean blue)
              0.4,
              "rgba(183, 121, 31, 0.50)",  // Moderate (muted amber)
              0.7,
              "rgba(194, 110, 74, 0.70)",  // High (warm orange)
              1,
              "rgba(185, 74, 72, 0.85)",   // Critical (muted red)
            ],
            "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 10, 30, 14, 70],
            "heatmap-opacity": filterState.layers.heatmap ? 0.70 : 0,
          },
        });

        // Point Circle indicator layer for higher zoom
        map.addLayer({
          id: circleLayerId,
          type: "circle",
          source: sourceId,
          minzoom: 12,
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["get", "congestion"], 0, 12, 100, 30],
            "circle-color": [
              "interpolate",
              ["linear"],
              ["get", "congestion"],
              0,
              "#2F6F86",
              40,
              "#B7791F",
              60,
              "#C26E4A",
              80,
              "#B94A48",
            ],
            "circle-opacity": filterState.layers.heatmap ? 0.20 : 0,
            "circle-stroke-width": 1.2,
            "circle-stroke-color": [
              "interpolate",
              ["linear"],
              ["get", "congestion"],
              0,
              "#2F6F86",
              40,
              "#B7791F",
              60,
              "#C26E4A",
              80,
              "#B94A48",
            ],
            "circle-stroke-opacity": filterState.layers.heatmap ? 0.45 : 0,
          },
        });
      }

      if (map.getLayer(heatmapLayerId)) {
        map.setPaintProperty(heatmapLayerId, "heatmap-opacity", filterState.layers.heatmap ? 0.70 : 0);
      }
      if (map.getLayer(circleLayerId)) {
        map.setPaintProperty(circleLayerId, "circle-opacity", filterState.layers.heatmap ? 0.20 : 0);
        map.setPaintProperty(circleLayerId, "circle-stroke-opacity", filterState.layers.heatmap ? 0.45 : 0);
      }
    };

    if (map.isStyleLoaded()) {
      updateLayers();
    } else {
      map.once("style.load", updateLayers);
    }
  }, [terminals, mapLoaded, filterState.mode, filterState.layers.heatmap, theme]);

  // Update Interactive HTML GIS Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clean old markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    if (!filterState.layers.markers) return;

    const isDark = theme === "dark";

    // 1. Terminal GIS Markers
    terminals.forEach((term) => {
      const isSelected = selectedTerminal?.code === term.code;
      const el = document.createElement("div");
      el.className = "portflow-gis-marker";
      el.style.cursor = "pointer";

      const val = (filterState.mode === "FORECAST" ? term.peak_index : term.current_index).toFixed(1);
      const isCrit = term.current_index >= 80;
      const badgeColor =
        term.current_index >= 80
          ? "#B94A48"
          : term.current_index >= 60
          ? "#C26E4A"
          : term.current_index >= 40
          ? "#B7791F"
          : "#2F6F86";

      const cardBg = isDark ? (isSelected ? "#181F24" : "#0F1418") : isSelected ? "#F4F7F8" : "#FFFFFF";
      const cardBorder = isSelected ? "var(--brand)" : isDark ? "#273139" : "#D8E1E5";
      const textColor = isDark ? "#E8EEF1" : "#102A35";

      el.innerHTML = `
        <div style="
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 3px 7px;
          border-radius: 6px;
          background: ${cardBg};
          border: 1px solid ${cardBorder};
          box-shadow: 0 2px 8px rgba(0,0,0,${isDark ? "0.4" : "0.08"});
          transition: transform 0.15s ease;
          font-family: inherit;
        ">
          <span style="font-weight: 600; font-size: 11px; color: ${textColor}; letter-spacing: 0.02em;">${term.code}</span>
          <span style="
            font-size: 10px;
            font-weight: 700;
            font-family: monospace;
            padding: 1px 5px;
            border-radius: 4px;
            background: ${badgeColor};
            color: #ffffff;
            line-height: 1.2;
          ">${val}</span>
          ${isCrit ? '<span style="color: #B94A48; font-size: 9px;">●</span>' : ""}
        </div>
      `;

      el.addEventListener("click", (e) => {
        e.stopPropagation();
        onSelectTerminal(term.code);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([term.lon, term.lat])
        .addTo(map);

      markersRef.current.push(marker);
    });

    // 2. Anchorage Markers
    if (filterState.layers.anchorage) {
      anchorages.forEach((anch) => {
        const el = document.createElement("div");
        el.className = "portflow-anchorage-marker";
        const anchBg = isDark ? "rgba(15, 20, 24, 0.88)" : "rgba(255, 255, 255, 0.92)";
        const anchBorder = isDark ? "rgba(59, 111, 143, 0.45)" : "rgba(23, 107, 135, 0.35)";
        const anchText = isDark ? "#5FA5BB" : "#176B87";
        const valText = isDark ? "#E8EEF1" : "#102A35";

        el.innerHTML = `
          <div style="
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 2px 6px;
            border-radius: 4px;
            background: ${anchBg};
            border: 1px dashed ${anchBorder};
            font-size: 9px;
            color: ${anchText};
            font-family: monospace;
          ">
            <span>⚓ ${anch.code}</span>
            <span style="color: ${valText}; font-weight: bold;">${anch.vessels_count}v</span>
          </div>
        `;
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([anch.lon, anch.lat])
          .addTo(map);

        markersRef.current.push(marker);
      });
    }
  }, [terminals, anchorages, filterState.layers.markers, filterState.layers.anchorage, filterState.mode, selectedTerminal, onSelectTerminal, theme]);

  // Fly to selected terminal if clicked
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedTerminal) return;

    map.flyTo({
      center: [selectedTerminal.lon, selectedTerminal.lat],
      zoom: 13.5,
      essential: true,
      duration: 800,
    });
  }, [selectedTerminal]);

  return (
    <div className={`relative w-full h-[400px] sm:h-[480px] lg:h-[580px] rounded-lg overflow-hidden border border-[var(--border-default)] bg-[var(--bg-app)] ${className || ""}`}>
      {/* MapLibre Canvas Container */}
      <div ref={mapContainer} className="w-full h-full" />

      {/* Map Legend */}
      <MapLegend />

      {/* Operational Scope & Data Honesty Overlay */}
      <div className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded-md bg-[var(--bg-surface)]/90 border border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)] font-mono shadow-xs pointer-events-none">
        San Pedro Bay · POLB / POLA Real Coordinates
      </div>

      {/* Tile attribution / error notice */}
      <div className="absolute bottom-2 right-3 z-10 px-2 py-0.5 rounded text-[9px] text-[var(--text-muted)] bg-[var(--bg-surface)]/80 backdrop-blur-xs pointer-events-none">
        {tileError ? "Tile server unreachable — markers and heatmap only" : defaultMapProvider.getShortAttribution()}
      </div>
    </div>
  );
}
