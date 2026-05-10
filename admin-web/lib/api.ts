"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AppRole = "admin" | "hod" | "faculty" | "student";

export async function fetchMe(getToken: () => Promise<string | null>) {
  const token = await getToken();
  const res = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("failed_to_fetch_me");
  }
  return res.json();
}

export async function apiGet(path: string, getToken: () => Promise<string | null>) {
  const token = await getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`api_error:${res.status}`);
  }
  return res.json();
}

export { API_BASE };
