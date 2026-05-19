"use client";

import { useEffect, useState } from "react";
import { AddressChip } from "@/components/primitives/AddressChip";
import { MoneyTicker } from "@/components/primitives/MoneyTicker";
import { HashLink } from "@/components/primitives/HashLink";
import { StateBadge } from "@/components/primitives/StateBadge";
import { ReputationGauge } from "@/components/primitives/ReputationGauge";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border border-line rounded-lg bg-surface p-6 space-y-4">
      <h2 className="text-xs font-mono uppercase tracking-[0.18em] text-text-faint">
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}

export default function PreviewPage() {
  // Live-changing money for the ticker demo
  const [userBalance, setUserBalance] = useState(1000);
  const [escrowBalance, setEscrowBalance] = useState(0);
  const [pmBalance, setPmBalance] = useState(0);
  const [writerBalance, setWriterBalance] = useState(0);

  useEffect(() => {
    // Simulate the storyboard money-flow beats every 6 seconds
    const beats = [
      () => { setUserBalance(1000); setEscrowBalance(0); setPmBalance(0); setWriterBalance(0); },
      () => { setUserBalance(800); setEscrowBalance(200); },
      () => { setEscrowBalance(18); setPmBalance(182); },
      () => { setPmBalance(148.75); setWriterBalance(33.25); },
    ];
    let i = 0;
    const id = window.setInterval(() => {
      i = (i + 1) % beats.length;
      beats[i]();
    }, 2500);
    return () => window.clearInterval(id);
  }, []);

  const taskStates = [
    "PENDING", "READY", "BIDDING", "ASSIGNED", "RUNNING",
    "DONE", "VERIFYING", "VERIFIED", "PAID", "REVISION",
    "REJECTED", "FAILED",
  ];
  const jobStates = [
    "CREATED", "MANAGER_BIDDING", "PLANNING", "EXECUTING",
    "COMPLETED", "REJECTED", "FAILED", "CANCELLED",
  ];
  const txTypes = [
    "GENESIS", "ESCROW_LOCK", "MANAGER_FUNDING", "MILESTONE_RELEASE",
    "JUDGE_FEE", "PM_PROFIT", "AGENT_PAYMENT", "REFUND",
  ];
  const verdicts = ["APPROVED", "REVISION_REQUESTED", "REJECTED"];

  return (
    <div className="min-h-screen bg-deep text-text-primary">
      <header className="border-b border-line px-8 py-5">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-semibold tracking-tight" style={{ fontFamily: "var(--font-space-grotesk)" }}>
            NEXORA · Primitives Preview
          </h1>
          <span className="text-xs text-text-faint font-mono">step 1 / 8 — primitives</span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-8 space-y-6">
        <Section title="AddressChip · hover for full address + wallet_id · click to copy">
          <div className="flex flex-wrap gap-3">
            <AddressChip walletId="wallet_user_demo" tone="user" />
            <AddressChip walletId="wallet_escrow_job_abc123" tone="escrow" />
            <AddressChip walletId="wallet_projectmanager_001" tone="agent" />
            <AddressChip walletId="wallet_contentwriter_001" tone="agent" />
            <AddressChip walletId="wallet_qajudge_001" tone="agent" />
            <AddressChip walletId="wallet_system_fees" tone="system" />
            <AddressChip walletId="GENESIS" tone="genesis" />
          </div>
          <p className="text-[11px] text-text-faint mt-3 font-mono">
            real wallet_id stays accessible · displayed as Ethereum-shaped 0x address ·
            <kbd className="ml-1 px-1.5 py-0.5 bg-sunken rounded text-text-muted">click</kbd> copies the full address
          </p>
        </Section>

        <Section title="MoneyTicker · animates between values · cyan flash on increase, amber on decrease">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="space-y-2">
              <p className="text-[10px] text-text-faint uppercase tracking-wider">User</p>
              <MoneyTicker value={userBalance} size="xl" />
            </div>
            <div className="space-y-2">
              <p className="text-[10px] text-text-faint uppercase tracking-wider">Escrow</p>
              <MoneyTicker value={escrowBalance} size="xl" />
            </div>
            <div className="space-y-2">
              <p className="text-[10px] text-text-faint uppercase tracking-wider">PM_001</p>
              <MoneyTicker value={pmBalance} size="xl" />
            </div>
            <div className="space-y-2">
              <p className="text-[10px] text-text-faint uppercase tracking-wider">Writer_001</p>
              <MoneyTicker value={writerBalance} size="xl" />
            </div>
          </div>
          <p className="text-[11px] text-text-faint mt-4 font-mono">
            simulating storyboard beats (escrow lock → PM funding → milestone release) on a 2.5 s loop
          </p>
        </Section>

        <Section title="HashLink · real block hashes from the live ledger">
          <div className="flex flex-col gap-2">
            <HashLink
              hash="27ba0da4dce3b2983ae8833813bd8b7f4b72f068c9c654074a5bb2df476a202e"
              label="block 0 · genesis"
            />
            <HashLink
              hash="77aae7d27f7d715de95735e4567f1aff85472ddfbe2d30e5729c6fa9d083de6b"
              label="block 7"
            />
            <HashLink
              hash="a6d62555dafff04b0d5a44658b1db452b6e22b69bfb1d108c2cff482df6ce8f4"
              label="prev_hash"
            />
          </div>
          <p className="text-[11px] text-text-faint mt-3 font-mono">
            hover for full 64-char hash · click to copy
          </p>
        </Section>

        <Section title="StateBadge · 12 task states · 8 job states · 3 verdicts · 8 transaction types">
          <div className="space-y-4">
            <div>
              <p className="text-[10px] text-text-faint uppercase tracking-wider mb-2">Task state · 12</p>
              <div className="flex flex-wrap gap-1.5">
                {taskStates.map((s) => <StateBadge key={s} state={s} />)}
              </div>
            </div>
            <div>
              <p className="text-[10px] text-text-faint uppercase tracking-wider mb-2">Job state · 8</p>
              <div className="flex flex-wrap gap-1.5">
                {jobStates.map((s) => <StateBadge key={s} state={s} />)}
              </div>
            </div>
            <div>
              <p className="text-[10px] text-text-faint uppercase tracking-wider mb-2">Judge verdict</p>
              <div className="flex flex-wrap gap-1.5">
                {verdicts.map((s) => <StateBadge key={s} state={s} />)}
              </div>
            </div>
            <div>
              <p className="text-[10px] text-text-faint uppercase tracking-wider mb-2">Transaction type</p>
              <div className="flex flex-wrap gap-1.5">
                {txTypes.map((s) => <StateBadge key={s} state={s} />)}
              </div>
            </div>
            <div>
              <p className="text-[10px] text-text-faint uppercase tracking-wider mb-2">Ghost agent override</p>
              <div className="flex flex-wrap gap-1.5">
                <StateBadge state="GHOST · NEVER WINS" tone="ghost" />
              </div>
            </div>
          </div>
        </Section>

        <Section title="ReputationGauge · semicircle · color shifts at 0.50 / 0.70 / 0.85">
          <div className="flex flex-wrap gap-8 items-end">
            <div className="text-center">
              <ReputationGauge value={0.95} />
              <p className="text-[10px] text-text-faint mt-1 font-mono">qa_judge_001</p>
            </div>
            <div className="text-center">
              <ReputationGauge value={0.88} />
              <p className="text-[10px] text-text-faint mt-1 font-mono">contentwriter_001</p>
            </div>
            <div className="text-center">
              <ReputationGauge value={0.82} />
              <p className="text-[10px] text-text-faint mt-1 font-mono">projectmanager_001</p>
            </div>
            <div className="text-center">
              <ReputationGauge value={0.71} />
              <p className="text-[10px] text-text-faint mt-1 font-mono">designer_001 (underdog)</p>
            </div>
            <div className="text-center">
              <ReputationGauge value={0.65} />
              <p className="text-[10px] text-text-faint mt-1 font-mono">contentwriter_002 (ghost)</p>
            </div>
            <div className="text-center">
              <ReputationGauge value={0.45} />
              <p className="text-[10px] text-text-faint mt-1 font-mono">demo: failing agent</p>
            </div>
          </div>
        </Section>
      </main>
    </div>
  );
}
