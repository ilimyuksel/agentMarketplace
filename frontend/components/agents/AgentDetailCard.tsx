"use client";

import { useEffect, useRef, useState } from "react";
import { Skull, Crown, Hammer, Gavel } from "lucide-react";
import { motion } from "framer-motion";
import { ReputationGauge } from "@/components/primitives/ReputationGauge";
import { ReputationSparkline } from "@/components/primitives/ReputationSparkline";
import { AddressChip } from "@/components/primitives/AddressChip";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";
import { PERSONAS } from "@/lib/personas";
import { EconomicsSection } from "./EconomicsSection";
import { SkillsSection } from "./SkillsSection";
import type { Agent, AgentDetail, Wallet } from "@/types";

interface Props {
  agent: Agent;
  detail?: AgentDetail;
  wallet?: Wallet;
}

function variant(agent: Agent): {
  border: string;
  badge: string;
  Icon: React.ComponentType<{ className?: string }>;
  badgeLabel: string;
} {
  if (agent.isGhost) {
    return {
      border: "border-l-4 border-l-ghost border-y border-r border-line opacity-80",
      badge: "border-ghost/40 bg-ghost/10 text-ghost",
      Icon: Skull,
      badgeLabel: "GHOST",
    };
  }
  if (agent.tier === "T1") {
    return {
      border: "border-l-4 border-l-active border-y border-r border-line",
      badge: "border-active/40 bg-active/10 text-active",
      Icon: Crown,
      badgeLabel: "T1 MANAGER",
    };
  }
  if (agent.tier === "JUDGE") {
    return {
      border: "border-l-4 border-l-success border-y border-r border-line shadow-[0_0_0_1px_rgba(16,185,129,0.06)]",
      badge: "border-success/40 bg-success/10 text-success",
      Icon: Gavel,
      badgeLabel: "JUDGE",
    };
  }
  const rep = agent.reputation ?? 0;
  if (rep >= 0.85) {
    return {
      border: "border-l-4 border-l-success border-y border-r border-line",
      badge: "border-success/40 bg-success/10 text-success",
      Icon: Hammer,
      badgeLabel: "T2 PREMIUM",
    };
  }
  if (rep < 0.75) {
    return {
      border: "border-l-4 border-l-pending border-y border-r border-line",
      badge: "border-pending/40 bg-pending/10 text-pending",
      Icon: Hammer,
      badgeLabel: "T2 UNDERDOG",
    };
  }
  return {
    border: "border-l-4 border-l-line border-y border-r border-line",
    badge: "border-line bg-sunken text-text-muted",
    Icon: Hammer,
    badgeLabel: "T2 WORKER",
  };
}

function useBalancePulse(balance: number): boolean {
  const prev = useRef(balance);
  const [pulse, setPulse] = useState(false);
  useEffect(() => {
    if (balance !== prev.current) {
      setPulse(true);
      prev.current = balance;
      const id = window.setTimeout(() => setPulse(false), 1400);
      return () => window.clearTimeout(id);
    }
  }, [balance]);
  return pulse;
}

export function AgentDetailCard({ agent, detail, wallet }: Props) {
  const persona = PERSONAS[agent.id];
  const v = variant(agent);
  const balance = wallet?.balance ?? 0;
  const pulse = useBalancePulse(balance);

  // Anchor target for /agents#agent_id navigation from the roster strip.
  const anchorId = agent.id.toLowerCase();

  return (
    <motion.article
      id={anchorId}
      className={`relative rounded-md bg-surface ${v.border} p-5 space-y-4 scroll-mt-[176px]`}
      animate={pulse ? { boxShadow: ["0 0 0 0 rgba(34,211,238,0)", "0 0 0 4px rgba(34,211,238,0.22)", "0 0 0 0 rgba(34,211,238,0)"] } : { boxShadow: "0 0 0 0 rgba(34,211,238,0)" }}
      transition={{ duration: 1.4, ease: "easeInOut" }}
    >
      <header className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex-shrink-0">
            <ReputationGauge value={agent.reputation} size={64} label />
          </div>
          <div className="min-w-0">
            <h3
              className="text-lg font-semibold text-text-primary truncate"
              style={{ fontFamily: "var(--font-jetbrains)" }}
            >
              {agent.id}
            </h3>
            <p className="text-[11px] font-mono text-text-faint mt-0.5">
              {agent.role} · {agent.completedJobs ?? 0} jobs ·{" "}
              {agent.successRate != null
                ? `${(agent.successRate * 100).toFixed(0)}% success`
                : "—"}
            </p>
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <span
                className={`inline-flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-[0.18em] px-2 py-0.5 rounded border ${v.badge}`}
              >
                <v.Icon className="w-3 h-3" />
                {v.badgeLabel}
              </span>
              {persona && (
                <span className="text-[9px] font-mono uppercase tracking-[0.16em] text-text-faint">
                  {persona.style}
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {persona && (
        <p className="text-[12px] text-text-muted leading-relaxed">
          {persona.full}
        </p>
      )}

      <div className="grid grid-cols-[1fr_auto] gap-3 items-end">
        <div className="space-y-1.5">
          <p className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-faint">
            Reputation · last 12 verdicts
          </p>
          <ReputationSparkline
            history={detail?.reputationHistory ?? []}
            currentRep={agent.reputation ?? 0}
            width={260}
            height={40}
          />
        </div>
        <div className="text-right text-[10px] font-mono text-text-faint">
          <p>delta on next verdict:</p>
          <p className="text-success">≥0.85 · +0.02</p>
          <p className="text-active">0.70–0.84 · +0.01</p>
          <p className="text-pending">0.50–0.69 · −0.01</p>
          <p className="text-danger">&lt;0.50 · −0.05</p>
        </div>
      </div>

      <EconomicsSection agent={agent} detail={detail} />

      <SkillsSection skillKeywords={agent.skillKeywords} />

      <div className="pt-3 border-t border-line/60">
        <p className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-faint mb-1.5">
          Wallet
        </p>
        <div className="flex items-baseline justify-between gap-3">
          <MoneyTicker value={balance} size="xl" />
          <AddressChip walletId={agent.walletId} tone="agent" size="sm" />
        </div>
        <p className="text-[10px] text-text-faint font-mono mt-1">
          earned across {agent.completedJobs ?? 0} completed jobs
        </p>
      </div>

      {agent.isGhost && (
        <footer className="text-[10px] font-mono text-ghost border-t border-ghost/20 pt-2 flex items-center gap-1.5">
          <Skull className="w-3 h-3" />
          ghost · filtered before reranking
        </footer>
      )}
    </motion.article>
  );
}
