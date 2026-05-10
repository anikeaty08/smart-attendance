"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Play, BarChart2, Clock, Users, BookOpen, ChevronRight } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Offering {
  id: number; subject_code: string; subject_name: string;
  section: string; semester: number; branch_code: string | null;
  academic_year: string; semester_type: string;
}

interface Summary {
  subject_offering_id: number; subject_code: string; subject_name: string;
  total_sessions: number; present_sessions: number; percentage: number;
}

function OfferingCard({ o, summary }: { o: Offering; summary?: Summary }) {
  const pct = summary?.percentage ?? 0;
  const sessions = summary?.total_sessions ?? 0;

  return (
    <div className="group relative bg-[oklch(0.09_0.008_260)] border border-[oklch(0.14_0.008_260)] hover:border-white/20 p-6 transition-all duration-300">
      {/* Accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#eca8d6] scale-x-0 group-hover:scale-x-100 transition-transform origin-left duration-300" />

      <div className="flex items-start justify-between mb-4">
        <div>
          <span className="text-xs font-mono text-white/40">{o.subject_code}</span>
          <h3 className="text-lg font-display text-white mt-1 leading-tight">{o.subject_name}</h3>
        </div>
        <Link
          href={`/teacher/session/start?offering=${o.id}`}
          id={`start-session-${o.id}`}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#eca8d6]/10 border border-[#eca8d6]/30 text-[#eca8d6] text-xs font-mono rounded-sm hover:bg-[#eca8d6]/20 transition-all"
        >
          <Play className="w-3 h-3" />Start
        </Link>
      </div>

      <div className="flex flex-wrap gap-3 mb-5 text-xs font-mono text-white/40">
        <span>Sem {o.semester}</span>
        <span>·</span>
        <span>Section {o.section}</span>
        <span>·</span>
        <span>{o.branch_code ?? "—"}</span>
        <span>·</span>
        <span>{o.academic_year}</span>
      </div>

      {/* Attendance bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-mono text-white/30">Avg attendance</span>
          <span className={`text-xs font-mono ${pct >= 75 ? "text-green-400" : pct >= 60 ? "text-yellow-400" : "text-red-400"}`}>
            {pct.toFixed(1)}%
          </span>
        </div>
        <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${pct >= 75 ? "bg-green-400" : pct >= 60 ? "bg-yellow-400" : "bg-red-400"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-[10px] font-mono text-white/20 mt-1">{sessions} session{sessions !== 1 ? "s" : ""} held</p>
      </div>
    </div>
  );
}

export default function TeacherDashboard() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [offerings, setOfferings] = useState<Offering[]>([]);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }

    (async () => {
      try {
        const token = await getToken();
        const [meRes, offeringsRes, reportRes] = await Promise.all([
          fetch(`${API_BASE}/me`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${API_BASE}/faculty/offerings`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${API_BASE}/faculty/attendance/report`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);

        if (meRes.ok) { 
          const me = await meRes.json(); 
          if (me.role === "student") {
            router.replace("/login");
            return;
          }
          setName(me.name ?? ""); 
        }
        if (offeringsRes.ok) setOfferings(await offeringsRes.json());
        if (reportRes.ok) setSummaries(await reportRes.json());
      } finally { setLoading(false); }
    })();
  }, [isLoaded, isSignedIn, getToken, router]);

  const summaryMap = Object.fromEntries(summaries.map((s) => [s.subject_offering_id, s]));

  return (
    <DashboardLayout role="faculty" pageTitle="My Subjects">
      <div className="max-w-6xl">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <span className="w-8 h-px bg-white/20" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-widest">Faculty Portal</span>
          </div>
          <h2 className="text-4xl font-display text-white">
            {name ? `Hello, ${name.split(" ")[0]}.` : "Your subjects."}
          </h2>
          <p className="text-white/40 text-sm mt-1 font-mono">
            {offerings.length} subject{offerings.length !== 1 ? "s" : ""} assigned this semester
          </p>
        </div>

        {/* Quick stat strip */}
        {!loading && summaries.length > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-10">
            {[
              {
                label: "Avg attendance",
                value: `${(summaries.reduce((a, s) => a + s.percentage, 0) / summaries.length).toFixed(1)}%`,
                icon: BarChart2,
              },
              {
                label: "Total sessions",
                value: summaries.reduce((a, s) => a + s.total_sessions, 0),
                icon: Clock,
              },
              {
                label: "Subjects",
                value: offerings.length,
                icon: BookOpen,
              },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.label} className="p-5 border border-[oklch(0.14_0.008_260)] bg-[oklch(0.09_0.008_260)]">
                  <Icon className="w-4 h-4 text-white/30 mb-3" />
                  <div className="text-2xl font-display text-white">{s.value}</div>
                  <div className="text-xs text-white/40 font-mono mt-1">{s.label}</div>
                </div>
              );
            })}
          </div>
        )}

        {/* Offerings grid */}
        {loading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-52 bg-[oklch(0.09_0.008_260)] border border-[oklch(0.14_0.008_260)] animate-pulse" />
            ))}
          </div>
        ) : offerings.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-white/10">
            <BookOpen className="w-10 h-10 text-white/20 mx-auto mb-4" />
            <p className="text-white/40 text-sm">No subjects assigned yet</p>
            <p className="text-white/20 text-xs font-mono mt-1">Contact your admin to get assigned</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {offerings.map((o) => (
              <OfferingCard key={o.id} o={o} summary={summaryMap[o.id]} />
            ))}
          </div>
        )}

        {/* Quick link to reports */}
        {!loading && offerings.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[oklch(0.13_0.008_260)]">
            <Link href="/teacher/reports"
              className="inline-flex items-center gap-2 text-sm text-white/40 hover:text-white transition-colors group">
              <BarChart2 className="w-4 h-4" />
              View detailed attendance reports
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
