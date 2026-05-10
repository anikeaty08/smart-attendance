"use client";

import { SignIn } from "@clerk/nextjs";
import { useEffect, useRef } from "react";

function GridLines() {
  return (
    <div className="absolute inset-0 z-[1] overflow-hidden pointer-events-none opacity-[0.07]">
      {[...Array(8)].map((_, i) => (
        <div
          key={`h-${i}`}
          className="absolute h-px bg-white"
          style={{ top: `${12.5 * (i + 1)}%`, left: 0, right: 0 }}
        />
      ))}
      {[...Array(12)].map((_, i) => (
        <div
          key={`v-${i}`}
          className="absolute w-px bg-white"
          style={{ left: `${8.33 * (i + 1)}%`, top: 0, bottom: 0 }}
        />
      ))}
    </div>
  );
}

function AnimatedOrb({ className }: { className?: string }) {
  return (
    <div
      className={`absolute rounded-full blur-[120px] opacity-20 animate-pulse pointer-events-none ${className}`}
    />
  );
}

export default function LoginPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let id: number;
    let t = 0;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const draw = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = "rgba(236,168,214,0.12)";
      ctx.lineWidth = 1;
      for (let wave = 0; wave < 4; wave++) {
        ctx.beginPath();
        for (let x = 0; x <= w; x += 4) {
          const y =
            h * 0.5 +
            Math.sin(x * 0.008 + t + wave * 0.7) * 40 +
            Math.sin(x * 0.015 + t * 1.3 + wave) * 25;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      t += 0.015;
      id = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(id);
    };
  }, []);

  return (
    <div className="relative min-h-screen bg-[oklch(0.06_0.008_260)] flex overflow-hidden">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 relative flex-col justify-between p-12 overflow-hidden">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
        <GridLines />
        <AnimatedOrb className="w-[600px] h-[600px] bg-[#eca8d6] -top-40 -left-40" />
        <AnimatedOrb className="w-[400px] h-[400px] bg-[#a78bfa] bottom-0 right-0" />

        {/* Logo */}
        <div className="relative z-10">
          <a href="/" className="inline-flex items-center gap-2">
            <span className="text-2xl font-display text-white font-bold">InSync</span>
            <span className="text-xs text-white/40 font-mono font-semibold">Attendance</span>
          </a>
        </div>

        {/* Main copy */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <span className="w-12 h-px bg-white/20" />
            <span className="text-sm font-mono text-white/40">BMS Institute of Technology</span>
          </div>
          <h1 className="text-6xl xl:text-[80px] font-display leading-[0.9] tracking-tight text-white mb-8">
            Smart.
            <br />
            <span className="text-white/30">Secure.</span>
            <br />
            <span className="text-white/10">Present.</span>
          </h1>
          <p className="text-white/50 leading-relaxed max-w-sm text-sm">
            Real-time attendance verification with session codes and location
            technology. Secure, accurate, and proxy-proof.
          </p>
        </div>

        {/* Bottom stats */}
        <div className="relative z-10 flex gap-10">
          {[
            { value: "10,000+", label: "Students" },
            { value: "99.9%", label: "Accuracy" },
            { value: "10 m", label: "Radius" },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-2xl font-display text-white">{s.value}</div>
              <div className="text-xs text-white/40 font-mono mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel — sign in form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12 relative">
        {/* Mobile logo */}
        <div className="absolute top-6 left-6 lg:hidden">
          <a href="/" className="inline-flex items-center gap-2">
            <span className="text-xl font-display text-white font-bold">InSync</span>
            <span className="text-xs text-white/40 font-mono">Attendance</span>
          </a>
        </div>

        <div className="w-full max-w-[400px]">
          {/* Header */}
          <div className="mb-10">
            <div className="flex items-center gap-3 mb-6">
              <span className="w-8 h-px bg-[#eca8d6]/60" />
              <span className="text-xs font-mono text-[#eca8d6]">Staff Portal</span>
            </div>
            <h2 className="text-4xl font-display text-white mb-3">Welcome back</h2>
            <p className="text-white/80 text-sm">
              Sign in with your institutional email to access your dashboard.
              <br />
              <span className="text-white/50 text-xs mt-1 block">
                Account access is managed by your institution.
              </span>
            </p>
          </div>

          {/* Clerk SignIn — no sign-up, no social */}
          <div className="clerk-login-wrapper">
            <SignIn
              routing="hash"
              fallbackRedirectUrl="/portal"
              appearance={{
                elements: {
                  rootBox: "w-full",
                  card: "w-full bg-transparent shadow-none p-0 gap-0",
                  headerTitle: "hidden",
                  headerSubtitle: "hidden",
                  socialButtonsBlockButton: "hidden",
                  socialButtonsBlock: "hidden",
                  dividerRow: "hidden",
                  dividerLine: "hidden",
                  dividerText: "hidden",
                  footerAction: "hidden",
                  footer: "hidden",
                  formButtonPrimary:
                    "w-full h-11 bg-white text-black text-sm font-medium rounded-sm hover:bg-white/90 active:bg-white/80 transition-all mt-2",
                  identityPreviewText: "text-white/70",
                  identityPreviewEditButtonIcon: "text-white/40",
                },
              }}
            />
          </div>

          {/* Bottom note */}
          <p className="text-center text-white/20 text-xs font-mono mt-8">
            © 2025 InSync Attendance · BMS Institute
          </p>
        </div>
      </div>
    </div>
  );
}
