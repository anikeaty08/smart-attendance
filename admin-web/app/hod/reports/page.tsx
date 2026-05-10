"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Row = { usn: string; name: string; section: string; subject_code: string; subject_name: string; total_sessions: number; present: number; percentage: number };

export default function HodReportsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/hod/defaulters?threshold=75`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      setRows(await res.json());
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="hod" pageTitle="Reports">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>USN</th><th>Name</th><th>Subject</th><th>Present</th><th>Total</th><th>%</th></tr></thead>
        <tbody>{rows.map((r, i) => <tr key={`${r.usn}-${r.subject_code}-${i}`}><td>{r.usn}</td><td>{r.name}</td><td>{r.subject_code}</td><td>{r.present}</td><td>{r.total_sessions}</td><td>{r.percentage}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
