"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Offering = { id: number; subject_code: string; subject_name: string; faculty_name: string; academic_year: string; semester: number; section: string; active: boolean };

export default function AdminOfferingsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Offering[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/subject-offerings?page=1&page_size=300`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      const data = await res.json();
      setRows(data.items ?? []);
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="admin" pageTitle="Offerings">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Subject</th><th>Faculty</th><th>AY</th><th>Sem/Section</th><th>Status</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.subject_code} - {r.subject_name}</td><td>{r.faculty_name}</td><td>{r.academic_year}</td><td>{r.semester}/{r.section}</td><td>{r.active ? "active" : "inactive"}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
