"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type AcademicYear = { id: number; year_code: string; start_date: string; end_date: string; is_current: boolean; active: boolean };

export default function AdminAcademicYearsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<AcademicYear[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/academic-years`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      setRows(await res.json());
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="admin" pageTitle="Academic Years">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Year</th><th>Start</th><th>End</th><th>Current</th><th>Active</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.year_code}</td><td>{r.start_date}</td><td>{r.end_date}</td><td>{r.is_current ? "yes" : "no"}</td><td>{r.active ? "yes" : "no"}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
