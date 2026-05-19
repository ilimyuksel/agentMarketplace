"use client";

import { useState } from "react";
import Link from "next/link";
import { Skull } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { PERSONAS, ROSTER_ORDER } from "@/lib/personas";
import { ReputationGauge } from "@/components/primitives/ReputationGauge";
import type { Agent } from "@/types";

function AgentChip({ agent, isActive }: { agent: Agent; isActive: boolean }) {
  const persona = PERSONAS[agent.id];
  const [hovered, setHovered] = useState(false);
  const isGhost = agent.isGhost;

  const tierLabel =
    agent.tier === "T1" ? "T1 Manager"
    : agent.tier === "JUDGE" ? "Judge"
    : "T2 Worker";

  const borderCls = isGhost
    ? "border-ghost/40 opacity-60"
    : isActive
    ? "border-active bg-active/5"
    : "border-line hover:border-active/40";

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <Link
        href={`/agents#${agent.id.toLowerCase()}`}
        aria-label={`${agent.id} · open dossier`}
        className={`flex items-center gap-2.5 h-14 px-3 rounded-md border bg-surface min-w-[200px] transition-colors ${borderCls} cursor-pointer`}
      >
        <ReputationGauge value={agent.reputation} size={42} label={false} />
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-1.5">
            {isGhost && <Skull className="w-3 h-3 text-ghost flex-shrink-0" />}
            <span className="text-[11px] font-mono text-text-primary truncate">
              {agent.id}
            </span>
          </div>
          <span className="text-[10px] text-text-faint">
            {tierLabel} · rep {(agent.reputation ?? 0).toFixed(2)}
          </span>
          {isGhost && (
            <span className="text-[9px] text-ghost uppercase tracking-wider font-mono">
              ghost · never wins
            </span>
          )}
        </div>
      </Link>

      {hovered && persona && (
        <div
          role="tooltip"
          className="absolute left-0 top-full mt-1 z-50 w-72 rounded-md border border-line bg-deep px-3 py-2 shadow-xl"
        >
          <p className="text-[10px] text-text-faint uppercase tracking-wider mb-1">
            {persona.archetype}
          </p>
          <p className="text-xs text-text-primary leading-relaxed">{persona.short}</p>
          {isGhost && (
            <p className="text-[10px] text-ghost mt-2 leading-relaxed">
              Ghost competitor — bids visibly but is filtered before reranking per spec §16-A5.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function AgentRosterStrip() {
  const agents = useAppStore((s) => s.agents);
  const tasks = useAppStore((s) => s.tasks);
  const byId = new Map(agents.map((a) => [a.id, a]));
  const ordered = ROSTER_ORDER.map((id) => byId.get(id)).filter(Boolean) as Agent[];

  // An agent is "active" if it owns at least one task currently RUNNING / VERIFYING.
  const activeIds = new Set(
    tasks
      .filter((t) => t.assignedAgentId && (t.state === "RUNNING" || t.state === "VERIFYING" || t.state === "ASSIGNED" || t.state === "BIDDING"))
      .map((t) => t.assignedAgentId as string)
  );

  return (
    <div className="border-b border-line bg-deep/80 backdrop-blur">
      <div className="flex items-center justify-between px-6 py-2">
        <span className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
          Marketplace roster · 9 agents
        </span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
          {ordered.length}/9 online
        </span>
      </div>
      <div className="overflow-x-auto px-6 pb-3">
        <div className="flex items-center gap-2">
          {ordered.map((a) => (
            <AgentChip key={a.id} agent={a} isActive={activeIds.has(a.id) && !a.isGhost} />
          ))}
        </div>
      </div>
    </div>
  );
}
