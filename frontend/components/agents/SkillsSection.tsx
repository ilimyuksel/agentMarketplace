"use client";

import { useState } from "react";

interface Props {
  /** Backend returns skill_keywords as a comma-separated string. */
  skillKeywords: string;
  initialVisible?: number;
}

export function SkillsSection({ skillKeywords, initialVisible = 5 }: Props) {
  const [expanded, setExpanded] = useState(false);
  const skills = skillKeywords
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const visible = expanded ? skills : skills.slice(0, initialVisible);
  const rest = skills.length - initialVisible;

  if (skills.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <p className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-faint">
        Skills
      </p>
      <div className="flex flex-wrap gap-1">
        {visible.map((s) => (
          <span
            key={s}
            className="text-[10px] font-mono text-text-muted px-1.5 py-0.5 rounded border border-line bg-surface/40"
          >
            {s}
          </span>
        ))}
        {!expanded && rest > 0 && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="text-[10px] font-mono text-active px-1.5 py-0.5 rounded border border-active/30 bg-active/5 hover:bg-active/10 transition-colors"
          >
            +{rest} more
          </button>
        )}
        {expanded && skills.length > initialVisible && (
          <button
            type="button"
            onClick={() => setExpanded(false)}
            className="text-[10px] font-mono text-text-faint px-1.5 py-0.5 rounded border border-line hover:text-text-primary transition-colors"
          >
            collapse
          </button>
        )}
      </div>
    </div>
  );
}
