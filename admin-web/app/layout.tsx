import React from "react";
import type { Metadata } from "next";
import { Instrument_Sans, Instrument_Serif, JetBrains_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const instrumentSans = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-instrument",
});
const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-instrument-serif",
});
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "InSync — Smart Attendance for Modern Campuses",
  description:
    "Real-time attendance verification with session codes and location technology. Trusted by BMS Institute.",
  icons: { icon: "/favicon.jpg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider
      appearance={{
        baseTheme: dark,
        variables: {
          colorPrimary: "#eca8d6",
          colorDanger: "#ef4444",
          borderRadius: "0.25rem",
          fontFamily: "Instrument Sans, system-ui, sans-serif",
        },
        elements: {
          card: "bg-transparent shadow-none border-0",
          headerTitle: "hidden",
          headerSubtitle: "hidden",
          socialButtonsBlockButton: "hidden",
          dividerLine: "hidden",
          dividerText: "hidden",
          footerAction: "hidden",
          footer: "hidden",
        },
      }}
    >
      <html lang="en" className="bg-background" data-scroll-behavior="smooth">
        <body
          className={`${instrumentSans.variable} ${instrumentSerif.variable} ${jetbrainsMono.variable} font-sans antialiased bg-background text-foreground`}
        >
          {children}
          <Analytics />
        </body>
      </html>
    </ClerkProvider>
  );
}
