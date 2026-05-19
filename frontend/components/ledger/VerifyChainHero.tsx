"use client";

import { ShieldCheck, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import { useAppStore } from "@/lib/store";

export function VerifyChainHero() {
  const status = useAppStore((s) => s.verificationStatus);
  const result = useAppStore((s) => s.verificationResult);
  const runVerification = useAppStore((s) => s.runVerification);
  const backendOnline = useAppStore((s) => s.backendOnline);

  const disabled = !backendOnline || status === "verifying";

  let tone: "idle" | "verifying" | "success" | "error" = "idle";
  let Icon: React.ComponentType<{ className?: string }> = ShieldCheck;
  let label = "Verify Chain Integrity";

  if (status === "verifying") {
    tone = "verifying";
    Icon = Loader2;
    label = "Verifying…";
  } else if (status === "success" && result) {
    tone = "success";
    Icon = CheckCircle2;
    label = `✓ ${result.blocksVerified} blocks · ${result.durationMs}ms · valid`;
  } else if (status === "error" && result) {
    tone = "error";
    Icon = AlertTriangle;
    label = result.firstBadBlock != null
      ? `✗ Chain broken · block #${result.firstBadBlock} tampered`
      : "✗ Chain verification failed";
  }

  const variants: Record<typeof tone, string> = {
    idle: "border-active/50 bg-active/5 hover:bg-active/10 hover:border-active text-active",
    verifying: "border-active/60 bg-active/10 text-active",
    success: "border-success bg-success/15 text-success",
    error: "border-danger bg-danger/15 text-danger",
  };

  return (
    <motion.button
      type="button"
      onClick={() => runVerification()}
      disabled={disabled}
      whileHover={!disabled ? { y: -1 } : {}}
      whileTap={!disabled ? { scale: 0.99 } : {}}
      animate={tone === "verifying" ? {
        boxShadow: ["0 0 0 0 rgba(34,211,238,0)", "0 0 0 6px rgba(34,211,238,0.25)", "0 0 0 0 rgba(34,211,238,0)"],
      } : { boxShadow: "0 0 0 0 rgba(34,211,238,0)" }}
      transition={tone === "verifying" ? { duration: 1.2, repeat: Infinity, ease: "easeInOut" } : {}}
      className={`inline-flex items-center gap-3 h-12 px-5 rounded-md border-2 font-mono uppercase tracking-[0.16em] text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors ${variants[tone]}`}
    >
      <Icon className={`w-4 h-4 ${tone === "verifying" ? "animate-spin" : ""}`} />
      {label}
    </motion.button>
  );
}
