"use client";

import { useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { useAppStore } from "@/lib/store";
import { BlockCard } from "./BlockCard";
import { useLedgerFilters } from "./LedgerFilters";

const RIPPLE_TOTAL_MS = 600;
const RIPPLE_PER_MS = 200;

export function BlockList() {
  const transactions = useAppStore(useShallow((s) => s.transactions));
  const filters = useLedgerFilters();
  const verificationStatus = useAppStore((s) => s.verificationStatus);
  const verificationResult = useAppStore((s) => s.verificationResult);

  const filtered = useMemo(() => {
    let txs = transactions;
    if (filters.job !== "all") txs = txs.filter((t) => t.jobId === filters.job);
    if (filters.type !== "all") txs = txs.filter((t) => t.transactionType === filters.type);
    if (filters.wallet !== "all") {
      txs = txs.filter((t) => t.fromWalletId === filters.wallet || t.toWalletId === filters.wallet);
    }
    // Newest first.
    return [...txs].sort((a, b) => b.blockNumber - a.blockNumber);
  }, [transactions, filters.job, filters.type, filters.wallet]);

  const rippleActive = verificationStatus === "verifying";
  const totalForRipple = filtered.length;
  // Spread the cascade across RIPPLE_TOTAL_MS regardless of block count.
  const spread = totalForRipple > 1
    ? Math.max(0, (RIPPLE_TOTAL_MS - RIPPLE_PER_MS) / 1000) / (totalForRipple - 1)
    : 0;

  const brokenBlock = verificationResult?.firstBadBlock ?? null;

  const onJumpToHash = (hash: string) => {
    const target = transactions.find((t) => t.blockHash === hash);
    if (!target) return;
    const el = document.getElementById(`block-${target.blockNumber}`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.animate(
      [
        { boxShadow: "0 0 0 0 rgba(34,211,238,0)" },
        { boxShadow: "0 0 0 6px rgba(34,211,238,0.30)" },
        { boxShadow: "0 0 0 0 rgba(34,211,238,0)" },
      ],
      { duration: 1200, easing: "ease-out" },
    );
  };

  if (filtered.length === 0) {
    return (
      <div className="px-8 py-12 text-center">
        <p className="text-[11px] uppercase tracking-[0.18em] text-text-faint font-mono">
          {transactions.length === 0 ? "no blocks yet" : "no blocks match the current filter"}
        </p>
        {transactions.length === 0 && (
          <p className="text-xs text-text-muted mt-2">
            submit a job to see the ledger build itself · genesis #0 already exists
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="px-8 py-6 space-y-2">
      {filtered.map((tx, i) => (
        <BlockCard
          key={tx.id}
          tx={tx}
          // Top-of-list (newest) flashes first → cascade walks toward genesis.
          rippleDelay={rippleActive ? i * spread : null}
          isBroken={brokenBlock != null && tx.blockNumber === brokenBlock}
          onJumpToHash={onJumpToHash}
        />
      ))}
    </div>
  );
}
