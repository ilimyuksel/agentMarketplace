"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/terminal", label: "Terminal" },
  { href: "/agents", label: "Agents" },
  { href: "/ledger", label: "Ledger" },
  { href: "/events", label: "Events" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="h-10 border-b border-line bg-deep flex items-center px-6 gap-6">
      {ITEMS.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`relative h-10 inline-flex items-center text-[10px] font-mono uppercase tracking-[0.18em] transition-colors ${
              active ? "text-active" : "text-text-faint hover:text-text-primary"
            }`}
          >
            {item.label}
            {active && (
              <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-active rounded-full" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
