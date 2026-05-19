"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";

interface Props {
  hash: string;
  head?: number;
  tail?: number;
  label?: string;
}

export function HashLink({ hash, head = 8, tail = 6, label }: Props) {
  const [copied, setCopied] = useState(false);
  const [hovered, setHovered] = useState(false);

  const truncated =
    hash.length > head + tail + 1
      ? `${hash.slice(0, head)}…${hash.slice(-tail)}`
      : hash;

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(hash);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      /* silent */
    }
  };

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        onClick={onCopy}
        className="inline-flex items-center gap-1.5 text-[11px] font-mono text-text-muted hover:text-active transition-colors"
      >
        {label && <span className="text-text-faint">{label}:</span>}
        <span className="underline decoration-text-faint/40 underline-offset-2 decoration-dashed">
          {truncated}
        </span>
        {copied ? (
          <Check className="w-3 h-3 text-success" />
        ) : (
          <Copy className="w-3 h-3 opacity-50" />
        )}
      </button>
      {hovered && (
        <span
          role="tooltip"
          className="absolute left-0 top-full mt-1 z-50 w-max max-w-[32rem] rounded-md border border-line bg-deep px-3 py-2 shadow-xl"
        >
          <span className="block text-[10px] text-text-faint uppercase tracking-wider mb-1">
            SHA-256
          </span>
          <span className="block text-[11px] font-mono text-text-primary break-all">
            {hash}
          </span>
        </span>
      )}
    </span>
  );
}
