import React from "react";
import {
  GitCompare,
  Play,
  CalendarRange,
  Route,
  Bot,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "../../components/layout/PageHeader";
import { PageContainer } from "../../components/layout/PageContainer";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Button } from "../../components/ui/Button";
import { SkeletonCard, SkeletonChart } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/ErrorState";
import { useScenarios } from "./useScenarios";
import { ScenarioControls } from "./ScenarioControls";
import { ScenarioComparison } from "./ScenarioComparison";
import { ScenarioTimeline } from "./ScenarioTimeline";

export interface ScenarioPageProps {
  onNavigateTab?: (tabId: string) => void;
}

export default function ScenarioPage({ onNavigateTab }: ScenarioPageProps) {
  const {
    params,
    setParams,
    activePresetId,
    applyPreset,
    runCustomScenario,
    data,
    isLoading,
    isInitialLoading,
    error,
    presets,
  } = useScenarios();

  if (isInitialLoading) {
    return (
      <PageContainer>
        <PageHeader
          title="What-If Scenario Simulation & Stress Testing"
          description="Parametric stress-testing against baseline OR-Tools CP-SAT discrete solver."
          breadcrumbs={["Analysis", "Scenarios"]}
          status={<StatusBadge status="SOLVING" label="CP-SAT Solver" size="xs" />}
        />
        <div className="space-y-4">
          <SkeletonCard />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <SkeletonChart height={256} />
        </div>
      </PageContainer>
    );
  }

  if (error && !data) {
    return (
      <PageContainer>
        <PageHeader
          title="What-If Scenario Simulation & Stress Testing"
          description="Parametric stress-testing against baseline OR-Tools CP-SAT discrete solver."
          breadcrumbs={["Analysis", "Scenarios"]}
          status={<StatusBadge status="FAILED" label="Solver Offline" size="xs" />}
        />
        <ErrorState
          title="Unable to execute scenario simulation"
          message={error.message || "Failed to contact /api/scenarios endpoint."}
          onRetry={runCustomScenario}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Page Header */}
      <PageHeader
        title="What-If Scenario Simulation & Stress Testing"
        description="Parametric stress-testing against baseline OR-Tools CP-SAT discrete solver. Simulate quay crane outages and productivity shocks."
        breadcrumbs={["Analysis", "Scenarios"]}
        status={
          <div className="flex items-center gap-1.5">
            <StatusBadge status="FEASIBLE" label="OR-Tools CP-SAT" size="xs" />
            <span className="text-[10px] font-mono text-[var(--text-muted)] bg-[var(--bg-surface-elevated)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)]">
              POST /api/scenarios
            </span>
          </div>
        }
      />

      {/* Main Content Sections */}
      <div className="space-y-6">
        {/* Controls & Parametric Sliders */}
        <ScenarioControls
          params={params}
          onChangeParams={setParams}
          activePresetId={activePresetId}
          onApplyPreset={applyPreset}
          onRunScenario={runCustomScenario}
          isLoading={isLoading}
          presets={presets}
        />

        {/* Real Results & Metric Comparison */}
        {data && <ScenarioComparison data={data} />}

        {/* 72-Hour Timeline Progression */}
        {data && <ScenarioTimeline data={data} />}

        {/* Contextual Workflow Navigation Bar */}
        <div className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-xs font-semibold text-[var(--text-primary)]">
              Next Actions &amp; Operational Flow
            </h3>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Propagate this scenario through the PortFlow decision chain.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onNavigateTab && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onNavigateTab("routing")}
                  icon={<Route className="w-3.5 h-3.5" />}
                  className="text-xs"
                >
                  Inspect Routing Options
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onNavigateTab("plan")}
                  icon={<CalendarRange className="w-3.5 h-3.5" />}
                  className="text-xs"
                >
                  View 72-Hour Plan
                </Button>
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => onNavigateTab("bob")}
                  icon={<Bot className="w-3.5 h-3.5" />}
                  className="text-xs"
                >
                  Ask Bob AI to Explain
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
