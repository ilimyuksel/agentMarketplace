"use client";

import { CheckCircle2, AlertTriangle, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useAppStore } from "@/lib/store";

export function VerificationResultPanel() {
  const status = useAppStore((s) => s.verificationStatus);
  const result = useAppStore((s) => s.verificationResult);
  const dismiss = useAppStore((s) => s.dismissVerificationResult);
  const transactions = useAppStore((s) => s.transactions);

  const visible = result != null && (status === "success" || status === "error");
  const genesisHash = transactions.find((t) => t.blockNumber === 0)?.blockHash ?? null;

  return (
    <AnimatePresence>
      {visible && result && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="overflow-hidden"
        >
          <div
            className={`mx-8 mt-4 rounded-md border-2 px-5 py-4 ${
              result.isValid
                ? "border-success/60 bg-success/5"
                : "border-danger/60 bg-danger/5"
            }`}
          >
            <div className="flex items-start gap-3">
              {result.isValid ? (
                <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-danger flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1 min-w-0">
                <p className={`text-[10px] uppercase tracking-[0.18em] font-mono ${result.isValid ? "text-success" : "text-danger"}`}>
                  {result.isValid ? "Chain Integrity Verified" : "Chain Tampered"}
                </p>
                <p className="text-sm font-mono text-text-primary mt-1 tabular-nums">
                  {result.isValid ? (
                    <>
                      {result.blocksVerified} block{result.blocksVerified === 1 ? "" : "s"}
                      <span className="text-text-faint"> · </span>
                      checked in {result.durationMs}ms
                      {genesisHash && (
                        <>
                          <span className="text-text-faint"> · </span>
                          genesis {genesisHash.slice(0, 8)}…{genesisHash.slice(-4)}
                        </>
                      )}
                    </>
                  ) : (
                    <>
                      first bad block: <span className="text-danger">#{result.firstBadBlock ?? "?"}</span>
                      <span className="text-text-faint"> · </span>
                      verification halted
                    </>
                  )}
                </p>
                <p className="text-[11px] text-text-faint mt-1.5 leading-relaxed">
                  {result.isValid
                    ? "All block hashes match · linkage intact · no tampering detected. SHA-256 hash chain in Postgres — same trust property as a blockchain at 100× lower complexity."
                    : "A stored block hash does not match the recomputed hash. Any later block whose previous_block_hash points at this one is also invalid. Resolve the source row before continuing."}
                </p>
              </div>
              <button
                type="button"
                onClick={dismiss}
                className="flex-shrink-0 text-text-faint hover:text-text-primary transition-colors"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
