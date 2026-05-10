"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Download, AlertTriangle, Filter } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Defaulter {
  usn: string; name: string; email: string;
  branch_code: string | null; semester: number; section: string;
  subject_code: string; subject_name: string;
  total_sessions: number; present: number; percentage: number;
}

export default function AdminReportsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  
  const [defaulters, setDefaulters] = useState<Defaulter[]>([]);
  const [loading, setLoading] = useState(true);
  const [threshold, setThreshold] = useState(75);
  const [branchFilter, setBranchFilter] = useState("");
  const [branches, setBranches] = useState<string[]>([]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, threshold, branchFilter]);

  async function load() {
    setLoading(true);
    try {
      const token = await getToken();
      const params = new URLSearchParams({ threshold: String(threshold) });
      const res = await fetch(`${API_BASE}/admin/reports/defaulters?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const filtered = branchFilter ? data.filter((d: Defaulter) => d.branch_code === branchFilter) : data;
        setDefaulters(filtered);
        
        // Extract unique branches
        const uniqueBranches = Array.from(new Set(data.map((d: Defaulter) => d.branch_code).filter(Boolean))) as string[];
        if (uniqueBranches.length > branches.length) setBranches(uniqueBranches.sort());
      }
    } finally { setLoading(false); }
  }

  async function exportCsv() {
    const token = await getToken();
    const params = new URLSearchParams({ threshold: String(threshold) });
    const res = await fetch(`${API_BASE}/admin/export/defaulters?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `defaulters_${threshold}pct.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <DashboardLayout role="admin" pageTitle="Reports">
      <div className="max-w-7xl">
        <div className="mb-8">
          <h2 className="text-3xl font-display text-white">Attendance Reports</h2>
          <p className="text-white/40 text-sm mt-2">Identify students falling below the minimum attendance requirement.</p>
        </div>

        <div className="flex flex-wrap items-center gap-4 mb-6 p-4 border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)]">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-widest">Filters:</span>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-white/60">Threshold:</label>
            <select value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}
              className="h-8 bg-[oklch(0.12_0.008_260)] border border-[oklch(0.18_0.008_260)] text-white text-sm px-2 rounded-sm focus:border-[#eca8d6]/40 outline-none">
              <option value="85">85%</option>
              <option value="75">75% (Standard)</option>
              <option value="60">60%</option>
              <option value="50">50%</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-white/60">Branch:</label>
            <select value={branchFilter} onChange={(e) => setBranchFilter(e.target.value)}
              className="h-8 bg-[oklch(0.12_0.008_260)] border border-[oklch(0.18_0.008_260)] text-white text-sm px-2 rounded-sm focus:border-[#eca8d6]/40 outline-none">
              <option value="">All Branches</option>
              {branches.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>

          <button onClick={exportCsv}
            className="ml-auto flex items-center gap-2 h-8 px-4 bg-white/5 border border-white/20 text-white/70 text-sm rounded-sm hover:bg-white/10 transition-all">
            <Download className="w-4 h-4" />Export CSV
          </button>
        </div>

        <div className="border border-[oklch(0.14_0.008_260)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[oklch(0.14_0.008_260)] bg-[oklch(0.09_0.008_260)]">
                  {["USN", "Name", "Branch", "Sem/Sec", "Subject", "Total", "Present", "%"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-mono text-white/40 uppercase tracking-widest whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-[oklch(0.12_0.008_260)] animate-pulse">
                      {Array.from({ length: 8 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="h-4 bg-white/5 rounded" /></td>
                      ))}
                    </tr>
                  ))
                ) : defaulters.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-white/40">
                      <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-20" />
                      No students found below the {threshold}% threshold.
                    </td>
                  </tr>
                ) : (
                  defaulters.map((d, i) => (
                    <tr key={`${d.usn}-${d.subject_code}-${i}`} className="border-b border-[oklch(0.11_0.008_260)] hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-3 font-mono text-white/80 text-xs">{d.usn}</td>
                      <td className="px-4 py-3 text-white font-medium whitespace-nowrap">{d.name}</td>
                      <td className="px-4 py-3 text-white/60 font-mono text-xs">{d.branch_code ?? "—"}</td>
                      <td className="px-4 py-3 text-white/60 font-mono text-xs">{d.semester}/{d.section}</td>
                      <td className="px-4 py-3 text-white/80 text-xs">
                        {d.subject_code} <span className="text-white/40 block text-[10px] truncate max-w-[150px]">{d.subject_name}</span>
                      </td>
                      <td className="px-4 py-3 text-white/60 font-mono text-xs">{d.total_sessions}</td>
                      <td className="px-4 py-3 text-white/60 font-mono text-xs">{d.present}</td>
                      <td className="px-4 py-3">
                        <span className={`font-mono text-xs ${d.percentage < 50 ? "text-red-400" : "text-yellow-400"}`}>
                          {d.percentage.toFixed(1)}%
                        </span>
                      </td>
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
