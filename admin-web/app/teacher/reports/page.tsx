"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Download, BarChart2, BookOpen } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Summary {
  subject_offering_id: number;
  subject_code: string;
  subject_name: string;
  total_sessions: number;
  present_sessions: number;
  percentage: number;
}

export default function TeacherReportsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }
    (async () => {
      try {
        const token = await getToken();
        const res = await fetch(`${API_BASE}/faculty/attendance/report`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) setSummaries(await res.json());
      } finally { setLoading(false); }
    })();
  }, [isLoaded, isSignedIn, getToken, router]);

  async function exportCsv(offeringId: number, subjectCode: string) {
    const token = await getToken();
    const res = await fetch(`${API_BASE}/faculty/export/attendance?offering_id=${offeringId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `attendance_${subjectCode}.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <DashboardLayout role="faculty" pageTitle="Reports">
      <div className="max-w-5xl">
        <div className="mb-8">
          <h2 className="text-3xl font-display text-white">Attendance Reports</h2>
          <p className="text-white/40 text-sm mt-2">View aggregate attendance metrics and download full CSV reports for your subjects.</p>
        </div>

        <div className="grid gap-4">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-24 border border-[oklch(0.14_0.008_260)] bg-[oklch(0.09_0.008_260)] animate-pulse" />
            ))
          ) : summaries.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-white/10">
              <BarChart2 className="w-10 h-10 text-white/20 mx-auto mb-4" />
              <p className="text-white/40 text-sm">No attendance data yet.</p>
            </div>
          ) : (
            summaries.map(s => (
              <div key={s.subject_offering_id} className="p-6 border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)] flex flex-col md:flex-row items-start md:items-center justify-between gap-6 hover:border-[#eca8d6]/30 transition-colors">
                <div className="flex items-start gap-4 flex-1">
                  <div className="w-12 h-12 bg-white/5 flex items-center justify-center shrink-0">
                    <BookOpen className="w-5 h-5 text-white/40" />
                  </div>
                  <div>
                    <div className="text-xs font-mono text-[#eca8d6] mb-1">{s.subject_code}</div>
                    <h3 className="text-lg text-white font-medium">{s.subject_name}</h3>
                    <div className="text-xs text-white/40 font-mono mt-2">
                      {s.total_sessions} total sessions held
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-8 md:w-64 shrink-0">
                  <div className="flex-1">
                    <div className="flex justify-between text-xs font-mono mb-2">
                      <span className="text-white/40">Avg. Attendance</span>
                      <span className={s.percentage >= 75 ? "text-green-400" : s.percentage >= 60 ? "text-yellow-400" : "text-red-400"}>
                        {s.percentage.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                      <div className={`h-full ${s.percentage >= 75 ? "bg-green-400" : s.percentage >= 60 ? "bg-yellow-400" : "bg-red-400"}`} style={{ width: `${s.percentage}%` }} />
                    </div>
                  </div>
                </div>

                <button onClick={() => exportCsv(s.subject_offering_id, s.subject_code)}
                  className="flex items-center gap-2 h-10 px-4 bg-white text-black text-sm font-medium hover:bg-white/90 transition-colors rounded-sm shrink-0 w-full md:w-auto justify-center">
                  <Download className="w-4 h-4" /> Export CSV
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
