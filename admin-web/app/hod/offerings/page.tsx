"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Offering = { id: number; subject_code: string; subject_name: string; faculty_name: string; semester: number; section: string; active: boolean };

export default function HodOfferingsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Offering[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/hod/offerings`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      setRows(await res.json());
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="hod" pageTitle="Offerings">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Code</th><th>Subject</th><th>Faculty</th><th>Sem/Section</th><th>Status</th></tr></thead>
        <tbody>{rows.map((o) => <tr key={o.id}><td>{o.subject_code}</td><td>{o.subject_name}</td><td>{o.faculty_name}</td><td>{o.semester}/{o.section}</td><td>{o.active ? "active" : "inactive"}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
