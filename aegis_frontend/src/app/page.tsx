"use client";

import React, { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { User, Client, Matter, Schedule, Document, TimeEntry, Invoice } from "../types";
import { 
  Shield, Scale, FileText, Calendar, Database, Search, 
  Trash2, AlertTriangle, RefreshCw, Key, 
  Users, Plus, Clock, FileDiff, Download, Info,
  Lock, DollarSign, BarChart2, Globe, Settings
} from "lucide-react";

import { ErrorBoundary } from "../components/ErrorBoundary";
import { DashboardTab } from "../components/DashboardTab";
import { CrmTab } from "../components/CrmTab";
import { ResearchTab } from "../components/ResearchTab";
import { AnalyzerTab } from "../components/AnalyzerTab";
import { AuditorTab } from "../components/AuditorTab";
import { DraftingTab } from "../components/DraftingTab";
import { BillingTab } from "../components/BillingTab";
import { AnalyticsTab } from "../components/AnalyticsTab";
import { SettingsTab } from "../components/SettingsTab";
import { BackupTab } from "../components/BackupTab";
import { OnboardingGuide } from "../components/OnboardingGuide";

let API_BASE = "http://localhost:8000";
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

// PDF export helper (jsPDF)
const exportToPDF = async (title: string, content: string, firmName?: string, logoBase64?: string) => {
  try {
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF();
    let currentY = 20;

    // Draw custom logo & letterhead if configured
    if (logoBase64) {
      try {
        const cleanBase64 = logoBase64.includes(",") ? logoBase64.split(",")[1] : logoBase64;
        doc.addImage(cleanBase64, "PNG", 14, 10, 15, 15);
        currentY = 32;
      } catch (err) {
        console.error("Failed to render firm logo in PDF", err);
      }
    }

    if (firmName) {
      doc.setFontSize(12);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(24, 24, 27); // Dark gray
      doc.text(firmName.toUpperCase(), logoBase64 ? 32 : 14, logoBase64 ? 17 : 14);
      doc.setFontSize(8);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(113, 113, 122); // Light gray
      doc.text("AEGIS LEGAL SUITE — SECURE OFFLINE SYSTEM", logoBase64 ? 32 : 14, logoBase64 ? 22 : 19);
      
      // Draw horizontal divider line
      doc.setDrawColor(228, 228, 231);
      doc.line(14, logoBase64 ? 28 : 22, 196, logoBase64 ? 28 : 22);
      currentY = logoBase64 ? 36 : 28;
    }

    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(9, 9, 11);
    doc.text(title, 14, currentY);
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(63, 63, 70);
    const lines = doc.splitTextToSize(content, 180);
    doc.text(lines, 14, currentY + 10);
    doc.save(`${title.replace(/\s+/g, "_")}.pdf`);
  } catch (e) {
    alert("PDF export failed. Ensure jsPDF is installed.");
  }
};

const LANG: Record<string, Record<string, string>> = {
  en: { billing: "Billing & Invoices", analytics: "Analytics", settings: "Settings" },
  hi: { billing: "बिलिंग और चालान", analytics: "विश्लेषण", settings: "सेटिंग्स" }
};

export default function Home() {
  // Authentication State
  const [token, setToken] = useState(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem("aegis_token") || "";
  });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("lawyer");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [twoFactorRequired, setTwoFactorRequired] = useState(false);
  const [totpCode, setTotpCode] = useState("");
  
  // App Navigation
  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, crm, research, analyzer, auditor, drafting, backup, billing, analytics, settings
  
  interface SystemStatus {
    ollama_connected: boolean;
    models_available: string[];
    database_size_bytes: number;
    registered_clients: number;
    registered_matters: number;
    vault_document_count: number;
  }
  // Global System State
  const { data: systemStatus, refetch: fetchSystemStatus } = useQuery({
    queryKey: ["systemStatus"],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/system/status`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch system status");
    },
    enabled: !!token
  });
  const [selectedModel, setSelectedModel] = useState("deepseek-r1:8b");
  
  // Scoped lists shared across tabs
  const { data: clients = [], refetch: fetchClients } = useQuery({
    queryKey: ["clients"],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/clients`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch clients");
    },
    enabled: !!token
  });
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);

  const { data: matters = [], refetch: fetchMatters } = useQuery({
    queryKey: ["matters", selectedClient?.id],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/matters?client_id=${selectedClient?.id}`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch matters");
    },
    enabled: !!token && !!selectedClient
  });
  const [selectedMatter, setSelectedMatter] = useState<Matter | null>(null);

  const { data: schedules = [], refetch: fetchSchedules } = useQuery({
    queryKey: ["schedules", selectedMatter?.id],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/schedules?matter_id=${selectedMatter?.id}`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch schedules");
    },
    enabled: !!token && !!selectedMatter
  });

  const { data: documents = [], refetch: fetchDocuments } = useQuery({
    queryKey: ["documents", selectedMatter?.id],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/documents?matter_id=${selectedMatter?.id}`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch documents");
    },
    enabled: !!token && !!selectedMatter
  });

  // Preview Drawer Modal
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [previewText, setPreviewText] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Onboarding
  const [showOllamaOnboarding, setShowOllamaOnboarding] = useState(false);
  
  interface NotificationType {
    message: string;
    type: "success" | "error" | "info" | "warning";
  }
  // Global Toast Notification
  const [notification, setNotification] = useState<NotificationType | null>(null);
  const notificationTimeoutRef = useRef<any>(null);

  // Language toggle (en / hi)
  const [lang, setLang] = useState<"en" | "hi">("en");
  
  interface Annotation {
    id: number;
    document_id: number;
    selected_text: string;
    note?: string;
    color: string;
    page_hint?: string;
    created_at: string;
  }
  // Annotations State
  const [docAnnotations, setDocAnnotations] = useState<Annotation[]>([]);
  const [newAnnotationText, setNewAnnotationText] = useState("");
  const [newAnnotationNote, setNewAnnotationNote] = useState("");
  const [annotationColor, setAnnotationColor] = useState("yellow");
  const [annotationDocId, setAnnotationDocId] = useState<number | null>(null);

  // Hearing Alert polling state
  const { data: upcomingAlerts = [], refetch: fetchUpcomingAlerts } = useQuery({
    queryKey: ["upcomingAlerts"],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/system/upcoming-hearings?hours=48`);
      if (res.ok) {
        const data = await res.json();
        if (data.length > 0 && "Notification" in window && Notification.permission === "granted") {
          data.slice(0, 1).forEach((s: Schedule) => {
            const d = new Date(s.target_date);
            const hoursLeft = Math.round((d.getTime() - Date.now()) / 3600000);
            if (hoursLeft <= 24 && hoursLeft > 0) {
              new Notification(`⚖️ Hearing in ${hoursLeft}h — ${s.title}`, { body: `${s.schedule_type} scheduled` });
            }
          });
        }
        return data;
      }
      return [];
    },
    enabled: !!token,
    refetchInterval: 300000 // 5 minutes
  });

  // Online / Offline Security Mode
  const [isOnlineMode, setIsOnlineMode] = useState(false);
  const [showOnlineModeModal, setShowOnlineModeModal] = useState(false);
  const [onlineModeSyncing, setOnlineModeSyncing] = useState(false);
  const [onlineModeResult, setOnlineModeResult] = useState<any>(null);
  const [onlineCnrNumber, setOnlineCnrNumber] = useState("");

  const syncOnlineMode = async (online: boolean) => {
    const effectiveToken = token || localStorage.getItem("aegis_token");
    if (!effectiveToken) return;
    try {
      await fetchWithAuth(`${API_BASE}/api/system/connection-mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ online })
      });
    } catch {
      // Non-critical background sync log
    }
  };

  const ALLOWED_TABS: Record<string, string[]> = {
    admin: ["dashboard", "crm", "research", "analyzer", "auditor", "drafting", "billing", "analytics", "settings", "backup"],
    lawyer: ["dashboard", "crm", "research", "analyzer", "drafting", "billing", "analytics", "settings"],
    auditor: ["auditor", "research", "analytics"],
    client: ["dashboard", "billing", "settings"]
  };

  // Language setup

  // Sync activeTab limits under RBAC

  // Polling is now handled by React Query refetchInterval above

  // Request notifications setup

  // Dependencies for selected entities are now handled dynamically by useQuery's queryKey.
  // Initialization

  const showNotification = (message: string, type: "info" | "success" | "error" | "warning" = "info") => {
    if (notificationTimeoutRef.current) {
      clearTimeout(notificationTimeoutRef.current);
    }
    setNotification({ message, type });
    notificationTimeoutRef.current = setTimeout(() => {
      setNotification(null);
      notificationTimeoutRef.current = null;
    }, 5000);
  };

  const fetchWithAuth = async (url: string, options: RequestInit = {}) => {
    const headers = options.headers || {};
    const effectiveToken = token || localStorage.getItem("aegis_token");
    if (effectiveToken) {
      headers["Authorization"] = `Bearer ${effectiveToken}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers
    });
    
    if (response.status === 401) {
      // Attempt token refresh
      const refreshToken = localStorage.getItem("aegis_refresh_token");
      if (refreshToken) {
        const refreshFormData = new URLSearchParams();
        refreshFormData.append("refresh_token", refreshToken);
        const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: refreshFormData.toString()
        });
        
        if (refreshResponse.ok) {
          const refreshData = await refreshResponse.json();
          localStorage.setItem("aegis_token", refreshData.access_token);
          localStorage.setItem("aegis_refresh_token", refreshData.refresh_token);
          setToken(refreshData.access_token);
          
          // Retry original request
          headers["Authorization"] = `Bearer ${refreshData.access_token}`;
          return fetch(url, { ...options, headers });
        }
      }
      
      localStorage.removeItem("aegis_token");
      localStorage.removeItem("aegis_refresh_token");
      setToken("");
      setCurrentUser(null);
      throw new Error("Session expired. Please sign in again.");
    }
    
    return response;
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
        showNotification("Two-factor authentication required. Please enter your TOTP code.", "info");
        return;
      }

      localStorage.setItem("aegis_token", data.access_token);
      localStorage.setItem("aegis_refresh_token", data.refresh_token);
      setToken(data.access_token);
      showNotification("Sign in successful!", "success");
      setPassword("");
      setTotpCode("");
      setTwoFactorRequired(false);
      fetchCurrentUser(data.access_token);
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

  const fetchCurrentUser = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentUser(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("aegis_token");
    localStorage.removeItem("aegis_refresh_token");
    setToken("");
    setCurrentUser(null);
    setSelectedClient(null);
    setSelectedMatter(null);
    setPreviewDoc(null);
    setPreviewText("");
    setEmail("");
    setPassword("");
    showNotification("Signed out successfully.", "success");
  };

  // Custom query for Annotations since they depend on a specific function call

  const fetchAnnotations = async (docId: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/annotations/${docId}`);
      if (res.ok) setDocAnnotations(await res.json());
    } catch {}
  };

  const handleSaveAnnotation = async () => {
    if (!annotationDocId || !newAnnotationText.trim()) return;
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/annotations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: annotationDocId,
          selected_text: newAnnotationText,
          note: newAnnotationNote,
          color: annotationColor
        })
      });
      if (res.ok) {
        showNotification("Annotation saved", "success");
        setNewAnnotationText("");
        setNewAnnotationNote("");
        fetchAnnotations(annotationDocId);
      }
    } catch (e: any) {
      if (e instanceof Error) showNotification(e.message, "error");
      showNotification(e.message, "error");
    }
  };

  const handleDeleteAnnotation = async (id: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/annotations/${id}`, { method: "DELETE" });
      if (res.ok) {
        showNotification("Annotation deleted");
        if (annotationDocId) fetchAnnotations(annotationDocId);
      }
    } catch (e: any) {
      if (e instanceof Error) showNotification(e.message, "error");
      showNotification(e.message, "error");
    }
  };

  const handleViewDocumentText = async (doc: Document) => {
    setPreviewDoc(doc);
    setPreviewText("");
    setShowPreviewModal(true);
    setPreviewLoading(true);
    setAnnotationDocId(doc.id);
    fetchAnnotations(doc.id);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/documents/${doc.id}/text`);
      if (response.ok) {
        const data = await response.json();
        setPreviewText(data.text);
      } else {
        throw new Error("Failed to load text.");
      }
    } catch (err: any) {
      if (err instanceof Error) showNotification(err.message, "error");
      showNotification(err.message, "error");
      handleClosePreview();
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleClosePreview = () => {
    setShowPreviewModal(false);
    setPreviewDoc(null);
    setPreviewText("");
    setAnnotationDocId(null);
    setNewAnnotationText("");
    setNewAnnotationNote("");
  };

  const handleTabChange = (tab: string, callback?: () => void) => {
    setActiveTab(tab);
    if (callback) callback();
  };

  // Auth Guard
  if (!token) {
    useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("aegis_lang");
      if (saved === "hi") setLang("hi");
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      const role = currentUser.role || "lawyer";
      const allowed = ALLOWED_TABS[role] || ALLOWED_TABS.lawyer;
      if (!allowed.includes(activeTab)) {
        setActiveTab(allowed[0]);
      }
    }
  }, [currentUser, activeTab]);

  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchCurrentUser(token);
    }
  }, [token]);

  return (
      <div className="min-h-screen flex items-center justify-center relative p-4 bg-[#030303] overflow-hidden bg-radial-glow">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-zinc-800/10 opacity-30 blur-[130px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-zinc-800/15 opacity-20 blur-[130px]" />
        
        <div className="w-full max-w-md glass-panel p-8 rounded-2xl animate-fade-in z-10 shadow-2xl relative border border-zinc-850">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-[1px] bg-gradient-to-r from-transparent via-zinc-400/40 to-transparent" />
          
          <div className="flex flex-col items-center mb-8">
            <div className="p-3.5 bg-zinc-950 border border-zinc-800/80 rounded-2xl mb-3 shadow-inner relative animate-pulse-glow">
              <Shield className="w-8 h-8 text-white filter drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]" />
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white premium-gradient-text">AegisAI</h1>
            <p className="text-xs font-semibold text-zinc-400 mt-1 uppercase tracking-widest font-mono">Offline Security Vault</p>
          </div>

          <form onSubmit={isRegisterMode ? handleRegister : handleLogin} className="space-y-5">
            <div>
              <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Advocate Email Address</label>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="advocate@firm.local"
                className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500 font-medium bg-zinc-950 border border-zinc-805"
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Master Security PIN / Password</label>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500 bg-zinc-950 border border-zinc-805"
                required
              />
            </div>

            {/* Security Role dropdown removed to prevent self-assigned admin roles */}

            {twoFactorRequired && (
              <div>
                <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Two-Factor Authentication Code (TOTP)</label>
                <input 
                  type="text" 
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  placeholder="Enter 6-digit code"
                  className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500 font-medium bg-zinc-950 border border-zinc-805"
                  required
                />
              </div>
            )}

            <button 
              type="submit" 
              className="w-full py-3 bg-white hover:bg-zinc-200 text-black font-semibold rounded-lg text-sm transition-all duration-300 transform active:scale-[0.99] shadow-lg shadow-white/5 cursor-pointer flex items-center justify-center gap-2 font-bold"
            >
              <Lock className="w-4 h-4" />
              {isRegisterMode ? "Create Desktop Account" : twoFactorRequired ? "Verify Code & Enter" : "Access Security Vault"}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-900 flex flex-col space-y-3.5 text-center">
            <button 
              onClick={() => setIsRegisterMode(!isRegisterMode)}
              className="text-xs text-zinc-400 hover:text-zinc-200 transition font-medium cursor-pointer"
            >
              {isRegisterMode ? "Already registered? Sign in here" : "Need to initialize first client? Register here"}
            </button>
          </div>
          
          <div className="mt-6 text-center">
            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest bg-zinc-900/50 px-2.5 py-1 rounded-full border border-zinc-900">
              🔒 Local Device Sandbox: 100% Encrypted
            </span>
          </div>
        </div>
      </div>
    );
  }

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("aegis_lang");
      if (saved === "hi") setLang("hi");
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      const role = currentUser.role || "lawyer";
      const allowed = ALLOWED_TABS[role] || ALLOWED_TABS.lawyer;
      if (!allowed.includes(activeTab)) {
        setActiveTab(allowed[0]);
      }
    }
  }, [currentUser, activeTab]);

  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchCurrentUser(token);
    }
  }, [token]);

  return (
    <ErrorBoundary>
      <div className="min-h-screen flex flex-col bg-[#030303] text-zinc-100 font-sans">
        {/* Top Banner Navigation */}
        <header className="h-16 border-b border-zinc-900/80 glass-panel px-6 flex items-center justify-between z-20 sticky top-0 bg-black/50 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-zinc-950 border border-zinc-800 rounded-lg">
              <Shield className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="font-extrabold tracking-tight text-white text-lg premium-gradient-text">AegisAI</span>
            <div className="h-4 w-px bg-zinc-900 mx-2" />
            <span className="text-[10px] font-bold text-zinc-400 bg-zinc-900/80 border border-zinc-800/80 px-2.5 py-1 rounded-full font-mono uppercase tracking-wider">
              🛡️ {currentUser?.role}
            </span>
            {/* Ollama offline status */}
            <div className="flex items-center gap-2 ml-2 bg-zinc-900/40 border border-zinc-900 px-3 py-1 rounded-full">
              <div className={`w-2 h-2 rounded-full ${systemStatus.ollama_connected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
              <span className="text-[9px] text-zinc-400 font-mono font-bold tracking-wider">
                AI RUNTIME: {systemStatus.ollama_connected ? "ONLINE" : "OFFLINE"}
              </span>
            </div>
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
            {/* Online / Offline Mode Toggle Button */}
            <button
              id="online-mode-toggle"
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

        {/* ============ ONLINE MODE CONFIRMATION MODAL ============ */}
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
                  <li>Click <strong>&quot;Go Offline&quot;</strong> to restore full local access</li>
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

        {/* ============ ONLINE MODE LOCK OVERLAY ============ */}
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

              {/* Go Offline Button */}
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
                🔒 AegisAI Secure Sandbox — All local data encrypted and locked during online session
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
                  onClick={() => handleTabChange("dashboard")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "dashboard" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <Scale className="w-4 h-4" />
                  Matters & Context
                </button>
              )}
              {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
                <button 
                  onClick={() => handleTabChange("crm")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "crm" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <Users className="w-4 h-4" />
                  Client CRM Directory
                </button>
              )}
              <button 
                onClick={() => handleTabChange("research")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "research" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Search className="w-4 h-4" />
                Hybrid Search RAG
              </button>
              {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
                <button 
                  onClick={() => handleTabChange("analyzer")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "analyzer" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <Clock className="w-4 h-4" />
                  Case Document Analyzer
                </button>
              )}
              {(currentUser?.role === "admin" || currentUser?.role === "auditor") && (
                <button 
                  onClick={() => handleTabChange("auditor")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "auditor" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <FileDiff className="w-4 h-4" />
                  Contract Auditor
                </button>
              )}
              {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
                <button 
                  onClick={() => handleTabChange("drafting")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "drafting" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <FileText className="w-4 h-4" />
                  Document Draftsman
                </button>
              )}
              {(currentUser?.role === "admin" || currentUser?.role === "lawyer" || currentUser?.role === "client") && (
                <button
                  onClick={() => handleTabChange("billing")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "billing" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <DollarSign className="w-4 h-4" />
                  {LANG[lang]?.billing || LANG.en.billing}
                </button>
              )}
              {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
                <button
                  onClick={() => handleTabChange("analytics")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "analytics" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <BarChart2 className="w-4 h-4" />
                  {LANG[lang]?.analytics || LANG.en.analytics}
                </button>
              )}
              <button
                onClick={() => handleTabChange("settings")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "settings" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Settings className="w-4 h-4" />
                {LANG[lang]?.settings || LANG.en.settings}
              </button>
              {currentUser?.role === "admin" && (
                <button
                  onClick={() => handleTabChange("backup")}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "backup" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
                >
                  <Lock className="w-4 h-4" />
                  Security Vault & Backups
                </button>
              )}
            </div>

            {/* Model settings widget */}
            <div className="p-3.5 border border-zinc-900 bg-zinc-950/60 rounded-xl space-y-2.5">
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block font-mono">Active Inference Model</span>
              <select 
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full p-2 text-xs rounded-lg glass-input text-zinc-300 focus:border-zinc-650 bg-zinc-950 border border-zinc-900 outline-none"
              >
                {systemStatus.models_available.length > 0 ? (
                  systemStatus.models_available.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))
                ) : (
                  <option value="deepseek-r1:8b">deepseek-r1:8b (Offline)</option>
                )}
              </select>
              {!systemStatus.ollama_connected && (
                <button 
                  onClick={() => setShowOllamaOnboarding(true)}
                  className="w-full text-left p-2.5 bg-rose-955/20 border border-rose-900/50 hover:bg-rose-955/40 rounded-xl text-[10px] text-rose-400 font-bold flex items-center gap-1.5 cursor-pointer animate-pulse-glow-red"
                >
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>Ollama Disconnected: Click to Troubleshoot</span>
                </button>
              )}
              <button 
                onClick={(e) => { e.preventDefault(); fetchSystemStatus(); }}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 text-[10px] text-zinc-400 hover:text-white transition duration-200 cursor-pointer border border-zinc-900 rounded-lg hover:bg-zinc-900/50"
              >
                <RefreshCw className="w-3 h-3" />
                Refresh Diagnostics
              </button>
            </div>
          </aside>

          {/* Primary View Content Grid */}
          <main className="flex-1 p-6 overflow-y-auto max-w-7xl mx-auto w-full space-y-6">
            
            {activeTab === "dashboard" && (
              <DashboardTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                currentUser={currentUser}
                clients={clients}
                selectedClient={selectedClient}
                setSelectedClient={setSelectedClient}
                matters={matters}
                setMatters={() => {}}
                selectedMatter={selectedMatter}
                setSelectedMatter={setSelectedMatter}
                schedules={schedules}
                setSchedules={() => {}}
                documents={documents}
                setDocuments={() => {}}
                fetchMatters={() => { fetchMatters(); return Promise.resolve(); }}
                fetchSchedules={() => { fetchSchedules(); return Promise.resolve(); }}
                fetchDocuments={() => { fetchDocuments(); return Promise.resolve(); }}
                fetchSystemStatus={() => { fetchSystemStatus(); return Promise.resolve(); }}
                handleViewDocumentText={handleViewDocumentText}
              />
            )}

            {activeTab === "crm" && (
              <CrmTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                clients={clients}
                fetchClients={() => { fetchClients(); return Promise.resolve(); }}
              />
            )}

            {activeTab === "research" && (
              <ResearchTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                selectedMatter={selectedMatter}
                documents={documents}
                selectedModel={selectedModel}
              />
            )}

            {activeTab === "analyzer" && (
              <AnalyzerTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                selectedMatter={selectedMatter}
                documents={documents}
                currentUser={currentUser}
                selectedModel={selectedModel}
                lang={lang}
                exportToPDF={exportToPDF}
              />
            )}

            {activeTab === "auditor" && (
              <AuditorTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                selectedMatter={selectedMatter}
                documents={documents}
                currentUser={currentUser}
                selectedModel={selectedModel}
                exportToPDF={exportToPDF}
              />
            )}

            {activeTab === "drafting" && (
              <DraftingTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                currentUser={currentUser}
                selectedModel={selectedModel}
                exportToPDF={exportToPDF}
              />
            )}

            {activeTab === "billing" && (
              <BillingTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                currentUser={currentUser}
                selectedClient={selectedClient}
                matters={matters}
                lang={lang}
                exportToPDF={exportToPDF}
              />
            )}

            {activeTab === "analytics" && (
              <AnalyticsTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
              />
            )}

            {activeTab === "settings" && (
              <SettingsTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                currentUser={currentUser}
                setCurrentUser={setCurrentUser}
                lang={lang}
                setLang={setLang}
                upcomingAlerts={upcomingAlerts}
              />
            )}

            {activeTab === "backup" && (
              <BackupTab
                API_BASE={API_BASE}
                fetchWithAuth={fetchWithAuth}
                showNotification={showNotification}
                currentUser={currentUser}
                systemStatus={systemStatus}
                fetchSystemStatus={() => { fetchSystemStatus(); return Promise.resolve(); }}
                setClients={() => {}}
                setMatters={() => {}}
                setSchedules={() => {}}
                setDocuments={() => {}}
                setSelectedClient={setSelectedClient}
                setSelectedMatter={setSelectedMatter}
              />
            )}

          </main>

        </div>

        {/* Extracted Text Preview Drawer Modal */}
        {showPreviewModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-filter backdrop-blur-sm flex items-center justify-end z-50 animate-fade-in animate-duration-200">
            <div className="w-full max-w-4xl h-screen glass-panel p-6 flex flex-col justify-between shadow-2xl relative bg-zinc-950 border-l border-zinc-900">
              <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-transparent via-zinc-800 to-transparent" />
              
              <div className="space-y-4 flex-1 flex flex-col min-h-0">
                <div className="flex justify-between items-center border-b border-zinc-900/60 pb-3">
                  <div className="truncate">
                    <h2 className="text-sm font-bold text-white font-mono truncate">{previewDoc?.original_name}</h2>
                    <span className="text-[10px] text-zinc-500 font-mono">EXTRACTED EVIDENCE TEXT & ANNOTATIONS</span>
                  </div>
                  <button 
                    onClick={handleClosePreview}
                    className="text-zinc-400 hover:text-white px-3 py-1.5 border border-zinc-850 rounded-lg text-xs font-medium cursor-pointer bg-zinc-900 hover:bg-zinc-800 transition"
                  >
                    Close Drawer
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
                  {/* Column 1: Document text viewer */}
                  <div className="flex flex-col min-h-0 h-full">
                    <span className="text-[10px] text-zinc-500 font-mono mb-2 uppercase">Document Text</span>
                    <div className="flex-1 overflow-y-auto bg-zinc-955 p-4 rounded-xl border border-zinc-900 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed select-text">
                      {previewLoading ? (
                        <div className="flex items-center justify-center h-full gap-2 text-zinc-500 italic">
                          <RefreshCw className="w-4 h-4 animate-spin text-zinc-500" /> Loading text extraction...
                        </div>
                      ) : (
                        previewText || "No text content extracted."
                      )}
                    </div>
                  </div>

                  {/* Column 2: Annotation sidebar */}
                  <div className="flex flex-col min-h-0 h-full border-l border-zinc-900/60 pl-4 space-y-4">
                    <span className="text-[10px] text-zinc-500 font-mono uppercase">Notes & Annotations</span>
                    
                    {/* Add annotation */}
                    <div className="space-y-3 p-3 bg-zinc-900/20 border border-zinc-900 rounded-xl text-xs">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-zinc-300">Add Sticky Highlight</span>
                        <button 
                          onClick={() => {
                            const sel = window.getSelection()?.toString();
                            if (sel) {
                              setNewAnnotationText(sel);
                              showNotification("Selection grabbed!", "success");
                            } else {
                              showNotification("Select text in the preview window first", "warning");
                            }
                          }}
                          className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[10px] font-semibold cursor-pointer"
                        >
                          Grab Selected Text
                        </button>
                      </div>
                      
                      <textarea 
                        value={newAnnotationText} 
                        onChange={e => setNewAnnotationText(e.target.value)}
                        placeholder="Selected text segment..." 
                        rows={2}
                        className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 resize-none font-mono bg-zinc-950 border border-zinc-805"
                      />
                      
                      <input 
                        value={newAnnotationNote} 
                        onChange={e => setNewAnnotationNote(e.target.value)}
                        placeholder="Type sticky note comment here..." 
                        className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
                      />

                      <div className="flex justify-between items-center">
                        <div className="flex gap-2">
                          {["yellow", "green", "pink"].map(c => (
                            <button 
                              key={c} 
                              onClick={() => setAnnotationColor(c)}
                              className={`w-4 h-4 rounded-full border cursor-pointer ${annotationColor === c ? "border-white scale-110" : "border-transparent"}`}
                              style={{ backgroundColor: c === "yellow" ? "#eab308" : c === "green" ? "#22c55e" : "#ec4899" }}
                            />
                          ))}
                        </div>
                        
                        <button 
                          onClick={handleSaveAnnotation}
                          disabled={!newAnnotationText.trim()}
                          className="px-3 py-1.5 bg-zinc-100 hover:bg-zinc-300 disabled:opacity-50 text-zinc-900 font-bold rounded-lg text-[10px] transition cursor-pointer"
                        >
                          Save Highlight
                        </button>
                      </div>
                    </div>

                    {/* Annotations List */}
                    <div className="flex-1 overflow-y-auto space-y-2">
                      <span className="text-[10px] text-zinc-550 font-bold uppercase tracking-wider block font-mono">Saved Highlights</span>
                      {docAnnotations.map((ann) => (
                        <div 
                          key={ann.id} 
                          className="p-3 border rounded-xl text-xs space-y-1 bg-zinc-950/20"
                          style={{ borderColor: ann.color === "yellow" ? "#854d0e" : ann.color === "green" ? "#166534" : "#9d174d" }}
                        >
                          <div className="flex justify-between items-start gap-2">
                            <span className="font-mono text-[10px] font-semibold italic bg-zinc-900 px-1 py-0.5 rounded truncate" style={{ color: ann.color === "yellow" ? "#fef08a" : ann.color === "green" ? "#bbf7d0" : "#fbcfe8" }}>
                              &quot;{ann.selected_text}&quot;
                            </span>
                            <button onClick={() => handleDeleteAnnotation(ann.id)} className="text-zinc-650 hover:text-rose-400 shrink-0 cursor-pointer">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          {ann.note && <p className="text-zinc-300 font-sans text-xs">{ann.note}</p>}
                          <p className="text-[9px] text-zinc-600 font-mono">{new Date(ann.created_at).toLocaleTimeString()}</p>
                        </div>
                      ))}
                      {docAnnotations.length === 0 && (
                        <p className="text-xs text-zinc-550 italic text-center py-4">No highlights on this document yet.</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Ollama Troubleshooting & Onboarding On-Click Modal */}
        {showOllamaOnboarding && (
          <OnboardingGuide
            onClose={() => setShowOllamaOnboarding(false)}
            ollamaConnected={systemStatus.ollama_connected}
            availableModels={systemStatus.models_available}
            refreshDiagnostics={fetchSystemStatus}
          />
        )}

      </div>
    </ErrorBoundary>
  );
}
