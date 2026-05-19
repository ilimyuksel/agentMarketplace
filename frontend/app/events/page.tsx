"use client";

import { Suspense, useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { TopBar } from "@/components/terminal/TopBar";
import { AgentRosterStrip } from "@/components/terminal/AgentRosterStrip";
import { AppNav } from "@/components/layout/AppNav";
import { EventsHeader } from "@/components/events/EventsHeader";
import { EventCategoryFilter } from "@/components/events/EventCategoryFilter";
import { EventTable } from "@/components/events/EventTable";

function EventsPageInner() {
  const checkBackend = useAppStore((s) => s.checkBackend);
  const openGlobalWs = useAppStore((s) => s.openGlobalWs);
  const closeGlobalWs = useAppStore((s) => s.closeGlobalWs);

  useEffect(() => {
    checkBackend();
    openGlobalWs();
    return () => closeGlobalWs();
  }, [checkBackend, openGlobalWs, closeGlobalWs]);

  const [autoScroll, setAutoScroll] = useState(true);
  // Local "since" cutoff — clear hides events received before this point
  // without touching the store (so other pages still see them).
  const [sinceMark, setSinceMark] = useState<string | null>(null);
  const [cleared, setCleared] = useState(false);

  const onClear = () => {
    setSinceMark(new Date().toISOString());
    setCleared(true);
  };

  return (
    <div className="h-screen bg-deep text-text-primary flex flex-col overflow-hidden">
      <TopBar />
      <AppNav />
      <AgentRosterStrip />
      <div className="content-light flex-1 flex flex-col overflow-hidden min-h-0">
        <EventsHeader
          autoScroll={autoScroll}
          onToggleAutoScroll={() => setAutoScroll((v) => !v)}
          onClear={onClear}
          cleared={cleared}
          sinceMark={sinceMark}
        />
        <EventCategoryFilter />
        <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <EventTable
            autoScroll={autoScroll}
            cleared={cleared}
            clearMark={sinceMark ? new Date(sinceMark).getTime() : 0}
            sinceMark={sinceMark}
          />
        </main>
      </div>
    </div>
  );
}

export default function EventsPage() {
  return (
    <Suspense fallback={null}>
      <EventsPageInner />
    </Suspense>
  );
}
