import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ScenarioParams, ScenarioResponse, ScenarioPreset } from "./types";

export const SCENARIO_PRESETS: ScenarioPreset[] = [
  {
    id: "baseline",
    name: "Baseline Operations",
    description: "Standard quay crane deployment (100%) at rated 28 moves/crane-hour.",
    crane_factor: 1.0,
    move_rate: 28.0,
    category: "STANDARD",
    badgeColor: "var(--accent)",
  },
  {
    id: "crane_outage_moderate",
    name: "Moderate Crane Outage (-15%)",
    description: "Unplanned mechanical outage taking 15% of STS cranes out of service.",
    crane_factor: 0.85,
    move_rate: 28.0,
    category: "DISRUPTION",
    badgeColor: "var(--status-warning)",
  },
  {
    id: "crane_outage_severe",
    name: "Severe Crane Disruption (-30%)",
    description: "Major power or maintenance disruption reducing crane availability to 70%.",
    crane_factor: 0.70,
    move_rate: 25.0,
    category: "DISRUPTION",
    badgeColor: "var(--status-critical)",
  },
  {
    id: "productivity_boost",
    name: "Peak Productivity Surge",
    description: "Dual-cycle crane automation boosting move rate from 28 to 34 moves/hour.",
    crane_factor: 1.0,
    move_rate: 34.0,
    category: "PRODUCTIVITY",
    badgeColor: "var(--status-success)",
  },
  {
    id: "stress_test",
    name: "Terminal Congestion Stress Test",
    description: "Combined 40% crane reduction and throughput drop to 22 moves/hour.",
    crane_factor: 0.60,
    move_rate: 22.0,
    category: "STRESS",
    badgeColor: "var(--status-critical)",
  },
];

export function useScenarios() {
  const [params, setParams] = useState<ScenarioParams>({
    crane_factor: 0.85,
    move_rate_per_crane_hour: 28.0,
  });

  const [activePresetId, setActivePresetId] = useState<string>("crane_outage_moderate");

  // Run scenario mutation calling real OR-Tools CP-SAT discrete solver via FastAPI
  const mutation = useMutation<ScenarioResponse, Error, ScenarioParams>({
    mutationFn: async (p: ScenarioParams) => {
      return (await api.scenario({
        crane_factor: p.crane_factor,
        move_rate_per_crane_hour: p.move_rate_per_crane_hour,
      })) as ScenarioResponse;
    },
  });

  // Initial baseline query if needed
  const baselineQuery = useQuery({
    queryKey: ["scenario-baseline"],
    queryFn: async () => {
      return (await api.scenario({
        crane_factor: 1.0,
        move_rate_per_crane_hour: 28.0,
      })) as ScenarioResponse;
    },
    staleTime: 5 * 60 * 1000,
  });

  const applyPreset = (preset: ScenarioPreset) => {
    setActivePresetId(preset.id);
    const newParams: ScenarioParams = {
      crane_factor: preset.crane_factor,
      move_rate_per_crane_hour: preset.move_rate,
    };
    setParams(newParams);
    mutation.mutate(newParams);
  };

  const runCustomScenario = () => {
    setActivePresetId("custom");
    mutation.mutate(params);
  };

  return {
    params,
    setParams,
    activePresetId,
    applyPreset,
    runCustomScenario,
    data: mutation.data || baselineQuery.data,
    isLoading: mutation.isPending || baselineQuery.isLoading,
    isInitialLoading: baselineQuery.isLoading && !mutation.data,
    error: mutation.error || baselineQuery.error,
    presets: SCENARIO_PRESETS,
  };
}
