"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Loader2, CheckCircle2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";

type Phase = "loading" | "success";

export function AddFundsButton() {
  const [open, setOpen] = useState(false);
  const [phase, setPhase] = useState<Phase>("loading");

  useEffect(() => {
    if (!open) return;
    setPhase("loading");
    const id = window.setTimeout(() => setPhase("success"), 2000);
    return () => window.clearTimeout(id);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full inline-flex items-center justify-center gap-2 h-10 rounded-md border border-success/40 bg-success/5 hover:bg-success/10 hover:border-success text-success text-[11px] font-mono uppercase tracking-wider font-medium transition-all hover:-translate-y-px"
      >
        <Plus className="w-4 h-4" />
        Add Funds
      </button>

      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Add Funds"
        subtitle={phase === "loading" ? "Top up your wallet balance" : undefined}
      >
        <AnimatePresence mode="wait">
          {phase === "loading" ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="flex flex-col items-center text-center py-6"
            >
              <div className="w-16 h-16 rounded-full border-2 border-success/40 bg-success/5 flex items-center justify-center mb-5">
                <Loader2 className="w-7 h-7 text-success animate-spin" />
              </div>
              <p className="text-sm font-mono text-text-primary">
                Processing payment…
              </p>
              <p className="text-[11px] text-text-muted mt-1">
                authorizing settlement · routing through escrow
              </p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="mt-6 h-9 px-5 rounded border border-line bg-sunken hover:border-text-muted text-text-muted hover:text-text-primary text-[11px] font-mono uppercase tracking-[0.14em] transition-colors"
              >
                Cancel
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="success"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-col items-center text-center py-6"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.18, 1] }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                className="w-16 h-16 rounded-full border-2 border-success/40 bg-success/10 flex items-center justify-center mb-5"
              >
                <CheckCircle2 className="w-8 h-8 text-success" />
              </motion.div>
              <p className="text-sm font-mono text-text-primary">
                Payment received
              </p>
              <p className="text-[12px] text-text-muted mt-3 leading-relaxed max-w-xs">
                Funds will appear in your wallet within 30 seconds.
              </p>
              <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-pending mt-3">
                Demo · wallet balance is unchanged
              </p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="mt-6 h-9 px-6 rounded border border-success/40 bg-success/10 hover:bg-success/15 hover:border-success/60 text-success text-[11px] font-mono uppercase tracking-[0.14em] transition-colors"
              >
                Done
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </Modal>
    </>
  );
}
