"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "@/lib/store";

function categoryColor(eventType: string, payload: Record<string, unknown>): string {
  if (eventType.startsWith("job.")) return "text-active";
  if (eventType.startsWith("task.")) return "text-text-muted";
  if (eventType.startsWith("bidding.")) return "text-pending";
  if (eventType.startsWith("judge.")) {
    const d = (payload?.decision as string) ?? "";
    if (d === "APPROVED") return "text-success";
    if (d === "REJECTED") return "text-danger";
    return "text-pending";
  }
  if (eventType.startsWith("payment.") || eventType.startsWith("ledger.")) return "text-success";
  if (eventType.startsWith("reputation.")) return "text-ghost";
  return "text-text-faint";
}

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour12: false });
  } catch {
    return "—";
  }
}

function shortDescription(eventType: string, payload: Record<string, unknown>): string {
  const p = payload ?? {};
  if (eventType === "bidding.bid_submitted") {
    return `${p.agentId ?? ""} bid $${(p.bidAmount as number)?.toFixed(2) ?? "?"}`;
  }
  if (eventType === "bidding.winner_selected") {
    return `winner: ${p.winnerId ?? ""}`;
  }
  if (eventType === "judge.verdict_delivered") {
    return `${p.decision ?? ""} · ${((p.finalScore as number) ?? 0).toFixed(2)}`;
  }
  if (eventType === "payment.milestone_released") {
    return `${p.milestone ?? ""} · $${(p.amount as number)?.toFixed(2) ?? "?"} → ${p.agentId ?? ""}`;
  }
  if (eventType === "payment.escrow_locked") {
    return `$${(p.amount as number)?.toFixed(2) ?? "?"} locked`;
  }
  if (eventType === "payment.refund_issued") {
    return `refund $${(p.amount as number)?.toFixed(2) ?? "?"}`;
  }
  if (eventType === "payment.judge_fee_paid") {
    return `judge fee $${(p.amount as number)?.toFixed(2) ?? "?"}`;
  }
  if (eventType === "payment.pm_profit_realized") {
    return `PM profit $${(p.profitAmount as number)?.toFixed(2) ?? "?"}`;
  }
  if (eventType === "ledger.transaction_added") {
    return `block #${p.blockNumber ?? "?"} · $${(p.amount as number)?.toFixed(2) ?? "?"}`;
  }
  if (eventType === "task.execution_started") {
    return `${p.agentId ?? ""} executing`;
  }
  if (eventType === "task.revision_requested") {
    return `revision · ${((p.score as number) ?? 0).toFixed(2)}`;
  }
  if (eventType === "task.state_changed") {
    return `${p.fromState ?? ""} → ${p.toState ?? ""}`;
  }
  if (eventType === "reputation.updated") {
    const delta = (p.delta as number) ?? 0;
    const sign = delta >= 0 ? "+" : "";
    return `${p.agentId ?? ""} ${sign}${delta.toFixed(2)} → ${(p.newReputation as number)?.toFixed(2) ?? "?"}`;
  }
  if (eventType === "job.failed") {
    return `reason: ${p.reason ?? "unknown"}`;
  }
  if (eventType === "job.completed") {
    return `final: ${p.finalState ?? "COMPLETED"}`;
  }
  return "";
}

export function EventTicker() {
  const backendOnline = useAppStore((s) => s.backendOnline);
  const backendChecked = useAppStore((s) => s.backendChecked);
  const events = useAppStore((s) => s.events);
  const agents = useAppStore((s) => s.agents);
  const transactions = useAppStore((s) => s.transactions);
  const globalStatus = useAppStore((s) => s.globalStatus);
  const jobStatus = useAppStore((s) => s.jobStatus);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-pin to the right edge as new events arrive.
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
  }, [events.length]);

  const idle = events.length === 0;
  const genesisBlock = transactions.find((t) => t.blockNumber === 0);
  const genesisHash = genesisBlock?.blockHash ?? null;

  // Pick the most pessimistic status across channels.
  const channelStatus = jobStatus !== "idle" && jobStatus !== "closed" ? jobStatus : globalStatus;
  let dot = "bg-genesis";
  let dotLabel = "idle";
  if (!backendChecked) { dot = "bg-pending"; dotLabel = "checking"; }
  else if (channelStatus === "live") { dot = "bg-active"; dotLabel = "live"; }
  else if (channelStatus === "connecting") { dot = "bg-pending"; dotLabel = "connecting"; }
  else if (channelStatus === "reconnecting") { dot = "bg-pending"; dotLabel = "reconnecting"; }
  else if (channelStatus === "polling") { dot = "bg-danger"; dotLabel = "polling fallback"; }
  else if (!backendOnline) { dot = "bg-danger"; dotLabel = "offline"; }

  const idleSegments = [
    { text: dotLabel, accent: backendOnline ? "text-active" : "text-pending" },
    { text: `backend ${backendOnline ? "online" : "offline"}`, accent: "text-text-muted" },
    genesisHash
      ? {
          text: `genesis block #0 · ${genesisHash.slice(0, 8)}…${genesisHash.slice(-4)}`,
          accent: "text-text-muted",
        }
      : { text: "genesis block pending", accent: "text-text-faint" },
    { text: "chain verified", accent: "text-success" },
    { text: "awaiting first job", accent: "text-text-faint" },
    { text: `${agents.length}/9 agents online`, accent: "text-text-muted" },
    { text: "ProjectManager_001 listening", accent: "text-text-faint" },
    { text: "QAJudge_001 listening", accent: "text-text-faint" },
  ];

  return (
    <footer className="h-12 border-t border-line bg-deep flex items-center overflow-hidden">
      <div className="flex items-center gap-3 px-4 border-r border-line h-full flex-shrink-0">
        <span className={`relative w-2 h-2 rounded-full ${dot}`}>
          {channelStatus === "live" && (
            <span className={`absolute inset-0 rounded-full ${dot} animate-ping opacity-60`} />
          )}
        </span>
        <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-text-faint">
          {dotLabel}
        </span>
      </div>

      <div className="flex-1 overflow-hidden relative h-full">
        {idle ? (
          <div className="ticker-marquee flex items-center gap-6 h-full whitespace-nowrap font-mono text-[11px] px-6">
            {[...idleSegments, ...idleSegments].map((seg, i) => (
              <span key={i} className="flex items-center gap-6">
                <span className={seg.accent}>· {seg.text}</span>
              </span>
            ))}
          </div>
        ) : (
          <div
            ref={scrollRef}
            className="flex items-center h-full px-4 overflow-x-auto scroll-smooth"
          >
            {events
              .slice(0, 24)
              .slice()
              .reverse()
              .map((e, i) => (
                <span key={`${e.eventType}-${e.timestamp}-${i}`} className="flex items-center gap-2 mr-5 whitespace-nowrap font-mono text-[11px]">
                  <span className="text-text-faint">{formatTime(e.timestamp)}</span>
                  <span className={categoryColor(e.eventType, e.payload)}>
                    {e.eventType}
                  </span>
                  {shortDescription(e.eventType, e.payload) && (
                    <span className="text-text-muted">· {shortDescription(e.eventType, e.payload)}</span>
                  )}
                </span>
              ))}
          </div>
        )}
      </div>
    </footer>
  );
}
