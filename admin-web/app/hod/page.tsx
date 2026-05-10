"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

type HodOverview = {
  total_students: number;
  total_faculty: number;
  total_subjects: number;
  total_offerings: number;
  active_sessions: number;
};

export default function HodDashboardPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<HodOverview | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.replace("/login");
      return;
    }
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/hod/department`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        if (res.status === 400) {
          const payload = await res.json().catch(() => null);
          if (payload?.detail === "hod_department_not_configured") {
            setErrorMessage(
              "Your HOD account is missing department mapping. Ask admin to assign department for this account."
            );
            return;
          }
        }
        setErrorMessage("Unable to load HOD dashboard right now.");
        return;
      }
      setData(await res.json());
    })();
  }, [isLoaded, isSignedIn, getToken, router]);

  return (
    <DashboardLayout role="hod" pageTitle="Department">
      {errorMessage && (
        <div className="mb-4 border border-amber-400/40 bg-amber-400/10 p-4 text-amber-300">
          {errorMessage}
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          ["Students", data?.total_students ?? 0],
          ["Faculty", data?.total_faculty ?? 0],
          ["Subjects", data?.total_subjects ?? 0],
          ["Offerings", data?.total_offerings ?? 0],
          ["Active Sessions", data?.active_sessions ?? 0],
        ].map(([label, value]) => (
          <div key={label} className="border border-white/10 bg-white/5 p-4">
            <p className="text-xs text-white/50">{label}</p>
            <p className="text-2xl text-white">{value}</p>
          </div>
        ))}
      </div>
    </DashboardLayout>
  );
}
