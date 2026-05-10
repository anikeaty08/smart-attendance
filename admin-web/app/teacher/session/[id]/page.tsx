"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { StopCircle, Users, CheckCircle2, UserX, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Session {
  id: number; subject_code: string; subject_name: string;
  session_type: string; starts_at: string; ends_at: string;
}

interface Record {
  id: number; student_id: number; student_name: string;
  usn: string; status: "present" | "absent" | "late";
  distance_from_teacher: number; marked_at: string | null;
}

function LiveSessionContent() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.id as string;
  const code = searchParams.get("code") ?? "----";

  const [session, setSession] = useState<Session | null>(null);
  const [records, setRecords] = useState<Record[]>([]);
  const [loading, setLoading] = useState(true);
  const [ending, setEnding] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);

  // Initial load
  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }

    (async () => {
      try {
        const token = await getToken();
        const [sessionRes, recordsRes] = await Promise.all([
          fetch(`${API_BASE}/faculty/sessions/${sessionId}`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${API_BASE}/faculty/sessions/${sessionId}/records`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);

        if (sessionRes.ok) {
          const s = await sessionRes.json();
          setSession(s);
          // calculate time left
          const end = new Date(s.ends_at).getTime();
          const now = new Date().getTime();
          setTimeLeft(Math.max(0, Math.floor((end - now) / 1000)));
        }
        if (recordsRes.ok) setRecords(await recordsRes.json());
      } finally { setLoading(false); }
    })();
  }, [isLoaded, isSignedIn, getToken, router, sessionId]);

  // Polling for records every 3 seconds
  useEffect(() => {
    if (!session || timeLeft <= 0) return;
    const interval = setInterval(async () => {
      try {
        const token = await getToken();
        const res = await fetch(`${API_BASE}/faculty/sessions/${sessionId}/records`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) setRecords(await res.json());
      } catch (e) { console.error("Poll failed", e); }
    }, 3000);
    return () => clearInterval(interval);
  }, [session, sessionId, timeLeft, getToken]);

  // Countdown timer
  useEffect(() => {
    if (timeLeft <= 0) return;
    const interval = setInterval(() => setTimeLeft((t) => Math.max(0, t - 1)), 1000);
    return () => clearInterval(interval);
  }, [timeLeft]);

  async function endSession() {
    if (!confirm("Are you sure you want to end this session early?")) return;
    setEnding(true);
    try {
      const token = await getToken();
      await fetch(`${API_BASE}/faculty/sessions/${sessionId}/end`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      setTimeLeft(0);
    } finally {
      setEnding(false);
    }
  }

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  const isActive = timeLeft > 0;
  const presentCount = records.filter(r => r.status === "present" || r.status === "late").length;

  if (loading) return <DashboardLayout role="faculty"><div className="w-6 h-6 border border-[#eca8d6]/40 border-t-[#eca8d6] rounded-full animate-spin mx-auto mt-20" /></DashboardLayout>;

  return (
    <DashboardLayout role="faculty" pageTitle="Live Session">
      <div className="max-w-4xl mx-auto flex flex-col lg:flex-row gap-6">
        
        {/* Left Column — Code & Controls */}
        <div className="lg:w-1/3 flex flex-col gap-6">
          {/* Main Code Box */}
          <div className={`p-8 border flex flex-col items-center justify-center text-center transition-all ${
            isActive ? "bg-[oklch(0.09_0.008_260)] border-[#eca8d6]/30 shadow-[0_0_40px_rgba(236,168,214,0.05)]" : "bg-white/5 border-white/10"
          }`}>
            <div className={`text-[10px] font-mono tracking-widest uppercase mb-4 px-2 py-1 flex items-center gap-2 ${
              isActive ? "bg-[#eca8d6]/10 text-[#eca8d6]" : "bg-red-400/10 text-red-400"
            }`}>
              {isActive && <span className="w-1.5 h-1.5 bg-[#eca8d6] rounded-full animate-pulse" />}
              {isActive ? "Accepting Check-ins" : "Session Ended"}
            </div>
            
            <div className={`text-6xl font-display tracking-[0.2em] mb-4 ${isActive ? "text-white" : "text-white/30"}`}>
              {code}
            </div>
            
            <div className="text-2xl font-mono text-white/60">
              {fmt(timeLeft)}
            </div>
          </div>

          {/* Details */}
          {session && (
            <div className="border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)] p-5 space-y-4">
              <div>
                <div className="text-xs font-mono text-white/40 mb-1">Subject</div>
                <div className="text-sm text-white font-medium">{session.subject_code}</div>
                <div className="text-xs text-white/60">{session.subject_name}</div>
              </div>
              <div className="flex gap-4">
                <div>
                  <div className="text-xs font-mono text-white/40 mb-1">Type</div>
                  <div className="text-sm text-white capitalize">{session.session_type}</div>
                </div>
                <div>
                  <div className="text-xs font-mono text-white/40 mb-1">Total Present</div>
                  <div className="text-sm text-[#eca8d6]">{presentCount}</div>
                </div>
              </div>

              {isActive && (
                <button onClick={endSession} disabled={ending}
                  className="w-full mt-4 h-10 border border-red-400/30 text-red-400 text-sm font-medium hover:bg-red-400/10 transition-colors flex items-center justify-center gap-2">
                  <StopCircle className="w-4 h-4" /> End Session Early
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right Column — Live Roster */}
        <div className="lg:w-2/3 border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)] flex flex-col h-[600px]">
          <div className="px-5 py-4 border-b border-[oklch(0.18_0.008_260)] flex items-center justify-between">
            <h3 className="text-sm font-medium text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-[#eca8d6]" />
              Live Check-ins
            </h3>
            <span className="text-xs font-mono text-white/40">{records.length} records</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2">
            {records.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-white/30 text-sm">
                <AlertCircle className="w-8 h-8 mb-2 opacity-20" />
                No students have checked in yet.
              </div>
            ) : (
              <div className="space-y-1">
                {records.map(r => (
                  <div key={r.id} className="flex items-center justify-between p-3 hover:bg-white/5 transition-colors border border-transparent hover:border-white/10 group">
                    <div className="flex items-center gap-4">
                      {r.status === "present" ? <CheckCircle2 className="w-5 h-5 text-green-400" /> :
                       r.status === "late" ? <CheckCircle2 className="w-5 h-5 text-yellow-400" /> :
                       <UserX className="w-5 h-5 text-red-400" />}
                      
                      <div>
                        <div className="text-sm text-white font-medium">{r.student_name}</div>
                        <div className="text-xs font-mono text-white/40">{r.usn}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-mono text-white/50">{r.distance_from_teacher.toFixed(1)}m</div>
                      <div className="text-[10px] font-mono text-white/30 mt-0.5">
                        {r.marked_at ? new Date(r.marked_at).toLocaleTimeString() : "—"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </DashboardLayout>
  );
}

export default function LiveSessionPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[oklch(0.06_0.008_260)] flex items-center justify-center">
        <div className="w-6 h-6 border border-white/20 border-t-[#eca8d6] rounded-full animate-spin" />
      </div>
    }>
      <LiveSessionContent />
    </Suspense>
  );
}
