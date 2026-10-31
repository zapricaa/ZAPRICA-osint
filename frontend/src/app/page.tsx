"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="flex items-center gap-3 text-slate-400 font-mono text-sm">
        <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-ping" />
        <span>Initializing ZAPRICA Intelligence Environment...</span>
      </div>
    </div>
  );
}
