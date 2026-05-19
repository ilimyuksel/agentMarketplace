"use client";

import { useShallow } from "zustand/react/shallow";
import { useAppStore } from "@/lib/store";
import { StateBadge } from "@/components/primitives/StateBadge";
import { AddressChip } from "@/components/primitives/AddressChip";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";
import { BidRow } from "./BidRow";
import { JudgeVerdictCard } from "./JudgeVerdictCard";
import { PERSONAS } from "@/lib/personas";

export function TaskDetailPanel() {
  const selectedTaskId = useAppStore((s) => s.selectedTaskId);
  const task = useAppStore((s) =>
    selectedTaskId ? s.tasks.find((t) => t.id === selectedTaskId) : undefined
  );
  const bids = useAppStore(
    useShallow((s) =>
      selectedTaskId ? s.bids.filter((b) => b.taskId === selectedTaskId) : []
    )
  );
  const evaluations = useAppStore(
    useShallow((s) =>
      selectedTaskId ? s.evaluations.filter((e) => e.taskId === selectedTaskId) : []
    )
  );
  const agents = useAppStore((s) => s.agents);
  const transactions = useAppStore(
    useShallow((s) =>
      selectedTaskId ? s.transactions.filter((t) => t.taskId === selectedTaskId) : []
    )
  );

  if (!selectedTaskId || !task) {
    return (
      <div className="rounded-md border border-dashed border-line bg-surface/40 p-6 text-center">
        <p className="text-[11px] uppercase tracking-[0.18em] text-text-faint font-mono">
          Task detail
        </p>
        <p className="text-xs text-text-muted mt-2">
          Click a node in the DAG to inspect bids, judge verdict and money flow.
        </p>
      </div>
    );
  }

  const agentById = new Map(agents.map((a) => [a.id, a]));
  const sortedBids = [...bids].sort((a, b) => {
    if (a.isWinner !== b.isWinner) return a.isWinner ? -1 : 1;
    return a.bidAmount - b.bidAmount;
  });
  const sortedEvals = [...evaluations].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  );

  const winnerBid = bids.find((b) => b.isWinner);
  const assignedAgent = task.assignedAgentId ? agentById.get(task.assignedAgentId) : undefined;
  const assignedPersona = task.assignedAgentId ? PERSONAS[task.assignedAgentId] : undefined;

  const milestoneTxs = transactions.filter((t) => t.transactionType === "MILESTONE_RELEASE");
  const judgeFeeTx = transactions.find((t) => t.transactionType === "JUDGE_FEE");

  return (
    <div className="rounded-md border border-line bg-surface">
      <header className="border-b border-line px-4 py-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono mb-1">
            Task
          </p>
          <h3 className="text-sm font-semibold text-text-primary truncate">{task.title}</h3>
          <p className="text-[11px] text-text-muted mt-1 leading-snug">{task.description}</p>
        </div>
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <StateBadge state={task.state} />
          <span
            className="font-mono text-base text-text-primary tabular-nums"
            style={{ fontFamily: "var(--font-jetbrains)" }}
          >
            ${task.budget.toFixed(2)}
          </span>
        </div>
      </header>

      <div className="px-4 py-3 space-y-4">
        <section className="grid grid-cols-2 gap-3 text-[11px] font-mono">
          <div>
            <span className="text-text-faint">Skills · </span>
            <span className="text-text-primary">
              {task.requiredSkills.join(", ") || "—"}
            </span>
          </div>
          <div>
            <span className="text-text-faint">Depends on · </span>
            <span className="text-text-primary">
              {task.dependencies.length > 0 ? task.dependencies.length : "none"}
            </span>
          </div>
          <div>
            <span className="text-text-faint">Assigned · </span>
            {assignedAgent ? (
              <span className="text-text-primary">
                {assignedAgent.id}
                {assignedPersona && (
                  <span className="text-text-faint"> · {assignedPersona.archetype}</span>
                )}
              </span>
            ) : (
              <span className="text-text-faint">—</span>
            )}
          </div>
          <div>
            <span className="text-text-faint">Revision · </span>
            <span className="text-text-primary">{task.revisionCount}</span>
          </div>
        </section>

        {bids.length > 0 && (
          <section className="space-y-2">
            <h4 className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
              Bidding round · {bids.length} bid{bids.length === 1 ? "" : "s"}
            </h4>
            <div className="space-y-1.5">
              {sortedBids.map((b) => (
                <BidRow key={b.id} bid={b} agent={agentById.get(b.agentId)} />
              ))}
            </div>
            {winnerBid && winnerBid.selectionScore != null && (
              <p className="text-[10px] font-mono text-text-faint">
                reranker: skill-match × 0.35 + reputation × 0.25 + price × 0.20 + confidence × 0.15 + speed × 0.05
              </p>
            )}
          </section>
        )}

        {milestoneTxs.length > 0 && (
          <section className="space-y-2">
            <h4 className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
              Milestone releases
            </h4>
            <div className="space-y-1">
              {milestoneTxs.map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between rounded border border-line bg-sunken px-2.5 py-1.5"
                >
                  <span className="text-[10px] uppercase tracking-wider font-mono text-success">
                    {tx.milestone}
                  </span>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
                    <MoneyTicker value={tx.amount} size="sm" highlightOnChange={false} />
                    <span className="text-text-faint">→</span>
                    <AddressChip walletId={tx.toWalletId} tone="agent" size="sm" />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {sortedEvals.length > 0 && (
          <section className="space-y-2">
            <h4 className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
              Judge · {sortedEvals.length} verdict{sortedEvals.length === 1 ? "" : "s"}
            </h4>
            <div className="space-y-2">
              {sortedEvals.map((ev, i) => (
                <JudgeVerdictCard key={ev.id} evaluation={ev} attemptIndex={i} />
              ))}
            </div>
          </section>
        )}

        {judgeFeeTx && (
          <section className="text-[10px] font-mono text-text-faint flex items-center justify-between">
            <span>judge fee booked</span>
            <span className="flex items-center gap-2">
              <MoneyTicker value={judgeFeeTx.amount} size="sm" highlightOnChange={false} />
              <span className="text-text-faint">→ wallet_qajudge_001</span>
            </span>
          </section>
        )}
      </div>
    </div>
  );
}
