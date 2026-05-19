"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useAppStore } from "@/lib/store";

export type AgentFilter = "ALL" | "MANAGERS" | "WORKERS" | "JUDGES" | "GHOSTS";

const TABS: AgentFilter[] = ["ALL", "MANAGERS", "WORKERS", "JUDGES", "GHOSTS"];

export function useAgentFilter(): AgentFilter {
  const sp = useSearchParams();
  const raw = sp.get("filter")?.toUpperCase() ?? "ALL";
  return (TABS as string[]).includes(raw) ? (raw as AgentFilter) : "ALL";
}

export function AgentFilterTabs() {
  const router = useRouter();
  const sp = useSearchParams();
  const active = useAgentFilter();
  const agents = useAppStore((s) => s.agents);

  const counts: Record<AgentFilter, number> = {
    ALL: agents.length,
    MANAGERS: agents.filter((a) => a.tier === "T1").length,
    WORKERS: agents.filter((a) => a.tier === "T2" && !a.isGhost).length,
    JUDGES: agents.filter((a) => a.tier === "JUDGE").length,
    GHOSTS: agents.filter((a) => a.isGhost).length,
  };

  const setFilter = (f: AgentFilter) => {
    const params = new URLSearchParams(sp.toString());
    if (f === "ALL") params.delete("filter");
    else params.set("filter", f.toLowerCase());
    const q = params.toString();
    router.replace(`/agents${q ? `?${q}` : ""}`, { scroll: false });
  };

  return (
    <div className="flex items-center gap-1 px-8 py-3 border-b border-line bg-deep">
      {TABS.map((t) => {
        const isActive = active === t;
        return (
          <button
            key={t}
            type="button"
            onClick={() => setFilter(t)}
            className={`px-3 h-7 rounded text-[10px] font-mono uppercase tracking-[0.16em] transition-colors flex items-center gap-1.5 ${
              isActive
                ? "bg-active/15 border border-active/40 text-active"
                : "border border-line text-text-muted hover:text-text-primary hover:border-line"
            }`}
          >
            {t}
            <span className={isActive ? "text-active/70" : "text-text-faint"}>
              {counts[t]}
            </span>
          </button>
        );
      })}
    </div>
  );
}
