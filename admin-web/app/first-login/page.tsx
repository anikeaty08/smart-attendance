"use client";

import { useEffect, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function FirstLoginPage() {
  const { isLoaded, isSignedIn, user } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState<"loading" | "send" | "verify" | "done">("loading");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [email, setEmail] = useState("");
  const [timeLeft, setTimeLeft] = useState(0);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.replace("/login"); return; }
    setEmail(user?.primaryEmailAddress?.emailAddress ?? "");
    setStep("send");
  }, [isLoaded, isSignedIn, user, router]);

  // Countdown timer
  useEffect(() => {
    if (timeLeft <= 0) return;
    const id = setInterval(() => setTimeLeft((t) => t - 1), 1000);
    return () => clearInterval(id);
  }, [timeLeft]);

  async function sendOtp() {
    setSending(true);
    setError("");
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/auth/first-login/start`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.status === "already_verified") {
        router.replace("/portal");
        return;
      }
      if (!res.ok) throw new Error(data.detail ?? "Failed to send OTP");
      setStep("verify");
      setTimeLeft(10 * 60); // 10 minutes
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setSending(false);
    }
  }

  async function verifyOtp() {
    if (otp.length !== 6) { setError("Enter the 6-digit code"); return; }
    setVerifying(true);
    setError("");
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/auth/first-login/verify`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ otp }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Invalid code");
      setStep("done");
      setTimeout(() => router.replace("/portal"), 1200);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setVerifying(false);
    }
  }

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="min-h-screen bg-[oklch(0.06_0.008_260)] flex items-center justify-center p-6">
      {/* Orb */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[#eca8d6] rounded-full blur-[200px] opacity-10 pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-12">
          <a href="/" className="inline-flex items-center gap-2 justify-center">
            <span className="text-2xl font-display text-white font-bold">InSync</span>
            <span className="text-xs text-white/40 font-mono">Attendance</span>
          </a>
        </div>

        <div className="border border-[oklch(0.18_0.008_260)] bg-[oklch(0.09_0.008_260)] p-8 lg:p-10">
          {/* Step indicator */}
          <div className="flex items-center gap-4 mb-8">
            <div className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono border transition-all ${step === "send" ? "border-[#eca8d6] bg-[#eca8d6]/10 text-[#eca8d6]" : "border-white/20 bg-white/5 text-white/40"}`}>1</div>
              <span className="text-xs font-mono text-white/40">Send</span>
            </div>
            <div className="flex-1 h-px bg-white/10" />
            <div className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono border transition-all ${step === "verify" ? "border-[#eca8d6] bg-[#eca8d6]/10 text-[#eca8d6]" : step === "done" ? "border-green-400 bg-green-400/10 text-green-400" : "border-white/20 bg-white/5 text-white/40"}`}>2</div>
              <span className="text-xs font-mono text-white/40">Verify</span>
            </div>
          </div>

          {step === "loading" && (
            <div className="text-center py-8">
              <div className="w-6 h-6 border border-[#eca8d6]/40 border-t-[#eca8d6] rounded-full animate-spin mx-auto" />
            </div>
          )}

          {step === "send" && (
            <>
              <h2 className="text-3xl font-display text-white mb-3">Verify your email</h2>
              <p className="text-white/50 text-sm leading-relaxed mb-8">
                This is your first login. We'll send a one-time code to{" "}
                <span className="text-white/80 font-mono">{email}</span> to confirm your identity.
              </p>
              {error && (
                <div className="mb-4 p-3 bg-red-400/10 border border-red-400/20 text-red-400 text-xs font-mono">
                  {error}
                </div>
              )}
              <button
                id="send-otp-btn"
                onClick={sendOtp}
                disabled={sending}
                className="w-full h-11 bg-white text-black text-sm font-medium rounded-sm hover:bg-white/90 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {sending ? (
                  <>
                    <div className="w-4 h-4 border border-black/30 border-t-black rounded-full animate-spin" />
                    Sending…
                  </>
                ) : "Send verification code"}
              </button>
            </>
          )}

          {step === "verify" && (
            <>
              <h2 className="text-3xl font-display text-white mb-3">Enter the code</h2>
              <p className="text-white/50 text-sm leading-relaxed mb-8">
                Check <span className="text-white/80 font-mono">{email}</span>. Code expires in{" "}
                <span className="text-[#eca8d6] font-mono">{fmt(timeLeft)}</span>.
              </p>

              <div className="mb-6">
                <label className="block text-xs font-mono text-white/60 uppercase tracking-widest mb-3">
                  6-digit OTP
                </label>
                <input
                  id="otp-input"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  placeholder="000000"
                  className="w-full h-14 bg-[oklch(0.12_0.008_260)] border border-[oklch(0.18_0.008_260)] focus:border-[#eca8d6]/60 outline-none text-white text-center text-2xl font-mono tracking-[0.5em] rounded-sm transition-colors"
                />
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-400/10 border border-red-400/20 text-red-400 text-xs font-mono">
                  {error}
                </div>
              )}

              <button
                id="verify-otp-btn"
                onClick={verifyOtp}
                disabled={verifying || otp.length !== 6}
                className="w-full h-11 bg-white text-black text-sm font-medium rounded-sm hover:bg-white/90 transition-all disabled:opacity-50 flex items-center justify-center gap-2 mb-4"
              >
                {verifying ? (
                  <>
                    <div className="w-4 h-4 border border-black/30 border-t-black rounded-full animate-spin" />
                    Verifying…
                  </>
                ) : "Confirm identity"}
              </button>

              <button
                onClick={() => { setStep("send"); setOtp(""); setError(""); }}
                className="w-full text-white/40 text-xs font-mono hover:text-white/60 transition-colors"
              >
                Resend code
              </button>
            </>
          )}

          {step === "done" && (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-full bg-green-400/10 border border-green-400/30 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-display text-white mb-2">Verified!</h2>
              <p className="text-white/50 text-sm">Redirecting to your dashboard…</p>
            </div>
          )}
        </div>

        <p className="text-center text-white/20 text-xs font-mono mt-6">
          © 2025 InSync Attendance · BMS Institute
        </p>
      </div>
    </div>
  );
}
