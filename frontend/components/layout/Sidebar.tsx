"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Store, Wallet, GitBranch, Settings, Zap } from "lucide-react";

const navItems = [
  { href: "/dashboard",   label: "Dashboard",   icon: LayoutDashboard },
  { href: "/marketplace", label: "Marketplace", icon: Store },
  { href: "/pipeline",    label: "Pipeline",    icon: GitBranch },
  { href: "/wallet",      label: "Wallet",      icon: Wallet },
  { href: "/settings",    label: "Ayarlar",     icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-white border-r border-gray-100 flex flex-col z-40">
      <div className="p-5 border-b border-gray-100">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-black flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-base text-black tracking-tight">AgentFlow</span>
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                active
                  ? "bg-black text-white"
                  : "text-gray-400 hover:text-black hover:bg-gray-50"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center">
            <span className="text-xs text-white font-bold">D</span>
          </div>
          <div>
            <p className="text-xs font-semibold text-black leading-tight">Demo User</p>
            <p className="text-[10px] text-gray-400">Ücretsiz Plan</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
