"use client";

import { motion } from "framer-motion";

const ITEMS = [
  "9 specialized agents · 6 active + 3 ghost",
  "Real-time WebSocket event streaming",
  "SHA-256 hash-chained transaction ledger",
  "Cryptographic chain integrity verification",
];

export function FeatureBullets() {
  return (
    <motion.ul
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.06, delayChildren: 0.45 } },
      }}
      className="space-y-2"
    >
      {ITEMS.map((text) => (
        <motion.li
          key={text}
          variants={{
            hidden: { opacity: 0, x: -4 },
            show: { opacity: 1, x: 0, transition: { duration: 0.35 } },
          }}
          className="text-[12px] md:text-[13px] font-mono text-text-muted flex items-center gap-3 justify-center"
        >
          <span className="w-1 h-1 rounded-full bg-active flex-shrink-0" />
          {text}
        </motion.li>
      ))}
    </motion.ul>
  );
}
