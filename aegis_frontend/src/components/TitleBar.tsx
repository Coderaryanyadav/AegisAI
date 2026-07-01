"use client";

import React, { useEffect, useState } from "react";
import { Minus, Square, X } from "lucide-react";

declare global {
  interface Window {
    aegisElectron?: {
      isOffline: boolean;
      version: string;
      invoke: (channel: string, data?: unknown) => Promise<unknown>;
    };
  }
}

export function TitleBar() {
  const [isElectron, setIsElectron] = useState(false);
  const [platform, setPlatform] = useState<string>("");

  useEffect(() => {
    const electron = typeof window !== "undefined" && window.aegisElectron;
    setIsElectron(!!electron);
    if (electron) {
      electron.invoke("window:getPlatform").then((p) => setPlatform(String(p || ""))).catch(() => {});
    }
  }, []);

  if (!isElectron) return null;

  const isMac = platform === "darwin";

  const handleMinimize = () => window.aegisElectron?.invoke("window:minimize");
  const handleMaximize = () => window.aegisElectron?.invoke("window:maximize");
  const handleClose = () => window.aegisElectron?.invoke("window:close");

  return (
    <div
      className="h-8 flex items-center justify-between bg-zinc-950 border-b border-zinc-900 select-none shrink-0"
      style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
    >
      <div className="flex items-center gap-2 px-3">
        {!isMac && (
          <span className="text-[10px] font-bold text-zinc-500 tracking-wider uppercase">AegisAI</span>
        )}
      </div>
      <div
        className="flex items-center h-full"
        style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
      >
        {isMac ? (
          <div className="flex items-center gap-2 px-3">
            <button
              onClick={handleClose}
              className="w-3 h-3 rounded-full bg-rose-500 hover:bg-rose-400 transition"
              aria-label="Close"
            />
            <button
              onClick={handleMinimize}
              className="w-3 h-3 rounded-full bg-amber-500 hover:bg-amber-400 transition"
              aria-label="Minimize"
            />
            <button
              onClick={handleMaximize}
              className="w-3 h-3 rounded-full bg-emerald-500 hover:bg-emerald-400 transition"
              aria-label="Maximize"
            />
          </div>
        ) : (
          <>
            <button
              onClick={handleMinimize}
              className="h-full px-4 hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 transition"
              aria-label="Minimize"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleMaximize}
              className="h-full px-4 hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 transition"
              aria-label="Maximize"
            >
              <Square className="w-3 h-3" />
            </button>
            <button
              onClick={handleClose}
              className="h-full px-4 hover:bg-rose-900 text-zinc-400 hover:text-white transition"
              aria-label="Close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
