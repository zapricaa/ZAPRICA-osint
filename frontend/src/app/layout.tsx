import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Navbar } from "@/components/Navbar";

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
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Navbar />
          <main className="ml-64 p-6 flex-1 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
