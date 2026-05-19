"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronUp } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { useAppStore } from "@/lib/store";
import { categoryFor, ALL_CATEGORIES, type EventCategory } from "@/lib/events";
import { EventRow } from "./EventRow";
import { useEventCategoryFilter } from "./EventCategoryFilter";

interface Props {
  autoScroll: boolean;
  cleared: boolean;
  clearMark: number; // when this changes, hide events present before that mark
  /** Local "since" timestamp — events older than this are filtered out. */
  sinceMark: string | null;
}

const MAX_ROWS = 500;

export function EventTable({ autoScroll, cleared, sinceMark }: Props) {
  const events = useAppStore(useShallow((s) => s.events));
  const filter = useEventCategoryFilter();
  const containerRef = useRef<HTMLDivElement>(null);
  const [bufferedCount, setBufferedCount] = useState(0);
  const prevTopIdRef = useRef<string | null>(null);

  // Effective rows: respect filter + "clear" cutoff.
  const filtered = useMemo(() => {
    let rows = events;
    if (sinceMark) rows = rows.filter((e) => (e.timestamp ?? "") > sinceMark);
    if (filter !== "ALL") rows = rows.filter((e) => categoryFor(e.eventType) === (filter as EventCategory));
    return rows.slice(0, MAX_ROWS);
  }, [events, sinceMark, filter]);

  const totalAvailable = useMemo(() => {
    let rows = events;
    if (sinceMark) rows = rows.filter((e) => (e.timestamp ?? "") > sinceMark);
    return rows.length;
  }, [events, sinceMark]);

  // Auto-scroll behaviour. When ON, snap to top on new events.
  // When OFF, freeze and count new events that arrived since last scroll.
  useEffect(() => {
    const topId = filtered[0]
      ? `${filtered[0].eventType}|${filtered[0].timestamp ?? ""}`
      : null;
    if (topId !== prevTopIdRef.current) {
      if (autoScroll) {
        containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
        setBufferedCount(0);
      } else if (prevTopIdRef.current !== null) {
        setBufferedCount((n) => n + 1);
      }
      prevTopIdRef.current = topId;
    }
  }, [filtered, autoScroll]);

  // When auto-scroll flips back ON, snap to top + clear buffer counter.
  useEffect(() => {
    if (autoScroll) {
      containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      setBufferedCount(0);
    }
  }, [autoScroll]);

  const onJumpToTop = () => {
    containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    setBufferedCount(0);
  };

  if (filtered.length === 0) {
    return (
      <div className="px-8 py-12 text-center">
        <p className="text-[11px] uppercase tracking-[0.18em] text-text-faint font-mono">
          {cleared || sinceMark
            ? "cleared · waiting for the next event"
            : filter === "ALL"
            ? "no events yet · submit a job to see the stream populate"
            : `no ${filter.toLowerCase()} events yet`}
        </p>
      </div>
    );
  }

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={containerRef}
        className="absolute inset-0 overflow-y-auto"
      >
        <div className="border border-line bg-surface/40 mx-8 my-4 rounded-md divide-y divide-line/60">
          {filtered.map((e, i) => (
            <EventRow
              key={`${e.eventType}|${e.timestamp ?? ""}|${e.jobId ?? ""}|${e.taskId ?? ""}|${i}`}
              event={e}
            />
          ))}
        </div>
        {totalAvailable > MAX_ROWS && (
          <p className="text-center text-[10px] font-mono text-text-faint pb-4">
            showing newest {MAX_ROWS} of {totalAvailable} buffered
          </p>
        )}
      </div>

      {!autoScroll && bufferedCount > 0 && (
        <button
          type="button"
          onClick={onJumpToTop}
          className="absolute left-1/2 -translate-x-1/2 top-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-active/40 bg-deep text-active text-[11px] font-mono uppercase tracking-[0.16em] shadow-lg hover:bg-active/10 transition-colors z-10"
        >
          <ChevronUp className="w-3.5 h-3.5" />
          {bufferedCount} new
        </button>
      )}
    </div>
  );
}
