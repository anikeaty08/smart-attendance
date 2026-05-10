"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type Department = { id: number; name: string; code: string };

export default function AdminDepartmentsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Department[]>([]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/departments`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) return;
      setRows(await res.json());
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <DashboardLayout role="admin" pageTitle="Departments">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Code</th><th>Name</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.code}</td><td>{r.name}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
