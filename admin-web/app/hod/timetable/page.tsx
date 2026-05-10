"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { API_BASE } from "@/lib/api";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useRef, useState } from "react";

type Slot = { id: number; subject_code: string; day_of_week: string; slot_number: number; start_time: string; end_time: string; room: string };

export default function HodTimetablePage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Slot[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const token = await getToken();
    const res = await fetch(`${API_BASE}/hod/timetable`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    setRows(await res.json());
  }

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const token = await getToken();
    const form = new FormData();
    form.append("file", file);
    await fetch(`${API_BASE}/hod/timetable/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
    await load();
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <DashboardLayout role="hod" pageTitle="Timetable">
      <div className="mb-4 flex gap-2">
        <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" className="text-sm" />
        <button onClick={upload} className="px-3 py-1 border border-white/20">Upload</button>
      </div>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-white/60"><th>Subject</th><th>Day</th><th>Slot</th><th>Time</th><th>Room</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.subject_code}</td><td>{r.day_of_week}</td><td>{r.slot_number}</td><td>{r.start_time}-{r.end_time}</td><td>{r.room}</td></tr>)}</tbody>
      </table>
    </DashboardLayout>
  );
}
