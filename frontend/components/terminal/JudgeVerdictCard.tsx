"use client";

import { Gavel } from "lucide-react";
import { AddressChip } from "@/components/primitives/AddressChip";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";
import type { JudgeEvaluation } from "@/types";

const RUBRIC: { key: keyof Pick<JudgeEvaluation, "scopeCompleteness" | "structuralQuality" | "contentQuality" | "briefFidelity">; label: string; weight: number }[] = [
  { key: "scopeCompleteness", label: "Scope",     weight: 0.25 },
  { key: "structuralQuality", label: "Structure", weight: 0.20 },
  { key: "contentQuality",    label: "Content",   weight: 0.35 },
  { key: "briefFidelity",     label: "Brief",     weight: 0.20 },
];

const DECISION_TONE = {
  APPROVED:           { bg: "border-success/40 bg-success/5",   text: "text-success" },
  REVISION_REQUESTED: { bg: "border-pending/40 bg-pending/5",   text: "text-pending" },
  REJECTED:           { bg: "border-danger/40 bg-danger/5",     text: "text-danger" },
} as const;

interface Props {
  evaluation: JudgeEvaluation;
  attemptIndex: number;
}

export function JudgeVerdictCard({ evaluation, attemptIndex }: Props) {
  const tone = DECISION_TONE[evaluation.decision] ?? DECISION_TONE.APPROVED;

  return (
    <div className={`rounded-md border ${tone.bg} p-3`}>
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <Gavel className={`w-3.5 h-3.5 ${tone.text}`} />
          <span className="text-[10px] uppercase tracking-[0.18em] font-mono text-text-faint">
            Verdict · attempt {attemptIndex + 1}
          </span>
        </div>
        <span className={`text-[10px] font-mono uppercase tracking-[0.14em] ${tone.text}`}>
          {evaluation.decision.replace(/_/g, " ")}
        </span>
      </div>

      <div className="flex items-baseline gap-3 mb-3">
        <span
          className={`font-mono tabular-nums text-2xl ${tone.text}`}
          style={{ fontFamily: "var(--font-jetbrains)" }}
        >
          {evaluation.finalScore.toFixed(2)}
        </span>
        <span className="text-[10px] text-text-faint font-mono">final score</span>
        <span className="flex-1" />
        <span className="text-[10px] text-text-faint font-mono">
          approval threshold ≥ 0.70
        </span>
      </div>

      <div className="space-y-1.5 mb-3">
        {RUBRIC.map((r) => {
          const v = evaluation[r.key] ?? null;
          const widthPct = v != null ? Math.max(2, Math.min(100, v * 100)) : 0;
          return (
            <div key={r.key} className="flex items-center gap-3">
              <span className="text-[10px] font-mono uppercase tracking-wider text-text-faint w-16">
                {r.label}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-sunken overflow-hidden">
                <div
                  className={tone.text.replace("text-", "bg-") + " h-full rounded-full"}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
              <span className="text-[10px] font-mono text-text-muted tabular-nums w-10 text-right">
                {v != null ? v.toFixed(2) : "—"}
              </span>
              <span className="text-[9px] font-mono text-text-faint tabular-nums w-8 text-right">
                ×{r.weight.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>

      {evaluation.reasoning && (
        <p className="text-[11px] text-text-muted italic leading-snug mb-2 font-mono">
          &ldquo;{evaluation.reasoning}&rdquo;
        </p>
      )}
      {evaluation.feedbackForRevision && (
        <div className="rounded border border-pending/30 bg-pending/5 p-2 mb-2">
          <p className="text-[9px] uppercase tracking-wider text-pending font-mono mb-1">
            Feedback for revision
          </p>
          <p className="text-[11px] text-text-muted leading-snug">
            {evaluation.feedbackForRevision}
          </p>
        </div>
      )}

      <div className="flex items-center justify-between text-[10px] font-mono text-text-faint pt-2 border-t border-line/60">
        <span>judge fee · flat regardless of verdict</span>
        <span className="flex items-center gap-2">
          <MoneyTicker value={2.0} size="sm" highlightOnChange={false} />
          <span className="text-text-faint">→</span>
          <AddressChip walletId="wallet_qajudge_001" tone="agent" size="sm" />
        </span>
      </div>
    </div>
  );
}
