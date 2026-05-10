"use client";

import { useState, createContext, useContext } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useClerk, useUser } from "@clerk/nextjs";
import {
  LayoutDashboard, Users, UserCheck, BookOpen, Building2,
  GitBranch, ClipboardList, Calendar, BarChart2,
  MonitorPlay, FileText, LogOut, Menu, X, ChevronRight,
} from "lucide-react";

// ─── Context ────────────────────────────────────────────────────────────────
interface SidebarCtx { collapsed: boolean; setCollapsed: (v: boolean) => void; }
const SidebarContext = createContext<SidebarCtx>({ collapsed: false, setCollapsed: () => {} });
export const useSidebar = () => useContext(SidebarContext);

// ─── Nav config ─────────────────────────────────────────────────────────────
const adminNav = [
  { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { label: "Students", href: "/admin/students", icon: Users },
  { label: "Faculty", href: "/admin/faculty", icon: UserCheck },
  { label: "Departments", href: "/admin/departments", icon: Building2 },
  { label: "Subjects", href: "/admin/subjects", icon: BookOpen },
  { label: "Offerings", href: "/admin/offerings", icon: GitBranch },
  { label: "Enrollments", href: "/admin/enrollments", icon: ClipboardList },
  { label: "Academic Years", href: "/admin/academic-years", icon: Calendar },
  { label: "Reports", href: "/admin/reports", icon: BarChart2 },
  { label: "Sessions", href: "/admin/sessions", icon: MonitorPlay },
  { label: "Corrections", href: "/admin/corrections", icon: FileText },
];

const hodNav = [
  { label: "Department", href: "/admin", icon: LayoutDashboard },
  { label: "Students", href: "/admin/students", icon: Users },
  { label: "Faculty", href: "/admin/faculty", icon: UserCheck },
  { label: "Offerings", href: "/admin/offerings", icon: GitBranch },
  { label: "Timetable", href: "/admin/timetable", icon: Calendar },
  { label: "Substitutes", href: "/admin/substitutes", icon: UserCheck },
  { label: "Leave Requests", href: "/admin/leave-requests", icon: FileText },
  { label: "Reports", href: "/admin/reports", icon: BarChart2 },
  { label: "Corrections", href: "/admin/corrections", icon: FileText },
];

const teacherNav = [
  { label: "My Subjects", href: "/teacher", icon: BookOpen },
  { label: "Start Session", href: "/teacher/session/start", icon: MonitorPlay },
  { label: "Reports", href: "/teacher/reports", icon: BarChart2 },
];

// ─── Nav Item ────────────────────────────────────────────────────────────────
function NavItem({
  item,
  collapsed,
}: {
  item: { label: string; href: string; icon: React.ElementType };
  collapsed: boolean;
}) {
  const pathname = usePathname();
  const isActive =
    item.href === "/admin" || item.href === "/teacher"
      ? pathname === item.href
      : pathname.startsWith(item.href);
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={`group flex items-center gap-3 px-3 py-2.5 rounded-sm transition-all duration-200 text-sm ${
        isActive
          ? "bg-white/8 text-white border-l-2 border-[#eca8d6] pl-[10px]"
          : "text-white/50 hover:text-white hover:bg-white/5 border-l-2 border-transparent"
      }`}
    >
      <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-[#eca8d6]" : ""}`} />
      {!collapsed && <span className="truncate">{item.label}</span>}
      {!collapsed && isActive && <ChevronRight className="w-3 h-3 ml-auto text-[#eca8d6]" />}
    </Link>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────
function Sidebar({
  navItems,
  role,
}: {
  navItems: typeof adminNav;
  role: string;
}) {
  const { collapsed, setCollapsed } = useSidebar();
  const { signOut } = useClerk();
  const { user } = useUser();

  return (
    <aside
      className={`fixed top-0 left-0 h-full z-40 flex flex-col bg-[oklch(0.08_0.008_260)] border-r border-[oklch(0.13_0.008_260)] transition-all duration-300 ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Top */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-[oklch(0.13_0.008_260)]">
        {!collapsed && (
          <Link href="/" className="flex items-center gap-2">
            <span className="text-lg font-display text-white font-bold">InSync</span>
            <span className="text-[10px] text-white/30 font-mono">
              {role === "admin" || role === "hod" ? "Admin" : "Faculty"}
            </span>
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-8 h-8 flex items-center justify-center text-white/40 hover:text-white transition-colors rounded-sm hover:bg-white/5"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <Menu className="w-4 h-4" /> : <X className="w-4 h-4" />}
        </button>
      </div>

      {/* Role badge */}
      {!collapsed && (
        <div className="px-4 py-3 border-b border-[oklch(0.13_0.008_260)]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#eca8d6] animate-pulse" />
            <span className="text-[11px] font-mono text-[#eca8d6] uppercase tracking-widest">
              {role}
            </span>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-4 space-y-0.5">
        {navItems.map((item) => (
          <NavItem key={item.href} item={item} collapsed={collapsed} />
        ))}
      </nav>

      {/* User + sign out */}
      <div className="border-t border-[oklch(0.13_0.008_260)] p-3">
        {!collapsed && (
          <div className="px-2 mb-3">
            <p className="text-xs text-white/80 truncate">
              {user?.primaryEmailAddress?.emailAddress}
            </p>
            <p className="text-[10px] text-white/30 font-mono mt-0.5">BMS Institute</p>
          </div>
        )}
        <button
          id="sign-out-btn"
          onClick={() => signOut({ redirectUrl: "/login" })}
          className={`w-full flex items-center gap-3 px-3 py-2 text-white/40 hover:text-red-400 hover:bg-red-400/5 rounded-sm transition-all text-sm ${
            collapsed ? "justify-center" : ""
          }`}
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  );
}

// ─── Topbar ───────────────────────────────────────────────────────────────────
function Topbar({ title }: { title?: string }) {
  const { collapsed } = useSidebar();
  const pathname = usePathname();

  // Auto-derive title from path
  const derivedTitle = title ?? (() => {
    const segment = pathname.split("/").filter(Boolean).pop() ?? "dashboard";
    return segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " ");
  })();

  return (
    <header
      className={`fixed top-0 right-0 z-30 h-14 flex items-center justify-between px-6 border-b border-[oklch(0.13_0.008_260)] bg-[oklch(0.06_0.008_260)]/90 backdrop-blur-sm transition-all duration-300 ${
        collapsed ? "left-16" : "left-60"
      }`}
    >
      <div className="flex items-center gap-3">
        <span className="w-1 h-4 bg-[#eca8d6] rounded-full" />
        <h1 className="text-sm font-medium text-white">{derivedTitle}</h1>
      </div>
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-2 px-2 py-1 bg-[#eca8d6]/10 text-[#eca8d6] text-[10px] font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-[#eca8d6] animate-pulse" />
          LIVE
        </span>
      </div>
    </header>
  );
}

// ─── Main Layout ──────────────────────────────────────────────────────────────
interface DashboardLayoutProps {
  children: React.ReactNode;
  role: "admin" | "hod" | "faculty";
  pageTitle?: string;
}

export function DashboardLayout({ children, role, pageTitle }: DashboardLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const navItems = role === "admin" ? adminNav : role === "hod" ? hodNav : teacherNav;

  return (
    <SidebarContext.Provider value={{ collapsed, setCollapsed }}>
      <div className="min-h-screen bg-[oklch(0.06_0.008_260)] text-white">
        <Sidebar navItems={navItems} role={role} />
        <Topbar title={pageTitle} />
        <main
          className={`pt-14 transition-all duration-300 ${collapsed ? "pl-16" : "pl-60"}`}
        >
          <div className="p-6 lg:p-8">{children}</div>
        </main>
      </div>
    </SidebarContext.Provider>
  );
}
