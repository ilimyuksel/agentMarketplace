"use client";

import { useEffect } from "react";
import { RotateCcw } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { useAppStore } from "@/lib/store";
import { JobStatePipeline } from "./JobStatePipeline";
import { TaskDAG } from "./TaskDAG";
import { TaskDetailPanel } from "./TaskDetailPanel";
import { ReconciliationStrip } from "./ReconciliationStrip";

export function RunningView({ jobId }: { jobId: string }) {
  const job = useAppStore((s) => s.jobs.find((j) => j.id === jobId));
  const tasks = useAppStore(
    useShallow((s) => s.tasks.filter((t) => t.jobId === jobId))
  );
  const selectedTaskId = useAppStore((s) => s.selectedTaskId);
  const setSelectedTaskId = useAppStore((s) => s.setSelectedTaskId);
  const resetJob = useAppStore((s) => s.resetJob);

  // Auto-select the first task as soon as one materializes, so the detail
  // panel populates without the juror having to click.
  useEffect(() => {
    if (!selectedTaskId && tasks.length > 0) setSelectedTaskId(tasks[0].id);
  }, [tasks, selectedTaskId, setSelectedTaskId]);

  if (!job) {
    return (
      <div className="rounded-md border border-dashed border-line bg-surface/40 p-6 text-center">
        <p className="text-[11px] uppercase tracking-[0.18em] text-text-faint font-mono">
          Hydrating job…
        </p>
      </div>
    );
  }

  const terminal = job.state === "COMPLETED" || job.state === "FAILED" || job.state === "REJECTED" || job.state === "CANCELLED";

  return (
    <div className="space-y-4">
      <JobStatePipeline job={job} tasks={tasks} />
      <TaskDAG tasks={tasks} selectedTaskId={selectedTaskId} onSelect={setSelectedTaskId} />
      <TaskDetailPanel />

      {job.state === "COMPLETED" && <ReconciliationStrip jobId={jobId} />}

      {terminal && (
        <div className="flex items-center justify-between rounded-md border border-line bg-surface px-4 py-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
              Job terminal · {job.state}
            </p>
            <p className="text-[11px] text-text-muted mt-0.5">
              {job.state === "COMPLETED"
                ? "All payments settled. Open ledger to verify the chain."
                : job.failureReason
                ? `Reason: ${job.failureReason}`
                : "No further events expected."}
            </p>
          </div>
          <button
            type="button"
            onClick={resetJob}
            className="inline-flex items-center gap-2 h-9 px-4 rounded-md border border-active/40 bg-active/10 hover:bg-active/15 text-active text-xs font-mono uppercase tracking-[0.14em] transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Submit another job
          </button>
        </div>
      )}
    </div>
  );
}
