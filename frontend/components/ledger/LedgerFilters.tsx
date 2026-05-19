"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { useAppStore } from "@/lib/store";

const TX_TYPES = [
  "GENESIS", "ESCROW_LOCK", "MANAGER_FUNDING", "MILESTONE_RELEASE",
  "JUDGE_FEE", "PM_PROFIT", "AGENT_PAYMENT", "REFUND",
];

export interface LedgerFilterState {
  job: string;     // "all" | jobId
  type: string;    // "all" | TransactionType
  wallet: string;  // "all" | walletId
}

export function useLedgerFilters(): LedgerFilterState {
  const sp = useSearchParams();
  return {
    job: sp.get("job") ?? "all",
    type: sp.get("type") ?? "all",
    wallet: sp.get("wallet") ?? "all",
  };
}

export function LedgerFilters() {
  const router = useRouter();
  const sp = useSearchParams();
  const filters = useLedgerFilters();
  const transactions = useAppStore((s) => s.transactions);

  const jobOptions = useMemo(() => {
    const set = new Set<string>();
    for (const t of transactions) if (t.jobId) set.add(t.jobId);
    return ["all", ...Array.from(set).sort()];
  }, [transactions]);

  const walletOptions = useMemo(() => {
    const set = new Set<string>();
    for (const t of transactions) {
      set.add(t.fromWalletId);
      set.add(t.toWalletId);
    }
    set.delete("GENESIS");
    return ["all", ...Array.from(set).sort()];
  }, [transactions]);

  const set = (key: keyof LedgerFilterState, value: string) => {
    const params = new URLSearchParams(sp.toString());
    if (value === "all") params.delete(key);
    else params.set(key, value);
    const q = params.toString();
    router.replace(`/ledger${q ? `?${q}` : ""}`, { scroll: false });
  };

  return (
    <div className="border-b border-line bg-deep px-8 py-3 flex items-center gap-6 text-[10px] font-mono">
      <FilterSelect
        label="Job"
        value={filters.job}
        onChange={(v) => set("job", v)}
        options={jobOptions}
        format={(v) => (v === "all" ? "all jobs" : v.length > 22 ? `${v.slice(0, 10)}…${v.slice(-6)}` : v)}
      />
      <FilterSelect
        label="Type"
        value={filters.type}
        onChange={(v) => set("type", v)}
        options={["all", ...TX_TYPES]}
        format={(v) => (v === "all" ? "all types" : v)}
      />
      <FilterSelect
        label="Wallet"
        value={filters.wallet}
        onChange={(v) => set("wallet", v)}
        options={walletOptions}
        format={(v) => (v === "all" ? "any wallet" : v.length > 28 ? `${v.slice(0, 14)}…${v.slice(-8)}` : v)}
      />
      {(filters.job !== "all" || filters.type !== "all" || filters.wallet !== "all") && (
        <button
          type="button"
          onClick={() => router.replace("/ledger", { scroll: false })}
          className="ml-auto text-text-faint hover:text-text-primary uppercase tracking-[0.16em]"
        >
          clear filters
        </button>
      )}
    </div>
  );
}

interface FilterSelectProps {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  format?: (v: string) => string;
}

function FilterSelect({ label, value, options, onChange, format = (v) => v }: FilterSelectProps) {
  return (
    <label className="inline-flex items-center gap-2">
      <span className="text-text-faint uppercase tracking-[0.16em]">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-sunken border border-line text-text-primary rounded px-2 py-1 font-mono focus:outline-none focus:border-active/60 hover:border-line/80 cursor-pointer min-w-[160px]"
      >
        {options.map((o) => (
          <option key={o} value={o} className="bg-deep text-text-primary">
            {format(o)}
          </option>
        ))}
      </select>
    </label>
  );
}
