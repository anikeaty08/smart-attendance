"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

type LeaveReq = { id: number; usn: string; student_name: string; leave_type: string; start_date: string; end_date: string; status: string };

export default function HodLeaveRequestsPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<LeaveReq[]>([]);

  async function load() {
    const token = await getToken();
    const res = await fetch(`${API_BASE}/hod/leave-requests?page=1&page_size=200`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    const data = await res.json();
    setRows(data.items ?? []);
  }

  async function review(id: number, status: "approved" | "rejected") {
    const token = await getToken();
    await fetch(`${API_BASE}/hod/leave-requests/${id}/review`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    await load();
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <DashboardLayout role="hod" pageTitle="Leave Requests">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>USN</th><th>Student</th><th>Type</th><th>From</th><th>To</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.usn}</td><td>{r.student_name}</td><td>{r.leave_type}</td><td>{r.start_date}</td><td>{r.end_date}</td><td>{r.status}</td><td className="space-x-2"><button onClick={() => review(r.id,"approved")}>Approve</button><button onClick={() => review(r.id,"rejected")}>Reject</button></td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
