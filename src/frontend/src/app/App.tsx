import { useEffect, useState, Suspense } from "react";
import { AppShell } from "../components/layout/AppShell";
import { TABS_REGISTRY } from "./routes";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

// B-3 deep linking: the tab lives in the URL path (/forecast, /berth, …). Vite serves
// the SPA fallback in dev; FastAPI serves index.html for unknown paths in production.
function tabFromPath(): string {
  const seg = window.location.pathname.replace(/^\/+|\/+$/g, "");
  return seg && TABS_REGISTRY[seg] ? seg : "overview";
}

function pathForTab(tabId: string): string {
  return tabId === "overview" ? "/" : `/${tabId}`;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<string>(tabFromPath);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const queryClient = useQueryClient();

  // Browser back/forward restores the tab (B-3).
  useEffect(() => {
    const onPop = () => setActiveTab(tabFromPath());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = (tabId: string) => {
    setActiveTab(tabId);
    const path = pathForTab(tabId);
    if (window.location.pathname !== path) {
      window.history.pushState({ tab: tabId }, "", path);
    }
  };

  const currentTabConfig = TABS_REGISTRY[activeTab] || TABS_REGISTRY.overview;
  const CurrentPageComponent = currentTabConfig.Component;

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await queryClient.invalidateQueries();
      toast.success("Telemetry updated", {
        description: "Successfully refreshed live port observations and engine state.",
      });
    } catch {
      toast.error("Telemetry refresh failed", {
        description: "Could not reach the FastAPI gateway. Check database and server status.",
      });
    } finally {
      setTimeout(() => setRefreshing(false), 600);
    }
  };

  return (
    <AppShell
      activeTab={activeTab}
      onSelectTab={navigate}
      activeTitle={currentTabConfig.title}
      activeSubtitle={currentTabConfig.subtitle}
      onRefresh={handleRefresh}
      refreshing={refreshing}
    >
      <Suspense
        fallback={
          <div className="flex items-center justify-center p-16 text-xs font-mono text-[var(--text-muted)] animate-pulse">
            Synchronizing engine state...
          </div>
        }
      >
        <CurrentPageComponent onNavigateTab={(tabId: string) => navigate(tabId)} />
      </Suspense>
    </AppShell>
  );
}
