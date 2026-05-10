"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Clock, MonitorPlay, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Session {
  id: number;
  subject_code: string;
  subject_name: string;
  faculty_name: string;
  session_type: string;
  status: string;
  starts_at: string;
  ends_at: string;
  radius_meters: number;
}

export default function AdminSessionsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }
    (async () => {
      try {
        const token = await getToken();
        // Since we don't have a specific GET /admin/sessions endpoint documented in detail, 
        // assuming it exists and returns a list. If it requires pagination, we can add it later.
        const res = await fetch(`${API_BASE}/admin/sessions`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setSessions(data.items ?? []);
        }
      } finally { setLoading(false); }
    })();
  }, [isLoaded, isSignedIn, getToken, router]);

  return (
    <DashboardLayout role="admin" pageTitle="Sessions">
      <div className="max-w-7xl">
        <div className="mb-8">
          <h2 className="text-3xl font-display text-white">Attendance Sessions</h2>
          <p className="text-white/40 text-sm mt-2">Monitor active and past attendance sessions across the institution.</p>
        </div>

        <div className="border border-[oklch(0.14_0.008_260)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[oklch(0.14_0.008_260)] bg-[oklch(0.09_0.008_260)]">
                  {["Status", "Subject", "Faculty", "Type", "Started", "Ends", "Radius"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-mono text-white/40 uppercase tracking-widest whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-[oklch(0.12_0.008_260)] animate-pulse">
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="h-4 bg-white/5 rounded" /></td>
                      ))}
                    </tr>
                  ))
                ) : sessions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-white/40">
                      <MonitorPlay className="w-8 h-8 mx-auto mb-2 opacity-20" />
                      No sessions found.
                    </td>
                  </tr>
                ) : (
                  sessions.map((s) => (
                    <tr key={s.id} className="border-b border-[oklch(0.11_0.008_260)] hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono ${
                          s.status === "active" ? "bg-green-400/10 text-green-400" : "bg-white/5 text-white/40"
                        }`}>
                          {s.status === "active" && <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />}
                          {s.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-white/80 text-xs">
                        {s.subject_code} <span className="text-white/40 block text-[10px]">{s.subject_name}</span>
                      </td>
                      <td className="px-4 py-3 text-white font-medium">{s.faculty_name}</td>
                      <td className="px-4 py-3 text-white/60 font-mono text-xs capitalize">{s.session_type}</td>
                      <td className="px-4 py-3 text-white/60 font-mono text-[10px]">
                        {new Date(s.starts_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-white/60 font-mono text-[10px]">
                        {new Date(s.ends_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-white/60 font-mono text-xs">{s.radius_meters}m</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
