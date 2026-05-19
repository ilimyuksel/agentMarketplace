"use client";

import type { Tier } from "@/lib/tier";

interface Col {
  tier: Tier;
  range: string;
  tasks: string;
  margin: string;
  note: string;
}

const COLS: Col[] = [
  { tier: "REJECTED", range: "< $50",     tasks: "no agents bid", margin: "100% refund", note: "PM declines" },
  { tier: "MINIMAL",  range: "$50–$149",  tasks: "2 sub-tasks",   margin: "PM margin 15%", note: "copy + dev" },
  { tier: "STANDARD", range: "$150–$499", tasks: "4 sub-tasks",   margin: "PM margin 18%", note: "research → copy/design → dev" },
  { tier: "PREMIUM",  range: "$500+",     tasks: "up to 6 tasks", margin: "PM margin 22%", note: "+ QA + variants" },
];

const TONE = {
  REJECTED: { active: "border-danger/40 bg-danger/5 text-danger" },
  MINIMAL:  { active: "border-text-muted/40 bg-sunken text-text-primary" },
  STANDARD: { active: "border-active/40 bg-active/5 text-active" },
  PREMIUM:  { active: "border-success/40 bg-success/5 text-success" },
} as const;

export function TierExplainerCard({ active }: { active: Tier }) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {COLS.map((c) => {
        const isActive = c.tier === active;
        const cls = isActive
          ? TONE[c.tier].active
          : "border-line bg-surface text-text-muted";
        return (
          <div
            key={c.tier}
            className={`rounded-md border ${cls} p-2.5 transition-colors`}
          >
            <p className={`text-[10px] font-mono uppercase tracking-[0.14em] ${isActive ? "" : "text-text-faint"}`}>
              {c.tier}
            </p>
            <p className="text-[10px] font-mono mt-1">{c.range}</p>
            <p className="text-[10px] text-text-faint mt-1.5">{c.tasks}</p>
            <p className="text-[10px] text-text-faint">{c.margin}</p>
          </div>
        );
      })}
    </div>
  );
}
