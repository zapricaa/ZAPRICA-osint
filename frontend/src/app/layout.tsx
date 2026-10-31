import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "ZAPRICA — AI-Powered OSINT Investigation Platform",
  description: "Autonomous, multi-agent cybersecurity and OSINT intelligence platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased flex flex-col font-sans">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
