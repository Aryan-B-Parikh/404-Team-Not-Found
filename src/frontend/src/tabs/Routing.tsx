import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Route,
  Ship,
  DollarSign,
  TrendingDown,
  Clock,
  Search,
  Filter,
  ArrowRight,
  ShieldAlert,
  Sliders,
  ExternalLink,
} from "lucide-react";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/Card";
import { SkeletonCard } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/ErrorState";
import { EmptyState } from "../components/ui/EmptyState";
import { RoutingDetailDrawer } from "../features/routing/RoutingDetailDrawer";
import type { RoutingApiResponse, RoutingRecommendation } from "../features/routing/types";

export interface RoutingProps {
  onNavigateTab?: (tabId: string) => void;
}

export default function Routing({ onNavigateTab }: RoutingProps) {
  const { data, isLoading, error, refetch } = useQuery<RoutingApiResponse>({
    queryKey: ["routing-recommendations"],
    queryFn: async () => (await api.routing()) as RoutingApiResponse,
    staleTime: 60 * 1000,
  });

  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showAll, setShowAll] = useState(false);
  const [selectedRec, setSelectedRec] = useState<RoutingRecommendation | null>(null);

  const filteredRecs = useMemo(() => {
    if (!data?.recommendations) return [];
    return data.recommendations.filter((r) => {
      const matchesFilter =
        selectedFilter === "ALL" || r.option === selectedFilter;
      const matchesSearch =
        searchQuery === "" ||
        r.vessel_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.carrier.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.target_port &&
          r.target_port.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesFilter && matchesSearch;
    });
  }, [data, selectedFilter, searchQuery]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Unable to load routing recommendations"
        message={error instanceof Error ? error.message : "Failed to fetch /api/routing"}
        onRetry={() => refetch()}
      />
    );
  }

  const optionColors: Record<string, { bg: string; text: string; border: string }> = {
    DIVERT: {
      bg: "var(--status-critical-bg)",
      text: "var(--status-critical)",
      border: "var(--status-critical-border)",
    },
    SLOW_STEAM: {
      bg: "var(--status-warning-bg)",
      text: "var(--status-warning)",
      border: "var(--status-warning-border)",
    },
    PRIORITY_WINDOW: {
      bg: "var(--brand-soft)",
      text: "var(--text-accent)",
      border: "var(--brand-border)",
    },
    HOLD: {
      bg: "var(--bg-surface-elevated)",
      text: "var(--text-secondary)",
      border: "var(--border-subtle)",
    },
  };

  return (
    <div className="space-y-6">
      {/* Top KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Total Fleet Savings */}
        <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)]">
          <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
            Fleet Potential Savings
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-[var(--status-success)] mt-1 truncate">
            ${Number(data.total_savings_usd).toLocaleString()}
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
            Fuel burn &amp; demurrage
          </div>
        </div>

        {/* Divert */}
        <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)]">
          <div className="text-[10px] uppercase font-bold text-[var(--status-critical)] tracking-wider">
            Divert Candidates
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-[var(--text-primary)] mt-1 truncate">
            {data.counts?.DIVERT || 0}{" "}
            <span className="text-xs font-normal text-[var(--text-secondary)]">vessels</span>
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
            Sustained wait &gt; 48h
          </div>
        </div>

        {/* Slow Steam */}
        <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)]">
          <div className="text-[10px] uppercase font-bold text-[var(--status-warning)] tracking-wider">
            Slow Steam
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-[var(--text-primary)] mt-1 truncate">
            {data.counts?.SLOW_STEAM || 0}{" "}
            <span className="text-xs font-normal text-[var(--text-secondary)]">vessels</span>
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
            18–48h wait reduction
          </div>
        </div>

        {/* Priority Window */}
        <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)]">
          <div className="text-[10px] uppercase font-bold text-[var(--text-accent)] tracking-wider">
            Priority Window
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-[var(--text-primary)] mt-1 truncate">
            {data.counts?.PRIORITY_WINDOW || 0}{" "}
            <span className="text-xs font-normal text-[var(--text-secondary)]">vessels</span>
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
            Reefer cargo &gt; 200 units
          </div>
        </div>

        {/* Hold */}
        <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)]">
          <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
            Schedule Hold
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-[var(--text-primary)] mt-1 truncate">
            {data.counts?.HOLD || 0}{" "}
            <span className="text-xs font-normal text-[var(--text-secondary)]">vessels</span>
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
            Standard anchorage queue
          </div>
        </div>
      </div>

      {/* Cost Model Parameters Banner */}
      <div className="p-3 rounded-lg bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-[var(--brand)] shrink-0" />
          <span className="font-semibold text-[var(--text-primary)]">
            Maritime Routing Economics Model
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-[var(--text-secondary)]">
          <span>Daily Op Cost: ${data.cost_model?.daily_op_cost_usd?.toLocaleString()}/day</span>
          <span>·</span>
          <span>Reefer Container Value: ${data.cost_model?.reefer_value_usd}/unit</span>
          <span>·</span>
          <span>
            Alt Ports: {data.cost_model?.alt_ports?.join(", ") || "Oakland, Seattle, Tacoma"}
          </span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {["ALL", "DIVERT", "SLOW_STEAM", "PRIORITY_WINDOW", "HOLD"].map((f) => {
            const count =
              f === "ALL" ? data.recommendations.length : data.counts?.[f] || 0;
            const isSelected = selectedFilter === f;
            return (
              <button
                key={f}
                type="button"
                onClick={() => setSelectedFilter(f)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-[var(--accent)] text-white dark:text-[#060d19] font-bold shadow-xs"
                    : "bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-default)]"
                }`}
              >
                <span>{f.replace("_", " ")}</span>
                <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-black/15">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search Box */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search vessel, carrier, port..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-md pl-8 pr-3 py-1.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]"
          />
        </div>
      </div>

      {/* Recommendation Cards Grid */}
      {filteredRecs.length === 0 ? (
        <EmptyState
          title="No recommendations match the filter"
          description="Try resetting search keywords or selecting 'ALL' to view all vessels."
          action={
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setSelectedFilter("ALL");
                setSearchQuery("");
              }}
            >
              Reset Filters
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Density pass: highest-priority cards by default, full list one click away. */}
          {(showAll ? filteredRecs : filteredRecs.slice(0, 8)).map((r) => {
            const optStyle = optionColors[r.option] || optionColors.HOLD;

            return (
              <div
                key={r.vessel_id}
                className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] hover:border-[var(--border-elevated)] transition-all flex flex-col justify-between space-y-3"
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Ship className="w-4 h-4 text-[var(--brand)] shrink-0" />
                      <span className="font-bold text-sm text-[var(--text-primary)]">
                        {r.vessel_name}
                      </span>
                      <span className="text-xs text-[var(--text-muted)]">
                        · {r.carrier}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] font-mono mt-0.5">
                      Class: {r.vessel_class} · Destination: {r.dest_zone_code} · Status: {r.status}
                    </div>
                  </div>

                  <span
                    className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border shrink-0"
                    style={{
                      backgroundColor: optStyle.bg,
                      color: optStyle.text,
                      borderColor: optStyle.border,
                    }}
                  >
                    {r.option}
                  </span>
                </div>

                {/* Primary Recommendation Banner */}
                <div className="p-2.5 rounded-md bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                      <Route className="w-3.5 h-3.5 text-[var(--brand)]" />
                      {r.target_port ? `DIVERT TO ${r.target_port.toUpperCase()}` : r.option.replace("_", " ")}
                    </span>
                    {r.sustained && (
                      <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-[var(--status-critical-bg)] text-[var(--status-critical)] border border-[var(--status-critical-border)]">
                        Sustained 48h+
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] line-clamp-2">
                    {r.rationale}
                  </p>
                </div>

                {/* Metrics Strip */}
                <div className="grid grid-cols-3 gap-2 pt-1 border-t border-[var(--border-subtle)] text-xs">
                  <div>
                    <div className="text-[10px] uppercase font-bold text-[var(--text-muted)]">
                      Predicted Wait
                    </div>
                    <div className="font-mono font-semibold text-[var(--text-primary)] mt-0.5">
                      {r.predicted_wait_hours.toFixed(1)}h
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] uppercase font-bold text-[var(--text-muted)]">
                      Est. Savings
                    </div>
                    <div className="font-mono font-semibold text-[var(--status-success)] mt-0.5">
                      {r.est_savings_usd > 0 ? `$${r.est_savings_usd.toLocaleString()}` : "$0"}
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] uppercase font-bold text-[var(--text-muted)]">
                      Confidence
                    </div>
                    <div className="font-mono font-semibold text-[var(--brand)] mt-0.5">
                      {(r.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>

                {/* Action Button */}
                <div className="pt-1 flex items-center justify-end">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedRec(r)}
                    icon={<ArrowRight className="w-3 h-3" />}
                    className="text-xs"
                  >
                    View Recommendation Details
                  </Button>
                </div>
              </div>
            );
          })}
          {!showAll && filteredRecs.length > 8 && (
            <div className="md:col-span-2 flex justify-center">
              <Button variant="outline" size="sm" onClick={() => setShowAll(true)}>
                Show all {filteredRecs.length} recommendations
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Routing Detail Drawer */}
      <RoutingDetailDrawer
        recommendation={selectedRec}
        costModel={data.cost_model}
        open={Boolean(selectedRec)}
        onClose={() => setSelectedRec(null)}
        onSimulateScenario={() => {
          setSelectedRec(null);
          if (onNavigateTab) onNavigateTab("scenarios");
        }}
        onAskBob={(prompt) => {
          setSelectedRec(null);
          if (onNavigateTab) onNavigateTab("bob");
        }}
      />
    </div>
  );
}
