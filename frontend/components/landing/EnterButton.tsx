"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

export function EnterButton() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
    >
      <Link
        href="/terminal"
        className="group inline-flex items-center gap-3 h-14 px-8 rounded-md border-2 border-active bg-active/10 hover:bg-active/20 text-active font-mono uppercase tracking-[0.22em] text-sm font-semibold transition-all hover:-translate-y-px"
      >
        Enter Marketplace
        <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
      </Link>
    </motion.div>
  );
}
