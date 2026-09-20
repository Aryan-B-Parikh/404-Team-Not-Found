/**
 * Data Quality & Ingestion page — live data from /api/quality, /api/weather, /api/vessels/upload, /api/ais
 * Replaces QualityPlaceholder with real API-backed content.
 */
import React, { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Database,
  FileCheck,
  ShieldCheck,
  Upload,
  CloudSun,
  Wind,
  Waves,
  Eye,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Radio,
} from "lucide-react";
import { api } from "../lib/api";
import { PageContainer } from "../components/layout/PageContainer";
import { PageHeader } from "../components/layout/PageHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/ui/StatusBadge";
import { SkeletonCard } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/ErrorState";
import type { z } from "zod";
import { QualitySchema, WeatherSchema } from "../lib/contract";
type QualityT = z.output<typeof QualitySchema>;
type WeatherT = z.output<typeof WeatherSchema>;

function CompletionBar({ pct }: { pct: number | null }) {
  const safe = pct ?? 0;
  const color = safe >= 90 ? "var(--status-success)" : safe >= 60 ? "var(--status-warning)" : "var(--status-critical)";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-[var(--bg-surface-elevated)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${safe}%`, background: color }}
        />
      </div>
      <span className="font-mono text-xs font-semibold" style={{ color }}>{safe.toFixed(1)}%</span>
    </div>
  );
}

function WeatherCard({ points }: { points: WeatherT["points"] }) {
  if (!points || points.length === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] py-4">
        <AlertTriangle className="w-4 h-4 text-[var(--status-warning)]" />
        No weather data yet — click Refresh Weather to fetch from Open-Meteo.
      </div>
    );
  }
  const now = points.find((p) => p.hour === 0) ?? points[0];
  const maxWind = Math.max(...points.map((p) => p.wind_kn ?? 0));
  const maxWave = Math.max(...points.map((p) => p.wave_m ?? 0));
  const minVis = Math.min(...points.filter((p) => p.visibility_km != null).map((p) => p.visibility_km!));

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          { icon: <Wind className="w-3.5 h-3.5" />, label: "Wind now", value: now?.wind_kn != null ? `${now.wind_kn.toFixed(1)} kn` : "—", sub: `peak ${maxWind.toFixed(1)} kn` },
          { icon: <Wind className="w-3.5 h-3.5" />, label: "Gusts now", value: now?.gust_kn != null ? `${now.gust_kn.toFixed(1)} kn` : "—", sub: "10m gust" },
          { icon: <Waves className="w-3.5 h-3.5" />, label: "Wave ht", value: now?.wave_m != null ? `${now.wave_m.toFixed(2)} m` : "—", sub: `peak ${maxWave.toFixed(2)} m` },
          { icon: <Eye className="w-3.5 h-3.5" />, label: "Visibility", value: now?.visibility_km != null ? `${now.visibility_km.toFixed(1)} km` : "—", sub: `min ${minVis.toFixed(1)} km` },
        ].map((m) => (
          <div key={m.label} className="p-2.5 rounded-md bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)]">
            <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase text-[var(--text-muted)] tracking-wider mb-1">
              <span className="text-[var(--brand)]">{m.icon}</span>
              {m.label}
            </div>
            <div className="font-mono font-semibold text-base text-[var(--text-primary)]">{m.value}</div>
            <div className="text-[10px] text-[var(--text-muted)]">{m.sub}</div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-xs">
          <thead>
            <tr className="text-[var(--text-muted)] text-[10px] uppercase">
              <th className="text-left py-1 pr-2">Ahead</th>
              <th className="text-right pr-2">Wind (kn)</th>
              <th className="text-right pr-2">Gust (kn)</th>
              <th className="text-right pr-2">Wave (m)</th>
              <th className="text-right">Vis (km)</th>
            </tr>
          </thead>
          <tbody>
            {points.slice(0, 24).map((p) => (
              <tr key={p.hour} className="border-t border-[var(--border-subtle)]">
                <td className="py-0.5 pr-2 font-mono text-[var(--text-muted)]">{p.hour === 0 ? "now" : `+${Math.abs(p.hour)}h`}</td>
                <td className="text-right pr-2 font-mono">{p.wind_kn?.toFixed(1) ?? "—"}</td>
                <td className="text-right pr-2 font-mono">{p.gust_kn?.toFixed(1) ?? "—"}</td>
                <td className="text-right pr-2 font-mono">{p.wave_m?.toFixed(2) ?? "—"}</td>
                <td className="text-right font-mono">{p.visibility_km?.toFixed(1) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface UploadResult {
  accepted: number;
  rejected: number;
  errors: string[];
  revisions_created: number;
  upload_id: number;
  filename: string;
  bytes: number;
}

export default function QualityPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [weatherRefreshing, setWeatherRefreshing] = useState(false);
  const [aisResult, setAisResult] = useState<any>(null);

  const { data: quality, isLoading: qLoading, error: qError, refetch: qRefetch } =
    useQuery({
      queryKey: ["quality"],
      queryFn: (): Promise<QualityT> => api.quality(),
      staleTime: 60_000,
    });

  const { data: weather, isLoading: wLoading, refetch: wRefetch } =
    useQuery({
      queryKey: ["weather"],
      queryFn: (): Promise<WeatherT> => api.weather(72),
      staleTime: 300_000,
    });

  const { data: aisStatus, refetch: aisRefetch } = useQuery({
    queryKey: ["ais-status"],
    queryFn: () => api.aisStatus(),
    staleTime: 60_000,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadSchedule(file),
    onSuccess: (data) => {
      setUploadResult(data as unknown as UploadResult);
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["quality"] });
    },
  });

  const aisMutation = useMutation({
    mutationFn: ({ days, seed }: { days: number; seed: number }) => api.aisGenerate(days, seed),
    onSuccess: (data) => {
      setAisResult(data);
      qc.invalidateQueries({ queryKey: ["ais-status"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadResult(null);
    uploadMutation.mutate(file);
    e.target.value = "";
  };

  const handleWeatherRefresh = async () => {
    setWeatherRefreshing(true);
    try {
      await api.weatherRefresh();
      await wRefetch();
    } finally {
      setWeatherRefreshing(false);
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title="Data Quality & Ingestion"
        description="Terminal completeness scores, vessel schedule uploads, weather ingestion, and normalisation audit."
        breadcrumbs={["Analysis", "Data Quality"]}
        status={<StatusBadge status="OPERATIONAL" size="xs" />}
      />

      {/* ── Completeness audit ── */}
      <Card className="mb-4">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[var(--status-success)]" />
              <CardTitle>Terminal Data Completeness</CardTitle>
            </div>
            <Button size="sm" variant="ghost" onClick={() => qRefetch()} icon={<RefreshCw className="w-3 h-3" />}>
              Refresh
            </Button>
          </div>
          <CardDescription>
            Completeness = share of vessel calls with IMO + voyage_number populated. Sourced from live DB.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {qLoading ? (
            <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
              {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
            </div>
          ) : qError || !quality ? (
            <ErrorState
              title="Could not load quality data"
              message="Check the FastAPI server is running and /api/quality is reachable."
              onRetry={() => qRefetch()}
            />
          ) : (
            <>
              <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
                {quality.terminals.map((t) => (
                  <div key={t.code} className="p-3 rounded-lg bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-sm">{t.code}</span>
                      <Badge variant={(t.completeness_pct ?? 0) >= 90 ? "success" : (t.completeness_pct ?? 0) >= 60 ? "warning" : "critical"}>
                        {(t.completeness_pct ?? 0) >= 90 ? "Good" : (t.completeness_pct ?? 0) >= 60 ? "Partial" : "Low"}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)] mb-2 truncate">{t.name}</div>
                    <CompletionBar pct={t.completeness_pct} />
                    {t.missing.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {t.missing.map((m) => (
                          <span key={m} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-[var(--status-critical-bg)] text-[var(--status-critical)] border border-[var(--status-critical-border)]">
                            {m}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div className="text-xs text-[var(--text-muted)] font-mono">
                Rules version: {quality.rules_version} · {quality.terminals.length} terminals audited
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Weather ── */}
      <Card className="mb-4">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <CloudSun className="w-4 h-4 text-[var(--brand)]" />
              <CardTitle>San Pedro Bay Weather (Open-Meteo)</CardTitle>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleWeatherRefresh}
              disabled={weatherRefreshing}
              icon={<RefreshCw className={`w-3 h-3 ${weatherRefreshing ? "animate-spin" : ""}`} />}
            >
              {weatherRefreshing ? "Fetching…" : "Refresh Weather"}
            </Button>
          </div>
          <CardDescription>
            72-hour wind / gust / wave / visibility forecast from Open-Meteo (no API key). Used as exogenous signal
            in LightGBM congestion forecasts when FEATURE_WEATHER=true.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {wLoading ? (
            <SkeletonCard />
          ) : (
            <WeatherCard points={weather?.points ?? []} />
          )}
        </CardContent>
      </Card>

      {/* ── AIS history management ── */}
      <Card className="mb-4">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Radio className="w-4 h-4 text-[var(--brand)]" />
              <CardTitle>AIS Congestion History</CardTitle>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => aisMutation.mutate({ days: 14, seed: Date.now() % 100000 })}
              disabled={aisMutation.isPending}
              icon={<RefreshCw className={`w-3 h-3 ${aisMutation.isPending ? "animate-spin" : ""}`} />}
            >
              {aisMutation.isPending ? "Generating AIS…" : "Regenerate AIS (14d)"}
            </Button>
          </div>
          <CardDescription>
            Realistic San Pedro Bay AIS position records — NOAA AccessAIS format — processed through
            the congestion-series pipeline. Replaces DEMO_AIS with <code className="font-mono text-[10px] px-1 py-0.5 rounded bg-[var(--bg-surface-elevated)]">source=AIS</code> data.
            All downstream engines (forecast · anomaly · hotspot) pick up the new history immediately.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* Current status */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { label: "Source", value: aisStatus?.source ?? "—" },
                { label: "Observations", value: aisStatus?.rows != null ? Number(aisStatus.rows).toLocaleString() : "—" },
                { label: "Zones", value: aisStatus?.zones ?? "—" },
                { label: "Newest", value: aisStatus?.newest_ts ? new Date(aisStatus.newest_ts).toLocaleString() : "—" },
              ].map(({ label, value }) => (
                <div key={label} className="p-2.5 rounded-md bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)]">
                  <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">{label}</div>
                  <div className="font-mono text-sm font-semibold mt-0.5"
                    style={{ color: label === "Source" && value === "AIS" ? "var(--status-success)" : label === "Source" && value === "DEMO_AIS" ? "var(--status-warning)" : "var(--text-primary)" }}>
                    {String(value)}
                  </div>
                </div>
              ))}
            </div>

            {aisMutation.isError && (
              <div className="p-3 rounded-lg border border-[var(--status-critical)] bg-[var(--status-critical-bg)] text-xs text-[var(--status-critical)]">
                AIS generation failed: {String((aisMutation.error as Error)?.message ?? aisMutation.error)}
              </div>
            )}
            {aisResult && (
              <div className="p-3 rounded-lg border border-[var(--status-success)] bg-[var(--bg-surface-elevated)] text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-semibold text-[var(--status-success)]">
                  <CheckCircle2 className="w-4 h-4" />
                  AIS history replaced
                </div>
                <div className="font-mono text-[var(--text-muted)]">
                  {aisResult.inserted} observations · {aisResult.zones} zones · {aisResult.vessels} vessels scanned
                </div>
              </div>
            )}

            <p className="text-xs text-[var(--text-muted)]">
              To use a real NOAA AccessAIS export instead, run in the backend shell:<br />
              <code className="font-mono text-[10px] bg-[var(--bg-surface-elevated)] px-1.5 py-0.5 rounded">
                python -m app.pipelines.ais build your_export.csv series.csv &amp;&amp; python -m app.pipelines.ais import series.csv
              </code>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ── Schedule upload ── */}
      <Card className="mb-4">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-[var(--brand)]" />
            <CardTitle>Vessel Schedule Upload (CSV)</CardTitle>
          </div>
          <CardDescription>
            Upload a CSV with columns: <code className="font-mono text-[10px] px-1 py-0.5 rounded bg-[var(--bg-surface-elevated)]">imo, voyage_number, declared_eta_hours</code> plus optional vessel attributes.
            Creates VesselCall rows with ETA revision history.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* Drop zone */}
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-[var(--border-default)] hover:border-[var(--brand)] rounded-lg p-6 text-center cursor-pointer transition-colors group"
            >
              <FileText className="w-8 h-8 mx-auto mb-2 text-[var(--text-muted)] group-hover:text-[var(--brand)] transition-colors" />
              <p className="text-sm font-medium text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors">
                {uploadMutation.isPending ? "Uploading…" : "Click to upload vessel schedule CSV"}
              </p>
              <p className="text-xs text-[var(--text-muted)] mt-1">Required: imo, voyage_number, declared_eta_hours</p>
              <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
            </div>

            {/* Result */}
            {uploadMutation.isError && (
              <div className="p-3 rounded-lg border border-[var(--status-critical)] bg-[var(--status-critical-bg)] text-xs text-[var(--status-critical)]">
                Upload failed: {String((uploadMutation.error as Error)?.message ?? uploadMutation.error)}
              </div>
            )}
            {uploadMutation.isPending && (
              <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Processing schedule…
              </div>
            )}
            {uploadResult && (
              <div className="p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] space-y-2">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="flex items-center gap-1.5 text-sm font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-[var(--status-success)]" />
                    {uploadResult.accepted} accepted
                  </span>
                  {uploadResult.rejected > 0 && (
                    <span className="flex items-center gap-1.5 text-sm text-[var(--status-critical)]">
                      <XCircle className="w-4 h-4" />
                      {uploadResult.rejected} rejected
                    </span>
                  )}
                  <span className="text-xs text-[var(--text-muted)] font-mono">
                    {uploadResult.revisions_created} ETA revisions · upload #{uploadResult.upload_id}
                  </span>
                </div>
                <div className="text-xs text-[var(--text-muted)] font-mono truncate">
                  {uploadResult.filename} · {(uploadResult.bytes / 1024).toFixed(1)} KB
                </div>
                {uploadResult.errors.length > 0 && (
                  <ul className="space-y-0.5 max-h-24 overflow-y-auto">
                    {uploadResult.errors.map((e, i) => (
                      <li key={i} className="text-[10px] font-mono text-[var(--status-critical)]">
                        {e}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Sample template download */}
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
              <FileCheck className="w-3.5 h-3.5 shrink-0" />
              Sample CSV template columns: imo, voyage_number, declared_eta_hours, name, carrier, vessel_class, loa_ft, beam_ft, draft_ft, teu_capacity, import_moves, export_moves, origin_port, reefer_units, dest_zone_code
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Normalisation audit ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-[var(--status-info)]" />
            <CardTitle>Normalisation Audit</CardTitle>
          </div>
          <CardDescription>
            SI unit conversion ledger — ft → m for LOA, beam, draft. Stored in VesselCall.normalised JSONB.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[360px] text-xs">
              <thead>
                <tr className="text-[10px] uppercase text-[var(--text-muted)]">
                  <th className="text-left py-1 pr-3">Field</th>
                  <th className="text-left pr-3">Raw unit</th>
                  <th className="text-left pr-3">SI unit</th>
                  <th className="text-left">Factor</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { field: "loa_ft", raw: "ft", si: "m", factor: "× 0.3048" },
                  { field: "beam_ft", raw: "ft", si: "m", factor: "× 0.3048" },
                  { field: "draft_ft", raw: "ft", si: "m", factor: "× 0.3048" },
                  { field: "wind_kn", raw: "knots", si: "m/s", factor: "÷ 1.9438" },
                  { field: "wave_m", raw: "m", si: "m", factor: "× 1.000" },
                  { field: "visibility_km", raw: "km", si: "km", factor: "× 1.000" },
                ].map((r) => (
                  <tr key={r.field} className="border-t border-[var(--border-subtle)]">
                    <td className="py-1 pr-3 font-mono">{r.field}</td>
                    <td className="pr-3 text-[var(--text-muted)]">{r.raw}</td>
                    <td className="pr-3 text-[var(--status-success)] font-mono">{r.si}</td>
                    <td className="font-mono text-[var(--text-secondary)]">{r.factor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-3">
            Normalisation runs on every new VesselCall row at ingestion time. Raw values are preserved in the
            <code className="font-mono text-[10px] px-1 py-0.5 rounded bg-[var(--bg-surface-elevated)]"> raw</code> and
            <code className="font-mono text-[10px] px-1 py-0.5 rounded bg-[var(--bg-surface-elevated)]"> normalised</code> JSONB columns.
          </p>
        </CardContent>
      </Card>
    </PageContainer>
  );
}
