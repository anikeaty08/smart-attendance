"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Student = { id: number; usn: string; name: string; email: string; section: string; current_semester: number };

export default function HodStudentsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Student[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/hod/students?page=1&page_size=200`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setRows(data.items ?? []);
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="hod" pageTitle="Students">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>USN</th><th>Name</th><th>Email</th><th>Sem</th><th>Section</th></tr></thead>
        <tbody>{rows.map((s) => <tr key={s.id}><td>{s.usn}</td><td>{s.name}</td><td>{s.email}</td><td>{s.current_semester}</td><td>{s.section}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
