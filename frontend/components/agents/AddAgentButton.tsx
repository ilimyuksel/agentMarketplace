"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Loader2, CheckCircle2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";

type Phase = "loading" | "success";

export function AddAgentButton() {
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
        className="inline-flex items-center gap-2 h-10 px-5 rounded-md border border-active/50 bg-active/10 hover:bg-active/20 hover:border-active text-active text-[11px] font-mono uppercase tracking-wider font-medium transition-all hover:-translate-y-px"
      >
        <Plus className="w-4 h-4" />
        Add Agent
      </button>

      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Register New Agent"
        subtitle={phase === "loading" ? "Onboard an autonomous agent to the marketplace" : undefined}
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
              <div className="w-16 h-16 rounded-full border-2 border-active/40 bg-active/5 flex items-center justify-center mb-5">
                <Loader2 className="w-7 h-7 text-active animate-spin" />
              </div>
              <p className="text-sm font-mono text-text-primary">
                Provisioning agent wallet…
              </p>
              <p className="text-[11px] text-text-muted mt-1">
                signing skill embedding · seeding reputation
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
                Agent registration queued
              </p>
              <p className="text-[12px] text-text-muted mt-3 leading-relaxed max-w-xs">
                The agent will appear in the marketplace once onboarding completes.
              </p>
              <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-pending mt-3">
                Demo · no real agent has been added
              </p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="mt-6 h-9 px-6 rounded border border-active/40 bg-active/10 hover:bg-active/15 hover:border-active/60 text-active text-[11px] font-mono uppercase tracking-[0.14em] transition-colors"
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
