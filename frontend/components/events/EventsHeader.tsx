"use client";

import { useEffect, useMemo, useState } from "react";
import { Pause, Play, Trash2 } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { useAppStore } from "@/lib/store";
import { categoryFor } from "@/lib/events";

interface Props {
  autoScroll: boolean;
  onToggleAutoScroll: () => void;
  onClear: () => void;
  cleared: boolean;
  sinceMark: string | null;
}

export function EventsHeader({ autoScroll, onToggleAutoScroll, onClear, sinceMark }: Props) {
  const events = useAppStore(useShallow((s) => s.events));
  const globalStatus = useAppStore((s) => s.globalStatus);
  const backendOnline = useAppStore((s) => s.backendOnline);
  const [, force] = useState(0);

  // Tick once a second so the burst-rate window stays accurate.
  useEffect(() => {
    const id = window.setInterval(() => force((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  const visible = sinceMark
    ? events.filter((e) => (e.timestamp ?? "") > sinceMark)
    : events;

  const categoriesWithActivity = useMemo(() => {
    const set = new Set<string>();
    for (const e of visible) {
      const cat = categoryFor(e.eventType);
      if (cat !== "OTHER") set.add(cat);
    }
    return set.size;
  }, [visible]);

  const burstWindow = 10_000;
  const now = Date.now();
  const recent = useMemo(
    () =>
      visible.filter((e) => {
        try {
          return new Date(e.timestamp ?? 0).getTime() > now - burstWindow;
        } catch {
          return false;
        }
      }).length,
    [visible, now],
  );

  const liveTone =
    globalStatus === "live" && backendOnline
      ? { dot: "bg-active", label: "live", textCls: "text-active" }
      : globalStatus === "reconnecting" || globalStatus === "connecting"
      ? { dot: "bg-pending", label: globalStatus, textCls: "text-pending" }
      : globalStatus === "polling"
      ? { dot: "bg-danger", label: "polling fallback", textCls: "text-danger" }
      : backendOnline
      ? { dot: "bg-active", label: "live", textCls: "text-active" }
      : { dot: "bg-danger", label: "offline", textCls: "text-danger" };

  return (
    <div className="border-b border-line bg-deep px-8 py-4 flex items-center justify-between gap-4 flex-wrap">
      <div>
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1
            className="text-base font-semibold tracking-tight text-text-primary"
            style={{ fontFamily: "var(--font-space-grotesk)" }}
          >
            Event Stream
          </h1>
          <span className="text-[11px] font-mono text-text-faint tabular-nums">
            <span className="text-text-primary">{visible.length}</span> events
            <span className="text-text-faint"> · </span>
            <span className="text-text-primary">{categoriesWithActivity}</span> categories active
          </span>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono">
            <span className={`relative w-2 h-2 rounded-full ${liveTone.dot}`}>
              {liveTone.label === "live" && (
                <span className={`absolute inset-0 rounded-full ${liveTone.dot} animate-ping opacity-60`} />
              )}
            </span>
            <span className={liveTone.textCls}>{liveTone.label}</span>
          </span>
        </div>
        <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-text-faint mt-1">
          wired to /ws/global · auto-reconnect on disconnect · {recent} events in last 10s
        </p>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleAutoScroll}
          className={`inline-flex items-center gap-1.5 h-8 px-3 rounded border text-[10px] font-mono uppercase tracking-[0.14em] transition-colors ${
            autoScroll
              ? "border-active/40 bg-active/10 text-active"
              : "border-line bg-sunken text-text-muted hover:text-text-primary"
          }`}
        >
          {autoScroll ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
          auto-scroll {autoScroll ? "on" : "off"}
        </button>
        <button
          type="button"
          onClick={onClear}
          className="inline-flex items-center gap-1.5 h-8 px-3 rounded border border-line bg-sunken text-text-muted hover:text-danger hover:border-danger/40 text-[10px] font-mono uppercase tracking-[0.14em] transition-colors"
        >
          <Trash2 className="w-3 h-3" />
          clear
        </button>
      </div>
    </div>
  );
}
