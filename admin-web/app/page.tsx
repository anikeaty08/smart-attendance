"use client";

import { SignInButton, SignedIn, SignedOut, UserButton, useAuth } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";

type View =
  | "dashboard"
  | "students"
  | "faculty"
  | "subjects"
  | "offerings"
  | "enrollments"
  | "imports"
  | "reports"
  | "defaulters"
  | "corrections"
  | "leave"
  | "condonation";

const views: Array<{ id: View; label: string }> = [
  { id: "dashboard", label: "Dashboard" },
  { id: "students", label: "Students" },
  { id: "faculty", label: "Faculty" },
  { id: "subjects", label: "Subjects" },
  { id: "offerings", label: "Offerings" },
  { id: "enrollments", label: "Enrollments" },
  { id: "imports", label: "Imports" },
  { id: "reports", label: "Reports" },
  { id: "defaulters", label: "Defaulters" },
  { id: "corrections", label: "Corrections" },
  { id: "leave", label: "Leave" },
  { id: "condonation", label: "Condonation" }
];

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

function Logo() {
  return <div className="logo">SA</div>;
}

function LoginScreen() {
  return (
    <main className="login">
      <section className="login-card">
        <div className="brand">
          <Logo />
          <div>
            <strong>Smart Attendance</strong>
            <span>BMSIT control room</span>
          </div>
        </div>
        <p className="eyebrow">Secure college operations</p>
        <h1>Attendance, enrollment, and shortage decisions in one quiet workspace.</h1>
        <p style={{ color: "var(--muted)", maxWidth: 620, marginTop: 18 }}>
          Sign in with the configured Clerk workspace to manage students, faculty, subject offerings, imports, requests,
          and reports.
        </p>
        <SignInButton mode="modal">
          <button>Sign in</button>
        </SignInButton>
      </section>
    </main>
  );
}

function normalizeRows(payload: any): any[] {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (payload && typeof payload === "object") return [payload];
  return [];
}

function DataTable({ rows }: { rows: any[] }) {
  const columns = useMemo(() => {
    const first = rows[0] || {};
    return Object.keys(first).filter((key) => !["id"].includes(key)).slice(0, 8);
  }, [rows]);
  if (!rows.length) return <div className="panel-body">No records found.</div>;
  return (
    <table>
      <thead>
        <tr>{columns.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={row.id ?? index}>
            {columns.map((column) => (
              <td key={column}>{formatCell(row[column])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function formatCell(value: any) {
  if (value === true) return <span className="badge success">yes</span>;
  if (value === false) return <span className="badge">no</span>;
  if (value == null || value === "") return "—";
  if (String(value).length > 80) return `${String(value).slice(0, 80)}...`;
  return String(value);
}

function AdminApp() {
  const { getToken } = useAuth();
  const [view, setView] = useState<View>("dashboard");
  const [rows, setRows] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  async function api(path: string, options: RequestInit = {}) {
    const token = await getToken();
    const response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw data;
    return data;
  }

  async function load(target = view) {
    setLoading(true);
    setStatus("");
    try {
      if (target === "dashboard") {
        const data = await api("/admin/dashboard");
        setMetrics(data);
        setRows([]);
      } else {
        const path = endpointFor(target, search);
        const data = await api(path);
        setRows(normalizeRows(data));
      }
    } catch (error) {
      setStatus(JSON.stringify(error, null, 2));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(view);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  async function upload(kind: string, file: File | null) {
    if (!file) {
      setStatus("Choose a file first.");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    setLoading(true);
    try {
      const data = await api(`/admin/import/${kind}`, { method: "POST", body: form });
      setStatus(JSON.stringify(data, null, 2));
    } catch (error) {
      setStatus(JSON.stringify(error, null, 2));
    } finally {
      setLoading(false);
    }
  }

  const active = views.find((item) => item.id === view);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Logo />
          <div>
            <strong>Smart Attendance</strong>
            <span>Admin dashboard</span>
          </div>
        </div>
        <nav className="nav">
          {views.map((item) => (
            <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => setView(item.id)}>
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">BMSIT operations</p>
            <h2>{active?.label}</h2>
          </div>
          <UserButton afterSignOutUrl="/" />
        </header>

        {view === "dashboard" ? (
          <>
            <section className="metrics">
              {Object.entries(metrics).map(([key, value]) => (
                <div className="metric" key={key}>
                  <span>{key.replaceAll("_", " ")}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </section>
            <section className="panel">
              <div className="panel-head">
                <h3>System posture</h3>
                <span className="badge success">Enrollment-first</span>
              </div>
              <div className="panel-body">
                Student subject visibility, active attendance sessions, and marking permissions are driven by
                enrollment records, not branch assumptions.
              </div>
            </section>
          </>
        ) : view === "imports" ? (
          <Imports upload={upload} loading={loading} />
        ) : (
          <section className="panel">
            <div className="panel-head">
              <h3>{active?.label}</h3>
              <div className="toolbar" style={{ marginBottom: 0 }}>
                {supportsSearch(view) && (
                  <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search" />
                )}
                <button className="secondary" onClick={() => void load()}>
                  {loading ? "Loading" : "Refresh"}
                </button>
                {downloadFor(view) && (
                  <a href={`${apiBase}${downloadFor(view)}`} target="_blank" rel="noreferrer">
                    <button>Export</button>
                  </a>
                )}
              </div>
            </div>
            <DataTable rows={rows} />
          </section>
        )}
        {status && <pre className="status">{status}</pre>}
      </main>
    </div>
  );
}

function endpointFor(view: View, search: string) {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  const map: Record<View, string> = {
    dashboard: "/admin/dashboard",
    students: `/admin/students${query}`,
    faculty: `/admin/faculty${query}`,
    subjects: `/admin/subjects${query}`,
    offerings: "/admin/subject-offerings",
    enrollments: "/admin/enrollments",
    imports: "/admin/dashboard",
    reports: "/admin/reports/attendance",
    defaulters: "/admin/reports/defaulters",
    corrections: "/admin/corrections",
    leave: "/admin/leave-requests",
    condonation: "/admin/condonation-requests"
  };
  return map[view];
}

function supportsSearch(view: View) {
  return ["students", "faculty", "subjects"].includes(view);
}

function downloadFor(view: View) {
  const map: Partial<Record<View, string>> = {
    students: "/admin/export/students",
    faculty: "/admin/export/faculty",
    subjects: "/admin/export/subjects",
    reports: "/admin/export/attendance",
    defaulters: "/admin/export/defaulters"
  };
  return map[view];
}

function Imports({ upload, loading }: { upload: (kind: string, file: File | null) => void; loading: boolean }) {
  const kinds = [
    ["students", "Students", "usn, name, email, branch_code, semester, section"],
    ["faculty", "Faculty", "name, email, department_code, is_hod, is_admin"],
    ["subjects", "Subjects", "subject_code, subject_name, semester, department_code"],
    ["enrollments", "Enrollments", "usn, subject_offering_id, enrollment_type"]
  ];
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>Validated CSV / Excel imports</h3>
        <span className="badge">Row-level errors</span>
      </div>
      <div className="panel-body" style={{ display: "grid", gap: 14 }}>
        {kinds.map(([kind, label, hint]) => (
          <ImportRow key={kind} kind={kind} label={label} hint={hint} loading={loading} upload={upload} />
        ))}
      </div>
    </section>
  );
}

function ImportRow({
  kind,
  label,
  hint,
  loading,
  upload
}: {
  kind: string;
  label: string;
  hint: string;
  loading: boolean;
  upload: (kind: string, file: File | null) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  return (
    <div className="toolbar" style={{ borderBottom: "1px solid var(--line)", paddingBottom: 12 }}>
      <strong style={{ minWidth: 110 }}>{label}</strong>
      <span style={{ color: "var(--muted)", flex: 1 }}>{hint}</span>
      <input type="file" accept=".csv,.xlsx,.xls" onChange={(event) => setFile(event.target.files?.[0] || null)} />
      <button disabled={loading} onClick={() => upload(kind, file)}>
        Upload
      </button>
    </div>
  );
}

export default function Page() {
  return (
    <>
      <SignedOut>
        <LoginScreen />
      </SignedOut>
      <SignedIn>
        <AdminApp />
      </SignedIn>
    </>
  );
}

