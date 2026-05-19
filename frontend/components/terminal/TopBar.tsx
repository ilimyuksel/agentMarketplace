"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { DemoControlsButton } from "@/components/demo/DemoControls";
import { NexoraLogo } from "@/components/brand/NexoraLogo";

export function TopBar() {
  const backendOnline = useAppStore((s) => s.backendOnline);
  const backendChecked = useAppStore((s) => s.backendChecked);
  const globalStatus = useAppStore((s) => s.globalStatus);
  const jobStatus = useAppStore((s) => s.jobStatus);
  const lastHeartbeatAt = useAppStore((s) => s.lastHeartbeatAt);
  const verificationStatus = useAppStore((s) => s.verificationStatus);
  const runVerification = useAppStore((s) => s.runVerification);
  const [, force] = useState(0);

  // Tick once per second so the "last heartbeat 7s ago" label refreshes.
  useEffect(() => {
    const id = window.setInterval(() => force((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  // Pick the most pessimistic visible status across channels.
  const channelStatus = jobStatus !== "idle" && jobStatus !== "closed" ? jobStatus : globalStatus;

  let tone: { dot: string; text: string; textCls: string };
  if (!backendChecked) tone = { dot: "bg-pending", text: "checking", textCls: "text-pending" };
  else if (!backendOnline) tone = { dot: "bg-danger", text: "offline", textCls: "text-danger" };
  else if (channelStatus === "live") tone = { dot: "bg-active", text: "live", textCls: "text-active" };
  else if (channelStatus === "connecting") tone = { dot: "bg-pending", text: "connecting", textCls: "text-pending" };
  else if (channelStatus === "reconnecting") tone = { dot: "bg-pending", text: "reconnecting…", textCls: "text-pending" };
  else if (channelStatus === "polling") tone = { dot: "bg-danger", text: "polling fallback", textCls: "text-danger" };
  else tone = { dot: "bg-active", text: "online", textCls: "text-active" };

  const verifying = verificationStatus === "verifying";
  const onVerify = () => { void runVerification(); };

  const heartbeatLabel =
    lastHeartbeatAt == null ? "—" : `${Math.max(0, Math.round((Date.now() - lastHeartbeatAt) / 1000))}s ago`;

  return (
    <header className="h-14 border-b border-line bg-deep flex items-center px-6 gap-6">
      <Link href="/" className="flex items-center gap-2 group" aria-label="Nexora home">
        <NexoraLogo size={26} className="text-active" />
        <span
          className="text-sm font-semibold tracking-[0.10em] text-text-primary"
          style={{ fontFamily: "var(--font-space-grotesk)" }}
        >
          NEXORA
        </span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-text-faint border-l border-line pl-3 ml-2">
          Agent-to-agent payment rails
        </span>
      </Link>

      <div className="flex-1" />

      <button
        type="button"
        title={`Backend ${tone.text} · last heartbeat ${heartbeatLabel}`}
        className="flex items-center gap-2 text-[11px] font-mono"
      >
        <span className={`relative w-2 h-2 rounded-full ${tone.dot}`}>
          {backendOnline && (
            <span className={`absolute inset-0 rounded-full ${tone.dot} animate-ping opacity-60`} />
          )}
        </span>
        <span className={tone.textCls}>backend {tone.text}</span>

      </button>

      <button
        type="button"
        onClick={onVerify}
        disabled={!backendOnline || verifying}
        className="inline-flex items-center gap-2 h-9 px-4 rounded-md border border-active/40 bg-active/10 hover:bg-active/15 hover:border-active/60 text-active text-xs font-mono uppercase tracking-[0.14em] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <ShieldCheck className="w-3.5 h-3.5" />
        {verifying ? "verifying…" : "Verify Chain Integrity"}
      </button>

      <DemoControlsButton />
    </header>
  );
}
