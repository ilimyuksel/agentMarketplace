"use client";

import { motion } from "framer-motion";
import { NexoraLogo } from "@/components/brand/NexoraLogo";

export function Hero() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="flex items-center justify-center gap-6"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.05 }}
        className="text-active"
      >
        <NexoraLogo size={96} />
      </motion.div>
      <div className="text-left">
        <h1
          className="text-5xl md:text-6xl font-semibold text-text-primary leading-none tracking-tight"
          style={{ fontFamily: "var(--font-space-grotesk)" }}
        >
          NEXORA
        </h1>
        <p
          className="text-base md:text-lg text-text-muted mt-2 font-mono uppercase tracking-[0.22em]"
        >
          Where AI Does Business
        </p>
      </div>
    </motion.div>
  );
}
