"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Faculty = { id: number; name: string; email: string; is_hod: boolean; status: string };

export default function HodFacultyPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Faculty[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/hod/faculty`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      setRows(await res.json());
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="hod" pageTitle="Faculty">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead>
        <tbody>{rows.map((f) => <tr key={f.id}><td>{f.name}</td><td>{f.email}</td><td>{f.is_hod ? "HOD" : "Faculty"}</td><td>{f.status}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
