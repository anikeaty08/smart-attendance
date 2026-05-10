"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useRef, useState } from "react";

type Row = { id: number; usn: string; student_name: string; subject_code: string; subject_name: string; enrollment_type: string };

export default function AdminEnrollmentsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Row[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const token = await getToken();
    const res = await fetch(`${API_BASE}/admin/enrollments?page=1&page_size=300`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    const data = await res.json();
    setRows(data.items ?? []);
  }

  async function importRows() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const token = await getToken();
    const form = new FormData();
    form.append("file", file);
    await fetch(`${API_BASE}/admin/import/enrollments`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
    await load();
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <DashboardLayout role="admin" pageTitle="Enrollments">
      <div className="mb-4 flex gap-2"><input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" /><button onClick={importRows}>Import</button></div>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>USN</th><th>Student</th><th>Subject</th><th>Type</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.usn}</td><td>{r.student_name}</td><td>{r.subject_code} - {r.subject_name}</td><td>{r.enrollment_type}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
