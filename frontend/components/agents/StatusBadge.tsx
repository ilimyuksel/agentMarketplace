"use client";

import { Badge } from "@/components/ui/badge";
import { AgentStatus } from "@/types";

const config: Record<AgentStatus, { label: string; className: string }> = {
  active:  { label: "Aktif",     className: "bg-[#dafbe1] text-[#1a7f37] border-[#aceebb]" },
  running: { label: "Çalışıyor", className: "bg-[#ddf4ff] text-[#0969da] border-[#54aeff] animate-pulse" },
  idle:    { label: "Bekliyor",  className: "bg-[#f6f8fa] text-[#656d76] border-[#d0d7de]" },
  error:   { label: "Hata",      className: "bg-[#ffebe9] text-[#cf222e] border-[#ffcecb]" },
};

export function StatusBadge({ status }: { status: AgentStatus }) {
  const { label, className } = config[status];
  return (
    <Badge variant="outline" className={`text-xs font-medium ${className}`}>
      <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </Badge>
  );
}
