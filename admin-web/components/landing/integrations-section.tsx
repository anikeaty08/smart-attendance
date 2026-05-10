"use client";

import { useEffect, useState, useRef } from "react";

const collegeData = [
  {
    category: "Academic Excellence",
    items: [
      { label: "NAAC Accreditation", value: "Grade A" },
      { label: "NIRF Ranking", value: "Band 151-300" },
      { label: "AICTE Approved", value: "Yes" },
      { label: "NBA Accreditation", value: "Multiple Programs" },
    ],
  },
  {
    category: "Campus & Facilities",
    items: [
      { label: "Campus Size", value: "21 Acres" },
      { label: "Student Population", value: "3500+" },
      { label: "Faculty Members", value: "50+" },
      { label: "Research Centers", value: "11" },
    ],
  },
  {
    category: "Placements",
    items: [
      { label: "Placement Rate", value: "95%" },
      { label: "Highest Package", value: "₹46.4 LPA" },
      { label: "Average Package", value: "₹8.07 LPA" },
      { label: "Top Recruiters", value: "Google, Amazon, IBM" },
    ],
  },
];

const programs = [
  "Computer Science & Engineering",
  "Information Science & Engineering",
  "Electronics & Communication",
  "Mechanical Engineering",
  "Civil Engineering",
  "Artificial Intelligence & ML",
  "M.Tech Programs",
  "MBA Programs",
];

export function IntegrationsSection() {
  const [isVisible, setIsVisible] = useState(false);
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

  return (
    <section
      id="stats"
      ref={sectionRef}
      className="relative py-24 lg:py-32 overflow-hidden bg-foreground/5"
    >
      <div className="absolute bottom-0 left-0 w-[600px] h-[400px] rounded-full bg-white/[0.02] blur-[120px] pointer-events-none" />
      
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className={`mb-16 transition-all duration-700 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}>
          <span className="inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-6">
            <span className="w-12 h-px bg-foreground/20" />
            Institution Overview
          </span>
          <h2 className="text-4xl lg:text-6xl font-display leading-tight">
            BMS Institute of Technology & Management
          </h2>
          <p className="text-muted-foreground mt-4 max-w-2xl">
            Established in 2002, recognized for academic excellence and innovation in engineering education.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid lg:grid-cols-3 gap-4 lg:gap-6 mb-20">
          {collegeData.map((section, idx) => (
            <div
              key={section.category}
              className={`bg-background border border-foreground/10 rounded-lg p-8 hover:border-foreground/20 transition-all duration-500 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: isVisible ? `${idx * 100}ms` : "0ms" }}
            >
              <h3 className="text-lg font-display mb-6 text-white">{section.category}</h3>
              <div className="space-y-4">
                {section.items.map((item) => (
                  <div key={item.label} className="flex justify-between items-start gap-4">
                    <span className="text-sm text-muted-foreground font-mono">{item.label}</span>
                    <span className="text-sm font-display text-white text-right">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Programs Section */}
        <div className={`transition-all duration-1000 delay-300 ${
          isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        }`}>
          <div className="mb-8">
            <h3 className="text-2xl lg:text-3xl font-display mb-8">
              Academic Programs
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {programs.map((program) => (
                <div
                  key={program}
                  className="bg-background border border-foreground/10 rounded-lg p-4 hover:border-foreground/20 hover:bg-foreground/5 transition-all duration-300"
                >
                  <p className="text-sm text-white font-medium">{program}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Location Card */}
        <div className={`mt-20 bg-gradient-to-r from-foreground/10 to-transparent border border-foreground/10 rounded-lg p-8 transition-all duration-1000 delay-400 ${
          isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        }`}>
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <h4 className="text-2xl font-display mb-4">Location</h4>
              <p className="text-muted-foreground mb-4">
                Doddaballapur Main Road, Avalahalli, Yelahanka, Bengaluru – 560119, Karnataka, India
              </p>
              <p className="text-sm text-muted-foreground font-mono">
                Affiliated with: Visvesvaraya Technological University (VTU), Belagavi
              </p>
            </div>
            <div>
              <h4 className="text-2xl font-display mb-4">Key Facts</h4>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li>24+ years of academic excellence</li>
                <li>10,000+ alumni network</li>
                <li>50+ industry collaborations</li>
                <li>Multiple research publications annually</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
