"use client";

import React, { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Shield, Globe, Lock, Database } from "lucide-react";
import { useAppStore } from "../store/useAppStore";
import { TitleBar } from "./TitleBar";
import { LoginView } from "./LoginView";

// API Base configuration
export let API_BASE = "http://localhost:8000";
if (typeof window !== "undefined") {
  const urlParams = new URLSearchParams(window.location.search);
  const backendPort = urlParams.get("backend_port");
  const protocol = window.location.protocol;
  const host = window.location.hostname || "localhost";
  if (backendPort) {
    API_BASE = `${protocol}//${host}:${backendPort}`;
  } else {
    const envApiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (envApiUrl) {
      API_BASE = envApiUrl;
    } else {
      API_BASE = `${protocol}//${host}:8000`;
    }
  }
}

const ALLOWED_TABS: Record<string, string[]> = {
  admin: ["dashboard", "crm", "research", "analyzer", "auditor", "drafting", "billing", "analytics", "settings", "backup"],
  lawyer: ["dashboard", "crm", "research", "analyzer", "drafting", "billing", "analytics", "settings"],
  auditor: ["auditor", "research", "analytics"],
  client: ["dashboard", "billing", "settings"]
};

// Helper to format raw text excerpt
const formatExcerpt = (text: string, maxLen: number = 300) => {
  if (!text) return "";
  if (text.length <= maxLen) return text;
  const sliced = text.slice(0, maxLen);
  const lastSpace = sliced.lastIndexOf(" ");
  if (lastSpace > maxLen * 0.8) {
    return `${sliced.slice(0, lastSpace)}...`;
  }
  return `${sliced}...`;
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  // Global Zustand Store
  const token = useAppStore(state => state.token);
  const setToken = useAppStore(state => state.setToken);
  const currentUser = useAppStore(state => state.currentUser);
  const setCurrentUser = useAppStore(state => state.setCurrentUser);
  const isOnlineMode = useAppStore(state => state.isOnlineMode);
  const setIsOnlineMode = useAppStore(state => state.setIsOnlineMode);
  const notification = useAppStore(state => state.notification);
  const showNotification = useAppStore(state => state.showNotification);
  
  const activeTab = useAppStore(state => state.activeTab);
  const setActiveTab = useAppStore(state => state.setActiveTab);

  // Local Auth State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [twoFactorRequired, setTwoFactorRequired] = useState(false);
  const [totpCode, setTotpCode] = useState("");

  // Online Mode State
  const [showOnlineModeModal, setShowOnlineModeModal] = useState(false);
  const [onlineModeSyncing, setOnlineModeSyncing] = useState(false);
  const [onlineModeResult, setOnlineModeResult] = useState<any>(null);
  const [onlineCnrNumber, setOnlineCnrNumber] = useState("");

  const { data: systemStatus = { ollama_connected: false }, refetch: fetchSystemStatus } = useQuery({
    queryKey: ["systemStatus"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/system/status`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (res.ok) return res.json();
      throw new Error("Failed to fetch system status");
    },
    enabled: !!token,
    refetchInterval: 10000
  });

  const syncOnlineMode = async (online: boolean) => {
    if (!token) return;
    try {
      await fetch(`${API_BASE}/api/system/connection-mode`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ online })
      });
    } catch {}
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);
      if (twoFactorRequired && totpCode) {
        formData.append("totp_code", totpCode);
      }

      const response = await fetch(`${API_BASE}/api/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString()
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Invalid email or password");
      }

      const data = await response.json();
      if (data.two_factor_required) {
        setTwoFactorRequired(true);
        showNotification("Two-factor authentication required.", "info");
        return;
      }

      localStorage.setItem("aegis_token", data.access_token);
      localStorage.setItem("aegis_refresh_token", data.refresh_token);
      setToken(data.access_token);
      showNotification("Sign in successful!", "success");
      setPassword("");
      setTotpCode("");
      setTwoFactorRequired(false);
      
      router.push("/dashboard");
    } catch (err: any) {
      showNotification(err.message, "error");
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      showNotification("Email and password are required", "error");
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Registration failed");
      }

      showNotification("Account created! Please sign in.", "success");
      setPassword("");
      setIsRegisterMode(false);
    } catch (err: any) {
      showNotification(err.message || "Registration failed", "error");
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("aegis_token");
    localStorage.removeItem("aegis_refresh_token");
    setToken("");
    setCurrentUser(null);
    setEmail("");
    setPassword("");
    showNotification("Signed out successfully.", "success");
    router.push("/");
  };

  useEffect(() => {
    if (token) {
      fetch(`${API_BASE}/api/auth/me`, {
        headers: { "Authorization": `Bearer ${token}` }
      })
      .then(res => {
        if (res.ok) return res.json();
        throw new Error("Invalid session");
      })
      .then(data => setCurrentUser(data))
      .catch(() => handleSignOut());
    }
  }, [token]);

  // Sync tab state with current route
  useEffect(() => {
    const path = pathname.replace("/", "");
    if (path && path !== activeTab) {
      setActiveTab(path);
    }
  }, [pathname]);

  if (!token) {
    return (
      <LoginView
        email={email}
        setEmail={setEmail}
        password={password}
        setPassword={setPassword}
        isRegisterMode={isRegisterMode}
        setIsRegisterMode={setIsRegisterMode}
        twoFactorRequired={twoFactorRequired}
        totpCode={totpCode}
        setTotpCode={setTotpCode}
        handleLogin={handleLogin}
        handleRegister={handleRegister}
      />
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#030303] text-zinc-100 font-sans">
      <TitleBar />
      {/* Top Banner Navigation */}
      <header className="h-16 border-b border-zinc-900/80 glass-panel px-6 flex items-center justify-between z-20 sticky top-0 bg-black/50 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-zinc-950 border border-zinc-800 rounded-lg">
            <Shield className="w-4.5 h-4.5 text-white" />
          </div>
          <span className="font-extrabold tracking-tight text-white text-lg premium-gradient-text">AegisAI</span>
          <div className="h-4 w-px bg-zinc-900 mx-2" />
          <span className="text-[10px] font-bold text-zinc-400 bg-zinc-900/80 border border-zinc-800/80 px-2.5 py-1 rounded-full font-mono uppercase tracking-wider">
            🛡️ {currentUser?.role || "loading"}
          </span>
          {/* Ollama offline status */}
          <div className="flex items-center gap-2 ml-2 bg-zinc-900/40 border border-zinc-900 px-3 py-1 rounded-full">
            <div className={`w-2 h-2 rounded-full ${systemStatus.ollama_connected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
            <span className="text-[9px] text-zinc-400 font-mono font-bold tracking-wider">
              AI RUNTIME: {systemStatus.ollama_connected ? "ONLINE" : "OFFLINE"}
            </span>
          </div>
          {systemStatus.memory && !systemStatus.memory.inference_allowed && (
            <div className="flex items-center gap-1.5 ml-2 bg-amber-950/30 border border-amber-900/50 px-3 py-1 rounded-full">
              <span className="text-[9px] text-amber-400 font-mono font-bold tracking-wider">
                LOW RAM: {systemStatus.memory.available_mb}MB free
              </span>
            </div>
          )}
        </div>

        {/* Global Notifications */}
        {notification && (
          <div className={`text-xs px-4 py-2.5 rounded-xl border max-w-sm font-medium animate-fade-in shadow-lg ${
            notification.type === "success" ? "bg-emerald-955/20 border-emerald-800/80 text-emerald-405 shadow-emerald-950/10" :
            notification.type === "error" ? "bg-rose-955/20 border-rose-800/80 text-rose-405 shadow-rose-950/10" :
            "bg-zinc-900 border-zinc-800 text-zinc-300 shadow-black/20"
          }`}>
            {notification.message}
          </div>
        )}

        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              if (!isOnlineMode) {
                setShowOnlineModeModal(true);
              } else {
                setIsOnlineMode(false);
                setOnlineModeResult(null);
                syncOnlineMode(false);
                showNotification("🔒 Offline mode restored — local data unlocked.", "success");
              }
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold border transition-all duration-300 cursor-pointer ${
              isOnlineMode
                ? "bg-amber-500/20 border-amber-500/60 text-amber-400 hover:bg-amber-500/30"
                : "bg-zinc-900 border-zinc-700 text-zinc-400 hover:bg-zinc-800 hover:text-white"
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            {isOnlineMode ? "Go Offline" : "Go Online"}
          </button>
          <span className="text-xs text-zinc-400 font-medium hidden sm:inline">{currentUser?.email}</span>
          <button 
            onClick={handleSignOut}
            className="text-xs border border-zinc-800 hover:bg-zinc-900 hover:text-white px-3.5 py-1.5 rounded-lg transition duration-200 font-medium cursor-pointer"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* ONLINE MODE MODALS (Same as before) */}
      {showOnlineModeModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-sm" id="online-mode-modal">
          <div className="bg-zinc-950 border border-amber-800/60 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl shadow-amber-955/20 space-y-5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-500/10 border border-amber-700/50 rounded-xl">
                <Globe className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Activate Online Mode?</h2>
                <p className="text-[11px] text-zinc-400 mt-0.5">This connects to external services.</p>
              </div>
            </div>

            <div className="bg-amber-955/20 border border-amber-900/40 rounded-xl p-4 space-y-2">
              <p className="text-xs font-bold text-amber-400 uppercase tracking-wider">⚠️ Security Notice</p>
              <ul className="text-xs text-zinc-300 space-y-1.5 list-disc list-inside">
                <li>All local data, chats, and documents will be <strong>locked & hidden</strong> while online</li>
                <li>Only eCourts sync will be permitted during this session</li>
                <li>No local AI inference runs while online</li>
                <li>Internet access is strictly limited to eCourts API only</li>
                <li>Click <strong>"Go Offline"</strong> to restore full local access</li>
              </ul>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowOnlineModeModal(false)}
                className="flex-1 py-2.5 text-sm text-zinc-400 border border-zinc-800 rounded-xl hover:bg-zinc-900 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="confirm-go-online"
                onClick={() => {
                  setIsOnlineMode(true);
                  setShowOnlineModeModal(false);
                  syncOnlineMode(true);
                  showNotification("🌐 Online mode active — local data locked for security.", "info");
                }}
                className="flex-1 py-2.5 text-sm font-bold text-white bg-amber-600 hover:bg-amber-500 border border-amber-500 rounded-xl transition cursor-pointer"
              >
                Activate Online Mode
              </button>
            </div>
          </div>
        </div>
      )}

      {isOnlineMode && (
        <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/90 backdrop-blur-md" id="online-mode-overlay">
          {/* Top warning banner */}
          <div className="absolute top-0 left-0 right-0 bg-amber-600 text-black text-xs font-bold py-2 text-center tracking-wider uppercase flex items-center justify-center gap-2">
            <Globe className="w-3.5 h-3.5" />
            🌐 ONLINE MODE ACTIVE — LOCAL DATA LOCKED FOR SECURITY
          </div>

          <div className="mt-12 w-full max-w-lg mx-4 space-y-6">
            {/* Logo */}
            <div className="text-center space-y-2">
              <div className="mx-auto w-16 h-16 bg-amber-500/10 border border-amber-700/40 rounded-2xl flex items-center justify-center">
                <Globe className="w-7 h-7 text-amber-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Online Session Active</h2>
              <p className="text-sm text-zinc-400">Local AI, documents, and client data are securely locked.<br />Use the tools below to sync with eCourts.</p>
            </div>

            {/* eCourts Sync Panel */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                <Database className="w-4 h-4 text-violet-400" />
                eCourts CNR Sync
              </h3>
              <p className="text-xs text-zinc-500">Enter a CNR number to fetch the latest hearing dates and case status from the eCourts platform.</p>

              <div className="space-y-3">
                <input
                  id="ecourts-cnr-input"
                  type="text"
                  placeholder="e.g. MHAU010012345678"
                  value={onlineCnrNumber}
                  onChange={e => setOnlineCnrNumber(e.target.value)}
                  className="w-full p-3 text-sm rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-700 focus:ring-0"
                />
                <button
                  id="ecourts-sync-btn"
                  onClick={async () => {
                    if (!onlineCnrNumber.trim()) {
                      showNotification("Please enter a CNR number", "error");
                      return;
                    }
                    setOnlineModeSyncing(true);
                    setOnlineModeResult(null);
                    try {
                      const res = await fetch(`${API_BASE}/api/ecourts/lookup?cnr=${encodeURIComponent(onlineCnrNumber.trim())}`, {
                        headers: { Authorization: `Bearer ${token}` }
                      });
                      const data = await res.json();
                      if (res.ok) {
                        setOnlineModeResult(data);
                        showNotification("eCourts data fetched successfully!", "success");
                      } else {
                        setOnlineModeResult({ error: data.detail || "Failed to fetch eCourts data" });
                        showNotification(data.detail || "eCourts lookup failed", "error");
                      }
                    } catch (err: any) {
                      const errorMsg = err instanceof Error ? err.message : "Error";
                      setOnlineModeResult({ error: errorMsg });
                      showNotification(errorMsg, "error");
                    } finally {
                      setOnlineModeSyncing(false);
                    }
                  }}
                  disabled={onlineModeSyncing}
                  className="w-full py-3 font-bold text-sm text-white bg-violet-700 hover:bg-violet-650 border border-violet-600 rounded-xl transition cursor-pointer disabled:opacity-50"
                >
                  {onlineModeSyncing ? "Syncing with eCourts..." : "Sync eCourts Data"}
                </button>
              </div>

              {/* Result Display */}
              {onlineModeResult && !onlineModeResult.error && (
                <div className="bg-emerald-955/20 border border-emerald-800/40 rounded-xl p-4 space-y-2 text-xs text-zinc-300">
                  <p className="text-emerald-400 font-bold text-[11px] uppercase tracking-wider">✅ eCourts Data Retrieved</p>
                  {onlineModeResult.case_title && <p><strong className="text-zinc-400">Case:</strong> {onlineModeResult.case_title}</p>}
                  {onlineModeResult.court && <p><strong className="text-zinc-400">Court:</strong> {onlineModeResult.court}</p>}
                  {onlineModeResult.judge && <p><strong className="text-zinc-400">Judge:</strong> {onlineModeResult.judge}</p>}
                  {onlineModeResult.next_date && <p><strong className="text-zinc-400">Next Hearing:</strong> {onlineModeResult.next_date}</p>}
                  {onlineModeResult.status && <p><strong className="text-zinc-400">Status:</strong> {onlineModeResult.status}</p>}
                  {onlineModeResult.raw_text && (
                    <p className="text-zinc-500 text-[10px] font-mono mt-2 border-t border-zinc-800 pt-2">{formatExcerpt(onlineModeResult.raw_text)}</p>
                  )}
                </div>
              )}
              {onlineModeResult?.error && (
                <div className="bg-rose-955/20 border border-rose-800/40 rounded-xl p-3 text-xs text-rose-400">
                  ❌ {onlineModeResult.error}
                </div>
              )}
            </div>

            <button
              id="go-offline-btn"
              onClick={() => {
                setIsOnlineMode(false);
                setOnlineModeResult(null);
                syncOnlineMode(false);
                showNotification("🔒 Offline mode restored — local data unlocked.", "success");
              }}
              className="w-full py-3 font-bold text-sm text-white bg-rose-800/60 hover:bg-rose-700 border border-rose-700/60 rounded-xl transition cursor-pointer flex items-center justify-center gap-2"
            >
              <Lock className="w-4 h-4" />
              Return to Offline Mode (Unlock Local Data)
            </button>
            <p className="text-center text-[10px] text-zinc-650 font-mono">
              🔒 AegisAI Secure Sandbox — All local data encrypted and locked
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-1">
        {/* Left Navigation Sidebar */}
        <aside className="w-64 border-r border-zinc-900/80 glass-panel p-4 flex flex-col justify-between hidden md:flex bg-black/20">
          <div className="space-y-1">
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer" || currentUser?.role === "client") && (
              <button 
                onClick={() => router.push("/dashboard")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "dashboard" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Shield className="w-4 h-4" />
                Matters & Context
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
              <button 
                onClick={() => router.push("/crm")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "crm" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Lock className="w-4 h-4" />
                Client CRM Directory
              </button>
            )}
            <button 
              onClick={() => router.push("/research")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "research" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
            >
              <Database className="w-4 h-4" />
              Hybrid Search RAG
            </button>
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
              <button 
                onClick={() => router.push("/analyzer")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "analyzer" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Globe className="w-4 h-4" />
                Case Document Analyzer
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "auditor") && (
              <button 
                onClick={() => router.push("/auditor")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "auditor" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Lock className="w-4 h-4" />
                Contract Auditor
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer" || currentUser?.role === "client") && (
              <button
                onClick={() => router.push("/billing")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "billing" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Shield className="w-4 h-4" />
                Billing & Invoices
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
              <button
                onClick={() => router.push("/analytics")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "analytics" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Database className="w-4 h-4" />
                Analytics
              </button>
            )}
            <button
              onClick={() => router.push("/settings")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "settings" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
            >
              <Globe className="w-4 h-4" />
              Settings
            </button>
            {currentUser?.role === "admin" && (
              <button
                onClick={() => router.push("/backup")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "backup" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Lock className="w-4 h-4" />
                Security Vault & Backups
              </button>
            )}
          </div>

          {/* Model settings widget */}
          <div className="p-3.5 border border-zinc-900 bg-zinc-950/60 rounded-xl space-y-2.5 mt-4">
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block font-mono">Active Inference Model</span>
            <select 
              value={useAppStore(state => state.selectedModel)}
              onChange={(e) => useAppStore.getState().setSelectedModel(e.target.value)}
              className="w-full p-2 text-xs rounded-lg glass-input text-zinc-300 focus:border-zinc-650 bg-zinc-950 border border-zinc-900 outline-none"
            >
              {systemStatus?.models_available?.length > 0 ? (
                systemStatus.models_available.map((m: string) => (
                  <option key={m} value={m}>{m}</option>
                ))
              ) : (
                <option value="deepseek-r1:8b">deepseek-r1:8b (Offline)</option>
              )}
            </select>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 overflow-y-auto max-w-7xl mx-auto w-full space-y-6">
          {children}
        </main>
      </div>
    </div>
  );
}
