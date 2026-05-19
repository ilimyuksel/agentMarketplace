"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import type { Job, JobState, Task } from "@/types";

const ORDER: JobState[] = [
  "CREATED",
  "ESCROW_LOCK",
  "MANAGER_BIDDING",
  "PLANNING",
  "EXECUTING",
  "COMPLETED",
];

function isTerminal(s: JobState): boolean {
  return s === "COMPLETED" || s === "FAILED" || s === "REJECTED" || s === "CANCELLED";
}

function useElapsedSeconds(startedAtIso: string | null | undefined) {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    if (!startedAtIso) return;
    const start = new Date(startedAtIso).getTime();
    const tick = () => setSecs(Math.max(0, Math.floor((Date.now() - start) / 1000)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [startedAtIso]);
  return secs;
}

function formatElapsed(s: number): string {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

function reachedIndex(job: Job, tasks?: Task[]): number {
  // Live path: state is in the ordered set.
  const direct = ORDER.indexOf(job.state as JobState);
  if (direct >= 0) return direct;
  // Terminal path: infer how far we got from job fields.
  if ((tasks?.length ?? 0) > 0) return ORDER.indexOf("EXECUTING");
  if (job.assignedManagerId) return ORDER.indexOf("PLANNING");
  if (job.escrowWalletId) return ORDER.indexOf("ESCROW_LOCK");
  return 0;
}

export function JobStatePipeline({ job, tasks }: { job: Job; tasks?: Task[] }) {
  const elapsed = useElapsedSeconds(job.createdAt);
  const failed = job.state === "FAILED" || job.state === "REJECTED" || job.state === "CANCELLED";
  const completed = job.state === "COMPLETED";
  const final = isTerminal(job.state as JobState);
  const directIdx = ORDER.indexOf(job.state as JobState);
  const idx = final ? reachedIndex(job, tasks) : directIdx;

  return (
    <div className="rounded-md border border-line bg-surface p-4 space-y-3">
      <div className="flex items-baseline justify-between">
        <div className="flex items-baseline gap-3">
          <span className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
            Job
          </span>
          <span className="text-[11px] font-mono text-text-primary">
            {job.id}
          </span>
          {job.budgetTier && (
            <span className="text-[10px] font-mono text-text-faint">
              · {job.budgetTier} · {moneyShort(job.budget)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono">
          <span className="text-text-faint">elapsed</span>
          <span className="text-text-primary tabular-nums">{formatElapsed(elapsed)}</span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        {ORDER.map((s, i) => {
          // "reached" means this state was achieved at some point.
          //   - Live: every step <= current index is reached.
          //   - Terminal-failed: every step <= the inferred max reached is "done";
          //     the next step is marked as the failure pill (handled below).
          const reached = failed ? i <= idx : i <= (idx === -1 ? -1 : idx);
          const isCurrent = i === directIdx && !final;
          const isLast = i === ORDER.length - 1;
          const failedHere = failed && i === idx + 1 && i < ORDER.length;

          const bg = failedHere
            ? "bg-danger/20 border-danger/60 text-danger"
            : isCurrent
            ? "bg-active/15 border-active/60 text-active"
            : reached
            ? "bg-success/15 border-success/60 text-success"
            : "bg-sunken border-line text-text-faint";

          return (
            <div key={s} className="flex items-center flex-1 min-w-0">
              <motion.div
                className={`flex-1 h-9 rounded border ${bg} flex items-center justify-center px-2 min-w-0 transition-colors`}
                animate={isCurrent ? { boxShadow: ["0 0 0 0 rgba(34,211,238,0.0)", "0 0 0 4px rgba(34,211,238,0.18)", "0 0 0 0 rgba(34,211,238,0.0)"] } : { boxShadow: "0 0 0 0 rgba(34,211,238,0)" }}
                transition={{ duration: 1.6, repeat: isCurrent ? Infinity : 0, ease: "easeInOut" }}
              >
                <span className="text-[9px] font-mono uppercase tracking-[0.08em] truncate">
                  {s.replace(/_/g, " ")}
                </span>
              </motion.div>
              {!isLast && (
                <div className={`w-3 h-px ${reached ? "bg-success/60" : "bg-line"} flex-shrink-0`} />
              )}
            </div>
          );
        })}
        {failed && (
          <div className="ml-3 flex items-center gap-2">
            <div className="h-9 px-3 rounded border border-danger/60 bg-danger/20 text-danger text-[9px] font-mono uppercase tracking-[0.08em] flex items-center">
              {job.state}
            </div>
          </div>
        )}
      </div>

      {failed && job.failureReason && (
        <p className="text-[11px] text-danger font-mono">
          reason: {job.failureReason}
        </p>
      )}
      {completed && (
        <p className="text-[11px] text-success font-mono">
          settled · ready for verification
        </p>
      )}
    </div>
  );
}

function moneyShort(n: number): string {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}
