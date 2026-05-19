"use client";

import { useAppStore } from "@/lib/store";
import { AddAgentButton } from "./AddAgentButton";

export function AgentsHeader() {
  const agents = useAppStore((s) => s.agents);
  const agentDetailsLoading = useAppStore((s) => s.agentDetailsLoading);

  const primary = agents.filter((a) => !a.isGhost).length;
  const ghosts = agents.filter((a) => a.isGhost).length;

  return (
    <div className="h-16 border-b border-line bg-deep flex items-center justify-between px-8 gap-4">
      <div className="flex items-baseline gap-4 min-w-0">
        <h1
          className="text-base font-semibold tracking-tight text-text-primary"
          style={{ fontFamily: "var(--font-space-grotesk)" }}
        >
          Agents
        </h1>
        <p className="text-[11px] font-mono text-text-faint">
          {agents.length} agents · {primary} primary · {ghosts} ghost · marketplace v1.0
        </p>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        {agentDetailsLoading && (
          <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-pending">
            loading reputation history…
          </span>
        )}
        <AddAgentButton />
      </div>
    </div>
  );
}
