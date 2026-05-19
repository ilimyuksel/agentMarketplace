import { Agent, AgentDetail, Job, Task, Bid, Transaction, JudgeEvaluation, WSEvent, SystemStats, Wallet, VerificationResult } from "@/types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api/v1";

function toCamelKey(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
}

function snakeToCamel<T = unknown>(value: unknown): T {
  if (Array.isArray(value)) return value.map((v) => snakeToCamel(v)) as T;
  if (value !== null && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[toCamelKey(k)] = snakeToCamel(v);
    }
    return out as T;
  }
  return value as T;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  const json = await res.json();
  if (!json.success) throw new Error(json.error?.message ?? "API error");
  return snakeToCamel<T>(json.data);
}

export const api = {
  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch((process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/health", {
        signal: AbortSignal.timeout(2000),
      });
      return res.ok;
    } catch {
      return false;
    }
  },

  async createJob(prompt: string, budget: number) {
    return apiFetch<{ jobId: string; state: string; websocketUrl: string; budgetTier: string }>("/jobs", {
      method: "POST",
      body: JSON.stringify({ user_id: "user_demo", prompt, budget }),
    });
  },

  async getJobs(): Promise<Job[]> {
    const data = await apiFetch<{ jobs: Job[]; count: number }>("/jobs");
    return data.jobs ?? [];
  },

  async getJob(id: string): Promise<Job> {
    return apiFetch<Job>(`/jobs/${id}`);
  },

  async getJobTasks(id: string): Promise<Task[]> {
    const data = await apiFetch<{ tasks: Task[]; count: number }>(`/jobs/${id}/tasks`);
    return data.tasks ?? [];
  },

  async getTaskBids(taskId: string): Promise<Bid[]> {
    const data = await apiFetch<{ bids: Bid[]; count: number }>(`/tasks/${taskId}/bids`);
    return data.bids ?? [];
  },

  async getTaskEvaluation(taskId: string): Promise<JudgeEvaluation> {
    return apiFetch<JudgeEvaluation>(`/tasks/${taskId}/evaluation`);
  },

  async getAgents(): Promise<Agent[]> {
    const data = await apiFetch<{ agents: Agent[]; count: number }>("/agents");
    return data.agents ?? [];
  },

  async getAgent(id: string): Promise<AgentDetail> {
    return apiFetch<AgentDetail>(`/agents/${id}?history_limit=50`);
  },

  async getWallets(): Promise<Wallet[]> {
    const data = await apiFetch<{ wallets: Wallet[]; count: number }>("/wallets");
    return data.wallets ?? [];
  },

  async getWallet(id: string): Promise<Wallet> {
    return apiFetch<Wallet>(`/wallets/${id}`);
  },

  async getLedger(): Promise<Transaction[]> {
    const data = await apiFetch<{ transactions: Transaction[]; count: number }>("/ledger/recent");
    return data.transactions ?? [];
  },

  async getStats(): Promise<SystemStats> {
    return apiFetch<SystemStats>("/stats");
  },

  async verifyChain(): Promise<VerificationResult> {
    return apiFetch<VerificationResult>("/ledger/verify", { method: "POST" });
  },

  /**
   * Probe the backend for admin / reset endpoints. The backend in this
   * project does not expose any — but we discover that at runtime rather
   * than assume, so the demo control can fall back gracefully if a future
   * backend version adds one.
   */
  async probeAdminAPI(): Promise<boolean> {
    const candidates = ["/admin/health", "/admin", "/system/reset"];
    for (const path of candidates) {
      try {
        const res = await fetch(`${API_BASE}${path}`, {
          method: "GET",
          signal: AbortSignal.timeout(800),
        });
        if (res.ok) return true;
      } catch { /* network / timeout — treat as missing */ }
    }
    return false;
  },

  async adminResetWallet(walletId: string, amount: number): Promise<void> {
    const res = await fetch(`${API_BASE}/admin/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: "wallet", wallet_id: walletId, amount }),
    });
    if (!res.ok) throw new Error(`admin reset failed: ${res.status}`);
  },

  async adminResetAll(): Promise<void> {
    const res = await fetch(`${API_BASE}/admin/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: "all" }),
    });
    if (!res.ok) throw new Error(`admin reset failed: ${res.status}`);
  },

  connectJobWS(jobId: string, onEvent: (event: WSEvent) => void): WebSocket {
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"}/ws/jobs/${jobId}`);
    ws.onmessage = (e) => {
      try { onEvent(snakeToCamel<WSEvent>(JSON.parse(e.data as string))); } catch { /* skip malformed */ }
    };
    return ws;
  },

  connectGlobalWS(onEvent: (event: WSEvent) => void): WebSocket {
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"}/ws/global`);
    ws.onmessage = (e) => {
      try { onEvent(snakeToCamel<WSEvent>(JSON.parse(e.data as string))); } catch { /* skip malformed */ }
    };
    return ws;
  },
};
