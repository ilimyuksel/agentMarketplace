"use client";

import { useEffect, useState } from "react";
import { Copy, Check } from "lucide-react";
import { deriveAddress, truncateAddress } from "@/lib/addr";

type Tone = "user" | "escrow" | "agent" | "system" | "genesis";

const TONE_DOT: Record<Tone, string> = {
  user: "bg-active",
  escrow: "bg-pending",
  agent: "bg-success",
  system: "bg-genesis",
  genesis: "bg-genesis",
};

interface Props {
  walletId: string;
  tone?: Tone;
  size?: "sm" | "md";
}

export function AddressChip({ walletId, tone = "agent", size = "md" }: Props) {
  const [addr, setAddr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    let alive = true;
    deriveAddress(walletId).then((a) => alive && setAddr(a));
    return () => {
      alive = false;
    };
  }, [walletId]);

  const onCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!addr) return;
    try {
      await navigator.clipboard.writeText(addr);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard blocked — silent */
    }
  };

  const sizing =
    size === "sm"
      ? "text-[10px] px-2 py-0.5 gap-1.5"
      : "text-xs px-2.5 py-1 gap-2";

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        onClick={onCopy}
        className={`inline-flex items-center ${sizing} rounded-md border border-line bg-sunken text-text-primary hover:border-active/50 transition-colors font-mono`}
        aria-label={`Wallet ${walletId} — copy address`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${TONE_DOT[tone]}`} />
        <span>{addr ? truncateAddress(addr) : "0x…"}</span>
        {copied ? (
          <Check className="w-3 h-3 text-success" />
        ) : (
          <Copy className="w-3 h-3 text-text-faint" />
        )}
      </button>

      {hovered && addr && (
        <span
          role="tooltip"
          className="absolute left-0 top-full mt-1 z-50 w-max max-w-[28rem] rounded-md border border-line bg-deep px-3 py-2 shadow-xl font-mono"
        >
          <span className="block text-[10px] text-text-faint uppercase tracking-wider mb-1">
            Address
          </span>
          <span className="block text-[11px] text-text-primary break-all">
            {addr}
          </span>
          <span className="block text-[10px] text-text-faint uppercase tracking-wider mt-2 mb-1">
            Wallet ID
          </span>
          <span className="block text-[11px] text-text-muted break-all">
            {walletId}
          </span>
        </span>
      )}
    </span>
  );
}
