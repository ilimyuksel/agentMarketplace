"use client";

import { useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { computeTier, formatMoney } from "@/lib/tier";
import { TierExplainerCard } from "./TierExplainerCard";

export function JobSubmitForm() {
  const backendOnline = useAppStore((s) => s.backendOnline);
  const backendChecked = useAppStore((s) => s.backendChecked);
  const submitJob = useAppStore((s) => s.submitJob);
  const isSubmitting = useAppStore((s) => s.isSubmitting);

  const [prompt, setPrompt] = useState("");
  const [budget, setBudget] = useState(200);

  const math = useMemo(() => computeTier(budget), [budget]);
  const disabled = isSubmitting || !backendOnline || prompt.trim().length === 0 || budget < 30;

  const tone =
    math.tier === "REJECTED" ? "danger"
    : math.tier === "MINIMAL" ? "muted"
    : math.tier === "STANDARD" ? "active"
    : "success";

  const TONE_RING: Record<typeof tone, string> = {
    danger: "border-danger/40 bg-danger/5",
    muted: "border-line bg-sunken",
    active: "border-active/40 bg-active/5",
    success: "border-success/40 bg-success/5",
  };
  const TONE_TEXT: Record<typeof tone, string> = {
    danger: "text-danger",
    muted: "text-text-muted",
    active: "text-active",
    success: "text-success",
  };

  const handleSubmit = async () => {
    if (disabled) return;
    await submitJob(prompt.trim(), budget);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <p className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
          Submit a job to the marketplace
        </p>
        <h1
          className="text-2xl font-semibold text-text-primary tracking-tight"
          style={{ fontFamily: "var(--font-space-grotesk)" }}
        >
          Describe the work · set a budget · watch agents bid live.
        </h1>
      </div>

      <div className="space-y-4">
        <label className="block">
          <span className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono mb-2 block">
            Prompt
          </span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Create a landing page for a developer AI tool"
            rows={3}
            maxLength={2000}
            className="w-full bg-sunken border border-line rounded-md px-3 py-2.5 text-sm text-text-primary placeholder:text-text-faint focus:outline-none focus:border-active/60 focus:ring-1 focus:ring-active/40 resize-none font-mono"
          />
          <div className="text-right text-[10px] text-text-faint font-mono mt-1">
            {prompt.length} / 2000
          </div>
        </label>

        <div>
          <div className="flex items-baseline justify-between mb-2">
            <span className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
              Budget
            </span>
            <span
              className="font-mono text-2xl text-text-primary tabular-nums"
              style={{ fontFamily: "var(--font-jetbrains)" }}
            >
              {formatMoney(budget)}
            </span>
          </div>

          <div className="relative pt-2">
            <input
              type="range"
              min={30}
              max={1000}
              step={5}
              value={budget}
              onChange={(e) => setBudget(parseInt(e.target.value, 10))}
              className="w-full h-1 bg-line rounded-full appearance-none cursor-pointer accent-active [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-active [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-deep [&::-webkit-slider-thumb]:cursor-pointer"
            />
            <div className="relative h-4 mt-2">
              {[30, 50, 150, 500, 1000].map((mark) => {
                const pct = ((mark - 30) / 970) * 100;
                return (
                  <div
                    key={mark}
                    className="absolute flex flex-col items-center"
                    style={{ left: `${pct}%`, transform: "translateX(-50%)" }}
                  >
                    <div className="w-px h-1.5 bg-text-faint/40" />
                    <span className="text-[9px] text-text-faint font-mono mt-0.5">
                      ${mark}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className={`rounded-md border ${TONE_RING[tone]} p-4 transition-colors`}>
          {math.tier === "REJECTED" ? (
            <div className="space-y-1">
              <div className="flex items-baseline gap-3">
                <span className={`text-[11px] font-mono uppercase tracking-[0.14em] ${TONE_TEXT[tone]}`}>
                  Tier · REJECTED
                </span>
                <span className="text-[11px] text-text-faint">budget below $50 minimum</span>
              </div>
              <p className="text-xs text-text-muted">
                ProjectManager_001 declines · 100% refund · no agents bid.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-baseline gap-3">
                <span className={`text-[11px] font-mono uppercase tracking-[0.14em] ${TONE_TEXT[tone]}`}>
                  Tier · {math.tier}
                </span>
                <span className="text-[11px] text-text-faint font-mono">
                  {math.numTasks} sub-tasks · PM margin {(math.margin * 100).toFixed(0)}%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[11px] font-mono">
                <div className="flex justify-between">
                  <span className="text-text-faint">PM bid</span>
                  <span className="text-text-primary tabular-nums">{formatMoney(math.pmBid)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-faint">Sub-agent pool</span>
                  <span className="text-text-primary tabular-nums">{formatMoney(math.subAgentPool)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-faint">Judge reserve</span>
                  <span className="text-text-primary tabular-nums">{formatMoney(math.judgeReserve)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-faint">Expected refund</span>
                  <span className="text-text-primary tabular-nums">~{formatMoney(math.expectedRefund)}</span>
                </div>
              </div>
              <p className="text-[10px] text-text-faint pt-1 border-t border-line/60 font-mono">
                bid = budget × (1 − margin × 0.5) · sub-pool = bid × (1 − margin)
              </p>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled}
          className="w-full h-12 rounded-md bg-active hover:bg-active/90 text-deep font-mono uppercase tracking-[0.18em] text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
        >
          {!backendChecked
            ? "Checking backend…"
            : !backendOnline
            ? "Backend offline"
            : isSubmitting
            ? "Submitting…"
            : (
              <>
                Submit to marketplace <ArrowRight className="w-4 h-4" />
              </>
            )}
        </button>
      </div>

      <TierExplainerCard active={math.tier} />
    </div>
  );
}
