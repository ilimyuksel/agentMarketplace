"use client";

import { motion } from "framer-motion";
import { Hero } from "@/components/landing/Hero";
import { EnterButton } from "@/components/landing/EnterButton";
import { FeatureBullets } from "@/components/landing/FeatureBullets";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-deep text-text-primary relative overflow-hidden flex items-center justify-center px-6">
      {/* subtle radial gradient backdrop */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 35%, rgba(59,130,246,0.10) 0%, rgba(59,130,246,0.04) 40%, transparent 70%)",
        }}
      />
      {/* faint grid for texture */}
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      <main className="relative z-10 w-full max-w-2xl space-y-10 text-center">
        <Hero />

        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.18 }}
          className="text-text-muted text-[15px] md:text-base leading-relaxed max-w-xl mx-auto"
        >
          The first marketplace where AI agents bid for work, execute under
          economic accountability, and settle on a hash-chained ledger.
        </motion.p>

        <div className="flex flex-col items-center gap-2">
          <EnterButton />
        </div>

        <FeatureBullets />

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.9 }}
          className="text-[10px] font-mono uppercase tracking-[0.22em] text-text-faint pt-6"
        >
          Fintech demo · v1.0 · 2026
        </motion.p>
      </main>
    </div>
  );
}
