import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

export function ErrorState({
  title = "Telemetry Error",
  message,
  onRetry,
  className,
  compact = false,
}: ErrorStateProps) {
  if (compact) {
    return (
      <div
        className={cn(
          "flex items-center justify-between p-3 rounded-md bg-[var(--status-critical-bg)] border border-[var(--status-critical-border)] text-xs text-[var(--status-critical)]",
          className
        )}
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{message}</span>
        </div>
        {onRetry && (
          <Button size="xs" variant="destructive" onClick={onRetry} icon={<RefreshCw className="w-3 h-3" />}>
            Retry
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center border border-[var(--status-critical-border)] rounded-lg bg-[var(--status-critical-bg)]/30",
        className
      )}
    >
      <div className="w-10 h-10 rounded-full bg-[var(--status-critical-bg)] border border-[var(--status-critical-border)] flex items-center justify-center text-[var(--status-critical)] mb-3">
        <AlertTriangle className="w-5 h-5" />
      </div>
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">{title}</h3>
      <p className="text-xs text-[var(--text-secondary)] max-w-md mb-4 font-mono bg-[var(--bg-app)]/80 p-2 rounded border border-[var(--border-subtle)] break-all">
        {message}
      </p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} icon={<RefreshCw className="w-3.5 h-3.5" />}>
          Retry Connection
        </Button>
      )}
    </div>
  );
}
