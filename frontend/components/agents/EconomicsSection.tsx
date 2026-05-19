"use client";

import type { Agent, AgentDetail } from "@/types";

interface Row {
  label: string;
  value: string;
  tone?: "primary" | "success" | "pending" | "danger" | "muted";
}

interface Props {
  agent: Agent;
  detail?: AgentDetail;
}

// Pricing-specific fields are ONLY on the detail endpoint. The list endpoint
// returns a slim Agent without basePrice / minAcceptance / biddingStyle /
// pricingConfig — so we must always resolve through `detail` (with null
// fallbacks), never assume the slim `agent` has them.

function moneyOr(value: number | null | undefined, fallback: string): string {
  return value != null ? `$${value.toFixed(0)}` : fallback;
}

function rows(agent: Agent, detail?: AgentDetail): Row[] {
  const cfg = (detail?.pricingConfig ?? {}) as Record<string, unknown>;
  const pickPct = (k: string) =>
    typeof cfg[k] === "number" ? `${((cfg[k] as number) * 100).toFixed(0)}%` : null;

  const rep = agent.reputation ?? 0;
  const basePrice = detail?.basePrice ?? null;
  const minAcceptance = detail?.minAcceptance ?? null;
  const biddingStyle = detail?.biddingStyle ?? agent.biddingStyle ?? null;

  if (agent.tier === "T1") {
    return [
      { label: "base price", value: "takes margin · no flat fee", tone: "muted" },
      {
        label: "margin",
        value: `${pickPct("margin_minimal") ?? pickPct("marginMinimal") ?? "15%"} MIN · ${pickPct("margin_standard") ?? pickPct("marginStandard") ?? "18%"} STD · ${pickPct("margin_premium") ?? pickPct("marginPremium") ?? "22%"} PRM`,
        tone: "primary",
      },
      { label: "bid formula", value: "budget × (1 − margin × 0.5)", tone: "muted" },
      { label: "next delta", value: `current ${rep.toFixed(2)} → +0.02 on COMPLETED`, tone: "success" },
    ];
  }

  if (agent.tier === "JUDGE") {
    return [
      { label: "fee", value: "$2.00 FLAT per evaluation", tone: "pending" },
      { label: "rubric weights", value: "scope 0.25 · structure 0.20 · content 0.35 · brief 0.20", tone: "primary" },
      { label: "thresholds", value: "≥0.70 APPROVED · 0.50–0.69 REVISION · <0.50 REJECTED", tone: "muted" },
      { label: "incentive", value: "fee independent of verdict — no approval bias", tone: "success" },
    ];
  }

  if (agent.isGhost) {
    const mult =
      agent.id === "ContentWriter_002" ? "65%"
      : agent.id === "WebDeveloper_002" ? "95%"
      : "90%";
    return [
      { label: "bid pattern", value: `task_budget × ${mult}`, tone: "muted" },
      { label: "selection", value: "filtered before LLM reranker · spec §16-A5", tone: "danger" },
      { label: "participation", value: "marketplace depth · zero economic effect", tone: "muted" },
    ];
  }

  // T2 worker
  const isPremium = agent.id === "ContentWriter_001";
  const isUnderdog = agent.id === "Designer_001";

  const baseRow: Row = {
    label: "base price",
    value: basePrice != null ? `$${basePrice.toFixed(0)} per task` : "n/a",
    tone: "primary",
  };
  const minAcceptanceRow: Row = {
    label: "min acceptance",
    value: moneyOr(minAcceptance, "n/a"),
    tone: "muted",
  };

  if (isPremium) {
    return [
      baseRow,
      { label: "premium mark", value: "+15% to +20% above market", tone: "success" },
      { label: "why they win", value: `reputation ${rep.toFixed(2)} weights selection above price`, tone: "muted" },
      minAcceptanceRow,
    ];
  }
  if (isUnderdog) {
    const discountedBid =
      basePrice != null ? `$${(basePrice * 0.9).toFixed(0)}` : "discounted";
    return [
      baseRow,
      { label: "underdog discount", value: "−10% auto when reputation < 0.80", tone: "pending" },
      { label: "effective bid", value: `current ${rep.toFixed(2)} → bids @ ~${discountedBid}`, tone: "muted" },
      minAcceptanceRow,
    ];
  }
  // Generic T2 (Researcher, WebDev)
  return [
    baseRow,
    minAcceptanceRow,
    { label: "bidding style", value: biddingStyle ?? "—", tone: "muted" },
    { label: "current rep", value: rep.toFixed(2), tone: "success" },
  ];
}

const TONE_CLS: Record<NonNullable<Row["tone"]>, string> = {
  primary: "text-text-primary",
  success: "text-success",
  pending: "text-pending",
  danger: "text-danger",
  muted: "text-text-muted",
};

export function EconomicsSection({ agent, detail }: Props) {
  const data = rows(agent, detail);
  return (
    <div className="space-y-1.5">
      <p className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-faint">
        Economics
      </p>
      <div className="rounded-md border border-line bg-sunken/70 px-3 py-2 space-y-1">
        {data.map((r) => (
          <div key={r.label} className="flex items-baseline justify-between gap-3">
            <span className="text-[10px] font-mono text-text-faint flex-shrink-0">
              {r.label}
            </span>
            <span className={`text-[10px] font-mono text-right ${TONE_CLS[r.tone ?? "primary"]}`}>
              {r.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
