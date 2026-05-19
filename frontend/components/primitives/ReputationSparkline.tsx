"use client";

import { useState } from "react";
import type { ReputationHistoryEntry } from "@/types";

interface Props {
  history: ReputationHistoryEntry[];
  currentRep: number;
  width?: number;
  height?: number;
}

const Y_MIN = 0.10;
const Y_MAX = 0.99;

function colorFor(v: number): string {
  if (v >= 0.85) return "var(--success)";
  if (v >= 0.70) return "var(--active)";
  if (v >= 0.50) return "var(--pending)";
  return "var(--danger)";
}

interface PlotPoint {
  rep: number;
  delta: number | null;
  reason: string | null;
  judgeScore: number | null;
  createdAt: string | null;
  synthetic: boolean;
}

function synthesize(currentRep: number, n: number): PlotPoint[] {
  // Tiny jitter around current value — implies "stable performance, no
  // verdicts yet". Never invents deltas.
  return Array.from({ length: n }, (_, i) => ({
    rep: Math.max(Y_MIN, Math.min(Y_MAX, currentRep + Math.sin(i * 0.7) * 0.012)),
    delta: null,
    reason: null,
    judgeScore: null,
    createdAt: null,
    synthetic: true,
  }));
}

export function ReputationSparkline({
  history,
  currentRep,
  width = 200,
  height = 40,
}: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const hasReal = history.length >= 2;
  const points: PlotPoint[] = hasReal
    ? history
        .slice(0, 12)
        .reverse() // chronological
        .map((h) => ({
          rep: h.newReputation ?? currentRep,
          delta: h.delta,
          reason: h.reason,
          judgeScore: h.judgeScore,
          createdAt: h.createdAt,
          synthetic: false,
        }))
    : synthesize(currentRep, 12);

  const N = points.length;
  const PAD_X = 4;
  const PAD_Y = 6;
  const innerW = width - PAD_X * 2;
  const innerH = height - PAD_Y * 2;
  const xStep = N > 1 ? innerW / (N - 1) : 0;
  const yScale = (v: number) =>
    PAD_Y + innerH - ((v - Y_MIN) / (Y_MAX - Y_MIN)) * innerH;

  const xs = points.map((_, i) => PAD_X + i * xStep);
  const ys = points.map((p) => yScale(p.rep));
  const path = points.map((p, i) => (i === 0 ? "M" : "L") + ` ${xs[i]} ${ys[i]}`).join(" ");
  const fillPath = `${path} L ${xs[N - 1]} ${height} L ${xs[0]} ${height} Z`;

  const color = colorFor(currentRep);

  return (
    <div className="relative inline-block" style={{ width, height }}>
      <svg width={width} height={height} className="block">
        <defs>
          <linearGradient id={`spark-${color.slice(4, -1)}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* threshold line at 0.70 (approval threshold) */}
        <line
          x1={PAD_X} x2={width - PAD_X}
          y1={yScale(0.70)} y2={yScale(0.70)}
          stroke="var(--line)"
          strokeDasharray="2 3"
          strokeWidth={1}
        />
        <path d={fillPath} fill={`url(#spark-${color.slice(4, -1)})`} opacity={hasReal ? 1 : 0.6} />
        <path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={hasReal ? 1 : 0.7}
          strokeDasharray={hasReal ? "" : "0"}
        />
        {/* hover hit-targets */}
        {hasReal && points.map((p, i) => (
          <g key={i}>
            <circle
              cx={xs[i]} cy={ys[i]} r={2.5}
              fill={color}
              opacity={hover === i ? 1 : 0.7}
            />
            <circle
              cx={xs[i]} cy={ys[i]} r={10}
              fill="transparent"
              className="cursor-pointer"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            />
          </g>
        ))}
      </svg>

      {!hasReal && (
        <span className="absolute top-0.5 right-1 text-[8px] font-mono text-text-faint uppercase tracking-wider">
          synthetic
        </span>
      )}

      {hover != null && hasReal && (
        <div
          role="tooltip"
          className="absolute z-50 rounded-md border border-line bg-deep px-2 py-1.5 shadow-xl pointer-events-none"
          style={{
            left: xs[hover] + 12,
            top: Math.max(0, ys[hover] - 36),
            minWidth: 180,
          }}
        >
          <p className="text-[10px] font-mono text-text-faint uppercase tracking-wider">
            Verdict
          </p>
          <p className="text-[11px] font-mono text-text-primary tabular-nums">
            {(points[hover].delta ?? 0) >= 0 ? "+" : ""}
            {(points[hover].delta ?? 0).toFixed(2)}
            <span className="text-text-faint"> · rep → </span>
            {points[hover].rep.toFixed(2)}
          </p>
          {points[hover].judgeScore != null && (
            <p className="text-[10px] font-mono text-text-muted">
              judge score {points[hover].judgeScore!.toFixed(2)}
            </p>
          )}
          {points[hover].reason && (
            <p className="text-[10px] text-text-faint mt-0.5 truncate max-w-[160px]">
              {points[hover].reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
