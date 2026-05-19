import type { WSEvent } from "@/types";

export type EventCategory =
  | "JOB" | "TASK" | "BIDDING" | "JUDGE" | "PAYMENT"
  | "LEDGER" | "REPUTATION" | "SYSTEM" | "OTHER";

export const ALL_CATEGORIES: EventCategory[] = [
  "JOB", "TASK", "BIDDING", "JUDGE", "PAYMENT", "LEDGER", "REPUTATION", "SYSTEM",
];

export function categoryFor(eventType: string): EventCategory {
  if (eventType.startsWith("job.")) return "JOB";
  if (eventType.startsWith("task.")) return "TASK";
  if (eventType.startsWith("bidding.")) return "BIDDING";
  if (eventType.startsWith("judge.")) return "JUDGE";
  if (eventType.startsWith("payment.")) return "PAYMENT";
  if (eventType.startsWith("ledger.")) return "LEDGER";
  if (eventType.startsWith("reputation.")) return "REPUTATION";
  if (eventType.startsWith("system.")) return "SYSTEM";
  return "OTHER";
}

export function categoryColor(
  eventType: string,
  payload: Record<string, unknown> | null | undefined,
): string {
  const p = payload ?? {};
  switch (categoryFor(eventType)) {
    case "JOB": return "text-active";
    case "TASK": return "text-text-muted";
    case "BIDDING": return "text-pending";
    case "JUDGE": {
      const d = (p.decision as string) ?? "";
      if (d === "APPROVED") return "text-success";
      if (d === "REJECTED") return "text-danger";
      return "text-pending";
    }
    case "PAYMENT": return "text-success";
    case "LEDGER": return "text-success";
    case "REPUTATION": return "text-ghost";
    case "SYSTEM": return "text-text-faint";
    default: return "text-text-faint";
  }
}

export function categoryBgTone(cat: EventCategory): string {
  switch (cat) {
    case "JOB": return "border-active/30 bg-active/5 text-active";
    case "TASK": return "border-line bg-sunken text-text-muted";
    case "BIDDING": return "border-pending/30 bg-pending/5 text-pending";
    case "JUDGE": return "border-success/30 bg-success/5 text-success";
    case "PAYMENT": return "border-success/30 bg-success/5 text-success";
    case "LEDGER": return "border-success/30 bg-success/5 text-success";
    case "REPUTATION": return "border-ghost/30 bg-ghost/5 text-ghost";
    case "SYSTEM": return "border-line bg-sunken text-text-faint";
    default: return "border-line bg-sunken text-text-faint";
  }
}

export function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return (
      d.toLocaleTimeString("en-US", { hour12: false }) +
      "." +
      String(d.getMilliseconds()).padStart(3, "0")
    );
  } catch {
    return "—";
  }
}

export function shortDescription(
  eventType: string,
  payload: Record<string, unknown> | null | undefined,
): string {
  const p = (payload ?? {}) as Record<string, unknown>;
  const num = (k: string) => (typeof p[k] === "number" ? (p[k] as number) : undefined);
  const str = (k: string) => (typeof p[k] === "string" ? (p[k] as string) : undefined);

  switch (eventType) {
    case "job.created":              return `budget $${num("budget")?.toFixed(2) ?? "?"} · ${str("budgetTier") ?? "?"}`;
    case "job.escrow_locked":        return `$${num("amount")?.toFixed(2) ?? "?"} locked`;
    case "job.manager_assigned":     return `manager ${str("managerId") ?? ""} · bid $${num("bidAmount")?.toFixed(2) ?? "?"}`;
    case "job.planning_started":     return `planning by ${str("managerId") ?? ""}`;
    case "job.plan_completed":       return `${num("subTaskCount") ?? "?"} tasks · expected profit $${num("expectedProfit")?.toFixed(2) ?? "?"}`;
    case "job.execution_started":    return `executing ${num("taskCount") ?? "?"} tasks`;
    case "job.completed":            return `final: ${str("finalState") ?? "COMPLETED"} · pm $${num("pmProfit")?.toFixed(2) ?? "?"} · refund $${num("refund")?.toFixed(2) ?? "?"}`;
    case "job.failed":               return `reason: ${str("reason") ?? "unknown"}`;
    case "job.refunded":             return `refund $${num("amount")?.toFixed(2) ?? "?"}`;
    case "task.created":             return `${str("title") ?? "task"} · $${num("budget")?.toFixed(2) ?? "?"}`;
    case "task.state_changed":       return `${str("fromState") ?? ""} → ${str("toState") ?? ""}`;
    case "task.execution_started":   return `${str("agentId") ?? ""} attempt ${num("attempt") ?? "?"}`;
    case "task.execution_completed": return `${str("agentId") ?? ""} done`;
    case "task.failed":              return `reason: ${str("reason") ?? str("error") ?? "unknown"}`;
    case "task.revision_requested":  return `revision · score ${num("score")?.toFixed(2) ?? "?"}`;
    case "task.rejected":            return `rejected · score ${num("score")?.toFixed(2) ?? "?"}`;
    case "bidding.round_started":    return `task ${str("taskTitle") ?? str("taskId") ?? "?"}`;
    case "bidding.bid_submitted":    return `${str("agentId") ?? ""} bid $${num("bidAmount")?.toFixed(2) ?? "?"} · conf ${num("confidence")?.toFixed(2) ?? "?"}`;
    case "bidding.winner_selected":  return `winner: ${str("winnerId") ?? ""} · score ${num("selectionScore")?.toFixed(2) ?? "?"}`;
    case "judge.evaluation_started": return `evaluating ${str("evaluatedAgentId") ?? ""}`;
    case "judge.verdict_delivered":  return `${str("decision") ?? ""} · ${num("finalScore")?.toFixed(2) ?? "?"}`;
    case "payment.escrow_locked":    return `$${num("amount")?.toFixed(2) ?? "?"} → escrow`;
    case "payment.milestone_released": return `${str("milestone") ?? ""} · $${num("amount")?.toFixed(2) ?? "?"} → ${str("agentId") ?? "?"}`;
    case "payment.judge_fee_paid":   return `$${num("amount")?.toFixed(2) ?? "?"} → judge`;
    case "payment.pm_profit_realized": return `PM profit $${num("profitAmount")?.toFixed(2) ?? "?"}`;
    case "payment.refund_issued":    return `refund $${num("amount")?.toFixed(2) ?? "?"} → user`;
    case "ledger.transaction_added": return `block #${num("blockNumber") ?? "?"} · $${num("amount")?.toFixed(2) ?? "?"}`;
    case "reputation.updated": {
      const delta = num("delta") ?? 0;
      const sign = delta >= 0 ? "+" : "";
      return `${str("agentId") ?? ""} ${sign}${delta.toFixed(2)} → ${num("newReputation")?.toFixed(2) ?? "?"}`;
    }
    case "system.heartbeat":         return `ts ${str("ts")?.slice(11, 19) ?? ""}`;
    default:                         return "";
  }
}

export function metadataChips(event: WSEvent): { key: string; value: string }[] {
  const out: { key: string; value: string }[] = [];
  if (event.jobId) out.push({ key: "job", value: event.jobId.slice(-12) });
  if (event.taskId) out.push({ key: "task", value: event.taskId.slice(-10) });
  return out;
}
