import type { Agent, Transaction } from "@/types";

export interface SubAgentLine {
  walletId: string;
  agentId: string;
  total: number;
  /** Milestone breakdown — START/MID/COMPLETION amounts in order observed. */
  breakdown: { milestone: string; amount: number }[];
}

export interface Reconciliation {
  jobId: string;
  escrow: number;            // total escrow lock for the job
  pmWalletId: string | null;
  pmMargin: number;          // pmRevenue − pmExpenses
  subAgents: SubAgentLine[];
  judgeFees: { walletId: string | null; count: number; total: number };
  refund: number;
  computedTotal: number;     // pmMargin + sum(subAgents) + judgeFees + refund
  delta: number;             // escrow − computedTotal (positive = unaccounted)
  balanced: boolean;         // |delta| < 0.005 (sub-penny tolerance)
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

/**
 * Pure reconciliation. Takes the global transaction list, a job ID, and the
 * agent roster. Returns a fully decomposed money trail for that job.
 *
 * Algorithm:
 *   escrow         = Σ ESCROW_LOCK transactions for the job
 *   pmRevenue      = Σ MANAGER_FUNDING transactions to PM wallet
 *   pmExpenses     = Σ MILESTONE_RELEASE + JUDGE_FEE transactions FROM PM
 *   pmMargin       = pmRevenue − pmExpenses
 *   subAgent_x     = Σ MILESTONE_RELEASE transactions TO wallet_x
 *   judgeFees      = Σ JUDGE_FEE transactions for the job
 *   refund         = Σ REFUND transactions for the job
 *
 * Invariant: pmMargin + Σ subAgents + judgeFees + refund ≡ escrow
 */
export function reconcile(
  jobId: string,
  transactions: Transaction[],
  agents: Agent[],
): Reconciliation {
  const jobTxs = transactions.filter((t) => t.jobId === jobId);

  // ── Escrow ──────────────────────────────────────────────────────
  const escrowLockTxs = jobTxs.filter((t) => t.transactionType === "ESCROW_LOCK");
  const escrow = escrowLockTxs.reduce((s, t) => s + t.amount, 0);

  // ── PM wallet (derive from MANAGER_FUNDING destination) ─────────
  const managerFundingTxs = jobTxs.filter((t) => t.transactionType === "MANAGER_FUNDING");
  const pmWalletId = managerFundingTxs[0]?.toWalletId ?? null;
  const pmRevenue = managerFundingTxs.reduce((s, t) => s + t.amount, 0);

  // ── Milestone + judge fee outflows from PM ──────────────────────
  const milestoneTxs = jobTxs.filter((t) => t.transactionType === "MILESTONE_RELEASE");
  const judgeFeeTxs = jobTxs.filter((t) => t.transactionType === "JUDGE_FEE");
  const refundTxs = jobTxs.filter((t) => t.transactionType === "REFUND");

  const pmMilestoneOut = pmWalletId
    ? milestoneTxs.filter((t) => t.fromWalletId === pmWalletId).reduce((s, t) => s + t.amount, 0)
    : 0;
  const pmJudgeOut = pmWalletId
    ? judgeFeeTxs.filter((t) => t.fromWalletId === pmWalletId).reduce((s, t) => s + t.amount, 0)
    : 0;
  const pmMargin = round2(pmRevenue - pmMilestoneOut - pmJudgeOut);

  // ── Per-sub-agent totals ────────────────────────────────────────
  const buckets = new Map<string, { total: number; breakdown: { milestone: string; amount: number }[] }>();
  for (const t of milestoneTxs) {
    if (t.toWalletId === pmWalletId) continue; // skip PM's own funding (shouldn't be a MILESTONE_RELEASE anyway)
    const cur = buckets.get(t.toWalletId) ?? { total: 0, breakdown: [] };
    cur.total += t.amount;
    cur.breakdown.push({ milestone: t.milestone ?? "—", amount: round2(t.amount) });
    buckets.set(t.toWalletId, cur);
  }
  const subAgents: SubAgentLine[] = Array.from(buckets.entries())
    .map(([walletId, data]) => ({
      walletId,
      agentId: agents.find((a) => a.walletId === walletId)?.id ?? walletId,
      total: round2(data.total),
      breakdown: data.breakdown,
    }))
    .sort((a, b) => b.total - a.total);

  // ── Judge fees ──────────────────────────────────────────────────
  const judgeWalletId = judgeFeeTxs[0]?.toWalletId ?? null;
  const judgeFeesTotal = round2(judgeFeeTxs.reduce((s, t) => s + t.amount, 0));

  // ── Refund ──────────────────────────────────────────────────────
  const refund = round2(refundTxs.reduce((s, t) => s + t.amount, 0));

  // ── Total + balance check ───────────────────────────────────────
  const subAgentTotal = subAgents.reduce((s, a) => s + a.total, 0);
  const computedTotal = round2(pmMargin + subAgentTotal + judgeFeesTotal + refund);
  const delta = round2(round2(escrow) - computedTotal);

  return {
    jobId,
    escrow: round2(escrow),
    pmWalletId,
    pmMargin,
    subAgents,
    judgeFees: { walletId: judgeWalletId, count: judgeFeeTxs.length, total: judgeFeesTotal },
    refund,
    computedTotal,
    delta,
    balanced: Math.abs(delta) < 0.005,
  };
}
