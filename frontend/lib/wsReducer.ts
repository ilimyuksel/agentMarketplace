import type {
  Agent, Bid, Job, JobState, JudgeEvaluation, Task, TaskState, WSEvent,
} from "@/types";

/**
 * Pure reducer: takes an incoming WebSocket event and the current store slice,
 * returns a partial state patch. All field naming assumes the api.ts
 * snake→camel converter has already run on the event.
 */

export interface ReducerSlice {
  jobs: Job[];
  tasks: Task[];
  bids: Bid[];
  evaluations: JudgeEvaluation[];
  agents: Agent[];
  events: WSEvent[];
  /** Side-effect flags surfaced to the caller. */
  __refetchWallets?: boolean;
  __refetchLedger?: boolean;
  __heartbeatAt?: number;
}

type Patch = Partial<ReducerSlice>;

// All payloads come in as `any` from JSON; we narrow where needed.
type P = Record<string, unknown> & {
  jobId?: string; taskId?: string; agentId?: string;
  bidId?: string; winnerBidId?: string; winnerId?: string;
  state?: string; toState?: string; fromState?: string;
  reason?: string; failureReason?: string;
  amount?: number; bidAmount?: number;
  finalState?: string;
  decision?: string; finalScore?: number;
  feedback?: string; feedbackForRevision?: string; reasoning?: string;
  score?: number;
  managerId?: string; bidAmount_?: number;
  profitMargin?: number; confidence?: number;
  escrowWalletId?: string;
  title?: string; description?: string;
  requiredSkills?: string[]; budget?: number;
  dependencies?: string[];
  selectionScore?: number;
  evaluatedAgentId?: string;
  oldReputation?: number; newReputation?: number; delta?: number;
  ts?: string;
};

const isTerminalJob = (s: string): s is JobState =>
  s === "COMPLETED" || s === "FAILED" || s === "REJECTED" || s === "CANCELLED";

export function applyEvent(state: ReducerSlice, event: WSEvent): Patch {
  const p = (event.payload ?? {}) as P;
  const now = event.timestamp ?? new Date().toISOString();
  const patch: Patch = {};
  // Always record the event so the ticker has truth.
  patch.events = dedupePush(state.events, event);

  switch (event.eventType) {
    // ── JOB LIFECYCLE ───────────────────────────────────────────────
    case "job.created": {
      if (!p.jobId) break;
      const exists = state.jobs.some((j) => j.id === p.jobId);
      if (exists) break;
      const newJob: Job = {
        id: p.jobId,
        userId: (p.userId as string) ?? "user_demo",
        userPrompt: (p.userPrompt as string) ?? "",
        budget: (p.budget as number) ?? 0,
        budgetTier: (p.budgetTier as Job["budgetTier"]) ?? null,
        escrowWalletId: null,
        assignedManagerId: null,
        managerBidAmount: null,
        managerProfitMargin: null,
        state: "CREATED",
        finalOutputId: null,
        createdAt: now,
        completedAt: null,
        failureReason: null,
      };
      patch.jobs = [newJob, ...state.jobs];
      break;
    }
    case "job.escrow_locked": {
      patch.jobs = patchJob(state.jobs, p.jobId, (j) => ({
        ...j,
        state: "ESCROW_LOCK" as JobState,
        escrowWalletId: (p.escrowWalletId as string) ?? j.escrowWalletId,
      }));
      patch.__refetchWallets = true;
      break;
    }
    case "job.manager_bidding_started":
      patch.jobs = patchJob(state.jobs, p.jobId, (j) => ({ ...j, state: "MANAGER_BIDDING" }));
      break;
    case "job.manager_assigned":
      patch.jobs = patchJob(state.jobs, p.jobId, (j) => ({
        ...j,
        assignedManagerId: (p.managerId as string) ?? null,
        managerBidAmount: (p.bidAmount as number) ?? null,
        managerProfitMargin: (p.profitMargin as number) ?? null,
      }));
      break;
    case "job.planning_started":
      patch.jobs = patchJob(state.jobs, p.jobId, (j) => ({ ...j, state: "PLANNING" }));
      break;
    case "job.plan_completed":
      // Tasks arrive via task.created; just record the event.
      break;
    case "job.execution_started":
      patch.jobs = patchJob(state.jobs, p.jobId, (j) => ({ ...j, state: "EXECUTING" }));
      break;
    case "job.completed": {
      const final = (p.finalState as JobState) ?? "COMPLETED";
      patch.jobs = patchJob(state.jobs, p.jobId, (j) => ({ ...j, state: final, completedAt: now }));
      patch.__refetchWallets = true;
      break;
    }
    case "job.failed":
      patch.jobs = patchJob(state.jobs, p.jobId, (j) => ({
        ...j,
        state: "FAILED",
        failureReason: (p.reason as string) ?? "unknown",
        completedAt: now,
      }));
      patch.__refetchWallets = true;
      break;
    case "job.refunded":
      patch.__refetchWallets = true;
      break;

    // ── TASK LIFECYCLE ──────────────────────────────────────────────
    case "task.created": {
      if (!p.taskId || !p.jobId) break;
      const exists = state.tasks.some((t) => t.id === p.taskId);
      if (exists) break;
      const newTask: Task = {
        id: p.taskId,
        jobId: p.jobId,
        title: (p.title as string) ?? "Task",
        description: (p.description as string) ?? "",
        requiredSkills: (p.requiredSkills as string[]) ?? [],
        budget: (p.budget as number) ?? 0,
        finalCost: null,
        state: "PENDING",
        dependencies: (p.dependencies as string[]) ?? [],
        assignedAgentId: null,
        judgeScore: null,
        judgeVerdict: null,
        judgeFeedback: null,
        revisionCount: 0,
        createdAt: now,
        startedAt: null,
        completedAt: null,
      };
      patch.tasks = [...state.tasks, newTask];
      break;
    }
    case "task.state_changed":
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({
        ...t,
        state: ((p.toState as TaskState) ?? t.state),
      }));
      break;
    case "task.execution_started":
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({
        ...t,
        state: "RUNNING",
        assignedAgentId: (p.agentId as string) ?? t.assignedAgentId,
        startedAt: now,
      }));
      break;
    case "task.execution_completed":
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({ ...t, state: "DONE" }));
      break;
    case "task.revision_requested":
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({
        ...t,
        state: "REVISION",
        judgeScore: (p.score as number) ?? t.judgeScore,
        judgeFeedback: (p.feedback as string) ?? t.judgeFeedback,
        revisionCount: t.revisionCount + 1,
      }));
      break;
    case "task.rejected":
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({
        ...t,
        state: "REJECTED",
        judgeScore: (p.score as number) ?? t.judgeScore,
      }));
      break;
    case "task.failed":
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({ ...t, state: "FAILED" }));
      break;

    // ── BIDDING ─────────────────────────────────────────────────────
    case "bidding.round_started":
      // Clear leftover bids for this task — covers revision rounds.
      patch.bids = state.bids.filter((b) => b.taskId !== p.taskId);
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({ ...t, state: "BIDDING" }));
      break;
    case "bidding.bid_submitted": {
      if (!p.bidId || !p.taskId || !p.agentId) break;
      if (state.bids.some((b) => b.id === p.bidId)) break;
      const newBid: Bid = {
        id: p.bidId,
        taskId: p.taskId,
        agentId: p.agentId,
        bidAmount: (p.bidAmount as number) ?? 0,
        reasoning: (p.reasoning as string) ?? null,
        confidence: (p.confidence as number) ?? null,
        estimatedTimeSeconds: null,
        scopeAssumption: null,
        isWinner: false,
        selectionScore: null,
        submittedAt: now,
      };
      patch.bids = [...state.bids, newBid];
      break;
    }
    case "bidding.winner_selected":
      patch.bids = state.bids.map((b) =>
        b.id === p.winnerBidId
          ? { ...b, isWinner: true, selectionScore: (p.selectionScore as number) ?? b.selectionScore }
          : b
      );
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({
        ...t,
        state: "ASSIGNED",
        assignedAgentId: (p.winnerId as string) ?? t.assignedAgentId,
      }));
      break;

    // ── JUDGE ───────────────────────────────────────────────────────
    case "judge.evaluation_started":
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({ ...t, state: "VERIFYING" }));
      break;
    case "judge.verdict_delivered": {
      if (!p.taskId) break;
      const evalIndex = state.evaluations.filter((e) => e.taskId === p.taskId).length;
      const newEval: JudgeEvaluation = {
        id: `eval_${p.taskId}_${evalIndex + 1}`,
        taskId: p.taskId,
        evaluatedAgentId: (p.evaluatedAgentId as string) ?? "",
        scopeCompleteness: null,
        structuralQuality: null,
        contentQuality: null,
        briefFidelity: null,
        finalScore: (p.finalScore as number) ?? 0,
        decision: (p.decision as JudgeEvaluation["decision"]) ?? "APPROVED",
        reasoning: (p.reasoning as string) ?? null,
        feedbackForRevision: (p.feedbackForRevision as string) ?? null,
        confidenceInJudgment: null,
        createdAt: now,
      };
      patch.evaluations = [...state.evaluations, newEval];
      const decision = p.decision as string | undefined;
      patch.tasks = patchTask(state.tasks, p.taskId, (t) => ({
        ...t,
        state: decision === "APPROVED" ? "VERIFIED" : t.state,
        judgeScore: (p.finalScore as number) ?? t.judgeScore,
        judgeVerdict: decision ?? t.judgeVerdict,
      }));
      break;
    }

    // ── PAYMENTS ────────────────────────────────────────────────────
    case "payment.escrow_locked":
    case "payment.milestone_released":
    case "payment.judge_fee_paid":
    case "payment.pm_profit_realized":
    case "payment.refund_issued":
      patch.__refetchWallets = true;
      break;

    // ── LEDGER ──────────────────────────────────────────────────────
    case "ledger.transaction_added":
      patch.__refetchLedger = true;
      break;

    // ── REPUTATION ──────────────────────────────────────────────────
    case "reputation.updated": {
      const aid = (p.agentId as string) ?? "";
      const newRep = (p.newReputation as number) ?? null;
      if (!aid || newRep == null) break;
      patch.agents = state.agents.map((a) =>
        a.id === aid ? { ...a, reputation: newRep } : a
      );
      break;
    }

    // ── SYSTEM ──────────────────────────────────────────────────────
    case "system.heartbeat":
      patch.__heartbeatAt = Date.now();
      break;
  }

  return patch;
}

function patchJob(jobs: Job[], id: string | undefined, fn: (j: Job) => Job): Job[] {
  if (!id) return jobs;
  return jobs.map((j) => (j.id === id ? fn(j) : j));
}
function patchTask(tasks: Task[], id: string | undefined, fn: (t: Task) => Task): Task[] {
  if (!id) return tasks;
  return tasks.map((t) => (t.id === id ? fn(t) : t));
}
function dedupePush(events: WSEvent[], event: WSEvent): WSEvent[] {
  const key = `${event.eventType}|${event.timestamp ?? ""}|${event.jobId ?? ""}|${event.taskId ?? ""}`;
  const seen = new Set<string>();
  const next = [event, ...events].filter((e) => {
    const k = `${e.eventType}|${e.timestamp ?? ""}|${e.jobId ?? ""}|${e.taskId ?? ""}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  return next.slice(0, 500);
}

export { isTerminalJob };
