const PROD = process.env.NODE_ENV === "production";
const ENV_API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim();

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

export function getApiBase() {
  if (ENV_API_BASE) return normalizeBaseUrl(ENV_API_BASE);
  if (!PROD) return "http://localhost:8000";
  return null;
}

export const API_BASE = getApiBase();

export type AppRole = "admin" | "hod" | "faculty" | "student";

export async function fetchMe(getToken: () => Promise<string | null>) {
  if (!API_BASE) {
    throw new Error("api_unavailable");
  }
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
  if (!API_BASE) {
    throw new Error("api_unavailable");
  }
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

export async function checkBackendReachable(timeoutMs = 2200) {
  if (!API_BASE) return false;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/openapi.json`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}
