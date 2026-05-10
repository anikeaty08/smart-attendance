"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Correction = { id: number; usn: string; student_name: string; old_status: string; new_status: string; reason: string; corrected_by_name: string };

export default function AdminCorrectionsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Correction[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/corrections?page=1&page_size=200`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      const data = await res.json();
      setRows(data.items ?? []);
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="admin" pageTitle="Corrections">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>USN</th><th>Student</th><th>Old</th><th>New</th><th>Reason</th><th>By</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.usn}</td><td>{r.student_name}</td><td>{r.old_status}</td><td>{r.new_status}</td><td>{r.reason}</td><td>{r.corrected_by_name}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
