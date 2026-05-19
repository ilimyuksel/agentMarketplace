"use client";

import { Skull, Trophy } from "lucide-react";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";
import { PERSONAS } from "@/lib/personas";
import type { Bid, Agent } from "@/types";

interface Props {
  bid: Bid;
  agent: Agent | undefined;
}

export function BidRow({ bid, agent }: Props) {
  const isGhost = agent?.isGhost ?? false;
  const persona = PERSONAS[bid.agentId];
  const isWinner = bid.isWinner;

  const tone = isWinner
    ? "border-l-4 border-success bg-success/5"
    : isGhost
    ? "border-l-4 border-ghost bg-surface opacity-60"
    : "border-l-4 border-line bg-surface";

  return (
    <div
      className={`${tone} rounded-r-md px-3 py-2 transition-colors`}
      title={persona?.short ?? ""}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isGhost && <Skull className="w-3 h-3 text-ghost flex-shrink-0" />}
            <span className="text-[11px] font-mono text-text-primary truncate">
              {bid.agentId}
            </span>
            {isWinner && (
              <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-[0.16em] text-success">
                <Trophy className="w-3 h-3" /> winner
              </span>
            )}
            {isGhost && (
              <span className="text-[9px] font-mono uppercase tracking-[0.14em] text-ghost">
                ghost · filtered
              </span>
            )}
          </div>
          {persona && (
            <p className="text-[10px] text-text-faint mt-0.5">{persona.archetype}</p>
          )}
          {bid.reasoning && (
            <p className="text-[11px] text-text-muted mt-1 leading-snug line-clamp-2 italic">
              &ldquo;{bid.reasoning}&rdquo;
            </p>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          <MoneyTicker value={bid.bidAmount} size="md" highlightOnChange={false} />
          {bid.confidence != null && (
            <p className="text-[9px] text-text-faint font-mono mt-0.5">
              conf {bid.confidence.toFixed(2)}
            </p>
          )}
          {bid.selectionScore != null && (
            <p className="text-[9px] text-success font-mono mt-0.5 tabular-nums">
              score {bid.selectionScore.toFixed(2)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
