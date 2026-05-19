import type { WSEvent } from "@/types";

function snakeToCamelKey(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
}
function snakeToCamel<T = unknown>(value: unknown): T {
  if (Array.isArray(value)) return value.map((v) => snakeToCamel(v)) as T;
  if (value !== null && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[snakeToCamelKey(k)] = snakeToCamel(v);
    }
    return out as T;
  }
  return value as T;
}

export type WSChannelStatus =
  | "idle"        // not yet attempted
  | "connecting"  // socket opening
  | "live"        // socket open
  | "reconnecting" // dropped, backoff active
  | "polling"     // gave up reconnect, polling REST instead
  | "closed";     // closed intentionally

export interface ManagedChannelOptions {
  url: string;
  onEvent: (event: WSEvent) => void;
  onStatus: (status: WSChannelStatus) => void;
  /** Called when the manager promotes to polling fallback. */
  onPollingTick?: () => void;
  /** Max reconnect attempts before promoting to polling. */
  maxAttempts?: number;
}

/** A single managed WebSocket channel with exponential backoff + polling fallback. */
export class ManagedChannel {
  private ws: WebSocket | null = null;
  private attempt = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private closedByUser = false;
  private status: WSChannelStatus = "idle";

  constructor(private opts: ManagedChannelOptions) {}

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.closedByUser = false;
    this.stopPolling();
    this.setStatus(this.attempt === 0 ? "connecting" : "reconnecting");

    try {
      const ws = new WebSocket(this.opts.url);
      this.ws = ws;

      ws.onopen = () => {
        this.attempt = 0;
        this.setStatus("live");
      };
      ws.onmessage = (e) => {
        try {
          const raw = JSON.parse(e.data as string);
          const event = snakeToCamel<WSEvent>(raw);
          this.opts.onEvent(event);
        } catch {
          /* malformed payload — drop silently */
        }
      };
      ws.onerror = () => {
        // onclose follows
      };
      ws.onclose = () => {
        this.ws = null;
        if (this.closedByUser) {
          this.setStatus("closed");
          return;
        }
        this.scheduleReconnect();
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    const max = this.opts.maxAttempts ?? 5;
    if (this.attempt >= max) {
      this.beginPolling();
      return;
    }
    this.attempt += 1;
    // 1s, 2s, 4s, 8s, 16s — capped at 30s
    const delay = Math.min(30_000, 1000 * Math.pow(2, this.attempt - 1));
    this.setStatus("reconnecting");
    this.timer = setTimeout(() => {
      this.timer = null;
      this.connect();
    }, delay);
  }

  private beginPolling() {
    this.setStatus("polling");
    if (this.pollTimer) return;
    this.pollTimer = setInterval(() => {
      this.opts.onPollingTick?.();
      // Try to reconnect every poll tick — if the server comes back, we promote out of polling.
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        this.attempt = 0;
        this.connect();
      }
    }, 3000);
  }

  private stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  close() {
    this.closedByUser = true;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.stopPolling();
    if (this.ws) {
      try { this.ws.close(); } catch { /* noop */ }
      this.ws = null;
    }
    this.setStatus("closed");
  }

  getStatus(): WSChannelStatus { return this.status; }

  private setStatus(s: WSChannelStatus) {
    if (this.status === s) return;
    this.status = s;
    this.opts.onStatus(s);
  }
}
