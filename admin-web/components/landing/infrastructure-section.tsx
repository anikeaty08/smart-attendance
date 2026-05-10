"use client";

import { useEffect, useState, useRef } from "react";

const campusImages = [
  {
    url: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/WhatsApp%20Image%202026-05-10%20at%204.03.59%20PM-i0aXNz6Ff580WaED7hDllaSxRMxJ2r.jpeg",
    title: "Academic Block",
    subtitle: "Sir M.V. Block - Modern learning spaces",
  },
  {
    url: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/WhatsApp%20Image%202026-05-10%20at%204.04.10%20PM-QTX8g1mZgQ8QxsQUBOLVAAd0HBSxdA.jpeg",
    title: "BSN Block",
    subtitle: "Chemistry & Science Labs",
  },
  {
    url: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/WhatsApp%20Image%202026-05-10%20at%204.03.49%20PM-n74kEweHjzQalLiPKyqWpTL3WUjOKM.jpeg",
    title: "Stationery Hub",
    subtitle: "Central Campus Facility",
  },
  {
    url: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/WhatsApp%20Image%202026-05-10%20at%204.08.36%20PM-6GFsbobUsDCerj9FFFKMmSk3xqcjPr.jpeg",
    title: "Campus Pathways",
    subtitle: "Scenic green corridors",
  },
  {
    url: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/WhatsApp%20Image%202026-05-10%20at%204.09.29%20PM-vYOYTlkHZIwMXPa4pWNuKGuKIaoWFD.jpeg",
    title: "Campus Walkway",
    subtitle: "Tree-lined study areas",
  },
  {
    url: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/scrollable-1-BzliM0e68O7ejgA4nuOlqws4HDKmOr.webp",
    title: "Evening Campus",
    subtitle: "Illuminated campus ambiance",
  },
];

export function InfrastructureSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [activeImage, setActiveImage] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveImage((prev) => (prev + 1) % campusImages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="campus" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden bg-black">
      <div className="absolute top-0 right-0 w-[500px] h-[500px] rounded-full bg-white/[0.02] blur-[120px] pointer-events-none" />
      
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="mb-16">
          <span className={`inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-8 transition-all duration-700 ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}>
            <span className="w-12 h-px bg-foreground/20" />
            Campus tour
          </span>
          
          <div className="grid lg:grid-cols-2 gap-8 lg:gap-16">
            {/* Text content */}
            <div className={`transition-all duration-1000 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}>
              <h2 className="text-5xl lg:text-7xl font-display leading-tight mb-6">
                Beautiful
                <br />
                <span className="text-muted-foreground">campus</span>
              </h2>
              <p className="text-lg text-muted-foreground leading-relaxed mb-8">
                BMS Institute spans 21 acres of green campus with state-of-the-art facilities, modern classrooms, research labs, and vibrant student spaces.
              </p>
            </div>

            {/* Image carousel with dots */}
            <div className={`relative transition-all duration-1000 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}>
              {/* Main image */}
              <div className="relative w-full aspect-square overflow-hidden rounded-2xl bg-black border border-foreground/10">
                {campusImages.map((img, idx) => (
                  <div
                    key={idx}
                    className={`absolute inset-0 transition-all duration-700 ${
                      activeImage === idx ? "opacity-100" : "opacity-0"
                    }`}
                  >
                    <img
                      src={img.url}
                      alt={img.title}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                    
                    {/* Image info overlay */}
                    <div className="absolute bottom-0 left-0 right-0 p-6">
                      <h3 className="text-2xl font-display text-white mb-1">{img.title}</h3>
                      <p className="text-sm text-white/70">{img.subtitle}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination dots */}
              <div className="flex items-center gap-3 mt-6 justify-center">
                {campusImages.map((_, idx) => (
                  <button
                    key={idx}
                    onClick={() => setActiveImage(idx)}
                    className={`transition-all duration-300 rounded-full ${
                      activeImage === idx
                        ? "w-8 h-2 bg-white"
                        : "w-2 h-2 bg-white/30 hover:bg-white/50"
                    }`}
                    aria-label={`View campus image ${idx + 1}`}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Stats grid */}
        <div className={`grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 transition-all duration-1000 delay-200 ${
          isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        }`}>
          {[
            { value: "21", label: "acre campus" },
            { value: "3500+", label: "students" },
            { value: "50+", label: "faculty members" },
            { value: "11", label: "research centers" },
          ].map((stat) => (
            <div key={stat.label} className="bg-foreground/5 border border-foreground/10 rounded-lg p-6 hover:border-foreground/20 transition-colors">
              <span className="text-3xl lg:text-4xl font-display text-white block mb-2">{stat.value}</span>
              <span className="text-xs text-muted-foreground font-mono">{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
