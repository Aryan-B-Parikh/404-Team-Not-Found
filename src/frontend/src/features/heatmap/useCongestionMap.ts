import { useState, useMemo } from "react";
import { useOverview, useTerminals, useVessels } from "../../hooks";
import type { EnrichedTerminal, MapFilterState, AnchorageZone, VesselItem } from "./types";

const ANCHORAGE_GEOMETRY = [
  { match: "san pedro anchorage a", code: "ANCH-A", name: "San Pedro Anchorage A (Outer Harbor)", lat: 33.722, lon: -118.225 },
  { match: "san pedro anchorage b", code: "ANCH-B", name: "San Pedro Anchorage B (Long Beach Outer)", lat: 33.715, lon: -118.195 },
  { match: "long beach anchorage c", code: "ANCH-C", name: "Long Beach Anchorage C", lat: 33.705, lon: -118.165 },
  { match: "anchorage 241", code: "ANCH-241", name: "Anchorage 241–243", lat: 33.700, lon: -118.145 },
  { match: "point fermin", code: "ANCH-F", name: "Outside Point Fermin", lat: 33.690, lon: -118.300 },
];

export function useCongestionMap() {
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useOverview();
  const { data: terminalsData, isLoading: terminalsLoading, error: terminalsError } = useTerminals();
  const { data: vesselsData, isLoading: vesselsLoading } = useVessels();
  const [filterState, setFilterState] = useState<MapFilterState>({ horizon: 72, selectedTerminalCode: null, severityFilter: "ALL", mode: "CURRENT", layers: { heatmap: true, markers: true, anchorage: true, fairway: true } });

  const enrichedTerminals: EnrichedTerminal[] = useMemo(() => {
    if (!terminalsData?.terminals || !overview?.zones) return [];
    return terminalsData.terminals.map((term: any) => {
      const zone = overview.zones.find((z: any) => z.zone_code === term.zone_code);
      const hotspot = overview.hotspots?.ranked?.find((h: any) => h.zone_code === term.zone_code);
      const anomaly = overview.anomalies?.find((a: any) => a.zone_code === term.zone_code);
      const currentIndex = zone?.current_index ?? 50.0; const peakIndex = zone?.peak_index ?? currentIndex;
      const activeScore = filterState.mode === "FORECAST" ? peakIndex : currentIndex;
      const level = activeScore >= 80 ? "CRITICAL" : activeScore >= 60 ? "HIGH" : activeScore >= 40 ? "ELEVATED" : "LOW";
      return { ...term, current_index: currentIndex, peak_index: peakIndex, peak_hour: zone?.peak_hour ?? 16, queue_now: zone?.queue_now ?? 0, wait_now: zone?.wait_now ?? 0, yard_util_pct: zone?.yard_util_pct ?? 0, level, risk_score: hotspot?.risk_score, binding_constraint: hotspot?.binding_constraint, confidence: hotspot?.confidence, has_anomaly: anomaly?.is_anomaly ?? false, anomaly_kind: anomaly?.kind, recent_index: zone?.recent_index ?? [] };
    });
  }, [terminalsData, overview, filterState.mode]);

  const filteredTerminals = useMemo(() => enrichedTerminals.filter((t) => {
    if (filterState.selectedTerminalCode && t.code !== filterState.selectedTerminalCode) return false;
    if (filterState.severityFilter !== "ALL" && t.level !== filterState.severityFilter) return false;
    return true;
  }), [enrichedTerminals, filterState.selectedTerminalCode, filterState.severityFilter]);

  const selectedTerminal = useMemo(() => !filterState.selectedTerminalCode ? null : enrichedTerminals.find((t) => t.code === filterState.selectedTerminalCode) || null, [enrichedTerminals, filterState.selectedTerminalCode]);
  const terminalVessels: VesselItem[] = useMemo(() => !vesselsData?.vessels || !selectedTerminal ? [] : vesselsData.vessels.filter((v: any) => v.dest_zone_code === selectedTerminal.zone_code) as VesselItem[], [vesselsData, selectedTerminal]);

  const anchorages: AnchorageZone[] = useMemo(() => {
    const vessels = ((vesselsData?.vessels ?? []) as any[]).filter((v) => v.status === "ANCHORAGE" || Number(v.anchored_hours || 0) > 0);
    return ANCHORAGE_GEOMETRY.map((g) => {
      const rows = vessels.filter((v) => String(v.anchorage_zone ?? "").toLowerCase().includes(g.match));
      const wait = rows.length ? rows.reduce((s, v) => s + Number(v.anchored_hours || 0), 0) / rows.length : 0;
      return { code: g.code, name: g.name, lat: g.lat, lon: g.lon, vessels_count: rows.length, avg_wait_hours: Number(wait.toFixed(1)) };
    }).filter((a) => a.vessels_count > 0);
  }, [vesselsData]);

  const setSelectedTerminalCode = (code: string | null) => setFilterState((prev) => ({ ...prev, selectedTerminalCode: code }));
  const setHorizon = (horizon: 24 | 48 | 72) => setFilterState((prev) => ({ ...prev, horizon }));
  const setSeverityFilter = (severity: MapFilterState["severityFilter"]) => setFilterState((prev) => ({ ...prev, severityFilter: severity }));
  const setMode = (mode: "CURRENT" | "FORECAST") => setFilterState((prev) => ({ ...prev, mode }));
  const toggleLayer = (layer: keyof MapFilterState["layers"]) => setFilterState((prev) => ({ ...prev, layers: { ...prev.layers, [layer]: !prev.layers[layer] } }));

  return { terminals: enrichedTerminals, filteredTerminals, selectedTerminal, terminalVessels, anchorages, filterState, datasetSource: (overview as any)?.dataset?.source ?? "UNKNOWN", setSelectedTerminalCode, setHorizon, setSeverityFilter, setMode, toggleLayer, isLoading: overviewLoading || terminalsLoading || vesselsLoading, error: overviewError || terminalsError };
}
