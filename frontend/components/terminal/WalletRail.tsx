"use client";

import { useAppStore } from "@/lib/store";
import { AddressChip } from "@/components/primitives/AddressChip";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";
import { ReputationGauge } from "@/components/primitives/ReputationGauge";
import { AddFundsButton } from "./AddFundsButton";
import type { Agent, Wallet } from "@/types";

type Tone = "user" | "escrow" | "agent" | "system" | "genesis";

interface CardConfig {
  walletId: string;
  title: string;
  subtitle?: string;
  tagline?: string;
  tone: Tone;
  hero?: boolean;
  agentId?: string;
  accent?: "premium" | "underdog";
  label?: string;
}

function WalletCard({
  cfg,
  wallet,
  agent,
}: {
  cfg: CardConfig;
  wallet: Wallet | undefined;
  agent?: Agent;
}) {
  const balance = wallet?.balance ?? 0;
  const accentBorder =
    cfg.accent === "premium" ? "border-success/30"
    : cfg.accent === "underdog" ? "border-pending/30"
    : "border-line";

  return (
    <div
      className={`relative rounded-md border ${accentBorder} bg-surface ${
        cfg.hero ? "p-4" : "p-3"
      }`}
    >
      {cfg.label && (
        <span className="absolute top-2 right-2 text-[8px] uppercase tracking-[0.16em] text-pending font-mono">
          {cfg.label}
        </span>
      )}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className={`text-[11px] font-mono text-text-primary truncate ${cfg.hero ? "font-semibold" : ""}`}>
              {cfg.title}
            </span>
            {agent && (
              <span className="text-[9px] text-text-faint font-mono">
                rep {(agent.reputation ?? 0).toFixed(2)}
              </span>
            )}
          </div>
          {cfg.subtitle && (
            <p className="text-[9px] text-text-faint mt-0.5">{cfg.subtitle}</p>
          )}
        </div>
        {agent && <ReputationGauge value={agent.reputation} size={32} label={false} />}
      </div>
      <div className={`${cfg.hero ? "mt-2" : "mt-1.5"}`}>
        <MoneyTicker value={balance} size={cfg.hero ? "2xl" : "lg"} />
      </div>
      {cfg.walletId !== "__hidden__" && (
        <div className="mt-2">
          <AddressChip walletId={cfg.walletId} tone={cfg.tone} size="sm" />
        </div>
      )}
      {cfg.tagline && (
        <p className="text-[9px] text-text-faint mt-1.5 leading-relaxed">
          {cfg.tagline}
        </p>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-faint px-1">
      {children}
    </p>
  );
}

export function WalletRail() {
  const wallets = useAppStore((s) => s.wallets);
  const agents = useAppStore((s) => s.agents);
  const activeJobId = useAppStore((s) => s.activeJobId);

  const walletById = new Map(wallets.map((w) => [w.id, w]));
  const agentById = new Map(agents.map((a) => [a.id, a]));

  const escrowWalletId = activeJobId ? `wallet_escrow_${activeJobId}` : null;
  const escrowWallet = escrowWalletId ? walletById.get(escrowWalletId) : undefined;

  return (
    <aside className="border-l border-line bg-deep h-full overflow-y-auto">
      <div className="p-5 space-y-6">
        <section className="space-y-3">
          <SectionLabel>User</SectionLabel>
          <div className="relative rounded-md border border-line bg-surface p-4">
            <span className="absolute top-3 right-3 text-[9px] uppercase tracking-[0.16em] text-pending font-mono">
              Demo starting credit
            </span>
            <p className="text-[11px] font-mono text-text-primary font-semibold">
              USER WALLET
            </p>
            <div className="mt-3">
              <MoneyTicker value={walletById.get("wallet_user_demo")?.balance ?? 0} size="2xl" />
            </div>
            <div className="mt-2">
              <AddressChip walletId="wallet_user_demo" tone="user" size="sm" />
            </div>
            <div className="mt-4">
              <AddFundsButton />
            </div>
            <p className="text-[10px] text-text-faint mt-3 leading-relaxed">
              seeded · day-zero balance · genesis block #0
            </p>
          </div>
        </section>

        <section className="space-y-3">
          <SectionLabel>Escrow</SectionLabel>
          {activeJobId ? (
            <div className="rounded-md border border-pending/40 bg-pending/5 p-3">
              <div className="flex items-baseline justify-between">
                <p className="text-[11px] font-mono text-pending">ESCROW · ACTIVE</p>
                <span className="text-[9px] text-text-faint font-mono">job {activeJobId.slice(-8)}</span>
              </div>
              <div className="mt-1.5">
                <MoneyTicker value={escrowWallet?.balance ?? 0} size="lg" />
              </div>
              {escrowWallet && (
                <div className="mt-2">
                  <AddressChip walletId={escrowWallet.id} tone="escrow" size="sm" />
                </div>
              )}
              <p className="text-[9px] text-text-faint mt-1.5 leading-relaxed">
                locks the user budget · refunds the unspent remainder
              </p>
            </div>
          ) : (
            <div className="rounded-md border border-dashed border-line bg-surface/40 p-3">
              <p className="text-[11px] font-mono text-text-muted">ESCROW</p>
              <p className="text-[9px] text-text-faint mt-0.5">awaiting first job</p>
              <p className="text-[9px] text-text-faint mt-2 leading-relaxed">
                locks the user budget the moment a job is submitted
              </p>
            </div>
          )}
        </section>

        <section className="space-y-3">
          <SectionLabel>Manager</SectionLabel>
          <WalletCard
            cfg={{
              walletId: "wallet_projectmanager_001",
              title: "ProjectManager_001",
              tone: "agent",
              tagline: "aggressive bidder · 15–22% margin",
              agentId: "ProjectManager_001",
            }}
            wallet={walletById.get("wallet_projectmanager_001")}
            agent={agentById.get("ProjectManager_001")}
          />
        </section>

        <section className="space-y-3">
          <SectionLabel>Workers</SectionLabel>
          <WalletCard
            cfg={{
              walletId: "wallet_marketresearcher_001",
              title: "MarketResearcher_001",
              tone: "agent",
              tagline: "McKinsey-grade analyst",
              agentId: "MarketResearcher_001",
            }}
            wallet={walletById.get("wallet_marketresearcher_001")}
            agent={agentById.get("MarketResearcher_001")}
          />
          <WalletCard
            cfg={{
              walletId: "wallet_contentwriter_001",
              title: "ContentWriter_001",
              tone: "agent",
              accent: "premium",
              tagline: "premium bidder · highest reputation",
              agentId: "ContentWriter_001",
            }}
            wallet={walletById.get("wallet_contentwriter_001")}
            agent={agentById.get("ContentWriter_001")}
          />
          <WalletCard
            cfg={{
              walletId: "wallet_webdeveloper_001",
              title: "WebDeveloper_001",
              tone: "agent",
              tagline: "ships running HTML · critical-path skill",
              agentId: "WebDeveloper_001",
            }}
            wallet={walletById.get("wallet_webdeveloper_001")}
            agent={agentById.get("WebDeveloper_001")}
          />
          <WalletCard
            cfg={{
              walletId: "wallet_designer_001",
              title: "Designer_001",
              tone: "agent",
              accent: "underdog",
              tagline: "underdog · 10% discount when rep < 0.80",
              agentId: "Designer_001",
            }}
            wallet={walletById.get("wallet_designer_001")}
            agent={agentById.get("Designer_001")}
          />
        </section>

        <section className="space-y-3">
          <SectionLabel>Judge</SectionLabel>
          <WalletCard
            cfg={{
              walletId: "wallet_qajudge_001",
              title: "QAJudge_001",
              tone: "agent",
              tagline: "$2 per evaluation · regardless of verdict",
              agentId: "QAJudge_001",
            }}
            wallet={walletById.get("wallet_qajudge_001")}
            agent={agentById.get("QAJudge_001")}
          />
        </section>

        <section className="space-y-3">
          <SectionLabel>System</SectionLabel>
          <WalletCard
            cfg={{
              walletId: "wallet_system_fees",
              title: "SYSTEM FEES",
              tone: "system",
              tagline: "platform fee sink · empty in v1",
            }}
            wallet={walletById.get("wallet_system_fees")}
          />
        </section>
      </div>
    </aside>
  );
}
