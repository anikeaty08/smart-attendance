"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { API_BASE, checkBackendReachable } from "@/lib/api";

export default function PortalRedirect() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken, signOut } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }

    (async () => {
      try {
        if (!API_BASE || !(await checkBackendReachable())) {
          router.replace("/");
          return;
        }
        const token = await getToken();
        const res = await fetch(`${API_BASE}/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          if (res.status === 403) {
            const data = await res.json();
            if (data?.detail === "first_login_verification_required") {
              router.replace("/first-login");
              return;
            }
          }
          // If unauthorized or unregistered, log them out of Clerk to break the loop!
          await signOut();
          router.replace("/login");
          return;
        }
        const me = await res.json();
        if (me.role === "admin") {
          router.replace("/admin");
        } else if (me.role === "hod") {
          router.replace("/hod");
        } else if (me.role === "faculty") {
          router.replace("/teacher");
        } else {
          await signOut();
          router.replace("/login");
        }
      } catch {
        await signOut();
        router.replace("/login");
      }
    })();
  }, [isLoaded, isSignedIn, getToken, signOut, router]);

  return (
    <div className="min-h-screen bg-[oklch(0.06_0.008_260)] flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border border-[#eca8d6]/40 border-t-[#eca8d6] rounded-full animate-spin mx-auto mb-4" />
        <p className="text-white/40 text-sm font-mono">Loading your dashboard…</p>
      </div>
    </div>
  );
}
