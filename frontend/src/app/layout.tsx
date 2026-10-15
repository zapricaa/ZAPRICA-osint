import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ZAPRICA — Autonomous AI OSINT Investigation Platform',
  description: 'AI-powered OSINT platform with verifiable cryptographic evidence provenance and interactive intelligence graph analysis.',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
