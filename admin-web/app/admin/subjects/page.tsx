"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useRef, useState } from "react";

type Subject = { id: number; subject_code: string; subject_name: string; semester: number; credits: number; department_code: string | null };

export default function AdminSubjectsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Subject[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const token = await getToken();
    const res = await fetch(`${API_BASE}/admin/subjects?page=1&page_size=300`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    const data = await res.json();
    setRows(data.items ?? []);
  }

  async function importSubjects() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const token = await getToken();
    const form = new FormData();
    form.append("file", file);
    await fetch(`${API_BASE}/admin/import/subjects`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
    await load();
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <DashboardLayout role="admin" pageTitle="Subjects">
      <div className="mb-4 flex gap-2"><input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" /><button onClick={importSubjects}>Import</button></div>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Code</th><th>Name</th><th>Sem</th><th>Credits</th><th>Dept</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.subject_code}</td><td>{r.subject_name}</td><td>{r.semester}</td><td>{r.credits}</td><td>{r.department_code ?? "-"}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
