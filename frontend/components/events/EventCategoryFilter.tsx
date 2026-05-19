"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { useAppStore } from "@/lib/store";
import { categoryFor, ALL_CATEGORIES, type EventCategory } from "@/lib/events";

export type FilterValue = "ALL" | EventCategory;

export function useEventCategoryFilter(): FilterValue {
  const sp = useSearchParams();
  const raw = sp.get("category")?.toUpperCase() ?? "ALL";
  const valid: FilterValue[] = ["ALL", ...ALL_CATEGORIES];
  return (valid as string[]).includes(raw) ? (raw as FilterValue) : "ALL";
}

export function EventCategoryFilter() {
  const router = useRouter();
  const sp = useSearchParams();
  const active = useEventCategoryFilter();
  const events = useAppStore(useShallow((s) => s.events));

  const counts = useMemo(() => {
    const c: Record<string, number> = { ALL: events.length };
    for (const cat of ALL_CATEGORIES) c[cat] = 0;
    for (const e of events) {
      const cat = categoryFor(e.eventType);
      if (cat !== "OTHER") c[cat] = (c[cat] ?? 0) + 1;
    }
    return c;
  }, [events]);

  const setFilter = (cat: FilterValue) => {
    const params = new URLSearchParams(sp.toString());
    if (cat === "ALL") params.delete("category");
    else params.set("category", cat.toLowerCase());
    const q = params.toString();
    router.replace(`/events${q ? `?${q}` : ""}`, { scroll: false });
  };

  const tabs: FilterValue[] = ["ALL", ...ALL_CATEGORIES];

  return (
    <div className="border-b border-line bg-deep px-8 py-3 flex flex-wrap items-center gap-1.5">
      {tabs.map((t) => {
        const isActive = active === t;
        return (
          <button
            key={t}
            type="button"
            onClick={() => setFilter(t)}
            className={`px-3 h-7 rounded text-[10px] font-mono uppercase tracking-[0.16em] transition-colors inline-flex items-center gap-1.5 ${
              isActive
                ? "bg-active/15 border border-active/40 text-active"
                : "border border-line text-text-muted hover:text-text-primary hover:border-line/80"
            }`}
          >
            {t}
            <span className={isActive ? "text-active/70" : "text-text-faint"}>
              {counts[t] ?? 0}
            </span>
          </button>
        );
      })}
    </div>
  );
}
