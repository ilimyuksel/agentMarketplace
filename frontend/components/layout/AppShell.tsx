"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Store, Wallet, Briefcase, PlusCircle, Settings, Zap,
} from "lucide-react";
import { useAppStore } from "@/lib/store";

const navItems = [
  { href: "/dashboard",   label: "Dashboard",   icon: LayoutDashboard },
  { href: "/pipeline",    label: "New Job",      icon: PlusCircle },
  { href: "/jobs",        label: "Jobs",         icon: Briefcase },
  { href: "/marketplace", label: "Marketplace",  icon: Store },
  { href: "/wallet",      label: "Wallet",       icon: Wallet },
  { href: "/settings",    label: "Ayarlar",      icon: Settings },
];

function TopNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 bg-[#0d1220] border-b border-[#1e2d4a]">
      <div className="flex items-center h-13 px-6 gap-6">
        <Link href="/" className="flex items-center gap-2 flex-shrink-0 mr-2">
          <div className="w-7 h-7 rounded-lg bg-[#3B82F6] flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-sm text-[#F8FAFC] tracking-tight" style={{ fontFamily: "var(--font-space-grotesk)" }}>NEXORA</span>
        </Link>

        <nav className="flex items-center gap-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                  active
                    ? "bg-[#3B82F6] text-white"
                    : "text-[#94a3b8] hover:text-[#F8FAFC] hover:bg-[#1a2440]"
                }`}
              >
                <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex-1" />

        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[#3B82F6] flex items-center justify-center">
            <span className="text-[10px] text-white font-bold">D</span>
          </div>
          <div className="hidden sm:block">
            <p className="text-xs font-semibold text-[#F8FAFC] leading-tight">Demo User</p>
            <p className="text-[10px] text-[#94a3b8]">user_demo</p>
          </div>
        </div>
      </div>
    </header>
  );
}

function OfflineBanner() {
  const backendChecked = useAppStore((s) => s.backendChecked);
  const backendOnline = useAppStore((s) => s.backendOnline);
  if (!backendChecked || backendOnline) return null;
  return (
    <div className="bg-amber-500/15 border-b border-amber-500/30 text-amber-200 text-xs px-6 py-2 text-center">
      Offline mode — backend unreachable. Showing simulation data.
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const checkBackend = useAppStore((s) => s.checkBackend);
  useEffect(() => { checkBackend(); }, [checkBackend]);

  return (
    <div className="min-h-screen bg-[#0B1020]">
      <TopNav />
      <OfflineBanner />
      <main>{children}</main>
    </div>
  );
}
