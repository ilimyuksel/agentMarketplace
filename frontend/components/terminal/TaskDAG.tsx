"use client";

import { motion } from "framer-motion";
import type { Task, TaskState } from "@/types";

interface Props {
  tasks: Task[];
  selectedTaskId: string | null;
  onSelect: (id: string) => void;
}

const STATE_RING: Record<TaskState, string> = {
  PENDING:   "stroke-line",
  READY:     "stroke-active",
  BIDDING:   "stroke-active",
  ASSIGNED:  "stroke-active",
  RUNNING:   "stroke-active",
  DONE:      "stroke-success",
  VERIFYING: "stroke-pending",
  VERIFIED:  "stroke-success",
  PAID:      "stroke-success",
  REVISION:  "stroke-pending",
  REJECTED:  "stroke-danger",
  FAILED:    "stroke-danger",
};

const STATE_FILL: Record<TaskState, string> = {
  PENDING:   "fill-sunken",
  READY:     "fill-sunken",
  BIDDING:   "fill-active/10",
  ASSIGNED:  "fill-active/10",
  RUNNING:   "fill-active/15",
  DONE:      "fill-success/10",
  VERIFYING: "fill-pending/10",
  VERIFIED:  "fill-success/15",
  PAID:      "fill-success/25",
  REVISION:  "fill-pending/15",
  REJECTED:  "fill-danger/15",
  FAILED:    "fill-danger/15",
};

/** Position tasks in topological columns. Simple BFS for our 2- to 6-task DAGs. */
function layout(tasks: Task[]): Map<string, { col: number; row: number }> {
  const depth = new Map<string, number>();
  for (const t of tasks) {
    if (t.dependencies.length === 0) depth.set(t.id, 0);
  }
  // Iterate until all assigned (DAG, so finite).
  let safety = 10;
  while (depth.size < tasks.length && safety-- > 0) {
    for (const t of tasks) {
      if (depth.has(t.id)) continue;
      const deps = t.dependencies;
      if (deps.every((d) => depth.has(d))) {
        const d = deps.length === 0 ? 0 : 1 + Math.max(...deps.map((id) => depth.get(id) ?? 0));
        depth.set(t.id, d);
      }
    }
  }
  // Group tasks by column to assign rows.
  const byCol = new Map<number, string[]>();
  for (const t of tasks) {
    const c = depth.get(t.id) ?? 0;
    const arr = byCol.get(c) ?? [];
    arr.push(t.id);
    byCol.set(c, arr);
  }
  const pos = new Map<string, { col: number; row: number }>();
  for (const [col, ids] of byCol) {
    ids.forEach((id, i) => pos.set(id, { col, row: i }));
  }
  return pos;
}

export function TaskDAG({ tasks, selectedTaskId, onSelect }: Props) {
  if (tasks.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-line bg-surface/40 p-6 text-center">
        <p className="text-[11px] uppercase tracking-[0.18em] text-text-faint font-mono">
          DAG · awaiting plan
        </p>
        <p className="text-xs text-text-muted mt-2">
          The Project Manager will publish the sub-task graph here once planning starts.
        </p>
      </div>
    );
  }

  const pos = layout(tasks);
  const cols = Math.max(...Array.from(pos.values()).map((p) => p.col)) + 1;
  const rows = Math.max(...Array.from(pos.values()).map((p) => p.row)) + 1;

  const W = 700;
  const COL_W = W / cols;
  const ROW_H = 110;
  const H = ROW_H * rows + 40;
  const R = 40;

  function nodePos(id: string) {
    const p = pos.get(id);
    if (!p) return { x: 0, y: 0 };
    return {
      x: COL_W * p.col + COL_W / 2,
      y: ROW_H * p.row + ROW_H / 2 + 20,
    };
  }

  return (
    <div className="rounded-md border border-line bg-surface p-4 space-y-2">
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-[0.18em] text-text-faint font-mono">
          DAG · {tasks.length} sub-task{tasks.length === 1 ? "" : "s"}
        </span>
        <span className="text-[10px] text-text-faint font-mono">click a node to inspect</span>
      </div>
      <div className="overflow-x-auto">
        <svg width={W} height={H} className="block">
          {/* Edges */}
          {tasks.flatMap((t) =>
            t.dependencies.map((dep) => {
              const src = nodePos(dep);
              const dst = nodePos(t.id);
              const depTask = tasks.find((x) => x.id === dep);
              const satisfied = depTask?.state === "PAID";
              return (
                <line
                  key={`${dep}->${t.id}`}
                  x1={src.x + R} y1={src.y}
                  x2={dst.x - R} y2={dst.y}
                  stroke={satisfied ? "var(--success)" : "var(--line)"}
                  strokeWidth={1.5}
                  strokeDasharray={satisfied ? "0" : "4 3"}
                  opacity={0.8}
                />
              );
            })
          )}
          {/* Nodes */}
          {tasks.map((t) => {
            const { x, y } = nodePos(t.id);
            const isSelected = t.id === selectedTaskId;
            const isRunning = t.state === "RUNNING" || t.state === "BIDDING" || t.state === "VERIFYING";
            return (
              <g
                key={t.id}
                onClick={() => onSelect(t.id)}
                className="cursor-pointer"
              >
                <motion.circle
                  cx={x}
                  cy={y}
                  r={R}
                  className={`${STATE_FILL[t.state]} ${STATE_RING[t.state]} ${isSelected ? "stroke-2" : ""}`}
                  strokeWidth={isSelected ? 3 : 1.5}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                />
                {isRunning && (
                  <motion.circle
                    cx={x}
                    cy={y}
                    r={R}
                    fill="none"
                    stroke="var(--active)"
                    strokeWidth={2}
                    animate={{ scale: [1, 1.18, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                  />
                )}
                <foreignObject x={x - R} y={y - R} width={R * 2} height={R * 2}>
                  <div className="w-full h-full flex flex-col items-center justify-center text-center px-1 select-none">
                    <span className="text-[9px] font-mono uppercase tracking-wider text-text-faint">
                      {t.state.replace(/_/g, " ")}
                    </span>
                    <span className="text-[10px] text-text-primary font-mono leading-tight line-clamp-2 mt-0.5">
                      {t.title}
                    </span>
                  </div>
                </foreignObject>
                {t.judgeScore != null && t.state !== "RUNNING" && (
                  <g>
                    <circle cx={x + R - 4} cy={y - R + 4} r={11} fill="var(--deep)" stroke="var(--success)" strokeWidth={1} />
                    <text x={x + R - 4} y={y - R + 7.5} textAnchor="middle" fontSize="9" fill="var(--success)" fontFamily="var(--font-jetbrains)">
                      {t.judgeScore.toFixed(2)}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
