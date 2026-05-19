export type AgentTier = "T1" | "T2" | "JUDGE";

export type BiddingStyle = "aggressive" | "analytical" | "premium" | "volume" | "underdog" | "none";

export type AgentStatus = "active" | "idle" | "error" | "running";

export interface Agent {
  id: string;
  displayName: string;
  tier: AgentTier;
  role: string;
  skillKeywords: string;
  basePrice: number | null;
  minAcceptance: number;
  biddingStyle: BiddingStyle;
  reputation: number;
  successRate: number;
  completedJobs: number;
  walletId: string;
  walletBalance?: number;
  canHireSubagents: boolean;
  isGhost: boolean;
  isActive: boolean;
}

export interface ReputationHistoryEntry {
  id: number;
  agentId: string;
  jobId: string | null;
  taskId: string | null;
  oldReputation: number | null;
  newReputation: number | null;
  delta: number | null;
  reason: string | null;
  judgeScore: number | null;
  createdAt: string;
}

export interface AgentDetail extends Agent {
  pricingConfig: Record<string, unknown>;
  reputationHistory: ReputationHistoryEntry[];
}

export type WalletOwnerType = "USER" | "ESCROW" | "AGENT" | "SYSTEM";

export interface Wallet {
  id: string;
  ownerType: WalletOwnerType;
  ownerId: string | null;
  balance: number;
  currency: string;
}

export type JobState =
  | "CREATED"
  | "ESCROW_LOCK"
  | "MANAGER_BIDDING"
  | "PLANNING"
  | "EXECUTING"
  | "COMPLETED"
  | "REJECTED"
  | "FAILED"
  | "CANCELLED";

export type TaskState =
  | "PENDING"
  | "READY"
  | "BIDDING"
  | "ASSIGNED"
  | "RUNNING"
  | "DONE"
  | "VERIFYING"
  | "VERIFIED"
  | "PAID"
  | "REVISION"
  | "REJECTED"
  | "FAILED";

export type BudgetTier = "REJECTED" | "MINIMAL" | "STANDARD" | "PREMIUM";

export interface Job {
  id: string;
  userId: string;
  userPrompt: string;
  budget: number;
  budgetTier: BudgetTier | null;
  escrowWalletId: string | null;
  assignedManagerId: string | null;
  managerBidAmount: number | null;
  managerProfitMargin: number | null;
  state: JobState;
  finalOutputId: string | null;
  createdAt: string;
  completedAt: string | null;
  failureReason: string | null;
}

export interface Task {
  id: string;
  jobId: string;
  title: string;
  description: string;
  requiredSkills: string[];
  budget: number;
  finalCost: number | null;
  state: TaskState;
  dependencies: string[];
  assignedAgentId: string | null;
  judgeScore: number | null;
  judgeVerdict: string | null;
  judgeFeedback: string | null;
  revisionCount: number;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
}

export interface Bid {
  id: string;
  taskId: string;
  agentId: string;
  bidAmount: number;
  reasoning: string | null;
  confidence: number | null;
  estimatedTimeSeconds: number | null;
  scopeAssumption: string | null;
  isWinner: boolean;
  selectionScore: number | null;
  submittedAt: string;
}

export interface JudgeEvaluation {
  id: string;
  taskId: string;
  evaluatedAgentId: string;
  scopeCompleteness: number | null;
  structuralQuality: number | null;
  contentQuality: number | null;
  briefFidelity: number | null;
  finalScore: number;
  decision: "APPROVED" | "REVISION_REQUESTED" | "REJECTED";
  reasoning: string | null;
  feedbackForRevision: string | null;
  confidenceInJudgment: number | null;
  createdAt: string;
}

export type TransactionType =
  | "ESCROW_LOCK"
  | "MANAGER_FUNDING"
  | "MILESTONE_RELEASE"
  | "JUDGE_FEE"
  | "PM_PROFIT"
  | "AGENT_PAYMENT"
  | "REFUND"
  | "GENESIS";

export interface Transaction {
  id: string;
  jobId: string | null;
  taskId: string | null;
  fromWalletId: string;
  toWalletId: string;
  amount: number;
  transactionType: TransactionType;
  milestone: "START" | "MID" | "COMPLETION" | null;
  description: string | null;
  blockNumber: number;
  blockHash: string;
  previousBlockHash: string;
  createdAt: string;
}

export interface WSEvent {
  eventType: string;
  timestamp: string;
  jobId: string | null;
  taskId: string | null;
  payload: Record<string, unknown>;
}

export interface PipelineLog {
  timestamp: string;
  message: string;
  type: "info" | "success" | "error" | "transfer";
}

export interface SystemStats {
  totalJobs: number;
  completedJobs: number;
  activeJobs: number;
  totalAgents: number;
  activeAgents: number;
  totalLedgerVolume: number;
  totalBlocks: number;
}

export interface VerificationResult {
  isValid: boolean;
  blocksVerified: number;
  firstBadBlock: number | null;
  durationMs: number;
}
