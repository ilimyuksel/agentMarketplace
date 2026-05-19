"use client";

import { Suspense, useEffect, useMemo } from "react";
import { useAppStore } from "@/lib/store";
import { TopBar } from "@/components/terminal/TopBar";
import { AgentRosterStrip } from "@/components/terminal/AgentRosterStrip";
import { EventTicker } from "@/components/terminal/EventTicker";
import { AppNav } from "@/components/layout/AppNav";
import { AgentsHeader } from "@/components/agents/AgentsHeader";
import {
  AgentFilterTabs,
  useAgentFilter,
  type AgentFilter,
} from "@/components/agents/AgentFilterTabs";
import { AgentDetailCard } from "@/components/agents/AgentDetailCard";
import { ROSTER_ORDER } from "@/lib/personas";
import type { Agent } from "@/types";

function matchesFilter(agent: Agent, filter: AgentFilter): boolean {
  if (filter === "ALL") return true;
  if (filter === "MANAGERS") return agent.tier === "T1" && !agent.isGhost;
  if (filter === "WORKERS") return agent.tier === "T2" && !agent.isGhost;
  if (filter === "JUDGES") return agent.tier === "JUDGE";
  if (filter === "GHOSTS") return agent.isGhost;
  return true;
}

function GhostDivider() {
  return (
    <div className="col-span-full flex items-center gap-3 pt-2 pb-1">
      <div className="flex-1 border-t border-dashed border-ghost/40" />
      <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-ghost">
        Ghost section · marketplace depth · cannot win
      </span>
      <div className="flex-1 border-t border-dashed border-ghost/40" />
    </div>
  );
}

function AgentsGrid() {
  const filter = useAgentFilter();
  const agents = useAppStore((s) => s.agents);
  const agentDetails = useAppStore((s) => s.agentDetails);
  const wallets = useAppStore((s) => s.wallets);

  const byId = useMemo(() => new Map(agents.map((a) => [a.id, a])), [agents]);
  const walletById = useMemo(() => new Map(wallets.map((w) => [w.id, w])), [wallets]);

  // Canonical roster order — primary first, ghosts last.
  const primary = ROSTER_ORDER
    .map((id) => byId.get(id))
    .filter((a): a is Agent => !!a && !a.isGhost)
    .filter((a) => matchesFilter(a, filter));
  const ghosts = ROSTER_ORDER
    .map((id) => byId.get(id))
    .filter((a): a is Agent => !!a && a.isGhost)
    .filter((a) => matchesFilter(a, filter));

  if (agents.length === 0) {
    return (
      <div className="px-8 py-12 text-center">
        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-text-faint">
          waiting for backend
        </p>
        <p className="text-xs text-text-muted mt-2">
          Agents hydrate from <span className="font-mono">GET /api/v1/agents</span> on backend connect.
        </p>
      </div>
    );
  }

  return (
    <div className="px-8 py-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {primary.map((a) => (
          <AgentDetailCard
            key={a.id}
            agent={a}
            detail={agentDetails[a.id]}
            wallet={walletById.get(a.walletId)}
          />
        ))}
        {ghosts.length > 0 && primary.length > 0 && <GhostDivider />}
        {ghosts.map((a) => (
          <AgentDetailCard
            key={a.id}
            agent={a}
            detail={agentDetails[a.id]}
            wallet={walletById.get(a.walletId)}
          />
        ))}
      </div>
    </div>
  );
}

function AgentsPageInner() {
  const checkBackend = useAppStore((s) => s.checkBackend);
  const openGlobalWs = useAppStore((s) => s.openGlobalWs);
  const closeGlobalWs = useAppStore((s) => s.closeGlobalWs);
  const fetchAgentDetails = useAppStore((s) => s.fetchAgentDetails);
  const agents = useAppStore((s) => s.agents);
  const backendOnline = useAppStore((s) => s.backendOnline);

  useEffect(() => {
    checkBackend();
    openGlobalWs();
    return () => closeGlobalWs();
  }, [checkBackend, openGlobalWs, closeGlobalWs]);

  // Once the agent list is hydrated, batch-fetch each detail in parallel.
  useEffect(() => {
    if (backendOnline && agents.length > 0) {
      void fetchAgentDetails();
    }
  }, [backendOnline, agents.length, fetchAgentDetails]);

  return (
    <div className="h-screen bg-deep text-text-primary flex flex-col overflow-hidden">
      <TopBar />
      <AppNav />
      <AgentRosterStrip />
      <main className="content-light flex-1 overflow-y-auto min-h-0">
        <AgentsHeader />
        <AgentFilterTabs />
        <AgentsGrid />
      </main>
      <EventTicker />
    </div>
  );
}

// `useSearchParams` (used by AgentFilterTabs) requires a Suspense boundary
// at build time in Next.js App Router.
export default function AgentsPage() {
  return (
    <Suspense fallback={null}>
      <AgentsPageInner />
    </Suspense>
  );
}
