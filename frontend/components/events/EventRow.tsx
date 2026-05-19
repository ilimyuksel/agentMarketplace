"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, Copy, Check } from "lucide-react";
import {
  categoryFor, categoryColor, categoryBgTone, formatTime,
  shortDescription, metadataChips,
} from "@/lib/events";
import type { WSEvent } from "@/types";

interface Props {
  event: WSEvent;
}

export function EventRow({ event }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const cat = categoryFor(event.eventType);
  const colorCls = categoryColor(event.eventType, event.payload);
  const desc = shortDescription(event.eventType, event.payload);
  const meta = metadataChips(event);

  const onCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(JSON.stringify(event, null, 2));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch { /* clipboard blocked — silent */ }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -3 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className="border-b border-line/60 last:border-b-0"
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-6 py-2 hover:bg-active/5 transition-colors cursor-pointer block"
      >
        <div className="grid grid-cols-[110px_14px_1fr_auto] items-baseline gap-3">
          <span className="text-[11px] font-mono text-text-faint tabular-nums">
            {formatTime(event.timestamp)}
          </span>
          <ChevronRight
            className={`w-3 h-3 text-text-faint transition-transform ${expanded ? "rotate-90" : ""}`}
          />
          <div className="min-w-0">
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className={`text-[12px] font-mono ${colorCls}`}>◆</span>
              <span className={`text-[12px] font-mono ${colorCls}`}>
                {event.eventType}
              </span>
              {desc && (
                <span className="text-[11px] font-mono text-text-muted">
                  · {desc}
                </span>
              )}
            </div>
            {meta.length > 0 && (
              <div className="flex items-center gap-2 mt-0.5">
                {meta.map((m) => (
                  <span key={m.key} className="text-[10px] font-mono text-text-faint">
                    {m.key} <span className="text-text-muted">{m.value}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
          <span
            className={`text-[9px] font-mono uppercase tracking-[0.16em] px-1.5 py-0.5 rounded border ${categoryBgTone(cat)}`}
          >
            {cat}
          </span>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-3 pt-1">
              <div className="rounded border border-line bg-sunken/60 px-3 py-2 relative">
                <button
                  type="button"
                  onClick={onCopy}
                  aria-label="Copy event JSON"
                  className="absolute top-2 right-2 inline-flex items-center gap-1 text-[10px] font-mono text-text-faint hover:text-active transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-success" />
                      <span className="text-success">copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> copy json
                    </>
                  )}
                </button>
                <pre className="text-[11px] font-mono text-text-muted leading-relaxed whitespace-pre-wrap break-words pr-16">
                  {JSON.stringify(event, null, 2)}
                </pre>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
