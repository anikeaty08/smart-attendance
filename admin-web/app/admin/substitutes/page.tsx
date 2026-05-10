"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Sub = { id: number; date: string; subject_code: string; original_faculty_name: string; substitute_faculty_name: string | null; status: string };

export default function AdminSubstitutesPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Sub[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/substitutes`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      setRows(await res.json());
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="admin" pageTitle="Substitutes">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Date</th><th>Subject</th><th>Original</th><th>Substitute</th><th>Status</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.date}</td><td>{r.subject_code}</td><td>{r.original_faculty_name}</td><td>{r.substitute_faculty_name ?? "-"}</td><td>{r.status}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
