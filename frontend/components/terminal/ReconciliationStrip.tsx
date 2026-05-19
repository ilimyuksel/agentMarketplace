"use client";

import { useMemo } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { CheckCircle2, AlertTriangle, ExternalLink } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { useAppStore } from "@/lib/store";
import { AddressChip } from "@/components/primitives/AddressChip";
import { reconcile, type Reconciliation } from "@/lib/reconciliation";

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

interface RowProps {
  label: string;
  amount: number;
  walletId?: string | null;
  annotation?: string;
  prefix?: string;
  bold?: boolean;
  delayIdx: number;
}

function Row({ label, amount, walletId, annotation, prefix = "→", bold, delayIdx }: RowProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: delayIdx * 0.08, ease: "easeOut" }}
      className="grid grid-cols-[1fr_140px_180px] items-baseline gap-3 py-1"
    >
      <div>
        <span className={`text-[12px] font-mono ${bold ? "text-text-primary" : "text-text-muted"}`}>
          <span className="text-text-faint">{prefix}</span> {label}
        </span>
        {annotation && (
          <span className="ml-2 text-[10px] font-mono text-text-faint">{annotation}</span>
        )}
      </div>
      <span
        className={`text-right font-mono tabular-nums ${bold ? "text-text-primary text-sm" : "text-text-primary text-[12px]"}`}
        style={{ fontFamily: "var(--font-jetbrains)" }}
      >
        {money(amount)}
      </span>
      <div className="text-right">
        {walletId && <AddressChip walletId={walletId} tone="agent" size="sm" />}
      </div>
    </motion.div>
  );
}

interface Props {
  jobId: string;
}

export function ReconciliationStrip({ jobId }: Props) {
  const transactions = useAppStore(useShallow((s) => s.transactions));
  const agents = useAppStore(useShallow((s) => s.agents));

  const rec: Reconciliation = useMemo(
    () => reconcile(jobId, transactions, agents),
    [jobId, transactions, agents],
  );

  // Order rows by milestone payment order — newest sub-agents first by total
  // is already sorted in the recon math. We also place PM margin first under
  // ESCROW, then sub-agents, then judge, then refund, then TOTAL.
  const balanced = rec.balanced;
  const borderTone = balanced ? "border-success/40 bg-success/5" : "border-danger/40 bg-danger/5";
  const TotalIcon = balanced ? CheckCircle2 : AlertTriangle;
  const totalCls = balanced ? "text-success" : "text-danger";

  // Step ordering for the stagger.
  let delay = 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={`rounded-md border-2 ${borderTone} px-6 py-5 font-mono`}
    >
      <div className="flex items-baseline justify-between mb-3">
        <p className="text-[10px] uppercase tracking-[0.18em] text-text-faint">
          Reconciliation
          <span className="ml-2 text-text-muted">· job {jobId.slice(-12)}</span>
          <span className="ml-2 text-text-muted">
            · {money(rec.escrow)} settled
          </span>
        </p>
        <Link
          href={`/ledger?job=${jobId}`}
          className="inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.16em] text-active hover:text-active/80 transition-colors"
        >
          view on ledger
          <ExternalLink className="w-3 h-3" />
        </Link>
      </div>

      <div className="space-y-0.5">
        {/* ESCROW header row */}
        <Row
          label="ESCROW"
          amount={rec.escrow}
          annotation="locked at t=0"
          prefix=""
          bold
          delayIdx={delay++}
        />
        <div className="border-t border-line/60 my-1" />

        {/* PM margin */}
        {rec.pmWalletId && (
          <Row
            label="PM (margin)"
            amount={rec.pmMargin}
            walletId={rec.pmWalletId}
            annotation={rec.subAgents.length > 0 ? "↳ sub-agents distributed below" : undefined}
            delayIdx={delay++}
          />
        )}

        {/* Sub-agents */}
        {rec.subAgents.map((s) => {
          const breakdown = s.breakdown
            .map((b) => `${b.milestone[0]}:${money(b.amount)}`)
            .join(" + ");
          return (
            <Row
              key={s.walletId}
              label={s.agentId}
              amount={s.total}
              walletId={s.walletId}
              annotation={s.breakdown.length > 1 ? `(${breakdown})` : undefined}
              delayIdx={delay++}
            />
          );
        })}

        {/* Judge fees */}
        {rec.judgeFees.count > 0 && (
          <Row
            label="Judge"
            amount={rec.judgeFees.total}
            walletId={rec.judgeFees.walletId ?? undefined}
            annotation={`(${rec.judgeFees.count} × $2.00)`}
            delayIdx={delay++}
          />
        )}

        {/* Refund */}
        {rec.refund > 0 && (
          <Row
            label="Refund"
            amount={rec.refund}
            walletId="wallet_user_demo"
            annotation="unfunded margin returned"
            delayIdx={delay++}
          />
        )}

        {/* TOTAL footer */}
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: delay * 0.08 + 0.1, ease: "easeOut" }}
          className="grid grid-cols-[1fr_140px_180px] items-baseline gap-3 pt-1.5 mt-1 border-t-2 border-success/60"
        >
          <span className={`text-[11px] font-mono uppercase tracking-[0.16em] ${totalCls}`}>
            Total
          </span>
          <span
            className={`text-right font-mono tabular-nums text-base ${totalCls}`}
            style={{ fontFamily: "var(--font-jetbrains)" }}
          >
            {money(rec.computedTotal)}
          </span>
          <div className="text-right flex items-center justify-end gap-2">
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: [0, 1.2, 1] }}
              transition={{ duration: 0.6, delay: delay * 0.08 + 0.4, ease: [0.22, 1, 0.36, 1] }}
              className={`inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-[0.16em] ${totalCls}`}
            >
              <TotalIcon className="w-3.5 h-3.5" />
              {balanced
                ? "conserved"
                : `${rec.delta > 0 ? "+" : ""}${money(rec.delta)} unaccounted`}
            </motion.span>
          </div>
        </motion.div>
      </div>

      <p className="text-[10px] font-mono text-text-faint mt-3 pt-3 border-t border-line/60">
        each row links to its on-chain block · math: pmMargin + Σ sub-agents + judge fees + refund ≡ escrow
      </p>
    </motion.div>
  );
}
