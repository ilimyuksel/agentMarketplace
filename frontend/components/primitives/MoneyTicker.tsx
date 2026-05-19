"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useMotionValue, useTransform, motion } from "framer-motion";

interface Props {
  value: number;
  decimals?: number;
  prefix?: string;
  size?: "sm" | "md" | "lg" | "xl" | "2xl";
  /** Tint amount briefly when value increases / decreases. */
  highlightOnChange?: boolean;
}

const SIZE: Record<NonNullable<Props["size"]>, string> = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-xl",
  xl: "text-3xl",
  "2xl": "text-4xl",
};

function format(n: number, decimals: number) {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function MoneyTicker({
  value,
  decimals = 2,
  prefix = "$",
  size = "md",
  highlightOnChange = true,
}: Props) {
  const mv = useMotionValue(value);
  const text = useTransform(mv, (latest) => `${prefix}${format(latest, decimals)}`);
  const prev = useRef(value);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    const controls = animate(mv, value, {
      duration: 0.6,
      ease: [0.22, 1, 0.36, 1],
    });
    if (highlightOnChange && value !== prev.current) {
      setFlash(value > prev.current ? "up" : "down");
      const id = window.setTimeout(() => setFlash(null), 700);
      prev.current = value;
      return () => {
        controls.stop();
        window.clearTimeout(id);
      };
    }
    prev.current = value;
    return () => controls.stop();
  }, [value, mv, highlightOnChange]);

  const flashColor =
    flash === "up"
      ? "text-success"
      : flash === "down"
      ? "text-pending"
      : "text-text-primary";

  return (
    <motion.span
      className={`font-mono tabular-nums ${SIZE[size]} ${flashColor} transition-colors duration-300`}
    >
      {text}
    </motion.span>
  );
}
