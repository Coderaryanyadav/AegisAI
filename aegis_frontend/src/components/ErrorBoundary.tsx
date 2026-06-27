"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in AegisAI UI:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#030303] text-zinc-100 flex flex-col items-center justify-center p-6 text-center space-y-6">
          <div className="p-4 bg-rose-950/20 border border-rose-900/50 rounded-2xl animate-pulse-glow">
            <AlertTriangle className="w-12 h-12 text-rose-500" />
          </div>
          <div className="space-y-2 max-w-md">
            <h1 className="text-2xl font-bold tracking-tight text-white">Something went wrong</h1>
            <p className="text-sm text-zinc-400">
              The application encountered an unexpected visual rendering error. Don&apos;t worry, your offline encrypted data remains safe.
            </p>
          </div>
          {this.state.error && (
            <div className="bg-zinc-950 border border-zinc-900 rounded-xl p-4 max-w-xl text-left font-mono text-[10px] text-rose-400 overflow-x-auto w-full leading-relaxed">
              {this.state.error.toString()}
            </div>
          )}
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-zinc-100 hover:bg-zinc-200 text-zinc-900 font-bold rounded-lg text-xs transition flex items-center gap-1.5 cursor-pointer shadow"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Reload Interface
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
