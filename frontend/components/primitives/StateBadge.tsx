"use client";

import { motion } from "framer-motion";

type Tone = "active" | "success" | "pending" | "danger" | "ghost" | "genesis" | "muted";

interface ToneStyle {
  pill: string;
  dot: string;
  pulse: boolean;
}

const TONE: Record<Tone, ToneStyle> = {
  active:  { pill: "border-active/40 bg-active/10 text-active",   dot: "bg-active",  pulse: true  },
  success: { pill: "border-success/40 bg-success/10 text-success", dot: "bg-success", pulse: false },
  pending: { pill: "border-pending/40 bg-pending/10 text-pending", dot: "bg-pending", pulse: false },
  danger:  { pill: "border-danger/40 bg-danger/10 text-danger",   dot: "bg-danger",  pulse: false },
  ghost:   { pill: "border-ghost/40 bg-ghost/10 text-ghost",     dot: "bg-ghost",   pulse: false },
  genesis: { pill: "border-genesis/40 bg-genesis/10 text-genesis", dot: "bg-genesis", pulse: false },
  muted:   { pill: "border-line bg-sunken text-text-muted",       dot: "bg-text-faint", pulse: false },
};

/**
 * Maps every TaskState / JobState / JudgeDecision / TransactionType /
 * BudgetTier we receive from the backend onto a tone. Anything unknown
 * falls back to "muted" rather than throwing — the demo must survive an
 * unfamiliar state without a hard crash.
 */
const STATE_TONE: Record<string, Tone> = {
  // Task states (12)
  PENDING: "muted",
  READY: "active",
  BIDDING: "active",
  ASSIGNED: "active",
  RUNNING: "active",
  DONE: "active",
  VERIFYING: "active",
  VERIFIED: "success",
  PAID: "success",
  REVISION: "pending",
  REJECTED: "danger",
  FAILED: "danger",
  // Job states (8) — overlap with task states uses the same tone
  CREATED: "muted",
  ESCROW_LOCK: "active",
  MANAGER_BIDDING: "active",
  PLANNING: "active",
  EXECUTING: "active",
  COMPLETED: "success",
  CANCELLED: "muted",
  // Judge verdicts
  APPROVED: "success",
  REVISION_REQUESTED: "pending",
  // Transaction types
  GENESIS: "genesis",
  MANAGER_FUNDING: "active",
  MILESTONE_RELEASE: "success",
  JUDGE_FEE: "pending",
  PM_PROFIT: "active",
  AGENT_PAYMENT: "success",
  REFUND: "muted",
  // Budget tiers
  MINIMAL: "muted",
  STANDARD: "active",
  PREMIUM: "success",
};

interface Props {
  state: string;
  /** Override the auto-tone mapping. */
  tone?: Tone;
  size?: "sm" | "md";
}

export function StateBadge({ state, tone, size = "md" }: Props) {
  const t = tone ?? STATE_TONE[state] ?? "muted";
  const style = TONE[t];

  const sizing =
    size === "sm"
      ? "text-[9px] px-1.5 py-0.5 gap-1"
      : "text-[10px] px-2 py-0.5 gap-1.5";

  return (
    <span
      className={`inline-flex items-center ${sizing} rounded border font-mono uppercase tracking-wider ${style.pill}`}
    >
      <span className={`relative w-1.5 h-1.5 rounded-full ${style.dot}`}>
        {style.pulse && (
          <motion.span
            className={`absolute inset-0 rounded-full ${style.dot}`}
            animate={{ opacity: [0.6, 0, 0.6], scale: [1, 1.8, 1] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
      </span>
      {state.replace(/_/g, " ")}
    </span>
  );
}
