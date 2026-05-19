"use client";

import { motion } from "framer-motion";

interface Props {
  /** 0.10–0.99 per backend clamp. Accepts null/undefined defensively — coerced to 0. */
  value: number | null | undefined;
  size?: number; // px
  label?: boolean;
}

function colorFor(v: number): { stroke: string; text: string } {
  if (v >= 0.85) return { stroke: "var(--success)", text: "text-success" };
  if (v >= 0.70) return { stroke: "var(--active)", text: "text-active" };
  if (v >= 0.50) return { stroke: "var(--pending)", text: "text-pending" };
  return { stroke: "var(--danger)", text: "text-danger" };
}

export function ReputationGauge({ value, size = 64, label = true }: Props) {
  const safe = value ?? 0;
  const clamped = Math.max(0, Math.min(1, safe));
  const radius = (size - 8) / 2;
  const circumference = Math.PI * radius; // semicircle
  const dash = circumference * clamped;
  const { stroke, text } = colorFor(clamped);

  const cx = size / 2;
  const cy = size / 2 + radius / 2;

  return (
    <div className="inline-flex flex-col items-center" style={{ width: size }}>
      <svg
        width={size}
        height={size / 2 + 8}
        viewBox={`0 0 ${size} ${size / 2 + 8}`}
        aria-label={`Reputation ${clamped.toFixed(2)}`}
      >
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="var(--line)"
          strokeWidth={4}
          strokeLinecap="round"
        />
        <motion.path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke={stroke}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - dash }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      {label && (
        <div className={`font-mono text-xs ${text} -mt-2 tabular-nums`}>
          {clamped.toFixed(2)}
        </div>
      )}
    </div>
  );
}
