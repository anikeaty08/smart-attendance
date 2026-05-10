"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Users, UserCheck, Building2, BookOpen,
  GitBranch, MonitorPlay, ClipboardList, Activity,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DashboardData {
  total_students: number;
  total_faculty: number;
  total_departments: number;
  total_subjects: number;
  total_offerings: number;
  total_sessions: number;
  active_sessions: number;
  total_attendance_records: number;
}

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
  sublabel,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  accent?: boolean;
  sublabel?: string;
}) {
  return (
    <div
      className={`relative p-6 border transition-all duration-300 hover:border-white/20 group ${
        accent
          ? "bg-[#eca8d6]/5 border-[#eca8d6]/20"
          : "bg-[oklch(0.09_0.008_260)] border-[oklch(0.14_0.008_260)]"
      }`}
    >
      <div className="flex items-start justify-between mb-4">
        <div
          className={`w-10 h-10 flex items-center justify-center ${
            accent ? "bg-[#eca8d6]/10" : "bg-white/5"
          }`}
        >
          <Icon className={`w-5 h-5 ${accent ? "text-[#eca8d6]" : "text-white/60"}`} />
        </div>
        {accent && (
          <span className="flex items-center gap-1.5 text-[10px] font-mono text-[#eca8d6] bg-[#eca8d6]/10 px-2 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#eca8d6] animate-pulse" />
            LIVE
          </span>
        )}
      </div>

      <div className="text-3xl lg:text-4xl font-display text-white mb-1 tabular-nums">
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div className="text-sm text-white/60">{label}</div>
      {sublabel && <div className="text-xs text-white/30 font-mono mt-1">{sublabel}</div>}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="p-6 border border-[oklch(0.14_0.008_260)] bg-[oklch(0.09_0.008_260)] animate-pulse">
      <div className="w-10 h-10 bg-white/5 mb-4" />
      <div className="h-10 bg-white/5 w-20 mb-2" />
      <div className="h-4 bg-white/5 w-28" />
    </div>
  );
}

export default function AdminDashboard() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [role, setRole] = useState<"admin" | "hod">("admin");

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }

    (async () => {
      try {
        const token = await getToken();

        // Get role
        const meRes = await fetch(`${API_BASE}/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!meRes.ok) {
          if (meRes.status === 403) router.replace("/first-login");
          return;
        }
        const me = await meRes.json();
        if (me.role === "student" || me.role === "faculty") {
          router.replace("/portal");
          return;
        }
        setRole(me.role);

        // Get dashboard data based on role
        const endpoint = me.role === "hod" ? "/hod/department" : "/admin/dashboard";
        const dashRes = await fetch(`${API_BASE}${endpoint}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!dashRes.ok) throw new Error("Failed to load dashboard");
        const dash = await dashRes.json();
        setData(dash);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, [isLoaded, isSignedIn, getToken, router]);

  const stats = data
    ? [
        { label: "Total students", value: data.total_students, icon: Users, sublabel: role === "admin" ? "All departments" : "In department" },
        { label: "Faculty members", value: data.total_faculty, icon: UserCheck, sublabel: role === "admin" ? "Active staff" : "In department" },
        ...(role === "admin"
          ? [{ label: "Departments", value: data.total_departments, icon: Building2, sublabel: "Across all branches" }]
          : []),
        { label: "Subjects", value: data.total_subjects, icon: BookOpen, sublabel: "In curriculum" },
        { label: "Offerings", value: data.total_offerings, icon: GitBranch, sublabel: "This semester" },
        ...(role === "admin"
          ? [{ label: "Total sessions", value: data.total_sessions, icon: MonitorPlay, sublabel: "All time" }]
          : []),
        {
          label: "Active sessions",
          value: data.active_sessions,
          icon: Activity,
          accent: true,
          sublabel: "Right now",
        },
        ...(role === "admin"
          ? [{ label: "Attendance records", value: data.total_attendance_records, icon: ClipboardList, sublabel: "Total verifications" }]
          : []),
      ]
    : [];

  return (
    <DashboardLayout role={role} pageTitle="Dashboard">
      <div className="max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <span className="w-8 h-px bg-white/20" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-widest">Overview</span>
          </div>
          <h2 className="text-4xl font-display text-white">
            Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}.
          </h2>
          <p className="text-white/40 text-sm mt-1 font-mono">
            {new Date().toLocaleDateString("en-IN", {
              weekday: "long", day: "numeric", month: "long", year: "numeric",
            })}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-400/10 border border-red-400/20 text-red-400 text-sm font-mono">
            {error}
          </div>
        )}

        {/* Stats grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)
            : stats.map((s) => (
                <StatCard
                  key={s.label}
                  label={s.label}
                  value={s.value}
                  icon={s.icon}
                  accent={"accent" in s ? s.accent : false}
                  sublabel={s.sublabel}
                />
              ))}
        </div>

        {/* Quick actions */}
        <div className="border-t border-[oklch(0.13_0.008_260)] pt-8">
          <h3 className="text-sm font-mono text-white/40 uppercase tracking-widest mb-4">Quick actions</h3>
          <div className="flex flex-wrap gap-3">
            {[
              { label: "Import Students", href: "/admin/students", desc: "Upload CSV" },
              { label: "Add Faculty", href: "/admin/faculty", desc: "New member" },
              ...(role === "admin" ? [
                { label: "Create Subject", href: "/admin/subjects", desc: "Curriculum" },
              ] : []),
              { label: "View Reports", href: "/admin/reports", desc: "Defaulters" },
              ...(role === "admin" ? [
                { label: "Live Sessions", href: "/admin/sessions", desc: "Monitor now" },
              ] : []),
            ].map((a) => (
              <a
                key={a.label}
                href={a.href}
                className="flex items-center gap-3 px-4 py-3 border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)] hover:border-white/30 hover:bg-white/5 transition-all group"
              >
                <div>
                  <div className="text-sm text-white group-hover:text-white transition-colors">{a.label}</div>
                  <div className="text-xs text-white/30 font-mono">{a.desc}</div>
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
