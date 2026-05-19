"use client";

import { Suspense, useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { TopBar } from "@/components/terminal/TopBar";
import { AgentRosterStrip } from "@/components/terminal/AgentRosterStrip";
import { EventTicker } from "@/components/terminal/EventTicker";
import { AppNav } from "@/components/layout/AppNav";
import { LedgerHeader } from "@/components/ledger/LedgerHeader";
import { LedgerFilters } from "@/components/ledger/LedgerFilters";
import { BlockList } from "@/components/ledger/BlockList";
import { VerificationResultPanel } from "@/components/ledger/VerificationResultPanel";

function LedgerPageInner() {
  const checkBackend = useAppStore((s) => s.checkBackend);
  const openGlobalWs = useAppStore((s) => s.openGlobalWs);
  const closeGlobalWs = useAppStore((s) => s.closeGlobalWs);
  const refetchLedger = useAppStore((s) => s.refetchLedger);
  const backendOnline = useAppStore((s) => s.backendOnline);
  const transactions = useAppStore((s) => s.transactions);

  useEffect(() => {
    checkBackend();
    openGlobalWs();
    return () => closeGlobalWs();
  }, [checkBackend, openGlobalWs, closeGlobalWs]);

  // Cold start: hydrate the ledger from REST if WS hasn't filled it yet.
  useEffect(() => {
    if (backendOnline && transactions.length === 0) {
      void refetchLedger();
    }
  }, [backendOnline, transactions.length, refetchLedger]);

  return (
    <div className="h-screen bg-deep text-text-primary flex flex-col overflow-hidden">
      <TopBar />
      <AppNav />
      <AgentRosterStrip />
      <main className="content-light flex-1 overflow-y-auto min-h-0">
        <LedgerHeader />
        <VerificationResultPanel />
        <LedgerFilters />
        <BlockList />
      </main>
      <EventTicker />
    </div>
  );
}

export default function LedgerPage() {
  return (
    <Suspense fallback={null}>
      <LedgerPageInner />
    </Suspense>
  );
}
