"use client";

import { DashboardLayout } from "@/components/dashboard/layout";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { MapPin, Wifi, WifiOff, Play, Clock, Crosshair, AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Offering {
  id: number; subject_code: string; subject_name: string;
  section: string; semester: number; branch_code: string | null;
}

interface LocationState {
  status: "idle" | "requesting" | "granted" | "denied" | "unavailable";
  lat: number | null;
  lon: number | null;
  accuracy: number | null;
}

function AccuracyRing({ accuracy }: { accuracy: number | null }) {
  const good = accuracy !== null && accuracy <= 20;
  const ok = accuracy !== null && accuracy <= 50;
  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full animate-pulse ${good ? "bg-green-400" : ok ? "bg-yellow-400" : "bg-red-400"}`} />
      <span className={`text-xs font-mono ${good ? "text-green-400" : ok ? "text-yellow-400" : "text-red-400"}`}>
        {accuracy !== null ? `±${Math.round(accuracy)}m accuracy` : "No signal"}
      </span>
    </div>
  );
}

// Animated concentric rings representing 10m radius
function RadiusVisual({ status }: { status: LocationState["status"] }) {
  const active = status === "granted";
  return (
    <div className="relative w-48 h-48 flex items-center justify-center mx-auto">
      {/* Outer rings */}
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={`absolute rounded-full border transition-all duration-1000 ${
            active ? "border-[#eca8d6]/20 animate-ping" : "border-white/5"
          }`}
          style={{
            width: `${i * 56}px`,
            height: `${i * 56}px`,
            animationDuration: `${1.5 + i * 0.5}s`,
            animationDelay: `${i * 0.3}s`,
          }}
        />
      ))}
      {/* Center dot */}
      <div
        className={`relative w-16 h-16 rounded-full border-2 flex items-center justify-center transition-all duration-500 ${
          active
            ? "border-[#eca8d6] bg-[#eca8d6]/10"
            : status === "requesting"
            ? "border-white/20 bg-white/5 animate-pulse"
            : status === "denied"
            ? "border-red-400/40 bg-red-400/5"
            : "border-white/20 bg-white/5"
        }`}
      >
        <MapPin
          className={`w-6 h-6 transition-colors ${
            active ? "text-[#eca8d6]" : status === "denied" ? "text-red-400" : "text-white/30"
          }`}
        />
      </div>
      {/* 10m label */}
      {active && (
        <span className="absolute bottom-2 text-[10px] font-mono text-[#eca8d6]/60">10 m radius</span>
      )}
    </div>
  );
}

export default function StartSessionPage() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselected = searchParams.get("offering");

  const [offerings, setOfferings] = useState<Offering[]>([]);
  const [selectedOffering, setSelectedOffering] = useState<string>(preselected ?? "");
  const [duration, setDuration] = useState(15);
  const [radius, setRadius] = useState(10);
  const [sessionType, setSessionType] = useState<"lecture" | "lab" | "tutorial">("lecture");
  const [location, setLocation] = useState<LocationState>({
    status: "idle", lat: null, lon: null, accuracy: null,
  });
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  // Load offerings
  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/faculty/offerings`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setOfferings(data);
        if (!preselected && data.length > 0) setSelectedOffering(String(data[0].id));
      }
    })();
  }, [isLoaded, isSignedIn, getToken, router, preselected]);

  // Request GPS location
  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocation((l) => ({ ...l, status: "unavailable" }));
      return;
    }
    setLocation((l) => ({ ...l, status: "requesting" }));
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          status: "granted",
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      (err) => {
        setLocation({ status: "denied", lat: null, lon: null, accuracy: null });
        setError(
          err.code === 1
            ? "Location access denied. Please allow location in your browser settings."
            : "Could not get your location. Try again."
        );
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }, []);

  async function startSession() {
    if (!selectedOffering) { setError("Select a subject first"); return; }
    if (location.status !== "granted" || location.lat === null) {
      setError("Location is required to start a session"); return;
    }
    setStarting(true);
    setError("");
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/faculty/sessions/start`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_offering_id: Number(selectedOffering),
          teacher_latitude: location.lat,
          teacher_longitude: location.lon,
          radius_meters: radius,
          duration_minutes: duration,
          session_type: sessionType,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed to start session");
      // Navigate to live session page
      router.push(`/teacher/session/${data.id}?code=${data.code}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setStarting(false);
    }
  }

  const selectedOfferingData = offerings.find((o) => String(o.id) === selectedOffering);

  return (
    <DashboardLayout role="faculty" pageTitle="Start Session">
      <div className="max-w-2xl">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <span className="w-8 h-px bg-white/20" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-widest">Attendance</span>
          </div>
          <h2 className="text-4xl font-display text-white">Start session</h2>
          <p className="text-white/40 text-sm mt-1">
            Your location will be used to enforce the {radius}m attendance radius.
          </p>
        </div>

        {/* Location block — most prominent */}
        <div className={`border p-8 mb-6 transition-all duration-500 ${
          location.status === "granted"
            ? "border-[#eca8d6]/30 bg-[#eca8d6]/5"
            : location.status === "denied"
            ? "border-red-400/30 bg-red-400/5"
            : "border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)]"
        }`}>
          <RadiusVisual status={location.status} />

          <div className="text-center mt-6">
            {location.status === "idle" && (
              <>
                <p className="text-white/60 text-sm mb-4">
                  We need your GPS location to set the attendance boundary.
                  Students must be within <span className="text-white font-mono">{radius}m</span> of you.
                </p>
                <button
                  id="get-location-btn"
                  onClick={requestLocation}
                  className="inline-flex items-center gap-2 px-6 py-2.5 bg-white text-black text-sm font-medium rounded-sm hover:bg-white/90 transition-all"
                >
                  <Crosshair className="w-4 h-4" />
                  Allow location access
                </button>
              </>
            )}

            {location.status === "requesting" && (
              <div className="flex flex-col items-center gap-3">
                <div className="w-6 h-6 border border-[#eca8d6]/40 border-t-[#eca8d6] rounded-full animate-spin" />
                <p className="text-white/50 text-sm">Waiting for GPS signal…</p>
              </div>
            )}

            {location.status === "granted" && location.lat !== null && (
              <div className="space-y-2">
                <AccuracyRing accuracy={location.accuracy} />
                <p className="text-xs font-mono text-white/30 mt-1">
                  {location.lat.toFixed(6)}, {location.lon?.toFixed(6)}
                </p>
                <button onClick={requestLocation}
                  className="text-xs font-mono text-white/30 hover:text-white/60 transition-colors underline underline-offset-2 mt-2 block mx-auto">
                  Re-detect location
                </button>
              </div>
            )}

            {location.status === "denied" && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 justify-center text-red-400">
                  <WifiOff className="w-4 h-4" />
                  <span className="text-sm">Location access denied</span>
                </div>
                <p className="text-white/30 text-xs max-w-xs mx-auto">
                  Enable location in your browser settings, then try again.
                </p>
                <button onClick={requestLocation}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-400/10 border border-red-400/20 text-red-400 text-sm rounded-sm hover:bg-red-400/20 transition-all">
                  Try again
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Session config */}
        <div className="border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)] p-6 space-y-5 mb-6">
          {/* Subject */}
          <div>
            <label className="block text-xs font-mono text-white/40 uppercase tracking-widest mb-2">Subject</label>
            <select
              id="offering-select"
              value={selectedOffering}
              onChange={(e) => setSelectedOffering(e.target.value)}
              className="w-full h-10 bg-[oklch(0.12_0.008_260)] border border-[oklch(0.18_0.008_260)] text-white text-sm px-3 rounded-sm focus:border-[#eca8d6]/40 outline-none appearance-none"
            >
              <option value="">Select subject…</option>
              {offerings.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.subject_code} — {o.subject_name} · Sec {o.section}
                </option>
              ))}
            </select>
          </div>

          {/* Session type */}
          <div>
            <label className="block text-xs font-mono text-white/40 uppercase tracking-widest mb-2">Session type</label>
            <div className="flex gap-2">
              {(["lecture", "lab", "tutorial"] as const).map((t) => (
                <button key={t} onClick={() => setSessionType(t)}
                  className={`flex-1 h-9 text-xs font-mono rounded-sm border transition-all capitalize ${
                    sessionType === t
                      ? "border-[#eca8d6]/50 bg-[#eca8d6]/10 text-[#eca8d6]"
                      : "border-[oklch(0.18_0.008_260)] text-white/40 hover:text-white hover:border-white/30"
                  }`}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Duration */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-mono text-white/40 uppercase tracking-widest">Duration</label>
              <span className="text-sm font-mono text-[#eca8d6]">{duration} min</span>
            </div>
            <div className="flex gap-2">
              {[5, 10, 15, 20, 25, 30].map((d) => (
                <button key={d} onClick={() => setDuration(d)}
                  className={`flex-1 h-9 text-xs font-mono rounded-sm border transition-all ${
                    duration === d
                      ? "border-[#eca8d6]/50 bg-[#eca8d6]/10 text-[#eca8d6]"
                      : "border-[oklch(0.18_0.008_260)] text-white/40 hover:text-white hover:border-white/30"
                  }`}>
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Radius */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-mono text-white/40 uppercase tracking-widest">Radius</label>
              <span className="text-sm font-mono text-white/60">{radius}m</span>
            </div>
            <input type="range" min={5} max={50} step={5} value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="w-full accent-[#eca8d6]" />
            <div className="flex justify-between text-[10px] font-mono text-white/20 mt-1">
              <span>5m (tight)</span><span>50m (loose)</span>
            </div>
          </div>
        </div>

        {/* Summary */}
        {selectedOfferingData && location.status === "granted" && (
          <div className="border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)] p-4 mb-6 flex flex-wrap gap-4 text-xs font-mono">
            <span className="text-white/40">Subject: <span className="text-white">{selectedOfferingData.subject_code}</span></span>
            <span className="text-white/40">Type: <span className="text-white capitalize">{sessionType}</span></span>
            <span className="text-white/40">Duration: <span className="text-[#eca8d6]">{duration} min</span></span>
            <span className="text-white/40">Radius: <span className="text-[#eca8d6]">{radius}m</span></span>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-400/10 border border-red-400/20 text-red-400 text-xs font-mono flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        <button
          id="start-session-btn"
          onClick={startSession}
          disabled={starting || location.status !== "granted" || !selectedOffering}
          className="w-full h-12 bg-white text-black text-sm font-medium rounded-sm hover:bg-white/90 transition-all disabled:opacity-30 flex items-center justify-center gap-2"
        >
          {starting ? (
            <>
              <div className="w-4 h-4 border border-black/30 border-t-black rounded-full animate-spin" />
              Starting…
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Start attendance session
            </>
          )}
        </button>

        {location.status !== "granted" && (
          <p className="text-center text-white/20 text-xs font-mono mt-3">
            Location access required to start
          </p>
        )}
      </div>
    </DashboardLayout>
  );
}
