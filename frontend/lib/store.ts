import { create } from "zustand";
import {
  Agent, AgentDetail, Wallet, Job, Task, Bid, Transaction, JudgeEvaluation, WSEvent, VerificationResult,
} from "@/types";
import { api } from "@/lib/api";
import { applyEvent, isTerminalJob } from "@/lib/wsReducer";
import { ManagedChannel, WSChannelStatus } from "@/lib/wsManager";

const BACKEND_HOST = "ws://localhost:8000";

interface AppState {
  agents: Agent[];
  agentDetails: Record<string, AgentDetail>;
  agentDetailsLoading: boolean;
  wallets: Wallet[];
  jobs: Job[];
  tasks: Task[];
  bids: Bid[];
  transactions: Transaction[];
  evaluations: JudgeEvaluation[];
  events: WSEvent[];
  activeJobId: string | null;
  selectedTaskId: string | null;
  isSubmitting: boolean;
  backendOnline: boolean;
  backendChecked: boolean;
  globalStatus: WSChannelStatus;
  jobStatus: WSChannelStatus;
  lastHeartbeatAt: number | null;
  verificationStatus: "idle" | "verifying" | "success" | "error";
  verificationResult: VerificationResult | null;
  verificationStartedAt: number | null;
  // Refs to managed channels (not directly readable by components).
  _globalCh?: ManagedChannel;
  _jobCh?: ManagedChannel;

  checkBackend: () => Promise<void>;
  submitJob: (prompt: string, budget: number) => Promise<void>;
  setActiveJobId: (id: string | null) => void;
  setSelectedTaskId: (id: string | null) => void;
  addEvent: (event: WSEvent) => void;
  openGlobalWs: () => void;
  closeGlobalWs: () => void;
  closeJobWs: () => void;
  refetchWallets: () => Promise<void>;
  refetchLedger: () => Promise<void>;
  fetchAgentDetails: () => Promise<void>;
  runVerification: () => Promise<void>;
  dismissVerificationResult: () => void;
  refreshAll: () => Promise<void>;
  resetJob: () => void;
}

// Cheap timestamp-based debounce for refetches triggered by event bursts.
const lastFetch = { wallets: 0, ledger: 0 };
const DEBOUNCE_MS = 400;

export const useAppStore = create<AppState>()((set, get) => ({
  agents: [],
  agentDetails: {},
  agentDetailsLoading: false,
  wallets: [],
  jobs: [],
  tasks: [],
  bids: [],
  transactions: [],
  evaluations: [],
  events: [],
  activeJobId: null,
  selectedTaskId: null,
  isSubmitting: false,
  backendOnline: false,
  backendChecked: false,
  globalStatus: "idle",
  jobStatus: "idle",
  lastHeartbeatAt: null,
  verificationStatus: "idle",
  verificationResult: null,
  verificationStartedAt: null,

  checkBackend: async () => {
    const online = await api.healthCheck();
    set({ backendOnline: online, backendChecked: true });
    if (!online) return;
    try {
      const [agents, wallets, jobs, transactions] = await Promise.all([
        api.getAgents(),
        api.getWallets(),
        api.getJobs(),
        api.getLedger(),
      ]);
      set({ agents, wallets, jobs, transactions });
    } catch (err) {
      console.error("Backend data load failed:", err);
      set({ backendOnline: false });
    }
  },

  submitJob: async (prompt, budget) => {
    if (!get().backendOnline) {
      console.warn("submitJob blocked — backend offline");
      return;
    }
    set({ isSubmitting: true });
    try {
      // Close any previous per-job channel before opening a new one.
      get().closeJobWs();
      const result = await api.createJob(prompt, budget);
      const jobId = result.jobId;
      set({ activeJobId: jobId, selectedTaskId: null });
      openJobWs(jobId, set, get);
    } catch (err) {
      console.error("submitJob failed:", err);
    } finally {
      set({ isSubmitting: false });
    }
  },

  setActiveJobId: (id) => set({ activeJobId: id }),
  setSelectedTaskId: (id) => set({ selectedTaskId: id }),

  addEvent: (event) =>
    set((s) => ({ events: [event, ...s.events].slice(0, 500) })),

  openGlobalWs: () => {
    if (get()._globalCh) return;
    const ch = new ManagedChannel({
      url: `${BACKEND_HOST}/ws/global`,
      onEvent: (event) => handleEvent(event, set, get),
      onStatus: (s) => set({ globalStatus: s }),
      onPollingTick: () => {
        // Re-hydrate snapshot data while WS is down.
        get().refetchWallets();
        get().refetchLedger();
      },
    });
    set({ _globalCh: ch });
    ch.connect();
  },

  closeGlobalWs: () => {
    const ch = get()._globalCh;
    if (!ch) return;
    ch.close();
    set({ _globalCh: undefined, globalStatus: "closed" });
  },

  closeJobWs: () => {
    const ch = get()._jobCh;
    if (!ch) return;
    ch.close();
    set({ _jobCh: undefined, jobStatus: "closed" });
  },

  refetchWallets: async () => {
    const now = Date.now();
    if (now - lastFetch.wallets < DEBOUNCE_MS) return;
    lastFetch.wallets = now;
    try {
      const wallets = await api.getWallets();
      set({ wallets });
    } catch { /* tolerate transient */ }
  },

  refetchLedger: async () => {
    const now = Date.now();
    if (now - lastFetch.ledger < DEBOUNCE_MS) return;
    lastFetch.ledger = now;
    try {
      const transactions = await api.getLedger();
      set({ transactions });
    } catch { /* tolerate transient */ }
  },

  resetJob: () => {
    get().closeJobWs();
    set({ activeJobId: null, selectedTaskId: null });
  },

  runVerification: async () => {
    const cur = get().verificationStatus;
    if (cur === "verifying") return; // ignore re-entry
    set({
      verificationStatus: "verifying",
      verificationResult: null,
      verificationStartedAt: Date.now(),
    });
    // Hold the verifying state at least 700ms so the ripple animation
    // (~600ms) lands visibly even if the backend returns in 3ms.
    const minHold = new Promise<void>((r) => setTimeout(r, 700));
    try {
      const [result] = await Promise.all([api.verifyChain(), minHold]);
      set({
        verificationStatus: result.isValid ? "success" : "error",
        verificationResult: result,
      });
      if (result.isValid) {
        // Auto-revert idle state after 4s; keep the result panel visible
        // until dismiss or next verify.
        window.setTimeout(() => {
          if (get().verificationStatus === "success") {
            set({ verificationStatus: "idle" });
          }
        }, 4000);
      }
    } catch (err) {
      console.error("verifyChain failed:", err);
      set({
        verificationStatus: "error",
        verificationResult: { isValid: false, blocksVerified: 0, firstBadBlock: null, durationMs: 0 },
      });
    }
  },

  dismissVerificationResult: () =>
    set({ verificationStatus: "idle", verificationResult: null }),

  refreshAll: async () => {
    // Single button the presenter can use after running the reset script
    // in their terminal — re-hydrates every snapshot from the backend and
    // clears any client-side job state pinned from a prior run.
    get().closeJobWs();
    set({ activeJobId: null, selectedTaskId: null });
    await get().checkBackend();
    if (get().backendOnline) {
      await get().fetchAgentDetails();
    }
  },

  fetchAgentDetails: async () => {
    const ids = get().agents.map((a) => a.id);
    if (ids.length === 0) {
      console.warn("fetchAgentDetails called before agents hydrated");
      return;
    }
    set({ agentDetailsLoading: true });
    try {
      const results = await Promise.all(
        ids.map((id) =>
          api.getAgent(id).then((d) => [id, d] as const).catch((err) => {
            console.error("getAgent failed", id, err);
            return null;
          })
        )
      );
      const next: Record<string, AgentDetail> = { ...get().agentDetails };
      for (const r of results) {
        if (r) next[r[0]] = r[1];
      }
      set({ agentDetails: next });
    } finally {
      set({ agentDetailsLoading: false });
    }
  },
}));

function openJobWs(
  jobId: string,
  set: (p: Partial<AppState>) => void,
  get: () => AppState,
) {
  const ch = new ManagedChannel({
    url: `${BACKEND_HOST}/ws/jobs/${jobId}`,
    onEvent: (event) => handleEvent(event, set, get),
    onStatus: (s) => set({ jobStatus: s }),
    onPollingTick: () => {
      // While WS is down, poll job snapshot.
      void api.getJob(jobId).catch(() => {});
    },
  });
  set({ _jobCh: ch });
  ch.connect();
}

function handleEvent(
  event: WSEvent,
  set: (p: Partial<AppState>) => void,
  get: () => AppState,
) {
  const state = get();
  const patch = applyEvent(state, event);

  // Pull out side-effect flags before merging.
  const refetchWallets = patch.__refetchWallets;
  const refetchLedger = patch.__refetchLedger;
  const heartbeatAt = patch.__heartbeatAt;
  delete patch.__refetchWallets;
  delete patch.__refetchLedger;
  delete patch.__heartbeatAt;

  set(patch as Partial<AppState>);
  if (heartbeatAt) set({ lastHeartbeatAt: heartbeatAt });
  if (refetchWallets) void get().refetchWallets();
  if (refetchLedger) void get().refetchLedger();

  // If the active job just hit a terminal state, close the per-job channel
  // so the connection count stays clean. The job stays in jobs[] for the
  // post-mortem / reconciliation view.
  const activeId = state.activeJobId;
  if (activeId && (patch.jobs)) {
    const updated = (patch.jobs as Job[]).find((j) => j.id === activeId);
    if (updated && isTerminalJob(updated.state)) {
      // Defer close so the final event finishes propagating to subscribers.
      window.setTimeout(() => {
        const ch = get()._jobCh;
        if (ch) {
          ch.close();
          set({ _jobCh: undefined, jobStatus: "closed" });
        }
      }, 100);
    }
  }
}
