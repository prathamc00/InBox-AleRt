"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";
import {
  Inbox,
  Link2,
  Settings2,
  Bot,
  CreditCard,
  LogOut,
  Sparkles
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Inbox", icon: Inbox },
  { href: "/dashboard/auto-reply", label: "Autonomous", icon: Bot },
  { href: "/dashboard/accounts", label: "Integrations", icon: Link2 },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "/dashboard/settings", label: "Settings", icon: Settings2 },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, clearAuth } = useAuthStore();

  return (
    <aside className="w-64 shrink-0 flex flex-col h-full bg-void border-r border-border-subtle z-20">
      
      {/* Brand */}
      <div className="h-16 flex items-center px-6 border-b border-border-subtle/50">
        <Link href="/dashboard" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
          <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-black" />
          </div>
          <span className="font-semibold text-sm tracking-tight text-white">InboxAlert</span>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-6 space-y-0.5">
        <div className="px-3 mb-2 text-xs font-medium text-text-tertiary tracking-wider uppercase">Menu</div>
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                active
                  ? "bg-surface-raised text-text-primary shadow-sm border border-border-subtle"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface border border-transparent"
              )}
            >
              <Icon className={cn("w-4 h-4", active ? "text-text-primary" : "text-text-tertiary group-hover:text-text-secondary")} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="p-4 border-t border-border-subtle/50">
        <div className="flex items-center justify-between group">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-surface-raised flex items-center justify-center text-xs font-medium border border-border-subtle text-text-secondary shrink-0">
              {user?.display_name?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className="truncate">
              <p className="text-sm font-medium truncate text-text-primary">{user?.display_name ?? "User"}</p>
              <p className="text-xs text-text-tertiary truncate">{user?.email ?? "user@example.com"}</p>
            </div>
          </div>
          <button
            onClick={(e) => { e.preventDefault(); clearAuth(); }}
            className="p-2 text-text-tertiary hover:text-text-primary rounded-md transition-colors"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
