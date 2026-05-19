"use client";

import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { TopBar } from "@/components/terminal/TopBar";
import { AgentRosterStrip } from "@/components/terminal/AgentRosterStrip";
import { JobSubmitForm } from "@/components/terminal/JobSubmitForm";
import { WalletRail } from "@/components/terminal/WalletRail";
import { EventTicker } from "@/components/terminal/EventTicker";
import { RunningView } from "@/components/terminal/RunningView";
import { AppNav } from "@/components/layout/AppNav";

export default function TerminalPage() {
  const checkBackend = useAppStore((s) => s.checkBackend);
  const openGlobalWs = useAppStore((s) => s.openGlobalWs);
  const closeGlobalWs = useAppStore((s) => s.closeGlobalWs);
  const closeJobWs = useAppStore((s) => s.closeJobWs);
  const activeJobId = useAppStore((s) => s.activeJobId);

  useEffect(() => {
    checkBackend();
    openGlobalWs();
    return () => {
      closeJobWs();
      closeGlobalWs();
    };
  }, [checkBackend, openGlobalWs, closeGlobalWs, closeJobWs]);

  return (
    <div className="h-screen bg-deep text-text-primary flex flex-col overflow-hidden">
      <TopBar />
      <AppNav />
      <AgentRosterStrip />
      <main className="content-light flex-1 grid grid-cols-[62fr_38fr] overflow-hidden min-h-0">
        <section className="overflow-y-auto px-12 py-8 border-r border-line">
          {activeJobId ? (
            <RunningView jobId={activeJobId} />
          ) : (
            <div className="max-w-2xl mx-auto">
              <JobSubmitForm />
            </div>
          )}
        </section>
        <section className="overflow-hidden">
          <WalletRail />
        </section>
      </main>
      <EventTicker />
    </div>
  );
}
