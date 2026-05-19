"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Settings, X, RotateCw, Copy, Check, Terminal, Wallet as WalletIcon, AlertTriangle,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";

const MANUAL_COMMAND = `cd ~/Desktop/ai-agent-marketplace
python scripts/reset_database.py`;

type AdminProbe = "checking" | "available" | "missing";

export function DemoControlsButton() {
  const [open, setOpen] = useState(false);
  const [probe, setProbe] = useState<AdminProbe>("checking");
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState<null | "wallet" | "all" | "refresh">(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const userWallet = useAppStore((s) =>
    s.wallets.find((w) => w.id === "wallet_user_demo"),
  );
  const refreshAll = useAppStore((s) => s.refreshAll);

  useEffect(() => {
    if (!open || probe !== "checking") return;
    api.probeAdminAPI().then((ok) => setProbe(ok ? "available" : "missing"));
  }, [open, probe]);

  // ESC + click-outside close.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        panelRef.current && !panelRef.current.contains(target) &&
        buttonRef.current && !buttonRef.current.contains(target)
      ) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  // Auto-clear transient toast.
  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 2200);
    return () => window.clearTimeout(id);
  }, [toast]);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(MANUAL_COMMAND);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setToast({ kind: "err", text: "clipboard blocked" });
    }
  };

  const onResetWallet = async () => {
    setBusy("wallet");
    try {
      await api.adminResetWallet("wallet_user_demo", 1000);
      await refreshAll();
      setToast({ kind: "ok", text: "user wallet reset to $1000" });
    } catch {
      setToast({ kind: "err", text: "endpoint unavailable — use manual" });
      setProbe("missing");
    } finally {
      setBusy(null);
    }
  };

  const onResetAll = async () => {
    const ok = window.confirm(
      "This clears all jobs, ledger blocks, and agent earnings. Genesis will be regenerated. Continue?",
    );
    if (!ok) return;
    setBusy("all");
    try {
      await api.adminResetAll();
      await refreshAll();
      setToast({ kind: "ok", text: "database reset" });
    } catch {
      setToast({ kind: "err", text: "endpoint unavailable — use manual" });
      setProbe("missing");
    } finally {
      setBusy(null);
    }
  };

  const onRefresh = async () => {
    setBusy("refresh");
    try {
      await refreshAll();
      setToast({ kind: "ok", text: "state refreshed from backend" });
    } catch {
      setToast({ kind: "err", text: "refresh failed" });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Demo controls"
        title="Demo controls"
        className={`inline-flex items-center justify-center w-9 h-9 rounded-md border transition-colors ${
          open
            ? "border-active bg-active/10 text-active"
            : "border-line bg-sunken text-text-muted hover:text-text-primary hover:border-line/80"
        }`}
      >
        <Settings className={`w-4 h-4 ${open ? "rotate-45" : ""} transition-transform`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            ref={panelRef}
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="absolute right-0 top-full mt-2 w-[420px] rounded-md border border-line bg-deep shadow-2xl z-50"
          >
            <header className="flex items-center justify-between px-4 py-3 border-b border-line">
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
                  Demo controls
                  {probe === "missing" && <span className="ml-2 text-pending">· manual mode</span>}
                  {probe === "available" && <span className="ml-2 text-success">· backend</span>}
                  {probe === "checking" && <span className="ml-2 text-text-muted">· probing…</span>}
                </p>
                <p className="text-[11px] text-text-muted mt-0.5">
                  presentation-time conveniences
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="text-text-faint hover:text-text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </header>

            <div className="px-4 py-3 space-y-4">
              {/* WALLET section */}
              <section className="space-y-2">
                <div className="flex items-baseline justify-between">
                  <p className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-faint inline-flex items-center gap-1.5">
                    <WalletIcon className="w-3 h-3" /> User wallet
                  </p>
                  <p className="text-[10px] font-mono text-text-faint">current</p>
                </div>
                <div className="flex items-baseline justify-between rounded border border-line bg-sunken px-3 py-2">
                  <span className="text-[10px] font-mono text-text-faint">wallet_user_demo</span>
                  <MoneyTicker value={userWallet?.balance ?? 0} size="lg" highlightOnChange={false} />
                </div>

                {probe === "available" ? (
                  <button
                    type="button"
                    disabled={busy != null}
                    onClick={onResetWallet}
                    className="w-full inline-flex items-center justify-center gap-2 h-9 rounded border border-active/40 bg-active/10 hover:bg-active/15 text-active text-[11px] font-mono uppercase tracking-[0.14em] disabled:opacity-40 transition-colors"
                  >
                    <RotateCw className={`w-3.5 h-3.5 ${busy === "wallet" ? "animate-spin" : ""}`} />
                    reset user wallet to $1000
                  </button>
                ) : (
                  <ManualBlock
                    onCopy={onCopy}
                    copied={copied}
                    note={
                      probe === "checking"
                        ? "checking for admin endpoint…"
                        : "no backend reset endpoint · run this in your terminal:"
                    }
                  />
                )}
              </section>

              {/* DATABASE section */}
              <section className="space-y-2 border-t border-line pt-4">
                <div className="flex items-baseline justify-between">
                  <p className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-faint">
                    Database
                  </p>
                  <p className="text-[10px] font-mono text-pending inline-flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> destructive
                  </p>
                </div>
                <p className="text-[11px] text-text-muted leading-relaxed">
                  clears jobs · ledger · agent earnings · regenerates genesis
                </p>
                {probe === "available" ? (
                  <button
                    type="button"
                    disabled={busy != null}
                    onClick={onResetAll}
                    className="w-full inline-flex items-center justify-center gap-2 h-9 rounded border border-danger/40 bg-danger/5 hover:bg-danger/10 text-danger text-[11px] font-mono uppercase tracking-[0.14em] disabled:opacity-40 transition-colors"
                  >
                    <AlertTriangle className={`w-3.5 h-3.5 ${busy === "all" ? "animate-pulse" : ""}`} />
                    reset everything
                  </button>
                ) : (
                  <p className="text-[10px] font-mono text-text-faint">
                    use the same command above to regenerate genesis + reseed agents
                  </p>
                )}
              </section>

              {/* REFRESH */}
              <section className="border-t border-line pt-4">
                <button
                  type="button"
                  disabled={busy != null}
                  onClick={onRefresh}
                  className="w-full inline-flex items-center justify-center gap-2 h-9 rounded border border-line bg-sunken hover:border-active/40 hover:text-text-primary text-text-muted text-[11px] font-mono uppercase tracking-[0.14em] disabled:opacity-40 transition-colors"
                >
                  <RotateCw className={`w-3.5 h-3.5 ${busy === "refresh" ? "animate-spin" : ""}`} />
                  refresh state from backend
                </button>
                <p className="text-[10px] font-mono text-text-faint text-center mt-1.5">
                  rehydrates agents · wallets · jobs · ledger · agent details
                </p>
              </section>
            </div>

            <AnimatePresence>
              {toast && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  className={`mx-4 mb-3 rounded border px-3 py-1.5 text-[11px] font-mono ${
                    toast.kind === "ok"
                      ? "border-success/40 bg-success/5 text-success"
                      : "border-danger/40 bg-danger/5 text-danger"
                  }`}
                >
                  {toast.text}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface ManualProps { onCopy: () => void; copied: boolean; note: string }
function ManualBlock({ onCopy, copied, note }: ManualProps) {
  return (
    <div className="rounded border border-pending/30 bg-pending/5 p-3 space-y-2">
      <p className="text-[10px] font-mono text-pending inline-flex items-center gap-1.5">
        <Terminal className="w-3 h-3" /> {note}
      </p>
      <pre className="text-[11px] font-mono text-text-primary bg-deep border border-line rounded px-2.5 py-1.5 leading-relaxed whitespace-pre-wrap">
{MANUAL_COMMAND}
      </pre>
      <button
        type="button"
        onClick={onCopy}
        className="w-full inline-flex items-center justify-center gap-2 h-8 rounded border border-line bg-sunken text-text-muted hover:text-text-primary hover:border-line/80 text-[10px] font-mono uppercase tracking-[0.14em] transition-colors"
      >
        {copied ? (
          <>
            <Check className="w-3 h-3 text-success" />
            <span className="text-success">copied</span>
          </>
        ) : (
          <>
            <Copy className="w-3 h-3" /> copy to clipboard
          </>
        )}
      </button>
    </div>
  );
}
