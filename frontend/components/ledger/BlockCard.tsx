"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ArrowUp, Hash, AlertTriangle } from "lucide-react";
import { StateBadge } from "@/components/primitives/StateBadge";
import { AddressChip } from "@/components/primitives/AddressChip";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";
import { HashLink } from "@/components/primitives/HashLink";
import type { Transaction } from "@/types";

interface Props {
  tx: Transaction;
  rippleDelay?: number | null; // seconds — when set, the card flashes
  isBroken?: boolean;          // first_bad_block match
  onJumpToHash: (hash: string) => void;
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour12: false }) + "." +
      String(d.getMilliseconds()).padStart(3, "0");
  } catch { return "—"; }
}

function walletTone(walletId: string): "user" | "escrow" | "agent" | "system" | "genesis" {
  if (walletId === "GENESIS") return "genesis";
  if (walletId.startsWith("wallet_user_")) return "user";
  if (walletId.startsWith("wallet_escrow_")) return "escrow";
  if (walletId.startsWith("wallet_system_")) return "system";
  return "agent";
}

export function BlockCard({ tx, rippleDelay, isBroken, onJumpToHash }: Props) {
  const [expanded, setExpanded] = useState(false);
  const isGenesis = tx.transactionType === "GENESIS";

  // Border tone — broken trumps genesis trumps default.
  const baseBorder = isBroken
    ? "border-danger/60 ring-1 ring-danger/40"
    : isGenesis
    ? "border-success/40"
    : "border-line";

  return (
    <motion.div
      id={`block-${tx.blockNumber}`}
      className={`rounded-md border ${baseBorder} bg-surface transition-colors scroll-mt-[200px]`}
      animate={
        rippleDelay != null
          ? {
              borderColor: ["var(--line)", "var(--active)", "var(--line)"],
              backgroundColor: ["rgba(17,23,40,1)", "rgba(34,211,238,0.07)", "rgba(17,23,40,1)"],
            }
          : {}
      }
      transition={rippleDelay != null ? { duration: 0.22, delay: rippleDelay, ease: "easeInOut" } : {}}
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 space-y-2"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-[10px] font-mono text-text-faint">
              tx
            </span>
            <span className="text-[11px] font-mono text-text-muted truncate">
              {tx.id.length > 18 ? `${tx.id.slice(0, 8)}…${tx.id.slice(-6)}` : tx.id}
            </span>
            <StateBadge state={tx.transactionType} size="sm" />
            {isBroken && (
              <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-[0.16em] text-danger">
                <AlertTriangle className="w-3 h-3" /> tampered
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-[10px] font-mono text-text-faint tabular-nums">
              {fmtTime(tx.createdAt)}
            </span>
            <span className="text-[11px] font-mono text-text-primary tabular-nums">
              #{tx.blockNumber}
            </span>
            <ChevronDown className={`w-3 h-3 text-text-faint transition-transform ${expanded ? "rotate-180" : ""}`} />
          </div>
        </div>

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <div className="min-w-0">
            <AddressChip walletId={tx.fromWalletId} tone={walletTone(tx.fromWalletId)} size="sm" />
          </div>
          <span className="text-text-faint">→</span>
          <div className="min-w-0">
            <AddressChip walletId={tx.toWalletId} tone={walletTone(tx.toWalletId)} size="sm" />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <MoneyTicker value={tx.amount} size="lg" highlightOnChange={false} />
          <div className="flex items-center gap-3 text-[10px] font-mono">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onJumpToHash(tx.previousBlockHash); }}
              className="inline-flex items-center gap-1 text-text-faint hover:text-active transition-colors"
            >
              <ArrowUp className="w-3 h-3" />
              prev
              <HashLinkInline hash={tx.previousBlockHash} />
            </button>
            <span className="inline-flex items-center gap-1 text-text-muted">
              <Hash className="w-3 h-3" />
              <HashLinkInline hash={tx.blockHash} />
            </span>
          </div>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-line"
          >
            <div className="px-4 py-3 space-y-2 bg-sunken/40 text-[11px] font-mono">
              <Detail label="tx id">{tx.id}</Detail>
              <Detail label="from wallet">{tx.fromWalletId}</Detail>
              <Detail label="to wallet">{tx.toWalletId}</Detail>
              <Detail label="block hash">
                <HashLink hash={tx.blockHash} />
              </Detail>
              <Detail label="previous">
                <HashLink hash={tx.previousBlockHash} />
              </Detail>
              {tx.milestone && <Detail label="milestone">{tx.milestone}</Detail>}
              {tx.jobId && <Detail label="job">{tx.jobId}</Detail>}
              {tx.taskId && <Detail label="task">{tx.taskId}</Detail>}
              {tx.description && <Detail label="description">{tx.description}</Detail>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3">
      <span className="text-text-faint uppercase tracking-wider">{label}</span>
      <span className="text-text-muted break-all">{children}</span>
    </div>
  );
}

function HashLinkInline({ hash }: { hash: string }) {
  // Compact display, no copy icon (BlockCard's "view details" expansion has the
  // full HashLink with copy). Keeping inline strip lean and scannable.
  return (
    <span className="font-mono">
      {hash.slice(0, 6)}…{hash.slice(-4)}
    </span>
  );
}
