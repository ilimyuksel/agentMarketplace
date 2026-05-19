"use client";

import { useAppStore } from "@/lib/store";
import { VerifyChainHero } from "./VerifyChainHero";

export function LedgerHeader() {
  const transactions = useAppStore((s) => s.transactions);
  const jobs = useAppStore((s) => s.jobs);

  const blocks = transactions.length;
  const jobsCount = jobs.length;
  const genesis = transactions.find((t) => t.blockNumber === 0);

  return (
    <div className="border-b border-line bg-deep px-8 py-5 flex items-center justify-between gap-6 flex-wrap">
      <div className="space-y-1">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1
            className="text-base font-semibold tracking-tight text-text-primary"
            style={{ fontFamily: "var(--font-space-grotesk)" }}
          >
            Economic Ledger
          </h1>
          <span className="text-[11px] font-mono text-text-faint tabular-nums">
            <span className="text-text-primary">{blocks}</span> blocks
            <span className="text-text-faint"> · </span>
            <span className="text-text-primary">{jobsCount}</span> jobs
            <span className="text-text-faint"> · </span>
            v1.0
          </span>
        </div>
        <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-text-faint">
          hash-chained · SHA-256 · audit-ready
        </p>
        {genesis && (
          <p className="text-[10px] font-mono text-text-faint mt-0.5">
            genesis · #{genesis.blockNumber} · {genesis.blockHash.slice(0, 8)}…{genesis.blockHash.slice(-4)}
          </p>
        )}
      </div>

      <VerifyChainHero />
    </div>
  );
}
