import React, { useState } from "react";
import {
  Anchor,
  Ship,
  Clock,
  TrendingUp,
  AlertTriangle,
  ChevronRight,
} from "lucide-react";
import { Drawer } from "../../components/ui/Drawer";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../../components/ui/Table";
import { Tabs, TabsList, TabTrigger, TabContent } from "../../components/ui/Tabs";
import { Button } from "../../components/ui/Button";
import { Sparkline } from "../../components/ui/legacy";
import { formatNumber, formatHours, formatPercent, formatTeu } from "../../lib/formatters";
import type { EnrichedTerminal, VesselItem } from "./types";

export interface TerminalDetailDrawerProps {
  terminal: EnrichedTerminal | null;
  open: boolean;
  onClose: () => void;
  vessels: VesselItem[];
}

export function TerminalDetailDrawer({
  terminal,
  open,
  onClose,
  vessels,
}: TerminalDetailDrawerProps) {
  const [activeSubTab, setActiveSubTab] = useState<string>("overview");
  const [selectedBerthName, setSelectedBerthName] = useState<string | null>(null);

  if (!terminal) return null;

  const berths = terminal.berths || [];

  return (
    <Drawer
      open={open}
      onOpenChange={(isOpen) => !isOpen && onClose()}
      width="lg"
      title={
        <div className="flex items-center gap-2">
          <span>{terminal.name}</span>
          <StatusBadge status={terminal.level} size="xs" />
        </div>
      }
      description={
        <nav className="flex items-center gap-1 text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
          <span>San Pedro Bay</span>
          <ChevronRight className="w-3 h-3 text-[var(--border-elevated)]" />
          <span className="text-[var(--text-secondary)] font-semibold">{terminal.code} ({terminal.pier})</span>
          {selectedBerthName && (
            <>
              <ChevronRight className="w-3 h-3 text-[var(--border-elevated)]" />
              <span className="text-[var(--text-accent)]">{selectedBerthName}</span>
            </>
          )}
        </nav>
      }
      footer={
        <div className="flex items-center justify-between w-full text-xs text-[var(--text-muted)]">
          <span className="font-mono">Zone: {terminal.zone_code}</span>
          <Button size="sm" variant="outline" onClick={onClose}>
            Close Inspector
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {/* KPI Summary Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
              Congestion Index
            </div>
            <div className="text-xl font-bold text-[var(--brand)] font-mono mt-1">
              {terminal.current_index.toFixed(1)}
            </div>
            <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">
              Peak: <span className="font-semibold text-[var(--status-warning)]">{terminal.peak_index.toFixed(1)}</span> @ +{terminal.peak_hour}h
            </div>
          </div>

          <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
              Vessel Queue
            </div>
            <div className="text-xl font-bold text-[var(--text-primary)] font-mono mt-1">
              {terminal.queue_now}
            </div>
            <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">
              Wait: <span className="font-semibold text-[var(--text-primary)]">{formatHours(terminal.wait_now)}</span>
            </div>
          </div>

          <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
              Berths & Cranes
            </div>
            <div className="text-xl font-bold text-[var(--text-primary)] font-mono mt-1">
              {terminal.deepsea_berths} / {terminal.gantry_cranes}
            </div>
            <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">
              Total {formatNumber(terminal.berth_length_ft)} ft
            </div>
          </div>

          <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)]">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
              Yard Util
            </div>
            <div className="text-xl font-bold text-[var(--text-primary)] font-mono mt-1">
              {formatPercent(terminal.yard_util_pct)}
            </div>
            <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 truncate">
              {terminal.capacity_teu_m ? `${terminal.capacity_teu_m}M TEU cap` : "POLB standard"}
            </div>
          </div>
        </div>

        {/* Binding Bottleneck Alert if Hotspot Flagged */}
        {terminal.binding_constraint && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-[var(--brand-soft)] border border-[var(--brand-border)] text-xs">
            <TrendingUp className="w-4 h-4 text-[var(--brand)] shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-[var(--text-primary)]">
                Binding Operational Constraint: {terminal.binding_constraint}
              </span>
              <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Composite risk score: <strong className="text-[var(--brand)]">{terminal.risk_score}/100</strong> (Confidence: {terminal.confidence}). The terminal schedule is bound by {terminal.binding_constraint.toLowerCase()} availability.
              </p>
            </div>
          </div>
        )}

        {/* Isolation Forest Anomaly Warning */}
        {terminal.has_anomaly && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-[var(--status-critical-bg)] border border-[var(--status-critical-border)] text-xs">
            <AlertTriangle className="w-4 h-4 text-[var(--status-critical)] shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-[var(--status-critical)]">
                Telemetry Anomaly Detected ({terminal.anomaly_kind || "Bunching"})
              </span>
              <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Isolation Forest flagged abnormal vessel inter-arrival rates or dwell time deviations in zone {terminal.zone_code}.
              </p>
            </div>
          </div>
        )}

        {/* Sub Navigation Tabs */}
        <Tabs value={activeSubTab} onValueChange={setActiveSubTab}>
          <TabsList className="w-full grid grid-cols-3">
            <TabTrigger value="overview">Overview</TabTrigger>
            <TabTrigger value="berths" badge={berths.length}>
              Berths ({berths.length})
            </TabTrigger>
            <TabTrigger value="vessels" badge={vessels.length}>
              Queue ({vessels.length})
            </TabTrigger>
          </TabsList>

          {/* SubTab 1: Overview & Forecast Sparkline */}
          <TabContent value="overview">
            <div className="space-y-4 pt-1">
              <Card>
                <CardHeader>
                  <CardTitle>14-Day Congestion Trend</CardTitle>
                  <span className="text-xs font-mono text-[var(--brand)]">
                    Now: {terminal.current_index.toFixed(1)}
                  </span>
                </CardHeader>
                <CardContent>
                  <div className="h-16 flex items-center justify-between">
                    <Sparkline data={terminal.recent_index || []} />
                    <div className="text-right text-xs">
                      <div className="text-[var(--text-muted)] text-[10px]">72h Outlook</div>
                      <div className="font-bold text-[var(--status-warning)]">
                        Peak {terminal.peak_index.toFixed(1)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Physical Specifications (POLB Fact Sheet)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-[var(--text-muted)]">Quay Length:</span>
                      <p className="font-mono font-medium text-[var(--text-primary)]">
                        {formatNumber(terminal.berth_length_ft)} ft
                      </p>
                    </div>
                    <div>
                      <span className="text-[var(--text-muted)]">Gantry STS Cranes:</span>
                      <p className="font-mono font-medium text-[var(--text-primary)]">
                        {terminal.gantry_cranes} units
                      </p>
                    </div>
                    <div>
                      <span className="text-[var(--text-muted)]">Deepsea Berths:</span>
                      <p className="font-mono font-medium text-[var(--text-primary)]">
                        {terminal.deepsea_berths} dedicated berths
                      </p>
                    </div>
                    <div>
                      <span className="text-[var(--text-muted)]">Terminal Note:</span>
                      <p className="text-[11px] text-[var(--text-secondary)]">
                        {terminal.note || "Continuous quay line"}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabContent>

          {/* SubTab 2: Berths Table */}
          <TabContent value="berths">
            <div className="space-y-3 pt-1">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Berth</TableHead>
                    <TableHead>Length</TableHead>
                    <TableHead>Alongside Depth</TableHead>
                    <TableHead>Max Cranes</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {berths.map((b) => (
                    <TableRow
                      key={b.name}
                      className={selectedBerthName === b.name ? "bg-[var(--bg-surface-active)]" : ""}
                    >
                      <TableCell className="font-mono font-bold text-[var(--text-primary)]">
                        {b.name}
                      </TableCell>
                      <TableCell className="font-mono">{formatNumber(b.length_ft)} ft</TableCell>
                      <TableCell className="font-mono">{b.depth_ft} ft</TableCell>
                      <TableCell className="font-mono">{b.cranes_max} STS</TableCell>
                      <TableCell>
                        <button
                          onClick={() => setSelectedBerthName(selectedBerthName === b.name ? null : b.name)}
                          className="text-[11px] text-[var(--brand)] hover:underline font-medium"
                        >
                          {selectedBerthName === b.name ? "Deselect" : "Inspect"}
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!berths.length && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-[var(--text-muted)] py-4">
                        No individual berth records exposed for this terminal.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </TabContent>

          {/* SubTab 3: Vessel Queue */}
          <TabContent value="vessels">
            <div className="space-y-3 pt-1">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Vessel</TableHead>
                    <TableHead>Carrier / Class</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Wait Time</TableHead>
                    <TableHead>Capacity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {vessels.map((v) => (
                    <TableRow key={v.id}>
                      <TableCell className="font-medium text-[var(--text-primary)]">
                        <div className="flex items-center gap-1.5">
                          <Ship className="w-3.5 h-3.5 text-[var(--brand)] shrink-0" />
                          <span>{v.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-[11px] text-[var(--text-primary)]">{v.carrier}</div>
                        <div className="text-[10px] text-[var(--text-muted)]">{v.vessel_class}</div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={v.status} size="xs" />
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {v.anchored_hours ? formatHours(v.anchored_hours) : "In transit"}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatTeu(v.teu_capacity)}
                      </TableCell>
                    </TableRow>
                  ))}
                  {!vessels.length && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-[var(--text-muted)] py-6">
                        <div className="flex flex-col items-center gap-1">
                          <Anchor className="w-5 h-5 text-[var(--text-muted)]" />
                          <span>No vessels currently bound or queued for {terminal.code}.</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </TabContent>
        </Tabs>
      </div>
    </Drawer>
  );
}
