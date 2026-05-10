"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import {
  Upload, Download, Search, ChevronLeft, ChevronRight,
  UserX, X, ShieldAlert, ShieldCheck
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Faculty {
  id: number; name: string; email: string;
  department_code: string | null;
  is_admin: boolean; is_hod: boolean; status: string;
}

interface ImportError { row: number; field: string; error: string; }

function ImportModal({
  open, onClose, getToken, onSuccess,
}: {
  open: boolean; onClose: () => void;
  getToken: () => Promise<string | null>; onSuccess: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ imported: number; errors: ImportError[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function upload() {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const token = await getToken();
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/admin/import/faculty`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form,
      });
      const data = await res.json();
      setResult(data);
      if (data.imported > 0) onSuccess();
    } catch { setResult({ imported: 0, errors: [{ row: 0, field: "", error: "Upload failed" }] }); }
    finally { setLoading(false); }
  }

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg bg-[oklch(0.09_0.008_260)] border border-[oklch(0.18_0.008_260)] p-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-display text-white">Import Faculty</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white transition-colors"><X className="w-5 h-5" /></button>
        </div>

        <div className="mb-4 p-3 bg-white/5 border border-white/10 text-xs font-mono text-white/60">
          CSV columns: <span className="text-white/80">name, email</span> (required) · department_code, is_hod, is_admin (optional)
        </div>

        <div
          onClick={() => fileRef.current?.click()}
          className="border border-dashed border-white/20 hover:border-[#eca8d6]/50 p-8 text-center cursor-pointer transition-colors mb-6 group"
        >
          <Upload className="w-6 h-6 text-white/30 group-hover:text-[#eca8d6] mx-auto mb-2 transition-colors" />
          <p className="text-sm text-white/50 group-hover:text-white/80 transition-colors">
            {file ? file.name : "Click to select CSV file"}
          </p>
          <input ref={fileRef} type="file" accept=".csv" className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>

        {result && (
          <div className={`mb-4 p-3 border text-xs font-mono ${result.errors.length > 0 ? "bg-red-400/10 border-red-400/20 text-red-400" : "bg-green-400/10 border-green-400/20 text-green-400"}`}>
            {result.errors.length > 0
              ? <>
                  <p className="mb-2">Import failed — {result.errors.length} error(s):</p>
                  {result.errors.slice(0, 5).map((e, i) => (
                    <p key={i}>Row {e.row}: [{e.field}] {e.error}</p>
                  ))}
                  {result.errors.length > 5 && <p>…and {result.errors.length - 5} more</p>}
                </>
              : <p>✓ Imported {result.imported} faculty successfully</p>
            }
          </div>
        )}

        <button onClick={upload} disabled={!file || loading}
          className="w-full h-10 bg-white text-black text-sm font-medium rounded-sm hover:bg-white/90 transition-all disabled:opacity-40 flex items-center justify-center gap-2">
          {loading ? <><div className="w-4 h-4 border border-black/30 border-t-black rounded-full animate-spin" />Uploading…</> : "Upload & Import"}
        </button>
      </div>
    </div>
  );
}

export default function FacultyPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();

  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [role, setRole] = useState<"admin" | "hod">("admin");

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, page, search]);

  async function load() {
    setLoading(true);
    try {
      const token = await getToken();
      
      const meRes = await fetch(`${API_BASE}/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!meRes.ok) return;
      const me = await meRes.json();
      setRole(me.role);
      
      const endpoint = me.role === "hod" ? "/hod/faculty" : "/admin/faculty";
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (search) params.set("search", search);
      const res = await fetch(`${API_BASE}${endpoint}?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setFaculty(data.items ?? []);
      setTotal(data.total ?? 0);
      setTotalPages(data.pages ?? 1);
    } finally { setLoading(false); }
  }

  async function deactivate(id: number) {
    if (!confirm("Deactivate this faculty member?")) return;
    const token = await getToken();
    await fetch(`${API_BASE}/admin/faculty/${id}`, {
      method: "DELETE", headers: { Authorization: `Bearer ${token}` },
    });
    load();
  }

  async function exportCsv() {
    const token = await getToken();
    const res = await fetch(`${API_BASE}/admin/export/faculty`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "faculty.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <DashboardLayout role="admin" pageTitle="Faculty">
      <ImportModal open={importOpen} onClose={() => setImportOpen(false)} getToken={getToken} onSuccess={load} />

      <div className="max-w-7xl">
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { setSearch(searchInput); setPage(1); } }}
              placeholder="Search name, email…"
              className="w-full h-9 pl-9 pr-4 bg-[oklch(0.09_0.008_260)] border border-[oklch(0.18_0.008_260)] text-white text-sm rounded-sm placeholder:text-white/20 focus:border-white/30 outline-none font-mono"
            />
          </div>

          <div className="flex items-center gap-2 ml-auto">
            {role === "admin" && (
              <button onClick={() => setImportOpen(true)}
                className="flex items-center gap-2 h-9 px-4 bg-[#eca8d6]/10 border border-[#eca8d6]/30 text-[#eca8d6] text-sm rounded-sm hover:bg-[#eca8d6]/20 transition-all">
                <Upload className="w-4 h-4" />Import CSV
              </button>
            )}
            <button onClick={exportCsv}
              className="flex items-center gap-2 h-9 px-4 bg-white/5 border border-white/20 text-white/70 text-sm rounded-sm hover:bg-white/10 transition-all">
              <Download className="w-4 h-4" />Export
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-4">
          <span className="text-xs font-mono text-white/40">{total.toLocaleString()} faculty members total</span>
        </div>

        <div className="border border-[oklch(0.14_0.008_260)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[oklch(0.14_0.008_260)] bg-[oklch(0.09_0.008_260)]">
                  {["Name", "Email", "Department", "Role", "Status", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-mono text-white/40 uppercase tracking-widest whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i} className="border-b border-[oklch(0.12_0.008_260)] animate-pulse">
                        {Array.from({ length: 6 }).map((_, j) => (
                          <td key={j} className="px-4 py-3"><div className="h-4 bg-white/5 rounded" /></td>
                        ))}
                      </tr>
                    ))
                  : faculty.map((f) => (
                      <tr key={f.id} className="border-b border-[oklch(0.11_0.008_260)] hover:bg-white/[0.02] transition-colors group">
                        <td className="px-4 py-3 text-white font-medium">{f.name}</td>
                        <td className="px-4 py-3 text-white/50 font-mono text-xs">{f.email}</td>
                        <td className="px-4 py-3 text-white/60 font-mono text-xs">{f.department_code ?? "—"}</td>
                        <td className="px-4 py-3">
                          {f.is_admin ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded-sm">
                              <ShieldAlert className="w-3 h-3" /> ADMIN
                            </span>
                          ) : f.is_hod ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-sm">
                              <ShieldCheck className="w-3 h-3" /> HOD
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-white/40 bg-white/5 px-2 py-0.5 rounded-sm">
                              FACULTY
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono ${f.status === "active" ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${f.status === "active" ? "bg-green-400" : "bg-red-400"}`} />
                            {f.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {role === "admin" && !f.is_admin && (
                            <button onClick={() => deactivate(f.id)}
                              className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-400 transition-all p-1">
                              <UserX className="w-4 h-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                }
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex items-center justify-between mt-4">
          <span className="text-xs font-mono text-white/30">Page {page} of {totalPages}</span>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="w-8 h-8 flex items-center justify-center border border-white/20 text-white/50 hover:text-white hover:border-white/40 disabled:opacity-30 transition-all rounded-sm">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="w-8 h-8 flex items-center justify-center border border-white/20 text-white/50 hover:text-white hover:border-white/40 disabled:opacity-30 transition-all rounded-sm">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
