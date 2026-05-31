"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { 
  Shield, Scale, FileText, Calendar, Database, Search, 
  Trash2, Upload, AlertTriangle, Play, RefreshCw, Key, 
  Users, CheckSquare, Plus, Clock, FileDiff, Download, Info,
  Lock, DollarSign, BarChart2, Mic, MicOff, Globe, TrendingUp,
  MessageCircle, BookOpen, Zap, Settings, Bell
} from "lucide-react";

const API_BASE = "http://localhost:8000";

// PDF export helper (jsPDF)
const exportToPDF = (title: string, content: string, firmName?: string, logoBase64?: string) => {
  try {
    const { jsPDF } = require("jspdf");
    const doc = new jsPDF();
    let currentY = 20;

    // 1. Draw custom logo & letterhead if configured
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

// Hindi translations
const LANG: Record<string, Record<string, string>> = {
  en: { billing: "Billing & Invoices", analytics: "Analytics", settings: "Settings", fir: "FIR Analyzer", predict: "Predict Outcome", voice: "Voice Dictation" },
  hi: { billing: "बिलिंग और चालान", analytics: "विश्लेषण", settings: "सेटिंग्स", fir: "FIR विश्लेषक", predict: "परिणाम पूर्वानुमान", voice: "वॉयस डिक्टेशन" }
};

const LANDMARK_PRECEDENTS = [
  { id: "kb", name: "Kesavananda Bharati v. State of Kerala", citation: "1973 SC", x: 200, y: 50, court: "Supreme Court", relevance: "Established the constitutional 'Basic Structure Doctrine' limiting amending powers." },
  { id: "mg", name: "Maneka Gandhi v. Union of India", citation: "1978 SC", x: 100, y: 150, court: "Supreme Court", relevance: "Expanded Article 21 to require 'due process of law' rather than just procedure." },
  { id: "mm", name: "Minerva Mills v. Union of India", citation: "1980 SC", x: 300, y: 150, court: "Supreme Court", relevance: "Ruled that judicial review is part of the basic structure of the constitution." },
  { id: "lk", name: "Lalita Kumari v. State of UP", citation: "2014 SC", x: 50, y: 250, court: "Supreme Court", relevance: "Made registration of FIR mandatory for cognizable offenses." },
  { id: "nj", name: "Navtej Singh Johar v. Union of India", citation: "2018 SC", x: 200, y: 250, court: "Supreme Court", relevance: "Decriminalized consensual sexual acts between same-sex adults." },
  { id: "js", name: "Joseph Shine v. Union of India", citation: "2018 SC", x: 350, y: 250, court: "Supreme Court", relevance: "Struck down Section 497 of IPC (Adultery) as unconstitutional." }
];

const PRECEDENT_LINKS = [
  { source: "kb", target: "mg" },
  { source: "kb", target: "mm" },
  { source: "mg", target: "nj" },
  { source: "mg", target: "js" },
  { source: "lk", target: "kb" }
];

export default function Home() {
  // Authentication State
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("lawyer");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  // App Navigation
  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, crm, research, analyzer, auditor, drafting, backup
  
  // Global System State
  const [systemStatus, setSystemStatus] = useState<any>({
    ollama_connected: false,
    models_available: [],
    database_size_bytes: 0,
    registered_clients: 0,
    registered_matters: 0,
    vault_document_count: 0
  });
  const [selectedModel, setSelectedModel] = useState("deepseek-r1:8b");
  
  // CRM States
  const [clients, setClients] = useState<any[]>([]);
  const [selectedClient, setSelectedClient] = useState<any>(null);
  const [matters, setMatters] = useState<any[]>([]);
  const [selectedMatter, setSelectedMatter] = useState<any>(null);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  
  // Forms
  const [newClient, setNewClient] = useState({ name: "", email: "", phone: "", notes: "" });
  const [newMatter, setNewMatter] = useState({ title: "", case_number: "", court: "", judge: "", opponent_name: "", opposing_advocate: "", facts: "", cnr_number: "" });
  const [newSchedule, setNewSchedule] = useState({ title: "", schedule_type: "hearing", target_date: "", notes: "" });

  // Conflict Checker States
  const [checkConflictClient, setCheckConflictClient] = useState("");
  const [checkConflictOpponent, setCheckConflictOpponent] = useState("");
  const [conflictResult, setConflictResult] = useState<any>(null);
  const [isCheckingConflict, setIsCheckingConflict] = useState(false);
  
  // RAG Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [ragResult, setRagResult] = useState("");
  const [ragSources, setRagSources] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Statutory Converter Helper
  const [helperAct, setHelperAct] = useState("ipc");
  const [helperSection, setHelperSection] = useState("");
  const [helperResult, setHelperResult] = useState<any>(null);

  // Document Analyzer / OCR State
  const [selectedDocForAnalysis, setSelectedDocForAnalysis] = useState<any>(null);
  const [analyzerTimeline, setAnalyzerTimeline] = useState<any[]>([]);
  const [analyzerFacts, setAnalyzerFacts] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Contract Auditor State
  const [selectedContractForAudit, setSelectedContractForAudit] = useState<any>(null);
  const [auditRisks, setAuditRisks] = useState<any[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);
  const [contractDocA, setContractDocA] = useState("");
  const [contractDocB, setContractDocB] = useState("");
  const [compareResults, setCompareResults] = useState<any[]>([]);
  const [isComparing, setIsComparing] = useState(false);

  // Simplify Clause State
  const [showSimplifyModal, setShowSimplifyModal] = useState(false);
  const [simplifyClauseText, setSimplifyClauseText] = useState("");
  const [simplifyResult, setSimplifyResult] = useState<any>(null);
  const [isSimplifying, setIsSimplifying] = useState(false);

  // Drafting State
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null);
  const [templateFields, setTemplateFields] = useState<any>({});
  const [generatedDraft, setGeneratedDraft] = useState("");
  const [isDrafting, setIsDrafting] = useState(false);
  const [courtHeader, setCourtHeader] = useState("none");
  const [lineSpacing, setLineSpacing] = useState("1.5");
  const [marginSpaces, setMarginSpaces] = useState("4");
  const [isFormattingDraft, setIsFormattingDraft] = useState(false);
  const [firmName, setFirmName] = useState("");
  const [firmLogo, setFirmLogo] = useState("");

  // Backups State
  const [backupHistory, setBackupHistory] = useState<any[]>([]);
  const [isBackupRunning, setIsBackupRunning] = useState(false);
  const [showPanicModal, setShowPanicModal] = useState(false);
  const [panicLoading, setPanicLoading] = useState(false);
  const [panicResult, setPanicResult] = useState<any>(null);

  // New Feature States
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<any>(null);
  const [previewText, setPreviewText] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [showOllamaOnboarding, setShowOllamaOnboarding] = useState(false);
  const [causeListUploadLoading, setCauseListUploadLoading] = useState(false);
  const [causeListMatches, setCauseListMatches] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Global Info / Error Notifications
  const [notification, setNotification] = useState<any>(null);

  // Language toggle (en / hi)
  const [lang, setLang] = useState<"en" | "hi">("en");
  const t = (key: string) => LANG[lang]?.[key] || LANG["en"][key] || key;

  // Billing / Invoice State
  const [billingMatterId, setBillingMatterId] = useState<number | null>(null);
  const [timeEntries, setTimeEntries] = useState<any[]>([]);
  const [newTimeEntry, setNewTimeEntry] = useState({ description: "", hours: "1", rate_per_hour: "5000", date: new Date().toISOString().split("T")[0] });
  const [invoices, setInvoices] = useState<any[]>([]);
  const [isCreatingInvoice, setIsCreatingInvoice] = useState(false);
  const [billingTimer, setBillingTimer] = useState<any>(null); // { start: Date, running: bool }
  const [timerSeconds, setTimerSeconds] = useState(0);
  const timerRef = useRef<any>(null);

  // Analytics State
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // 2FA State
  const [twoFaEnabled, setTwoFaEnabled] = useState(false);
  const [twoFaQr, setTwoFaQr] = useState("");
  const [twoFaSecret, setTwoFaSecret] = useState("");
  const [twoFaCode, setTwoFaCode] = useState("");
  const [twoFaLoading, setTwoFaLoading] = useState(false);

  // FIR Analyzer State
  const [firDocIds, setFirDocIds] = useState<number[]>([]);
  const [firResult, setFirResult] = useState<any>(null);
  const [isFirAnalyzing, setIsFirAnalyzing] = useState(false);

  // Predictive Outcome State
  const [predictFacts, setPredictFacts] = useState("");
  const [predictCourt, setPredictCourt] = useState("District Court");
  const [predictSections, setPredictSections] = useState("");
  const [predictResult, setPredictResult] = useState<any>(null);
  const [isPredicting, setIsPredicting] = useState(false);

  // Voice Dictation State
  const [isRecording, setIsRecording] = useState(false);
  const [transcribedText, setTranscribedText] = useState("");
  const mediaRecorderRef = useRef<any>(null);
  const audioChunksRef = useRef<any[]>([]);

  // Annotations State
  const [docAnnotations, setDocAnnotations] = useState<any[]>([]);
  const [newAnnotationText, setNewAnnotationText] = useState("");
  const [newAnnotationNote, setNewAnnotationNote] = useState("");
  const [annotationColor, setAnnotationColor] = useState("yellow");
  const [annotationDocId, setAnnotationDocId] = useState<number | null>(null);

  // Hearing Notification State
  const [upcomingAlerts, setUpcomingAlerts] = useState<any[]>([]);
  const [showAlertsPanel, setShowAlertsPanel] = useState(false);

  // Citation Graph Precedents State
  const [selectedPrecedent, setSelectedPrecedent] = useState<any>(null);

  // Online / Offline Security Mode
  const [isOnlineMode, setIsOnlineMode] = useState(false);
  const [showOnlineModeModal, setShowOnlineModeModal] = useState(false);
  const [onlineModeSyncing, setOnlineModeSyncing] = useState(false);
  const [onlineModeResult, setOnlineModeResult] = useState<any>(null);

  // RBAC Access Maps
  const ALLOWED_TABS: Record<string, string[]> = {
    admin: ["dashboard", "crm", "research", "analyzer", "auditor", "drafting", "billing", "analytics", "settings", "backup"],
    lawyer: ["dashboard", "crm", "research", "analyzer", "drafting", "billing", "analytics", "settings"],
    auditor: ["auditor", "research", "analytics"],
    client: ["dashboard", "billing", "settings"]
  };

  // Keep track of active tab legality under RBAC
  useEffect(() => {
    if (currentUser) {
      const role = currentUser.role || "lawyer";
      const allowed = ALLOWED_TABS[role] || ALLOWED_TABS.lawyer;
      if (!allowed.includes(activeTab)) {
        setActiveTab(allowed[0]);
      }
    }
  }, [currentUser, activeTab]);

  // Hearing notification polling (every 5 minutes)
  useEffect(() => {
    if (!token) return;
    const poll = async () => {
      try {
        const res = await fetchWithAuth(`${API_BASE}/api/system/upcoming-hearings?hours=48`);
        if (res.ok) {
          const data = await res.json();
          setUpcomingAlerts(data);
          if (data.length > 0 && "Notification" in window && Notification.permission === "granted") {
            data.slice(0, 1).forEach((s: any) => {
              const d = new Date(s.target_date);
              const hoursLeft = Math.round((d.getTime() - Date.now()) / 3600000);
              if (hoursLeft <= 24 && hoursLeft > 0) {
                new Notification(`⚖️ Hearing in ${hoursLeft}h — ${s.title}`, { body: `${s.schedule_type} scheduled` });
              }
            });
          }
        }
      } catch {}
    };
    poll();
    const id = setInterval(poll, 300000);
    return () => clearInterval(id);
  }, [token]);

  // Request notification permission
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  // Billing timer tick
  useEffect(() => {
    if (billingTimer?.running) {
      timerRef.current = setInterval(() => setTimerSeconds(s => s + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [billingTimer?.running]);

  // Load lang from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("aegis_lang") as any;
    if (saved) setLang(saved);
  }, []);

  const toggleLang = () => {
    const next = lang === "en" ? "hi" : "en";
    setLang(next);
    localStorage.setItem("aegis_lang", next);
  };

  // Initialization & Token Checks
  useEffect(() => {
    const savedToken = localStorage.getItem("aegis_token");
    if (savedToken) {
      setToken(savedToken);
      fetchCurrentUser(savedToken);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchSystemStatus();
      fetchClients();
      fetchBackupHistory();
      fetchDraftTemplates();
    }
  }, [token]);

  useEffect(() => {
    if (selectedClient) {
      fetchMatters(selectedClient.id);
      setSelectedMatter(null);
      setSchedules([]);
      setDocuments([]);
    }
  }, [selectedClient]);

  useEffect(() => {
    if (token && activeTab === "backup" && currentUser?.role === "admin") {
      fetchBackupHistory();
      fetchAuditLogs();
    }
  }, [activeTab, token, currentUser]);

  useEffect(() => {
    if (selectedMatter) {
      fetchSchedules(selectedMatter.id);
      fetchDocuments(selectedMatter.id);
    }
  }, [selectedMatter]);

  const showNotification = (message, type = "info") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };

  // HTTP Helper wrapper
  const fetchWithAuth = async (url: string, options: any = {}) => {
    const headers = options.headers || {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers
    });
    
    if (response.status === 401) {
      localStorage.removeItem("aegis_token");
      setToken("");
      setCurrentUser(null);
      throw new Error("Session expired. Please sign in again.");
    }
    
    return response;
  };

  // ================= API CALLS =================

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch(`${API_BASE}/api/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString()
      });

      if (!response.ok) {
        throw new Error("Invalid email or password");
      }

      const data = await response.json();
      localStorage.setItem("aegis_token", data.access_token);
      setToken(data.access_token);
      showNotification("Sign in successful!", "success");
      fetchCurrentUser(data.access_token);
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, role })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Registration failed");
      }

      showNotification("Account created! Please sign in.", "success");
      setIsRegisterMode(false);
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const autofillDemo = () => {
    setEmail("admin@legalai.local");
    setPassword("adminpassword123");
  };

  const fetchCurrentUser = async (authToken) => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentUser(data);
        setFirmName(data.firm_name || "");
        setFirmLogo(data.firm_logo || "");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("aegis_token");
    setToken("");
    setCurrentUser(null);
    showNotification("Signed out successfully.");
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/system/status`);
      if (response.ok) {
        const data = await response.json();
        setSystemStatus(data);
        if (data.models_available.length > 0 && !data.models_available.includes(selectedModel)) {
          setSelectedModel(data.models_available[0]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchClients = async () => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/clients`);
      if (response.ok) {
        const data = await response.json();
        setClients(data);
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleCreateClient = async (e) => {
    e.preventDefault();
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/clients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newClient)
      });
      if (response.ok) {
        showNotification("Client directory entry created", "success");
        setNewClient({ name: "", email: "", phone: "", notes: "" });
        fetchClients();
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleDeleteClient = async (clientId) => {
    if (!confirm("Are you sure? This will permanently wipe this client and all associated case matters.")) return;
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/clients/${clientId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        showNotification("Client record removed.");
        setSelectedClient(null);
        fetchClients();
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const fetchMatters = async (clientId) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/matters?client_id=${clientId}`);
      if (response.ok) {
        const data = await response.json();
        setMatters(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCheckConflict = async (e: any) => {
    if (e) e.preventDefault();
    if (!checkConflictClient.trim() || !checkConflictOpponent.trim()) {
      showNotification("Please enter both Prospective Client and Opponent Name", "error");
      return;
    }
    setIsCheckingConflict(true);
    setConflictResult(null);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/matters/check-conflict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_name: checkConflictClient,
          opponent_name: checkConflictOpponent
        })
      });
      if (response.ok) {
        const data = await response.json();
        setConflictResult(data);
        if (data.conflict_detected) {
          showNotification(`Conflict detected: ${data.severity.toUpperCase()} severity`, "warning");
        } else {
          showNotification("No conflict of interest detected", "success");
        }
      } else {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to run conflict check");
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to connect to backend server for conflict check", "error");
    } finally {
      setIsCheckingConflict(false);
    }
  };

  const handleCreateMatter = async (e) => {
    e.preventDefault();
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/matters`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...newMatter, client_id: selectedClient.id })
      });
      if (response.ok) {
        showNotification("Matter created successfully", "success");
        setNewMatter({ title: "", case_number: "", court: "", judge: "", opponent_name: "", opposing_advocate: "", facts: "", cnr_number: "" });
        fetchMatters(selectedClient.id);
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleDeleteMatter = async (matterId) => {
    if (!confirm("Are you sure you want to delete this case matter file?")) return;
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/matters/${matterId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        showNotification("Matter file deleted.");
        setSelectedMatter(null);
        fetchMatters(selectedClient.id);
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const fetchSchedules = async (matterId) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/schedules?matter_id=${matterId}`);
      if (response.ok) {
        const data = await response.json();
        setSchedules(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateSchedule = async (e) => {
    e.preventDefault();
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/schedules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...newSchedule, matter_id: selectedMatter.id })
      });
      if (response.ok) {
        showNotification("Event schedule added", "success");
        setNewSchedule({ title: "", schedule_type: "hearing", target_date: "", notes: "" });
        fetchSchedules(selectedMatter.id);
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleToggleSchedule = async (scheduleId, isCompleted) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/schedules/${scheduleId}/complete?completed=${isCompleted}`, {
        method: "PUT"
      });
      if (response.ok) {
        fetchSchedules(selectedMatter.id);
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const fetchDocuments = async (matterId) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/documents?matter_id=${matterId}`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUploadDocument = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    if (selectedMatter) {
      formData.append("matter_id", selectedMatter.id.toString());
    }

    try {
      showNotification("Uploading and preparing text parser...", "info");
      const response = await fetchWithAuth(`${API_BASE}/api/documents/upload`, {
        method: "POST",
        body: formData
      });
      if (response.ok) {
        showNotification("File uploaded successfully. Processing context indexing in background.", "success");
        if (selectedMatter) {
          fetchDocuments(selectedMatter.id);
        }
        fetchSystemStatus();
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!confirm("Are you sure? This will remove the file from your local Vault and wipe all its search vector chunks.")) return;
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/documents/${docId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        showNotification("Document scrubbed from device.");
        fetchDocuments(selectedMatter.id);
        fetchSystemStatus();
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  const handleViewDocumentText = async (doc: any) => {
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
      showNotification(err.message, "error");
      setShowPreviewModal(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCauseListUpload = async (e: any) => {
    const file = e.target.files[0];
    if (!file) return;

    setCauseListUploadLoading(true);
    setCauseListMatches([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      showNotification("Uploading Cause List PDF...", "info");
      const response = await fetchWithAuth(`${API_BASE}/api/analyze/cause-list`, {
        method: "POST",
        body: formData
      });
      if (response.ok) {
        const data = await response.json();
        setCauseListMatches(data.matches || []);
        showNotification(`Cause list scanning finished. Found ${data.matches_found} matching case(s).`, "success");
        if (selectedMatter) {
          fetchSchedules(selectedMatter.id);
        }
        fetchSystemStatus();
      } else {
        throw new Error("Failed to parse cause list PDF");
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setCauseListUploadLoading(false);
    }
  };

  // RAG Search API
  const handleRagSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setRagResult("");
    setRagSources([]);

    try {
      const body: any = {
        query: searchQuery,
        model_name: selectedModel
      };
      if (selectedMatter) {
        body.matter_ids = [selectedMatter.id];
      }

      const response = await fetchWithAuth(`${API_BASE}/api/research/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        throw new Error("Failed to query local AI models");
      }

      const data = await response.json();
      setRagResult(data.response);
      setRagSources(data.sources);
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setIsSearching(false);
    }
  };

  // Statutory converter call
  const handleConvertSection = async () => {
    if (!helperSection.trim()) return;
    setHelperResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/helper/ipc-bns?act=${helperAct}&section=${helperSection}`);
      if (!response.ok) {
        throw new Error("Section mapping not found.");
      }
      const data = await response.json();
      setHelperResult(data);
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  // Case Analyzer Call
  const handleAnalyzeDocument = async (docId) => {
    setIsAnalyzing(true);
    setAnalyzerTimeline([]);
    setAnalyzerFacts(null);
    try {
      // Timeline
      const timelineRes = await fetchWithAuth(`${API_BASE}/api/analyze/extract-timeline?document_id=${docId}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (timelineRes.ok) {
        const timelineData = await timelineRes.json();
        setAnalyzerTimeline(Array.isArray(timelineData.timeline) ? timelineData.timeline : []);
      }

      // Facts
      const factsRes = await fetchWithAuth(`${API_BASE}/api/analyze/facts?document_id=${docId}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (factsRes.ok) {
        const factsData = await factsRes.json();
        setAnalyzerFacts(factsData.facts);
      }
      showNotification("Document analysis completed", "success");
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Contract Audit Call
  const handleAuditContract = async (docId) => {
    setIsAuditing(true);
    setAuditRisks([]);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/audit/risk-scan?document_id=${docId}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (response.ok) {
        const data = await response.json();
        setAuditRisks(Array.isArray(data.risks) ? data.risks : []);
        showNotification("Contract risk scan completed", "success");
      }
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setIsAuditing(false);
    }
  };

  // ====== BILLING HANDLERS ======
  const fetchTimeEntries = async (matterId: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/billing/time-entries?matter_id=${matterId}`);
      if (res.ok) setTimeEntries(await res.json());
    } catch {}
  };

  const handleAddTimeEntry = async () => {
    if (!billingMatterId || !newTimeEntry.description) return;
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/billing/time-entry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ matter_id: billingMatterId, ...newTimeEntry })
      });
      if (res.ok) {
        showNotification("Time entry logged", "success");
        fetchTimeEntries(billingMatterId);
        setNewTimeEntry({ description: "", hours: "1", rate_per_hour: "5000", date: new Date().toISOString().split("T")[0] });
      }
    } catch (e: any) { showNotification(e.message, "error"); }
  };

  const handleDeleteTimeEntry = async (id: number) => {
    await fetchWithAuth(`${API_BASE}/api/billing/time-entry/${id}`, { method: "DELETE" });
    if (billingMatterId) fetchTimeEntries(billingMatterId);
  };

  const handleGenerateInvoice = async () => {
    if (!billingMatterId || !selectedClient) return;
    setIsCreatingInvoice(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/billing/invoice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: selectedClient.id, matter_id: billingMatterId })
      });
      if (res.ok) {
        const inv = await res.json();
        showNotification(`Invoice ${inv.invoice_number} generated!`, "success");
        fetchInvoices();
        // Auto PDF export
        exportToPDF(
          inv.invoice_number,
          `INVOICE\n${inv.invoice_number}\nClient: ${selectedClient?.name}\nTotal: ₹${inv.total_amount}\nGST (18%): ₹${inv.gst_amount}\nGrand Total: ₹${inv.grand_total}\nStatus: ${inv.status}\nDate: ${new Date().toLocaleDateString("en-IN")}`,
          currentUser?.firm_name,
          currentUser?.firm_logo
        );
      }
    } catch (e: any) { showNotification(e.message, "error"); }
    finally { setIsCreatingInvoice(false); }
  };

  const fetchInvoices = async () => {
    try {
      const url = selectedClient ? `${API_BASE}/api/billing/invoices?client_id=${selectedClient.id}` : `${API_BASE}/api/billing/invoices`;
      const res = await fetchWithAuth(url);
      if (res.ok) setInvoices(await res.json());
    } catch {}
  };

  const startTimer = () => {
    setTimerSeconds(0);
    setBillingTimer({ running: true, start: Date.now() });
  };
  const stopTimer = () => {
    setBillingTimer((t: any) => ({ ...t, running: false }));
    const hours = (timerSeconds / 3600).toFixed(2);
    setNewTimeEntry(prev => ({ ...prev, hours }));
    showNotification(`Timer stopped: ${hours} hours logged`, "info");
  };
  const formatTimer = (s: number) => `${String(Math.floor(s/3600)).padStart(2,"0")}:${String(Math.floor((s%3600)/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;

  // ====== ANALYTICS HANDLERS ======
  const fetchAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/analytics/summary`);
      if (res.ok) setAnalyticsData(await res.json());
    } catch {}
    finally { setAnalyticsLoading(false); }
  };

  // ====== 2FA HANDLERS ======
  const handle2FASetup = async () => {
    setTwoFaLoading(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/2fa/setup`, { method: "POST" });
      if (res.ok) {
        const d = await res.json();
        setTwoFaQr(d.qr_code_base64);
        setTwoFaSecret(d.secret);
      } else { showNotification("2FA setup failed", "error"); }
    } catch (e: any) { showNotification(e.message, "error"); }
    finally { setTwoFaLoading(false); }
  };

  const handle2FAEnable = async () => {
    if (!twoFaCode) return;
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/2fa/enable`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ totp_code: twoFaCode })
      });
      if (res.ok) {
        setTwoFaEnabled(true);
        setTwoFaQr("");
        showNotification("2FA enabled successfully!", "success");
      } else { showNotification("Invalid TOTP code", "error"); }
    } catch (e: any) { showNotification(e.message, "error"); }
  };

  const check2FAStatus = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/2fa/status`);
      if (res.ok) { const d = await res.json(); setTwoFaEnabled(d.enabled); }
    } catch {}
  };

  // ====== FIR ANALYZER ======
  const handleFIRAnalysis = async () => {
    if (firDocIds.length === 0) { showNotification("Select at least one document", "warning"); return; }
    setIsFirAnalyzing(true); setFirResult(null);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/analyze/fir`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_ids: firDocIds, model_name: selectedModel })
      });
      if (res.ok) { setFirResult(await res.json()); showNotification("FIR analysis complete", "success"); }
      else { showNotification("FIR analysis failed", "error"); }
    } catch (e: any) { showNotification(e.message, "error"); }
    finally { setIsFirAnalyzing(false); }
  };

  // ====== PREDICTIVE OUTCOME ======
  const handlePredictOutcome = async () => {
    if (!predictFacts.trim()) { showNotification("Enter case facts", "warning"); return; }
    setIsPredicting(true); setPredictResult(null);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/analyze/predict-outcome`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ facts: predictFacts, court: predictCourt, sections: predictSections, model_name: selectedModel })
      });
      if (res.ok) { setPredictResult(await res.json()); showNotification("Prediction complete", "success"); }
      else { showNotification("Prediction failed", "error"); }
    } catch (e: any) { showNotification(e.message, "error"); }
    finally { setIsPredicting(false); }
  };

  // ====== VOICE DICTATION ======
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      mr.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        const reader = new FileReader();
        reader.onloadend = async () => {
          const b64 = (reader.result as string).split(",")[1];
          try {
            const res = await fetchWithAuth(`${API_BASE}/api/analyze/transcribe`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ audio_base64: b64, language: lang })
            });
            if (res.ok) {
              const d = await res.json();
              setTranscribedText(prev => prev + " " + (d.transcript || ""));
              if (d.warning) showNotification(d.warning, "warning");
              else showNotification("Transcribed!", "success");
            }
          } catch (e: any) { showNotification(e.message, "error"); }
        };
        reader.readAsDataURL(blob);
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setIsRecording(true);
    } catch {
      showNotification("Microphone access denied", "error");
    }
  };
  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  // ====== WHATSAPP ======
  const handleWhatsAppReminder = async (scheduleId: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/whatsapp/reminder/${scheduleId}`);
      if (res.ok) {
        const d = await res.json();
        window.open(d.whatsapp_url, "_blank");
      }
    } catch (e: any) { showNotification(e.message, "error"); }
  };

  // ====== ANNOTATIONS ======
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
        body: JSON.stringify({ document_id: annotationDocId, selected_text: newAnnotationText, note: newAnnotationNote, color: annotationColor })
      });
      if (res.ok) {
        showNotification("Annotation saved!", "success");
        fetchAnnotations(annotationDocId);
        setNewAnnotationText(""); setNewAnnotationNote("");
      }
    } catch (e: any) { showNotification(e.message, "error"); }
  };

  const handleDeleteAnnotation = async (id: number) => {
    await fetchWithAuth(`${API_BASE}/api/annotations/${id}`, { method: "DELETE" });
    if (annotationDocId) fetchAnnotations(annotationDocId);
  };


  // ====== EXISTING HANDLERS BELOW ======

  // Simplify Clause Call
  const handleSimplifyClause = async () => {
    if (!simplifyClauseText.trim()) {
      showNotification("Please enter clause text to simplify", "warning");
      return;
    }
    setIsSimplifying(true);
    setSimplifyResult(null);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/audit/simplify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clause_text: simplifyClauseText, model_name: selectedModel })
      });
      if (response.ok) {
        const data = await response.json();
        setSimplifyResult(data);
      } else {
        showNotification("Failed to simplify clause", "error");
      }
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setIsSimplifying(false);
    }
  };

  // Clause Comparison Call
  const handleCompareContracts = async () => {
    if (!contractDocA || !contractDocB) {
      showNotification("Please select both documents to run comparison audit", "warning");
      return;
    }
    setIsComparing(true);
    setCompareResults([]);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/audit/compare?doc_id_a=${contractDocA}&doc_id_b=${contractDocB}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (response.ok) {
        const data = await response.json();
        setCompareResults(Array.isArray(data.comparison) ? data.comparison : []);
        showNotification("Clause variance audit completed", "success");
      }
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setIsComparing(false);
    }
  };

  // Drafting templates call
  const fetchDraftTemplates = async () => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/draft/templates`);
      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectTemplate = (template) => {
    setSelectedTemplate(template);
    const fields = {};
    template.fields.forEach(f => {
      fields[f] = "";
    });
    setTemplateFields(fields);
    setGeneratedDraft("");
  };

  const handleGenerateDraft = async (e) => {
    e.preventDefault();
    setIsDrafting(true);
    setGeneratedDraft("");
    try {
      const response = await fetchWithAuth(
        `${API_BASE}/api/draft/generate?template_id=${selectedTemplate.id}&model_name=${selectedModel}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(templateFields)
        }
      );
      if (response.ok) {
        const data = await response.json();
        setGeneratedDraft(data.draft);
        showNotification("Legal draft generated successfully", "success");
      }
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setIsDrafting(false);
    }
  };

  const handleApplyFormatting = async () => {
    if (!generatedDraft) return;
    setIsFormattingDraft(true);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/draft/format`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          draft_text: generatedDraft,
          court_header: courtHeader,
          line_spacing: parseFloat(lineSpacing),
          margin_spaces: parseInt(marginSpaces, 10)
        })
      });
      if (response.ok) {
        const data = await response.json();
        setGeneratedDraft(data.formatted_draft);
        showNotification("Applied court formatting guidelines.", "success");
      } else {
        throw new Error("Failed to apply formatting");
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsFormattingDraft(false);
    }
  };

  // Backup calls
  const fetchBackupHistory = async () => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/backup/history`);
      if (response.ok) {
        const data = await response.json();
        setBackupHistory(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/system/audit-logs`);
      if (response.ok) {
        const data = await response.json();
        setAuditLogs(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleExportAuditLogs = async () => {
    try {
      showNotification("Generating cryptographically signed audit report...", "info");
      const response = await fetchWithAuth(`${API_BASE}/api/system/audit-logs/export`);
      if (response.ok) {
        const text = await response.text();
        const blob = new Blob([text], { type: "text/plain" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "aegis_compliance_audit_report.txt";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        showNotification("Signed audit report exported successfully.", "success");
      } else {
        throw new Error("Failed to export signed audit report");
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    }
  };

  const handleRunManualBackup = async () => {
    setIsBackupRunning(true);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/backup/create`, {
        method: "POST"
      });
      if (response.ok) {
        showNotification("AES-256 backup archive saved successfully", "success");
        fetchBackupHistory();
        fetchSystemStatus();
      }
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setIsBackupRunning(false);
    }
  };

  const handleTriggerRestore = async (backupPath) => {
    if (!confirm("Are you sure? Restoring will revert all active cases, files, and vector spaces to the chosen backup point.")) return;
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/backup/restore?backup_path=${encodeURIComponent(backupPath)}`, {
        method: "POST"
      });
      if (response.ok) {
        showNotification("Application state restored successfully. Reloading...", "success");
        setTimeout(() => window.location.reload(), 1500);
      }
    } catch (err) {
      showNotification(err.message, "error");
    }
  };

  // EMERGENCY WIPE BUTTON API
  const handlePanicWipe = async () => {
    setPanicLoading(true);
    setPanicResult(null);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/backup/panic`, {
        method: "POST"
      });
      if (response.ok) {
        const data = await response.json();
        setPanicResult(data);
        showNotification("Panic wipe executed. System has been sealed and cleared.", "success");
        // Reset states
        setClients([]);
        setSelectedClient(null);
        setMatters([]);
        setSelectedMatter(null);
        setSchedules([]);
        setDocuments([]);
      }
    } catch (err) {
      showNotification(err.message, "error");
    } finally {
      setPanicLoading(false);
    }
  };

  // Render Login Gate
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center relative p-4 bg-[#030303] overflow-hidden bg-radial-glow">
        {/* Cybernetic glowing background spots */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-zinc-800/10 opacity-30 blur-[130px] animate-pulse-glow" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-zinc-800/15 opacity-20 blur-[130px]" />
        
        <div className="w-full max-w-md glass-panel p-8 rounded-2xl animate-fade-in z-10 shadow-2xl relative border-zinc-850">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-[1px] bg-gradient-to-r from-transparent via-zinc-400/40 to-transparent" />
          
          <div className="flex flex-col items-center mb-8">
            <div className="p-3.5 bg-zinc-950 border border-zinc-800/80 rounded-2xl mb-3 shadow-inner relative animate-pulse-glow">
              <Shield className="w-8 h-8 text-white filter drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]" />
              <div className="absolute inset-0 border border-white/5 rounded-2xl" />
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
                className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500 font-medium"
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
                className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500"
                required
              />
            </div>

            {isRegisterMode && (
              <div>
                <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Security Role Authorization</label>
                <select 
                  value={role} 
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full p-3 rounded-lg glass-input text-zinc-300 text-sm focus:border-zinc-500 font-mono bg-zinc-950"
                >
                  <option value="lawyer">Advocate / Lawyer</option>
                  <option value="admin">Administrator (DB/Restore)</option>
                  <option value="auditor">Audit Officer</option>
                  <option value="client">Client (Read-Only Portal)</option>
                </select>
              </div>
            )}

            <button 
              type="submit" 
              className="w-full py-3 bg-white hover:bg-zinc-200 text-black font-semibold rounded-lg text-sm transition-all duration-300 transform active:scale-[0.99] shadow-lg shadow-white/5 cursor-pointer flex items-center justify-center gap-2"
            >
              <Lock className="w-4 h-4" />
              {isRegisterMode ? "Create Desktop Account" : "Access Security Vault"}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-900 flex flex-col space-y-3.5 text-center">
            <button 
              onClick={() => setIsRegisterMode(!isRegisterMode)}
              className="text-xs text-zinc-400 hover:text-zinc-200 transition font-medium"
            >
              {isRegisterMode ? "Already registered? Sign in here" : "Need to initialize first client? Register here"}
            </button>
            <button 
              onClick={autofillDemo}
              className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center justify-center gap-1.5 transition font-medium border border-zinc-900 hover:border-zinc-800/80 bg-zinc-900/30 hover:bg-zinc-900/60 py-2 rounded-lg cursor-pointer animate-pulse-glow"
            >
              <Key className="w-3.5 h-3.5" />
              Autofill Local Demo Account
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

  return (
    <div className="min-h-screen flex flex-col bg-[#030303] text-zinc-100">
      {/* Top Banner Navigation */}
      <header className="h-16 border-b border-zinc-900/80 glass-panel px-6 flex items-center justify-between z-20 sticky top-0">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-zinc-900 border border-zinc-800 rounded-lg">
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
            notification.type === "success" ? "bg-emerald-950/20 border-emerald-800/80 text-emerald-400 shadow-emerald-950/10" :
            notification.type === "error" ? "bg-rose-950/20 border-rose-800/80 text-rose-400 shadow-rose-950/10" :
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
                showNotification("🔒 Offline mode restored — local data unlocked.", "success");
              }
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold border transition-all duration-300 cursor-pointer ${
              isOnlineMode
                ? "bg-amber-500/20 border-amber-500/60 text-amber-400 hover:bg-amber-500/30 animate-pulse"
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
          <div className="bg-zinc-950 border border-amber-800/60 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl shadow-amber-950/20 space-y-5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-500/10 border border-amber-700/50 rounded-xl">
                <Globe className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Activate Online Mode?</h2>
                <p className="text-[11px] text-zinc-400 mt-0.5">This connects to external services.</p>
              </div>
            </div>

            <div className="bg-amber-950/20 border border-amber-900/40 rounded-xl p-4 space-y-2">
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
                  value={newMatter.cnr_number}
                  onChange={e => setNewMatter(prev => ({ ...prev, cnr_number: e.target.value }))}
                  className="w-full p-3 text-sm rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-violet-700"
                />
                <button
                  id="ecourts-sync-btn"
                  onClick={async () => {
                    if (!newMatter.cnr_number.trim()) {
                      showNotification("Please enter a CNR number", "error");
                      return;
                    }
                    setOnlineModeSyncing(true);
                    setOnlineModeResult(null);
                    try {
                      const res = await fetch(`${API_BASE}/api/ecourts/lookup?cnr=${encodeURIComponent(newMatter.cnr_number.trim())}`, {
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
                      setOnlineModeResult({ error: err.message });
                      showNotification(err.message, "error");
                    } finally {
                      setOnlineModeSyncing(false);
                    }
                  }}
                  disabled={onlineModeSyncing}
                  className="w-full py-3 font-bold text-sm text-white bg-violet-700 hover:bg-violet-600 border border-violet-600 rounded-xl transition cursor-pointer disabled:opacity-50"
                >
                  {onlineModeSyncing ? "Syncing with eCourts..." : "Sync eCourts Data"}
                </button>
              </div>

              {/* Result Display */}
              {onlineModeResult && !onlineModeResult.error && (
                <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-xl p-4 space-y-2 text-xs text-zinc-300">
                  <p className="text-emerald-400 font-bold text-[11px] uppercase tracking-wider">✅ eCourts Data Retrieved</p>
                  {onlineModeResult.case_title && <p><strong className="text-zinc-400">Case:</strong> {onlineModeResult.case_title}</p>}
                  {onlineModeResult.court && <p><strong className="text-zinc-400">Court:</strong> {onlineModeResult.court}</p>}
                  {onlineModeResult.judge && <p><strong className="text-zinc-400">Judge:</strong> {onlineModeResult.judge}</p>}
                  {onlineModeResult.next_date && <p><strong className="text-zinc-400">Next Hearing:</strong> {onlineModeResult.next_date}</p>}
                  {onlineModeResult.status && <p><strong className="text-zinc-400">Status:</strong> {onlineModeResult.status}</p>}
                  {onlineModeResult.raw_text && (
                    <p className="text-zinc-500 text-[10px] font-mono mt-2 border-t border-zinc-800 pt-2">{onlineModeResult.raw_text.slice(0, 300)}...</p>
                  )}
                </div>
              )}
              {onlineModeResult?.error && (
                <div className="bg-rose-950/20 border border-rose-800/40 rounded-xl p-3 text-xs text-rose-400">
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
                showNotification("🔒 Offline mode restored — local data unlocked.", "success");
              }}
              className="w-full py-3 font-bold text-sm text-white bg-rose-800/60 hover:bg-rose-700 border border-rose-700/60 rounded-xl transition cursor-pointer flex items-center justify-center gap-2"
            >
              <Lock className="w-4 h-4" />
              Return to Offline Mode (Unlock Local Data)
            </button>

            <p className="text-center text-[10px] text-zinc-600 font-mono">
              🔒 AegisAI Secure Sandbox — All local data encrypted and locked during online session
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-1">
        {/* Left Navigation Sidebar */}
        <aside className="w-64 border-r border-zinc-900/80 glass-panel p-4 flex flex-col justify-between hidden md:flex">
          <div className="space-y-1">
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer" || currentUser?.role === "client") && (
              <button 
                onClick={() => setActiveTab("dashboard")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "dashboard" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Scale className="w-4 h-4" />
                Matters & Context
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
              <button 
                onClick={() => setActiveTab("crm")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "crm" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Users className="w-4 h-4" />
                Client CRM Directory
              </button>
            )}
            <button 
              onClick={() => setActiveTab("research")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "research" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
            >
              <Search className="w-4 h-4" />
              Hybrid Search RAG
            </button>
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
              <button 
                onClick={() => setActiveTab("analyzer")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "analyzer" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <Clock className="w-4 h-4" />
                Case Document Analyzer
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "auditor") && (
              <button 
                onClick={() => setActiveTab("auditor")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "auditor" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <FileDiff className="w-4 h-4" />
                Contract Auditor
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
              <button 
                onClick={() => setActiveTab("drafting")}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "drafting" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <FileText className="w-4 h-4" />
                Document Draftsman
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer" || currentUser?.role === "client") && (
              <button
                onClick={() => { setActiveTab("billing"); if (selectedMatter) { setBillingMatterId(selectedMatter.id); fetchTimeEntries(selectedMatter.id); fetchInvoices(); } }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "billing" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <DollarSign className="w-4 h-4" />
                {lang === "hi" ? "बिलिंग" : "Billing & Invoices"}
              </button>
            )}
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
              <button
                onClick={() => { setActiveTab("analytics"); fetchAnalytics(); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "analytics" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
              >
                <BarChart2 className="w-4 h-4" />
                {lang === "hi" ? "विश्लेषण" : "Analytics"}
              </button>
            )}
            <button
              onClick={() => { setActiveTab("settings"); check2FAStatus(); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 cursor-pointer ${activeTab === "settings" ? "bg-zinc-900/80 text-white border border-zinc-800 font-semibold shadow-inner" : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-200"}`}
            >
              <Settings className="w-4 h-4" />
              {lang === "hi" ? "सेटिंग्स" : "Settings"}
            </button>
            {currentUser?.role === "admin" && (
              <button
                onClick={() => setActiveTab("backup")}
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
              className="w-full p-2 text-xs rounded-lg glass-input text-zinc-300 focus:border-zinc-650 bg-zinc-950"
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
                className="w-full text-left p-2.5 bg-rose-950/20 border border-rose-900/50 hover:bg-rose-950/40 rounded-xl text-[10px] text-rose-400 font-bold flex items-center gap-1.5 cursor-pointer animate-pulse-glow-red"
              >
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>Ollama Disconnected: Click to Troubleshoot</span>
              </button>
            )}
            <button 
              onClick={fetchSystemStatus}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 text-[10px] text-zinc-400 hover:text-white transition duration-200 cursor-pointer border border-zinc-900 rounded-lg hover:bg-zinc-900/50"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh Diagnostics
            </button>
          </div>
        </aside>

        {/* Primary View Content Grid */}
        <main className="flex-1 p-6 overflow-y-auto max-w-7xl mx-auto w-full space-y-6">
          
          {/* TAB 1: MATTERS & CONTEXT SCOPER */}
          {activeTab === "dashboard" && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight">Matters Scoper & Context Vault</h1>
                  <p className="text-sm text-zinc-400">Scope RAG search index context or upload case file evidence.</p>
                </div>
              </div>

              {/* Scope Selection Box */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* 1. Client Select */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-4 rounded-xl space-y-3">
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5" /> 1. Select Client Folder
                  </h3>
                  <div className="space-y-1.5 max-h-[220px] overflow-y-auto">
                    {clients.map(c => (
                      <button 
                        key={c.id} 
                        onClick={() => setSelectedClient(c)}
                        className={`w-full text-left p-2 rounded-lg text-sm transition ${selectedClient?.id === c.id ? "bg-zinc-800 text-zinc-100 border border-zinc-700" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"}`}
                      >
                        {c.name}
                      </button>
                    ))}
                    {clients.length === 0 && (
                      <div className="text-xs text-zinc-500 p-2 italic">No clients registered. Register under CRM tab.</div>
                    )}
                  </div>
                </div>

                {/* 2. Matter Files Select */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-4 rounded-xl space-y-3">
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" /> 2. Select Matter File
                  </h3>
                  <div className="space-y-1.5 max-h-[220px] overflow-y-auto">
                    {selectedClient ? (
                      matters.map(m => (
                        <button 
                          key={m.id} 
                          onClick={() => setSelectedMatter(m)}
                          className={`w-full text-left p-2 rounded-lg text-sm transition ${selectedMatter?.id === m.id ? "bg-zinc-800 text-zinc-100 border border-zinc-700" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"}`}
                        >
                          <div className="font-medium">{m.title}</div>
                          <div className="text-[10px] text-zinc-500 font-mono">{m.case_number || "NO_CASE_NUM"}</div>
                        </button>
                      ))
                    ) : (
                      <div className="text-xs text-zinc-500 p-2 italic">Select a client folder first.</div>
                    )}
                    {selectedClient && matters.length === 0 && (
                      <div className="text-xs text-zinc-500 p-2 italic">No case matters found for this client. Create one below.</div>
                    )}
                  </div>
                </div>

                {/* 3. Matter metadata view */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-4 rounded-xl space-y-3">
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5" /> Case Details
                  </h3>
                  {selectedMatter ? (
                    <div className="text-xs space-y-2 text-zinc-300">
                      <div><strong className="text-zinc-500">Court:</strong> {selectedMatter.court || "Not specified"}</div>
                      <div><strong className="text-zinc-500">Judge:</strong> {selectedMatter.judge || "Not specified"}</div>
                      <div><strong className="text-zinc-500">Status:</strong> <span className="px-1.5 py-0.5 bg-zinc-800 rounded uppercase text-[10px] font-mono text-zinc-400">{selectedMatter.status}</span></div>
                      
                      {selectedMatter.cnr_number && (
                        <div className="pt-1.5 flex items-center justify-between border-t border-zinc-850/60">
                          <div>
                            <strong className="text-zinc-500">CNR Number:</strong>
                            <p className="font-mono text-zinc-300 text-[10px] mt-0.5">{selectedMatter.cnr_number}</p>
                          </div>
                          
                          <div className="flex items-center gap-1.5">
                            {selectedMatter.is_locked ? (
                              <span className="text-[9px] px-2 py-0.5 rounded-md border border-emerald-800/60 bg-emerald-950/20 text-emerald-400 font-bold tracking-wider font-mono">
                                LOCKED SECURE
                              </span>
                            ) : (
                              <button 
                                onClick={async () => {
                                  try {
                                    showNotification("Connecting safely to eCourts platform...", "success");
                                    const res = await fetchWithAuth(`${API_BASE}/api/matters/${selectedMatter.id}/sync-ecourts`, {
                                      method: "POST"
                                    });
                                    const data = await res.json();
                                    if (res.ok && data.status === "success") {
                                      showNotification(data.message, "success");
                                      fetchMatters(selectedClient.id);
                                      setSelectedMatter((prev: any) => ({ 
                                        ...prev, 
                                        court: data.court, 
                                        judge: data.judge, 
                                        is_locked: true 
                                      }));
                                      fetchSchedules(selectedMatter.id);
                                    } else {
                                      showNotification(data.message || "Failed to sync eCourts date", "error");
                                    }
                                  } catch (e: any) {
                                    showNotification(e.message, "error");
                                  }
                                }}
                                className="px-2.5 py-1 bg-violet-900/60 border border-violet-850 text-white font-semibold text-[9px] rounded-lg hover:bg-violet-800 transition cursor-pointer"
                              >
                                Sync eCourts
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                      
                      <div className="pt-2 border-t border-zinc-800">
                        <strong className="text-zinc-500">Case Facts Summary:</strong>
                        <p className="text-[11px] text-zinc-400 mt-1 line-clamp-4">{selectedMatter.facts || "No encrypted facts summary saved."}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-zinc-500 p-2 italic">Select a matter file to view details.</div>
                  )}
                </div>

              </div>

              {/* Court Cause List PDF Auto-Scheduler Widget */}
              {currentUser?.role !== "client" && (
                <div className="border border-zinc-900 bg-zinc-950/40 p-5 rounded-2xl space-y-4">
                  <div>
                    <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-zinc-400" /> Court Cause List Auto-Scheduler
                    </h3>
                    <p className="text-xs text-zinc-500 mt-1">Upload your daily cause list PDF. AegisAI parses it offline, matches case numbers against your matters, and schedules hearings automatically.</p>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row gap-4 items-center">
                    <div className="relative border-2 border-dashed border-zinc-900 rounded-xl p-6 text-center hover:border-zinc-800 transition w-full flex-1 cursor-pointer">
                      <input 
                        type="file" 
                        onChange={handleCauseListUpload}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        accept=".pdf"
                        disabled={causeListUploadLoading}
                      />
                      {causeListUploadLoading ? (
                        <div className="text-xs text-zinc-400 flex items-center justify-center gap-2">
                          <RefreshCw className="w-4 h-4 animate-spin text-zinc-500" /> Scanning Cause List & auto-scheduling matching hearings...
                        </div>
                      ) : (
                        <div className="text-xs text-zinc-300">
                          <Upload className="w-6 h-6 text-zinc-500 mx-auto mb-1.5" />
                          <span>Select daily Court Cause List PDF</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {causeListMatches.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider font-mono">Auto-Scheduled Hearings Matching Your Matters</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[180px] overflow-y-auto">
                        {causeListMatches.map((m, idx) => (
                          <div key={idx} className="p-3 bg-emerald-950/20 border border-emerald-900/60 rounded-xl text-xs flex flex-col justify-between">
                            <div>
                              <div className="font-bold text-emerald-400 font-mono">{m.case_number}</div>
                              <div className="text-zinc-200 font-medium mt-0.5">{m.title}</div>
                            </div>
                            <div className="text-[10px] text-emerald-500 font-mono mt-1.5 flex justify-between">
                              <span>Date: {m.target_date}</span>
                              <span>{m.already_scheduled ? "Already Scheduled" : "Scheduled Successfully"}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Dynamic Context Documents Ingestor */}
              {selectedMatter && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* File Vault Uploader */}
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <h3 className="text-sm font-bold text-zinc-200">Ingest Document Evidence</h3>
                    {currentUser?.role !== "client" ? (
                      <div className="border-2 border-dashed border-zinc-800 rounded-xl p-8 text-center hover:border-zinc-700 transition relative">
                        <input 
                          type="file" 
                          onChange={handleUploadDocument}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                          accept=".pdf,.txt"
                        />
                        <Upload className="w-8 h-8 text-zinc-500 mx-auto mb-2" />
                        <span className="text-xs text-zinc-300 block font-medium">Click to select files or drag-and-drop</span>
                        <span className="text-[10px] text-zinc-500 block mt-1">Supports PDF, TXT (Max 50MB)</span>
                      </div>
                    ) : (
                      <div className="p-4 border border-zinc-800 rounded-lg text-xs text-zinc-500 italic text-center">
                        Document uploads disabled in read-only portal view.
                      </div>
                    )}

                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Scoped Document Context Vault</h4>
                      <div className="space-y-1.5">
                        {documents.map(d => (
                          <div key={d.id} className="flex items-center justify-between p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs">
                            <div className="flex items-center gap-2 truncate">
                              <FileText className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                              <span className="truncate text-zinc-300 font-medium">{d.original_name}</span>
                              <span className={`text-[9px] px-1 rounded font-mono ${
                                d.status === "processed" ? "bg-emerald-950/40 text-emerald-400 border border-emerald-900" :
                                d.status === "failed" ? "bg-rose-950/40 text-rose-400 border border-rose-900" :
                                "bg-zinc-800 text-zinc-400 border border-zinc-700"
                              }`}>{d.status.toUpperCase()}</span>
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              {d.status === "processed" && (
                                <button 
                                  onClick={() => handleViewDocumentText(d)}
                                  className="text-zinc-400 hover:text-white p-1 transition"
                                  title="View Extracted Text"
                                >
                                  <FileText className="w-3.5 h-3.5" />
                                </button>
                              )}
                              {currentUser?.role !== "client" && (
                                <button 
                                  onClick={() => handleDeleteDocument(d.id)}
                                  className="text-zinc-500 hover:text-rose-400 p-1 transition"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                        {documents.length === 0 && (
                          <div className="text-xs text-zinc-500 p-2 italic">No document evidence uploaded for this matter folder.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Quick Case Deadlines Scheduler */}
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <div className="flex justify-between items-center">
                      <h3 className="text-sm font-bold text-zinc-200">Court Deadlines & Hearings</h3>
                    </div>

                    {currentUser?.role !== "client" ? (
                      <form onSubmit={handleCreateSchedule} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <input 
                          type="text" 
                          value={newSchedule.title}
                          onChange={(e) => setNewSchedule({ ...newSchedule, title: e.target.value })}
                          placeholder="E.g., File Rejoinder Affidavit"
                          className="p-2.5 text-xs rounded-lg glass-input text-zinc-200 w-full bg-zinc-950"
                          required
                        />
                        <select 
                          value={newSchedule.schedule_type}
                          onChange={(e) => setNewSchedule({ ...newSchedule, schedule_type: e.target.value })}
                          className="p-2.5 text-xs rounded-lg glass-input text-zinc-300 bg-zinc-950"
                        >
                          <option value="hearing">Court Hearing</option>
                          <option value="deadline">Filing Deadline</option>
                          <option value="meeting">Client Meeting</option>
                        </select>
                        <input 
                          type="date" 
                          value={newSchedule.target_date}
                          onChange={(e) => setNewSchedule({ ...newSchedule, target_date: e.target.value })}
                          className="p-2.5 text-xs rounded-lg glass-input text-zinc-300 w-full bg-zinc-950"
                          required
                        />
                        <button 
                          type="submit"
                          className="p-2.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs flex items-center justify-center gap-1 shadow transition cursor-pointer"
                        >
                          <Plus className="w-3.5 h-3.5" /> Add Task
                        </button>
                      </form>
                    ) : (
                      <div className="p-3 border border-zinc-800 rounded-lg text-xs text-zinc-500 italic text-center">
                        Task creation disabled in read-only portal view.
                      </div>
                    )}

                    <div className="space-y-2">
                      <div className="space-y-1.5 max-h-[220px] overflow-y-auto">
                        {schedules.map(s => (
                          <div key={s.id} className="flex items-center justify-between p-2 bg-zinc-900/60 border border-zinc-800/80 rounded-lg text-xs">
                            <div className="flex items-center gap-2.5">
                              <input 
                                type="checkbox"
                                checked={s.is_completed}
                                onChange={(e) => handleToggleSchedule(s.id, e.target.checked)}
                                disabled={currentUser?.role === "client"}
                                className="w-3.5 h-3.5 rounded border-zinc-800 text-zinc-100 accent-zinc-800 focus:ring-0 disabled:opacity-50"
                              />
                              <div className={s.is_completed ? "line-through text-zinc-500" : "text-zinc-300"}>
                                <div className="font-semibold">{s.title}</div>
                                <div className="text-[10px] text-zinc-500 flex items-center gap-1.5 font-mono">
                                  <Calendar className="w-3 h-3" /> {s.target_date}
                                  <span className="uppercase text-[9px] px-1 bg-zinc-800 border border-zinc-700 rounded text-zinc-400">{s.schedule_type}</span>
                                </div>
                              </div>
                            </div>
                            <button onClick={() => handleWhatsAppReminder(s.id)} title="Send WhatsApp Reminder"
                              className="text-emerald-600 hover:text-emerald-400 transition shrink-0">
                              <MessageCircle className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                        {schedules.length === 0 && (
                          <div className="text-xs text-zinc-500 p-2 italic animate-pulse">No upcoming schedules or deadlines saved.</div>
                        )}
                      </div>
                    </div>
                  </div>

                </div>
              )}

              {/* Add New Case Matter Form */}
              {selectedClient && currentUser?.role !== "client" && (
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                  <h3 className="text-sm font-bold text-zinc-200">Open New Matter File for {selectedClient.name}</h3>
                  <form onSubmit={handleCreateMatter} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Case Title / Subj</label>
                      <input 
                        type="text" 
                        value={newMatter.title}
                        onChange={(e) => setNewMatter({ ...newMatter, title: e.target.value })}
                        placeholder="State vs John Doe"
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Case Index Number</label>
                      <input 
                        type="text" 
                        value={newMatter.case_number}
                        onChange={(e) => setNewMatter({ ...newMatter, case_number: e.target.value })}
                        placeholder="FIR 104/2026 or OS 24/2026"
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Court Forum</label>
                      <input 
                        type="text" 
                        value={newMatter.court}
                        onChange={(e) => setNewMatter({ ...newMatter, court: e.target.value })}
                        placeholder="High Court of Delhi"
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Presiding Judge</label>
                      <input 
                        type="text" 
                        value={newMatter.judge}
                        onChange={(e) => setNewMatter({ ...newMatter, judge: e.target.value })}
                        placeholder="Hon'ble Justice Roy"
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Opponent Party Name</label>
                      <input 
                        type="text" 
                        value={newMatter.opponent_name || ""}
                        onChange={(e) => setNewMatter({ ...newMatter, opponent_name: e.target.value })}
                        placeholder="John Doe"
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Opposing Advocate</label>
                      <input 
                        type="text" 
                        value={newMatter.opposing_advocate || ""}
                        onChange={(e) => setNewMatter({ ...newMatter, opposing_advocate: e.target.value })}
                        placeholder="Jane Smith, Adv."
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">eCourts CNR Number</label>
                      <input 
                        type="text" 
                        value={newMatter.cnr_number || ""}
                        onChange={(e) => setNewMatter({ ...newMatter, cnr_number: e.target.value })}
                        placeholder="e.g. DLHC010001232026"
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    <div className="space-y-1 sm:col-span-3">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Initial Encrypted Facts</label>
                      <input 
                        type="text" 
                        value={newMatter.facts}
                        onChange={(e) => setNewMatter({ ...newMatter, facts: e.target.value })}
                        placeholder="Describe initial details which will be saved in encrypted columns..."
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    <div className="sm:col-span-3 pt-2">
                      <button 
                        type="submit"
                        className="px-4 py-2.5 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs shadow transition"
                      >
                        Create Matter File
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: CLIENT CRM */}
          {activeTab === "crm" && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Client Directory CRM</h1>
                <p className="text-sm text-zinc-400">Writably encrypt new client profiles at rest in database.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left side sidebar column */}
                <div className="space-y-6">
                  {/* Registration form */}
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <h3 className="text-sm font-bold text-zinc-200">Register Client File</h3>
                    <form onSubmit={handleCreateClient} className="space-y-4">
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Full Client Name</label>
                        <input 
                          type="text" 
                          value={newClient.name}
                          onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
                          placeholder="Mr. Suresh Kumar"
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Email (Optional)</label>
                        <input 
                          type="email" 
                          value={newClient.email}
                          onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                          placeholder="suresh@gmail.local"
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Phone Number (Optional)</label>
                        <input 
                          type="text" 
                          value={newClient.phone}
                          onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                          placeholder="+91 98765 43210"
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Confidential Notes (AES-256 Encrypted)</label>
                        <textarea 
                          value={newClient.notes}
                          onChange={(e) => setNewClient({ ...newClient, notes: e.target.value })}
                          placeholder="Enter highly sensitive remarks, fee parameters, or witness coordinates which will be encrypted..."
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200 h-24"
                        />
                      </div>
                      <button 
                        type="submit"
                        className="w-full py-2.5 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs shadow transition"
                      >
                        Encrypt & Save Client
                      </button>
                    </form>
                  </div>

                  {/* Conflict of Interest Checker Card */}
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <div>
                      <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-1.5">
                        <Scale className="w-4 h-4 text-indigo-400" /> Conflict Checker
                      </h3>
                      <p className="text-[11px] text-zinc-500 mt-1">Verify prospective representation safety against active database listings.</p>
                    </div>
                    
                    <form onSubmit={handleCheckConflict} className="space-y-3.5">
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Prospective Client Name</label>
                        <input 
                          type="text" 
                          value={checkConflictClient}
                          onChange={(e) => setCheckConflictClient(e.target.value)}
                          placeholder="e.g. Mr. Ramesh Saxena"
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Prospective Opponent Name</label>
                        <input 
                          type="text" 
                          value={checkConflictOpponent}
                          onChange={(e) => setCheckConflictOpponent(e.target.value)}
                          placeholder="e.g. John Doe"
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                          required
                        />
                      </div>
                      
                      <button 
                        type="submit"
                        disabled={isCheckingConflict}
                        className="w-full py-2.5 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs shadow transition flex items-center justify-center gap-1.5 disabled:opacity-50"
                      >
                        {isCheckingConflict ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            Checking Compliance...
                          </>
                        ) : (
                          <>
                            <Shield className="w-3.5 h-3.5 animate-pulse text-indigo-400" />
                            Run Conflict Search
                          </>
                        )}
                      </button>
                    </form>

                    {conflictResult && (
                      <div className={`p-4 rounded-xl border text-xs space-y-2 animate-fade-in ${
                        conflictResult.conflict_detected 
                          ? 'bg-rose-950/20 border-rose-900/55 text-rose-200' 
                          : 'bg-emerald-950/20 border-emerald-900/55 text-emerald-200'
                      }`}>
                        <div className="flex items-center justify-between">
                          <span className="font-bold flex items-center gap-1.5">
                            {conflictResult.conflict_detected ? (
                              <>
                                <AlertTriangle className="w-4 h-4 text-rose-400" />
                                Conflict Found
                              </>
                            ) : (
                              <>
                                <Shield className="w-4 h-4 text-emerald-400" />
                                Clearance Approved
                              </>
                            )}
                          </span>
                          {conflictResult.conflict_detected && (
                            <span className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-bold ${
                              conflictResult.severity === 'high' 
                                ? 'bg-rose-900/60 border border-rose-700 text-rose-200' 
                                : conflictResult.severity === 'medium'
                                ? 'bg-amber-900/60 border border-amber-700 text-amber-200'
                                : 'bg-zinc-800 border border-zinc-700 text-zinc-300'
                            }`}>
                              {conflictResult.severity} RISK
                            </span>
                          )}
                        </div>
                        
                        <p className="text-[11px] leading-relaxed">
                          {conflictResult.conflict_detected 
                            ? 'A potential conflict has been detected:' 
                            : 'No matching client or matter entries found in database.'
                          }
                        </p>

                        {conflictResult.reasons && conflictResult.reasons.length > 0 && (
                          <ul className="list-disc pl-4 space-y-1 text-[11px] text-rose-300/90 font-mono">
                            {conflictResult.reasons.map((reason: string, idx: number) => (
                              <li key={idx}>{reason}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Directory list */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4 lg:col-span-2">
                  <h3 className="text-sm font-bold text-zinc-200">Registered Directory Listings</h3>
                  <div className="space-y-3">
                    {clients.map(c => (
                      <div key={c.id} className="flex justify-between items-start p-4 bg-zinc-900/50 border border-zinc-800/80 rounded-xl text-xs">
                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-zinc-100">{c.name}</h4>
                          {c.email && <div className="text-zinc-400">Email: {c.email}</div>}
                          {c.phone && <div className="text-zinc-400">Phone: {c.phone}</div>}
                          {c.notes && (
                            <div className="bg-zinc-950/60 p-2.5 rounded border border-zinc-850 text-zinc-400 font-mono mt-2 text-[10px] leading-relaxed">
                              🔒 <strong className="text-zinc-300">Decrypted Notes:</strong> {c.notes}
                            </div>
                          )}
                        </div>
                        <button 
                          onClick={() => handleDeleteClient(c.id)}
                          className="text-zinc-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-zinc-900 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                    {clients.length === 0 && (
                      <div className="text-xs text-zinc-500 italic p-4 text-center">No client directories registered yet.</div>
                    )}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 3: HYBRID RAG SEARCH */}
          {activeTab === "research" && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Citation-Aware Hybrid RAG Search</h1>
                <p className="text-sm text-zinc-400">Query legal facts fused across ChromaDB vector weights and BM25 local indexers.</p>
              </div>

              {/* RAG Context Lock warning */}
              <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-xl flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-zinc-400">
                  <Info className="w-4 h-4 text-zinc-300" />
                  <span>
                    {selectedMatter ? (
                      <>Currently searching scoped context of matter: <strong className="text-zinc-100">{selectedMatter.title}</strong> ({documents.length} files indexed).</>
                    ) : (
                      <>Searching global database vaults. Lock search context on specific matter in the <strong className="text-zinc-100">Matters & Context</strong> tab for speed.</>
                    )}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Left query column */}
                <div className="lg:col-span-2 space-y-4">
                  <form onSubmit={handleRagSearch} className="flex gap-2">
                    <input 
                      type="text" 
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Ask the local AI about charge details, contract defaults, ratio decidendi..."
                      className="flex-1 p-3 text-sm rounded-lg glass-input text-zinc-200 font-medium"
                      required
                    />
                    <button 
                      type="submit"
                      disabled={isSearching}
                      className="px-5 bg-zinc-50 hover:bg-zinc-200 disabled:bg-zinc-800 text-zinc-950 disabled:text-zinc-500 font-semibold rounded-lg text-sm transition flex items-center gap-1.5 shadow"
                    >
                      {isSearching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                      Query RAG
                    </button>
                  </form>

                  {/* LLM Result Box */}
                  <div className="border border-zinc-800 bg-zinc-900/20 p-6 rounded-2xl min-h-[300px] flex flex-col justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-4 font-mono">Local AI Agent Response</h3>
                      {ragResult ? (
                        <div className="text-sm leading-relaxed text-zinc-200 whitespace-pre-wrap font-sans">
                          {ragResult}
                        </div>
                      ) : (
                        <div className="text-xs text-zinc-500 italic mt-8 text-center">
                          {isSearching ? "Synthesizing answer from local index..." : "Awaiting your local query request."}
                        </div>
                      )}
                    </div>
                    {ragSources.length > 0 && (
                      <div className="mt-8 pt-4 border-t border-zinc-800">
                        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-2">Sources and Citations Recalled:</span>
                        <div className="flex flex-wrap gap-2">
                          {ragSources.map((s, idx) => (
                            <div key={s.id} className="text-[10px] px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-zinc-400 font-mono">
                              [{idx + 1}] {s.metadata.filename || "CaseFile"}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Precedent Mapping & Case Citation Graph */}
                  <div className="border border-zinc-900 bg-zinc-950/40 p-6 rounded-2xl space-y-4">
                    <div>
                      <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-zinc-400" /> Landmark Precedent & Case Citation Network
                      </h3>
                      <p className="text-xs text-zinc-500 mt-1">
                        Interactive precedent citation map. Click on any case node to explore judicial holdings, citations, and authority levels.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* SVG Canvas (left 2 cols) */}
                      <div className="md:col-span-2 relative bg-zinc-950/60 rounded-xl border border-zinc-900 overflow-hidden flex items-center justify-center p-4">
                        <svg viewBox="0 0 400 300" className="w-full h-auto max-h-[300px]">
                          <defs>
                            <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                              <path d="M 0 0 L 10 5 L 0 10 z" fill="#3f3f46" />
                            </marker>
                          </defs>

                          {/* Render links */}
                          {PRECEDENT_LINKS.map((link, idx) => {
                            const sourceNode = LANDMARK_PRECEDENTS.find(p => p.id === link.source);
                            const targetNode = LANDMARK_PRECEDENTS.find(p => p.id === link.target);
                            if (!sourceNode || !targetNode) return null;
                            return (
                              <line 
                                key={idx} 
                                x1={sourceNode.x} 
                                y1={sourceNode.y} 
                                x2={targetNode.x} 
                                y2={targetNode.y} 
                                stroke="#27272a" 
                                strokeWidth="1.5" 
                                markerEnd="url(#arrow)" 
                              />
                            );
                          })}

                          {/* Render nodes */}
                          {LANDMARK_PRECEDENTS.map((node) => (
                            <g 
                              key={node.id} 
                              className="cursor-pointer group"
                              onClick={() => setSelectedPrecedent(node)}
                            >
                              <circle 
                                cx={node.x} 
                                cy={node.y} 
                                r="10" 
                                className={`transition-all duration-300 ${selectedPrecedent?.id === node.id ? "stroke-white stroke-2 scale-110" : "stroke-zinc-800 hover:stroke-zinc-400"}`}
                                fill={node.id === "kb" ? "#eab308" : node.id === "mg" || node.id === "mm" ? "#3b82f6" : "#71717a"} 
                              />
                              <text 
                                x={node.x} 
                                y={node.y - 14} 
                                textAnchor="middle" 
                                className="text-[8px] font-mono font-bold fill-zinc-400 group-hover:fill-zinc-100 transition-colors pointer-events-none"
                              >
                                {node.citation}
                              </text>
                            </g>
                          ))}
                        </svg>

                        {/* Legend */}
                        <div className="absolute bottom-2 left-2 flex gap-3 text-[9px] text-zinc-500 font-mono bg-zinc-950/80 px-2 py-1 rounded border border-zinc-900/60">
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Basic Structure</span>
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Constitutional SC</span>
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-zinc-500" /> Precedents</span>
                        </div>
                      </div>

                      {/* Detail View (right 1 col) */}
                      <div className="p-4 bg-zinc-900/30 border border-zinc-900 rounded-xl flex flex-col justify-between text-xs min-h-[200px]">
                        {selectedPrecedent ? (
                          <div className="space-y-2">
                            <div className="flex justify-between items-start">
                              <h4 className="font-bold text-zinc-200 leading-tight">{selectedPrecedent.name}</h4>
                            </div>
                            <div className="flex gap-2">
                              <span className="px-1.5 py-0.5 bg-zinc-805 border border-zinc-800 rounded font-mono text-[9px] text-zinc-400 uppercase">{selectedPrecedent.court}</span>
                              <span className="px-1.5 py-0.5 bg-zinc-805 rounded font-mono text-[9px] text-amber-400 border border-zinc-800">{selectedPrecedent.citation}</span>
                            </div>
                            <p className="text-zinc-400 leading-relaxed text-[11px] pt-1">
                              {selectedPrecedent.relevance}
                            </p>
                          </div>
                        ) : (
                          <div className="text-zinc-500 italic flex items-center justify-center h-full text-center p-4">
                            Click a node on the citation network to view legal authority details.
                          </div>
                        )}
                        {selectedPrecedent && (
                          <button 
                            onClick={() => setSelectedPrecedent(null)} 
                            className="mt-3 w-full py-1.5 bg-zinc-950 border border-zinc-900 hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 transition text-[10px] rounded-lg font-mono cursor-pointer"
                          >
                            Clear View
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right statutory conversion sidebar */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4 h-fit">
                  <h3 className="text-sm font-bold text-zinc-200">Statutory Converter (IPC-to-BNS)</h3>
                  <p className="text-xs text-zinc-400">Offline section conversion mapping old codes to new 2024 legislated acts.</p>
                  
                  <div className="space-y-3">
                    <div>
                      <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Old Act</label>
                      <select 
                        value={helperAct} 
                        onChange={(e) => setHelperAct(e.target.value)}
                        className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-300"
                      >
                        <option value="ipc">Indian Penal Code (IPC)</option>
                        <option value="crpc">Code of Criminal Procedure (CrPC)</option>
                        <option value="iea">Indian Evidence Act (IEA)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Section Number</label>
                      <div className="flex gap-2">
                        <input 
                          type="text" 
                          value={helperSection}
                          onChange={(e) => setHelperSection(e.target.value)}
                          placeholder="e.g. 302, 420, 154"
                          className="flex-1 p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                        />
                        <button 
                          onClick={handleConvertSection}
                          className="px-3 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-zinc-200 font-medium rounded-lg text-xs transition"
                        >
                          Translate
                        </button>
                      </div>
                    </div>
                  </div>

                  {helperResult && (
                    <div className="bg-zinc-950/60 p-4 border border-zinc-900 rounded-xl text-xs space-y-2.5 font-sans">
                      <div className="flex justify-between items-center border-b border-zinc-800 pb-1.5">
                        <span className="font-bold text-zinc-100">{helperAct.toUpperCase()} Section {helperSection}</span>
                        <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/40 border border-emerald-900 px-1.5 py-0.5 rounded font-mono">
                          {helperResult.act} Section {helperResult.new_section}
                        </span>
                      </div>
                      <div><strong className="text-zinc-500">Subject:</strong> <span className="text-zinc-200">{helperResult.subject}</span></div>
                      <div><strong className="text-zinc-500">Changes:</strong> <span className="text-zinc-300">{helperResult.change_type}</span></div>
                      <p className="text-[11px] text-zinc-400 leading-relaxed pt-1.5 border-t border-zinc-900">{helperResult.description}</p>
                      {helperResult.full_text && (
                        <div className="pt-2 border-t border-zinc-900 space-y-1">
                          <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Offline Bare Act Content:</span>
                          <div className="p-2.5 bg-zinc-900/60 border border-zinc-850 rounded text-[10px] text-zinc-400 leading-relaxed whitespace-pre-wrap font-mono select-text max-h-[180px] overflow-y-auto">
                            {helperResult.full_text}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

              </div>
            </div>
          )}

          {/* TAB 4: CASE ANALYZER */}
          {activeTab === "analyzer" && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Scanned Case Document Analyzer</h1>
                <p className="text-sm text-zinc-400">Wipe out manual reading. Feed FIRs or charge sheets to trigger automatic event timelines and statutory fact extractors.</p>
              </div>

              {/* Scoped selection check */}
              <div className="border border-zinc-855 bg-zinc-900/30 p-4 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="text-xs space-y-1">
                  <div className="text-zinc-400">
                    Active Scoped Matter Folder: <strong className="text-zinc-200">{selectedMatter ? selectedMatter.title : "None Selected (Set scope under Matters tab)"}</strong>
                  </div>
                  {selectedMatter && (
                    <div className="flex gap-2">
                      <label className="text-[10px] text-zinc-500 font-bold uppercase">Select Document to Analyze:</label>
                      <select 
                        onChange={(e) => setSelectedDocForAnalysis(e.target.value)}
                        className="bg-transparent text-zinc-300 border-none outline-none focus:ring-0 p-0 text-[10px]"
                      >
                        <option value="">-- Choose file --</option>
                        {documents.map(d => (
                          <option key={d.id} value={d.id}>{d.original_name}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>

                {selectedDocForAnalysis && (
                  <button 
                    onClick={() => handleAnalyzeDocument(selectedDocForAnalysis)}
                    disabled={isAnalyzing}
                    className="px-4 py-2 bg-zinc-50 hover:bg-zinc-200 disabled:bg-zinc-800 text-zinc-950 disabled:text-zinc-500 font-semibold rounded-lg text-xs transition flex items-center gap-1.5 shadow"
                  >
                    {isAnalyzing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    Extract Case Outline
                  </button>
                )}
              </div>

              {isAnalyzing && (
                <div className="p-8 border border-zinc-800 bg-zinc-900/10 rounded-xl text-center space-y-2">
                  <RefreshCw className="w-8 h-8 animate-spin text-zinc-400 mx-auto" />
                  <div className="text-xs text-zinc-300">Running legal NLP parsing pipelines over document text...</div>
                  <div className="text-[10px] text-zinc-500">Wait time can take 1-2 minutes depending on GPU power.</div>
                </div>
              )}

              {/* ===== AI ANALYSIS TOOLKIT ===== */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* FIR Analyzer */}
                <div className="border border-rose-900/40 bg-rose-950/10 p-5 rounded-xl space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-rose-400">🚨</span>
                    <h3 className="text-sm font-bold text-rose-300">FIR / Criminal Analyzer</h3>
                  </div>
                  <p className="text-[11px] text-zinc-400">Detect contradictions across FIR, medical report & witness statements. Finds defense points automatically.</p>
                  <div className="space-y-1">
                    <p className="text-[10px] text-zinc-500 uppercase font-bold">Select documents to analyze:</p>
                    {documents.map(d => (
                      <label key={d.id} className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                        <input type="checkbox" checked={firDocIds.includes(d.id)}
                          onChange={e => setFirDocIds(prev => e.target.checked ? [...prev, d.id] : prev.filter(x => x !== d.id))}
                          className="accent-rose-600" />
                        {d.original_name}
                      </label>
                    ))}
                  </div>
                  <button onClick={handleFIRAnalysis} disabled={isFirAnalyzing || firDocIds.length === 0}
                    className="w-full py-2 bg-rose-800 hover:bg-rose-700 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50">
                    {isFirAnalyzing ? <span className="flex items-center justify-center gap-2"><RefreshCw className="w-3 h-3 animate-spin" /> Analyzing...</span> : "🔍 Analyze Criminal Docs"}
                  </button>
                </div>

                {/* Predictive Outcome */}
                <div className="border border-blue-900/40 bg-blue-950/10 p-5 rounded-xl space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-blue-400">⚖️</span>
                    <h3 className="text-sm font-bold text-blue-300">Case Outcome Predictor</h3>
                  </div>
                  <p className="text-[11px] text-zinc-400">AI-powered verdict prediction with Indian precedent analysis, risk factors, and confidence score.</p>
                  <textarea value={predictFacts} onChange={e => setPredictFacts(e.target.value)} rows={3}
                    placeholder="Paste key case facts here..." className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 resize-none" />
                  <div className="grid grid-cols-2 gap-2">
                    <select value={predictCourt} onChange={e => setPredictCourt(e.target.value)} className="p-2 text-xs rounded-lg glass-input text-zinc-300">
                      {["Supreme Court", "High Court", "District Court", "Sessions Court", "Consumer Forum", "Tribunal"].map(c => <option key={c}>{c}</option>)}
                    </select>
                    <input value={predictSections} onChange={e => setPredictSections(e.target.value)} placeholder="BNS sections (opt.)" className="p-2 text-xs rounded-lg glass-input text-zinc-200" />
                  </div>
                  <button onClick={handlePredictOutcome} disabled={isPredicting || !predictFacts.trim()}
                    className="w-full py-2 bg-blue-800 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50">
                    {isPredicting ? <span className="flex items-center justify-center gap-2"><RefreshCw className="w-3 h-3 animate-spin" /> Predicting...</span> : "🎯 Predict Outcome"}
                  </button>
                </div>

                {/* Voice Dictation */}
                <div className="border border-violet-900/40 bg-violet-950/10 p-5 rounded-xl space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-violet-400">🎙️</span>
                    <h3 className="text-sm font-bold text-violet-300">Voice Dictation</h3>
                  </div>
                  <p className="text-[11px] text-zinc-400">Record audio to transcribe notes, client statements, or case summaries using local Whisper AI.</p>
                  <div className="flex justify-center">
                    <button onClick={isRecording ? stopRecording : startRecording}
                      className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg ${isRecording ? "bg-rose-600 animate-pulse scale-110" : "bg-violet-700 hover:bg-violet-600"}`}>
                      {isRecording ? <MicOff className="w-8 h-8 text-white" /> : <Mic className="w-8 h-8 text-white" />}
                    </button>
                  </div>
                  <p className="text-[10px] text-center text-zinc-500">{isRecording ? "🔴 Recording... click to stop" : "Click mic to start recording"}</p>
                  {transcribedText && (
                    <div className="p-2 bg-violet-950/30 border border-violet-800 rounded-lg">
                      <p className="text-[10px] text-zinc-500 uppercase font-bold mb-1">Transcript</p>
                      <p className="text-xs text-zinc-200 whitespace-pre-wrap">{transcribedText}</p>
                      <button onClick={() => setTranscribedText("")} className="text-[10px] text-zinc-500 hover:text-zinc-300 mt-1">Clear</button>
                    </div>
                  )}
                </div>
              </div>

              {/* ===== AI ANALYSIS TOOLKIT RESULTS ===== */}
              {(firResult || predictResult) && (
                <div className="grid grid-cols-1 gap-6">
                  {/* FIR Result */}
                  {firResult && (
                    <div className="border border-rose-900/50 bg-rose-950/5 p-6 rounded-xl space-y-4 animate-fade-in">
                      <div className="flex justify-between items-center border-b border-rose-900/40 pb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-rose-400">🚨</span>
                          <h3 className="text-md font-bold text-rose-300">FIR & Criminal Contradiction Report</h3>
                        </div>
                        <button 
                          onClick={() => {
                            const content = `FIR & CRIMINAL CONTRADICTION REPORT\n\nOVERVIEW:\n${firResult.case_overview}\n\nCONTRADICTIONS:\n${firResult.contradictions?.map((c: any) => `- [${c.severity}] ${c.document_a} vs ${c.document_b}: ${c.contradiction_detail}`).join("\n")}\n\nDEFENSE POINTS:\n${firResult.defense_points?.map((d: any) => `- [Strength: ${d.strength}] ${d.point} (${d.legal_basis})`).join("\n")}\n\nGAPS IN EVIDENCE:\n${firResult.missing_evidence?.map((g: string) => `- ${g}`).join("\n")}\n\nAPPLICABLE BNS SECTIONS:\n${firResult.applicable_sections_bns?.join(", ")}`;
                            exportToPDF("FIR_Contradiction_Report", content, currentUser?.firm_name, currentUser?.firm_logo);
                          }}
                          className="px-3 py-1.5 bg-rose-900/50 hover:bg-rose-800 border border-rose-800 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                        >
                          <Download className="w-3.5 h-3.5" /> Export PDF
                        </button>
                      </div>

                      <div className="space-y-3 text-xs">
                        <div>
                          <strong className="text-zinc-400 block mb-1">Case Overview:</strong>
                          <p className="text-zinc-300 leading-relaxed bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">{firResult.case_overview}</p>
                        </div>

                        {firResult.fir_timeline && firResult.fir_timeline.length > 0 && (
                          <div>
                            <strong className="text-zinc-400 block mb-1">Extracted FIR Timeline:</strong>
                            <div className="space-y-1.5 bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">
                              {firResult.fir_timeline.map((item: any, i: number) => (
                                <div key={i} className="flex gap-2 text-zinc-300">
                                  <span className="text-rose-500 font-mono">[{item.timestamp || "TBD"}]</span>
                                  <span>{item.event} <span className="text-zinc-500 font-mono">({item.source})</span></span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {firResult.contradictions && firResult.contradictions.length > 0 && (
                          <div>
                            <strong className="text-zinc-400 block mb-1">Contradictions Detected:</strong>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {firResult.contradictions.map((c: any, i: number) => (
                                <div key={i} className="p-3 bg-zinc-950/40 border rounded-lg border-zinc-900 space-y-1">
                                  <div className="flex justify-between items-center">
                                    <span className="text-[10px] font-bold text-zinc-500">{c.document_a} &harr; {c.document_b}</span>
                                    <span className={`text-[9px] px-1 rounded font-bold ${c.severity === "High" ? "bg-rose-950 text-rose-400 border border-rose-900" : c.severity === "Medium" ? "bg-amber-950 text-amber-400 border border-amber-900" : "bg-zinc-800 text-zinc-400"}`}>{c.severity}</span>
                                  </div>
                                  <p className="text-zinc-300">{c.contradiction_detail}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {firResult.defense_points && firResult.defense_points.length > 0 && (
                          <div>
                            <strong className="text-zinc-400 block mb-1">Recommended Defense Points:</strong>
                            <div className="space-y-2">
                              {firResult.defense_points.map((d: any, i: number) => (
                                <div key={i} className="p-3 bg-rose-950/5 border border-rose-900/30 rounded-lg">
                                  <div className="flex justify-between font-semibold text-zinc-200">
                                    <span>{d.point}</span>
                                    <span className="text-[10px] text-rose-400">Strength: {d.strength}</span>
                                  </div>
                                  <p className="text-zinc-400 mt-1 text-[11px]">Legal Basis: {d.legal_basis}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {firResult.missing_evidence && firResult.missing_evidence.length > 0 && (
                            <div>
                              <strong className="text-zinc-400 block mb-1">Gaps in Evidence / Investigation:</strong>
                              <ul className="list-disc list-inside space-y-1 text-zinc-300">
                                {firResult.missing_evidence.map((g: string, i: number) => <li key={i}>{g}</li>)}
                              </ul>
                            </div>
                          )}
                          {firResult.applicable_sections_bns && firResult.applicable_sections_bns.length > 0 && (
                            <div>
                              <strong className="text-zinc-400 block mb-1">Applicable Sections (BNS):</strong>
                              <div className="flex gap-1.5 flex-wrap">
                                {firResult.applicable_sections_bns.map((s: string, i: number) => (
                                  <span key={i} className="px-2 py-0.5 bg-rose-950/40 border border-rose-900 text-rose-300 rounded font-mono font-semibold">{s}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Outcome Prediction Result */}
                  {predictResult && (
                    <div className="border border-blue-900/50 bg-blue-950/5 p-6 rounded-xl space-y-4 animate-fade-in">
                      <div className="flex justify-between items-center border-b border-blue-900/40 pb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-blue-400">🎯</span>
                          <h3 className="text-md font-bold text-blue-300">Case Verdict Outcome Prediction</h3>
                        </div>
                        <button 
                          onClick={() => {
                            const content = `CASE OUTCOME PREDICTION REPORT\n\nPREDICTED OUTCOME: ${predictResult.predicted_outcome} (${predictResult.confidence_percentage}% Confidence)\n\nREASONING:\n${predictResult.reasoning?.map((r: string) => `- ${r}`).join("\n")}\n\nRISK FACTORS:\n${predictResult.risk_factors?.map((rf: string) => `- ${rf}`).join("\n")}\n\nSUGGESTIONS:\n${predictResult.strengthening_suggestions?.map((s: string) => `- ${s}`).join("\n")}\n\nPRECEDENTS:\n${predictResult.similar_precedents?.map((p: any) => `- ${p.case_name} (${p.citation}): ${p.relevance}`).join("\n")}\n\nESTIMATED TIMELINE: ${predictResult.estimated_timeline_months} months`;
                            exportToPDF("Case_Prediction_Report", content, currentUser?.firm_name, currentUser?.firm_logo);
                          }}
                          className="px-3 py-1.5 bg-blue-900/50 hover:bg-blue-800 border border-blue-800 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                        >
                          <Download className="w-3.5 h-3.5" /> Export PDF
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl text-center space-y-1">
                          <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">Predicted Outcome</span>
                          <p className={`text-sm font-bold uppercase ${predictResult.predicted_outcome === "Likely to Succeed" ? "text-emerald-400" : predictResult.predicted_outcome === "Likely to Fail" ? "text-rose-400" : "text-amber-400"}`}>{predictResult.predicted_outcome}</p>
                        </div>
                        <div className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl text-center space-y-1">
                          <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">AI Confidence Rating</span>
                          <p className="text-xl font-bold font-mono text-blue-400">{predictResult.confidence_percentage}%</p>
                        </div>
                        <div className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl text-center space-y-1">
                          <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">Estimated Timeline</span>
                          <p className="text-xl font-bold font-mono text-zinc-300">{predictResult.estimated_timeline_months} mos</p>
                        </div>
                      </div>

                      <div className="space-y-3 text-xs">
                        {predictResult.reasoning && predictResult.reasoning.length > 0 && (
                          <div>
                            <strong className="text-zinc-400 block mb-1">Key Legal Reasoning:</strong>
                            <ul className="list-decimal list-inside space-y-1 text-zinc-300 leading-relaxed bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">
                              {predictResult.reasoning.map((r: string, i: number) => <li key={i}>{r}</li>)}
                            </ul>
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {predictResult.risk_factors && predictResult.risk_factors.length > 0 && (
                            <div className="p-3.5 bg-rose-950/5 border border-rose-900/20 rounded-xl">
                              <strong className="text-rose-300 block mb-1.5">Identified Risk Factors:</strong>
                              <ul className="list-disc list-inside space-y-1.5 text-zinc-400 text-[11px]">
                                {predictResult.risk_factors.map((rf: string, i: number) => <li key={i}>{rf}</li>)}
                              </ul>
                            </div>
                          )}
                          {predictResult.strengthening_suggestions && predictResult.strengthening_suggestions.length > 0 && (
                            <div className="p-3.5 bg-emerald-950/5 border border-emerald-900/20 rounded-xl">
                              <strong className="text-emerald-300 block mb-1.5">Action Items to Strengthen Case:</strong>
                              <ul className="list-disc list-inside space-y-1.5 text-zinc-400 text-[11px]">
                                {predictResult.strengthening_suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}
                              </ul>
                            </div>
                          )}
                        </div>

                        {predictResult.similar_precedents && predictResult.similar_precedents.length > 0 && (
                          <div>
                            <strong className="text-zinc-400 block mb-1.5">Relevant Supreme Court / High Court Precedents:</strong>
                            <div className="space-y-2">
                              {predictResult.similar_precedents.map((p: any, i: number) => (
                                <div key={i} className="p-3 bg-zinc-950/40 border border-zinc-900 rounded-lg text-xs">
                                  <div className="flex justify-between font-bold text-zinc-300 font-mono">
                                    <span>{p.case_name}</span>
                                    <span className="text-blue-400">{p.citation}</span>
                                  </div>
                                  <p className="text-zinc-400 mt-1">{p.relevance}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}


              {/* Analyzer Results Grid */}
              {!isAnalyzing && (analyzerTimeline.length > 0 || analyzerFacts) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Timeline */}
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-zinc-400" /> Chronological Event Timeline
                    </h3>
                    <div className="space-y-4 relative border-l border-zinc-800 pl-4 ml-2 max-h-[450px] overflow-y-auto pt-2">
                      {analyzerTimeline.map((item, idx) => (
                        <div key={idx} className="relative space-y-1">
                          <div className="absolute top-1.5 left-[-21px] w-2.5 h-2.5 rounded-full bg-zinc-700 border border-zinc-950" />
                          <span className="text-[10px] font-bold font-mono text-zinc-500">{item.date || "Date Unspecified"}</span>
                          <h4 className="text-xs font-semibold text-zinc-200">{item.description}</h4>
                          {item.involved_parties && (
                            <p className="text-[10px] text-zinc-400 italic">Parties: {item.involved_parties}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Fact sheet */}
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-zinc-400" /> Fact Sheet extraction
                    </h3>
                    {analyzerFacts ? (
                      <div className="text-xs space-y-3 font-sans text-zinc-300">
                        <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                          <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Offence Description</strong>
                          <p className="text-zinc-200">{analyzerFacts.offence}</p>
                        </div>
                        <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                          <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Statutory Provisions Invoked</strong>
                          <p className="text-zinc-200 font-mono">{analyzerFacts.sections_invoked}</p>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                            <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Accused Individuals</strong>
                            <p className="text-zinc-200">{analyzerFacts.accused}</p>
                          </div>
                          <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                            <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Victims / Complainants</strong>
                            <p className="text-zinc-200">{analyzerFacts.victims}</p>
                          </div>
                        </div>
                        <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                          <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Case Narrative</strong>
                          <p className="text-zinc-300 leading-relaxed">{analyzerFacts.summary}</p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-zinc-500 italic">No fact sheet extracted.</div>
                    )}
                  </div>

                </div>
              )}
            </div>
          )}

          {/* TAB 5: CONTRACT AUDITOR */}
          {activeTab === "auditor" && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Contract Auditor & Clause Comparator</h1>
                <p className="text-sm text-zinc-400">Perform local compliance checks. Audit liabilities or compare variance details between contract drafts.</p>
              </div>

              {/* Scoper Header */}
              <div className="border border-zinc-800 bg-zinc-900/30 p-4 rounded-xl text-xs text-zinc-400">
                {selectedMatter ? (
                  <>Active Scoped Matter Folder: <strong className="text-zinc-200">{selectedMatter.title}</strong></>
                ) : (
                  <>Select case matter folder inside Matters page to load scope documents.</>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* 1. Risk Scanner panel */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4 lg:col-span-2">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-sm font-bold text-zinc-200">Contract Risk Scanning</h3>
                    {auditRisks.length > 0 && (
                      <button
                        onClick={() => {
                          const content = `CONTRACT RISK SCAN REPORT\n\n${auditRisks.map(r => `CLAUSE: ${r.clause_title} [Risk: ${r.risk_rating}]\nSummary: ${r.summary}\nRemediation: ${r.remediation_advice}`).join("\n\n")}`;
                          exportToPDF("Contract_Risk_Scan_Report", content, currentUser?.firm_name, currentUser?.firm_logo);
                        }}
                        className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded-lg text-xs flex items-center gap-1.5 transition cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" /> Export PDF
                      </button>
                    )}
                  </div>
                  {selectedMatter && (
                    <div className="flex gap-4 items-center mb-3">
                      <select 
                        onChange={(e) => setSelectedContractForAudit(e.target.value)}
                        className="p-2 text-xs rounded-lg glass-input text-zinc-300"
                      >
                        <option value="">-- Choose Contract Doc --</option>
                        {documents.map(d => (
                          <option key={d.id} value={d.id}>{d.original_name}</option>
                        ))}
                      </select>
                      {selectedContractForAudit && (
                        <button 
                          onClick={() => handleAuditContract(selectedContractForAudit)}
                          disabled={isAuditing}
                          className="px-4 py-2 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-semibold rounded-lg text-xs transition"
                        >
                          {isAuditing ? "Scanning..." : "Start Risk Audit"}
                        </button>
                      )}
                    </div>
                  )}

                  {isAuditing && (
                    <div className="p-4 text-center text-xs text-zinc-400 animate-pulse">Running semantic risk scanner...</div>
                  )}

                  <div className="space-y-3">
                    {auditRisks.map((risk, idx) => (
                      <div key={idx} className="p-4 bg-zinc-900/50 border border-zinc-800/80 rounded-xl space-y-2">
                        <div className="flex justify-between items-center">
                          <h4 className="text-xs font-bold text-zinc-100">{risk.clause_title}</h4>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                setSimplifyClauseText(risk.summary || "");
                                setSimplifyResult(null);
                                setShowSimplifyModal(true);
                              }}
                              className="px-2 py-0.5 rounded text-[9px] font-semibold bg-violet-900/40 border border-violet-700 text-violet-300 hover:bg-violet-800/60 transition"
                              title="Simplify this clause in plain language"
                            >✨ Simplify</button>
                            <span className={`px-2 py-0.5 rounded font-mono text-[9px] border ${
                              risk.risk_rating === "High" ? "bg-rose-950/40 border-rose-900 text-rose-400" :
                              risk.risk_rating === "Medium" ? "bg-amber-955/40 border-amber-900 text-amber-400" :
                              "bg-emerald-955/40 border-emerald-900 text-emerald-400"
                            }`}>{risk.risk_rating.toUpperCase()} RISK</span>
                          </div>
                        </div>
                        <p className="text-xs text-zinc-300 leading-relaxed">{risk.summary}</p>
                        <div className="text-[11px] text-zinc-400 italic bg-zinc-950/40 p-2 rounded">
                          <strong>Remediation Advice:</strong> {risk.remediation_advice}
                        </div>
                      </div>
                    ))}
                    {auditRisks.length === 0 && !isAuditing && (
                      <div className="text-xs text-zinc-500 italic p-4 text-center">Select contract and trigger scanning to parse compliance issues.</div>
                    )}
                  </div>
                </div>

                {/* 2. Clause Comparator Panel */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                  <h3 className="text-sm font-bold text-zinc-200">Clause Comparator Audit</h3>
                  
                  {selectedMatter && (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Document Draft A</label>
                        <select 
                          value={contractDocA}
                          onChange={(e) => setContractDocA(e.target.value)}
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-300"
                        >
                          <option value="">-- Choose Document --</option>
                          {documents.map(d => (
                            <option key={d.id} value={d.id}>{d.original_name}</option>
                          ))}
                        </select>
                      </div>
                      
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Document Draft B</label>
                        <select 
                          value={contractDocB}
                          onChange={(e) => setContractDocB(e.target.value)}
                          className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-300"
                        >
                          <option value="">-- Choose Document --</option>
                          {documents.map(d => (
                            <option key={d.id} value={d.id}>{d.original_name}</option>
                          ))}
                        </select>
                      </div>

                      <button 
                        onClick={handleCompareContracts}
                        disabled={isComparing}
                        className="w-full py-2.5 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs shadow transition"
                      >
                        {isComparing ? "Comparing..." : "Run Variance Check"}
                      </button>
                    </div>
                  )}

                  {/* Comparison output */}
                  <div className="space-y-3 pt-2 max-h-[300px] overflow-y-auto">
                    {compareResults.map((c, idx) => (
                      <div key={idx} className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-lg text-xs space-y-1.5">
                        <div className="flex justify-between items-center">
                          <strong className="text-zinc-200 font-semibold">{c.clause_title}</strong>
                          <span className="text-[9px] px-1 bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono uppercase">{c.variance_type}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[10px] text-zinc-400 pt-1">
                          <div><strong>Doc A:</strong> {c.doc_a_provision}</div>
                          <div><strong>Doc B:</strong> {c.doc_b_provision}</div>
                        </div>
                        <div className="text-[10px] text-zinc-400 border-t border-zinc-800/80 pt-1">
                          <span className="text-zinc-500">Risk Scan:</span> {c.risk_assessment}
                        </div>
                      </div>
                    ))}
                    {compareResults.length === 0 && !isComparing && (
                      <div className="text-xs text-zinc-500 italic p-2 text-center">Run variance check to map clause changes.</div>
                    )}
                  </div>
                </div>

              </div>

              {/* Simplify Clause Manual Input Panel */}
              <div className="border border-violet-900/50 bg-violet-950/10 p-5 rounded-xl space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm">✨</span>
                  <h3 className="text-sm font-bold text-violet-300">Plain-Language Clause Simplifier</h3>
                </div>
                <p className="text-xs text-zinc-400">Paste any legal clause text below and the AI will rewrite it in clear, simple language suitable for clients.</p>
                <textarea
                  value={simplifyClauseText}
                  onChange={(e) => setSimplifyClauseText(e.target.value)}
                  placeholder="Paste clause text here..."
                  rows={3}
                  className="w-full p-3 text-xs rounded-lg glass-input text-zinc-200 resize-none"
                />
                <button
                  onClick={() => { setSimplifyResult(null); setShowSimplifyModal(true); handleSimplifyClause(); }}
                  disabled={isSimplifying || !simplifyClauseText.trim()}
                  className="px-4 py-2 bg-violet-700 hover:bg-violet-600 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50"
                >
                  {isSimplifying ? "Simplifying..." : "Simplify Clause"}
                </button>
              </div>
            </div>
          )}

          {/* SIMPLIFY CLAUSE MODAL */}
          {showSimplifyModal && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)" }}
              onClick={(e) => { if (e.target === e.currentTarget) setShowSimplifyModal(false); }}
            >
              <div className="bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl w-full max-w-xl p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-base font-bold text-violet-300">✨ Clause Simplifier</h2>
                    <p className="text-xs text-zinc-400 mt-0.5">AI-powered plain-language rewrite</p>
                  </div>
                  <button
                    onClick={() => setShowSimplifyModal(false)}
                    className="text-zinc-500 hover:text-zinc-200 text-lg leading-none transition"
                  >✕</button>
                </div>

                {/* Input */}
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Original Clause</label>
                  <textarea
                    value={simplifyClauseText}
                    onChange={(e) => setSimplifyClauseText(e.target.value)}
                    placeholder="Paste or edit clause text..."
                    rows={4}
                    className="w-full p-3 text-xs rounded-lg glass-input text-zinc-200 resize-none"
                  />
                </div>

                <button
                  onClick={handleSimplifyClause}
                  disabled={isSimplifying || !simplifyClauseText.trim()}
                  className="w-full py-2.5 bg-violet-700 hover:bg-violet-600 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50"
                >
                  {isSimplifying ? "Simplifying with AI..." : "✨ Simplify Now"}
                </button>

                {isSimplifying && (
                  <div className="p-4 text-center text-xs text-violet-300 animate-pulse">AI is rewriting the clause in plain language...</div>
                )}

                {simplifyResult && !isSimplifying && (
                  <div className="space-y-3">
                    <div className="p-4 bg-violet-950/30 border border-violet-900/50 rounded-xl">
                      <p className="text-[10px] font-bold text-violet-400 uppercase mb-2">Plain-Language Version</p>
                      <p className="text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap">{simplifyResult.simplified}</p>
                    </div>
                    {simplifyResult.key_obligations && simplifyResult.key_obligations.length > 0 && (
                      <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-xl">
                        <p className="text-[10px] font-bold text-zinc-400 uppercase mb-2">Key Obligations</p>
                        <ul className="space-y-1">
                          {simplifyResult.key_obligations.map((ob, i) => (
                            <li key={i} className="text-xs text-zinc-300 flex gap-2"><span className="text-violet-400">→</span>{ob}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {simplifyResult.risk_flags && simplifyResult.risk_flags.length > 0 && (
                      <div className="p-3 bg-rose-950/20 border border-rose-900/40 rounded-xl">
                        <p className="text-[10px] font-bold text-rose-400 uppercase mb-2">Risk Flags</p>
                        <ul className="space-y-1">
                          {simplifyResult.risk_flags.map((flag, i) => (
                            <li key={i} className="text-xs text-rose-300 flex gap-2"><span>⚠️</span>{flag}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: DOCUMENT DRAFTING */}
          {activeTab === "drafting" && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Legal Document Draftsman</h1>
                <p className="text-sm text-zinc-400">Generate fully compliant legal drafts offline grounding details locally.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Templates Column */}
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                  <h3 className="text-sm font-bold text-zinc-200">Legal Templates</h3>
                  <div className="space-y-1.5">
                    {templates.map(t => (
                      <button 
                        key={t.id}
                        onClick={() => handleSelectTemplate(t)}
                        className={`w-full text-left p-3 rounded-lg text-xs transition border ${
                          selectedTemplate?.id === t.id ? "bg-zinc-800 border-zinc-700 text-zinc-100 font-semibold" : "bg-transparent border-transparent text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                        }`}
                      >
                        {t.name}
                      </button>
                    ))}
                  </div>

                  {selectedTemplate && (
                    <form onSubmit={handleGenerateDraft} className="space-y-3 pt-4 border-t border-zinc-800">
                      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Fill Variables</h4>
                      {selectedTemplate.fields.map(field => (
                        <div key={field} className="space-y-1">
                          <label className="block text-[10px] text-zinc-500 font-bold uppercase">{field.replace(/_/g, ' ')}</label>
                          <input 
                            type="text"
                            value={templateFields[field] || ""}
                            onChange={(e) => setTemplateFields({ ...templateFields, [field]: e.target.value })}
                            className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200"
                            required
                          />
                        </div>
                      ))}
                      <button 
                        type="submit"
                        disabled={isDrafting}
                        className="w-full py-2 bg-zinc-50 hover:bg-zinc-200 disabled:bg-zinc-800 text-zinc-950 disabled:text-zinc-500 font-bold rounded-lg text-xs transition"
                      >
                        {isDrafting ? "Drafting Document..." : "Generate AI Draft"}
                      </button>
                    </form>
                  )}
                </div>

                {/* AI Draft Editor Workspace */}
                <div className="lg:col-span-2 border border-zinc-800 bg-zinc-900/10 p-6 rounded-2xl flex flex-col justify-between min-h-[450px]">
                  <div className="space-y-4">
                    <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
                      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Workspace Editor</h3>
                      {generatedDraft && (
                        <div className="flex gap-3">
                          <button 
                            onClick={() => {
                              const blob = new Blob([generatedDraft], { type: "text/plain;charset=utf-8" });
                              const url = URL.createObjectURL(blob);
                              const link = document.createElement("a");
                              link.href = url;
                              link.download = `${selectedTemplate?.id || "draft"}_generated.txt`;
                              link.click();
                            }}
                            className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-200 transition cursor-pointer"
                          >
                            <Download className="w-3 h-3" /> Save Text
                          </button>
                          <button 
                            onClick={() => {
                              exportToPDF(selectedTemplate?.name || "Legal_Draft", generatedDraft, currentUser?.firm_name, currentUser?.firm_logo);
                            }}
                            className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-200 transition cursor-pointer border-l border-zinc-800 pl-2"
                          >
                            <Download className="w-3 h-3 text-emerald-500" /> Export PDF
                          </button>
                        </div>
                      )}
                    </div>
                    {generatedDraft ? (
                      <div className="space-y-4">
                        {/* Court Formatter Toolbar */}
                        <div className="p-3 bg-zinc-950/40 border border-zinc-850 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
                          <div className="flex flex-wrap items-center gap-4">
                            {/* Court Header Select */}
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] text-zinc-500 font-bold uppercase">Court Pleading Header:</span>
                              <select 
                                value={courtHeader} 
                                onChange={(e) => setCourtHeader(e.target.value)}
                                className="bg-zinc-900 border border-zinc-850 text-zinc-300 rounded px-2 py-1 text-xs outline-none focus:border-zinc-700"
                              >
                                <option value="none">None (Plain Text)</option>
                                <option value="supreme_court">Supreme Court of India</option>
                                <option value="high_court">High Court of Delhi</option>
                                <option value="district_court">District Court of Saket</option>
                              </select>
                            </div>

                            {/* Spacing Select */}
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] text-zinc-500 font-bold uppercase">Spacing:</span>
                              <select 
                                value={lineSpacing} 
                                onChange={(e) => setLineSpacing(e.target.value)}
                                className="bg-zinc-900 border border-zinc-850 text-zinc-300 rounded px-2 py-1 text-xs outline-none focus:border-zinc-700"
                              >
                                <option value="1.0">Single Space</option>
                                <option value="1.5">1.5 Lines</option>
                                <option value="2.0">Double Space</option>
                              </select>
                            </div>

                            {/* Margin Select */}
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] text-zinc-500 font-bold uppercase">Left Margin:</span>
                              <select 
                                value={marginSpaces} 
                                onChange={(e) => setMarginSpaces(e.target.value)}
                                className="bg-zinc-900 border border-zinc-850 text-zinc-300 rounded px-2 py-1 text-xs outline-none focus:border-zinc-700"
                              >
                                <option value="0">0 Spaces</option>
                                <option value="4">4 Spaces (Standard)</option>
                                <option value="8">8 Spaces (Broad)</option>
                                <option value="12">12 Spaces (Very Broad)</option>
                              </select>
                            </div>
                          </div>

                          <button 
                            onClick={handleApplyFormatting}
                            disabled={isFormattingDraft}
                            className="px-3 py-1.5 bg-zinc-50 hover:bg-zinc-200 disabled:bg-zinc-800 text-zinc-950 disabled:text-zinc-500 font-bold rounded-lg text-[10px] transition flex items-center gap-1 shrink-0 cursor-pointer"
                          >
                            {isFormattingDraft ? (
                              <>
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                Applying...
                              </>
                            ) : (
                              <>
                                <Scale className="w-3 h-3 text-indigo-500" />
                                Apply Formatting
                              </>
                            )}
                          </button>
                        </div>

                        {/* Editor Textarea */}
                        <textarea 
                          value={generatedDraft}
                          onChange={(e) => setGeneratedDraft(e.target.value)}
                          className="w-full h-[380px] p-4 bg-transparent border border-zinc-900 rounded-lg text-xs leading-relaxed font-mono focus:ring-0 focus:border-zinc-850 outline-none text-zinc-300"
                        />
                      </div>
                    ) : (
                      <div className="text-xs text-zinc-500 italic p-8 text-center mt-16 animate-pulse">
                        {isDrafting ? "Advocate compiler engine running local generation parameters..." : "Choose template, fill custom parameters, and generate draft."}
                      </div>
                    )}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 7: ENCRYPTED LOCAL BACKUPS */}
          {activeTab === "backup" && (
            <div className="space-y-6 animate-fade-in bg-radial-glow p-2 rounded-2xl">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-zinc-900 pb-5">
                <div>
                  <h1 className="text-3xl font-extrabold tracking-tight text-white premium-gradient-text">Security Vault & Backups</h1>
                  <p className="text-sm text-zinc-400 mt-1">AES-256 GCM encrypted zip backups. Trigger scheduled points or safe restores.</p>
                </div>
                
                {/* Highlighted Panic Trigger */}
                {currentUser?.role === "admin" && (
                  <button 
                    onClick={() => setShowPanicModal(true)}
                    className="px-4 py-2.5 bg-rose-900/30 hover:bg-rose-600 border border-rose-800 text-rose-300 hover:text-white font-bold rounded-lg text-xs transition duration-200 flex items-center gap-2 shadow-lg shadow-rose-950/20 cursor-pointer animate-pulse-glow-red"
                  >
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    EMERGENCY PANIC WIPE
                  </button>
                )}
              </div>

              {/* System parameters */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5">
                  <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Database Size</span>
                  <span className="text-xl font-bold font-mono text-zinc-200">{(systemStatus.database_size_bytes / 1024).toFixed(1)} KB</span>
                </div>
                <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5">
                  <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Clients Folder</span>
                  <span className="text-xl font-bold font-mono text-zinc-200">{systemStatus.registered_clients}</span>
                </div>
                <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5">
                  <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Active Matters</span>
                  <span className="text-xl font-bold font-mono text-zinc-200">{systemStatus.registered_matters}</span>
                </div>
                <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5">
                  <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Vault Documents</span>
                  <span className="text-xl font-bold font-mono text-zinc-200">{systemStatus.vault_document_count}</span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
                
                {/* Perform Backups widget */}
                <div className="border border-zinc-900 bg-zinc-950/50 p-6 rounded-xl space-y-4 h-fit">
                  <h3 className="text-sm font-bold text-zinc-200 font-mono uppercase tracking-wider">Secure Backup Points</h3>
                  <p className="text-xs text-zinc-400 leading-relaxed">Generate a unified AES-256 GCM encrypted zip file including database schemas, document vault, and search vector paths.</p>
                  <button 
                    onClick={handleRunManualBackup}
                    disabled={isBackupRunning}
                    className="w-full py-3 bg-white hover:bg-zinc-200 disabled:bg-zinc-900 text-black disabled:text-zinc-600 font-bold rounded-lg text-xs transition duration-200 cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <Lock className="w-3.5 h-3.5" />
                    {isBackupRunning ? "Generating Encrypted Snapshot..." : "Generate Safe Recovery Point"}
                  </button>
                </div>

                {/* Logs History */}
                <div className="border border-zinc-900 bg-zinc-950/50 p-6 rounded-xl space-y-4 lg:col-span-2">
                  <h3 className="text-sm font-bold text-zinc-200 font-mono uppercase tracking-wider">Snapshots Log history</h3>
                  <div className="space-y-3.5 max-h-[300px] overflow-y-auto pr-1">
                    {backupHistory.map(b => (
                      <div key={b.id} className="p-3.5 bg-zinc-900/20 hover:bg-zinc-900/40 border border-zinc-900 rounded-xl flex items-center justify-between text-xs transition duration-150">
                        <div className="space-y-1.5 truncate">
                          <div className="font-semibold text-zinc-200 font-mono truncate">{b.backup_name}</div>
                          <div className="text-[10px] text-zinc-500 font-mono flex items-center gap-3">
                            <span>Size: {(b.backup_size_bytes / 1024).toFixed(1)} KB</span>
                            <span>Type: {b.is_manual ? "Manual" : "Auto Snapshot"}</span>
                            <span>Time: {b.created_at}</span>
                          </div>
                        </div>
                        <button 
                          onClick={() => handleTriggerRestore(b.destination_path)}
                          className="px-3.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-semibold rounded-lg text-[10px] transition duration-150 cursor-pointer"
                        >
                          Restore
                        </button>
                      </div>
                    ))}
                    {backupHistory.length === 0 && (
                      <div className="text-xs text-zinc-500 italic p-4 text-center">No backup attempts recorded.</div>
                    )}
                  </div>
                </div>

              </div>

              {/* Compliance Audit Trail (Only for admin) */}
              {currentUser?.role === "admin" && (
                <div className="border border-zinc-900 bg-zinc-950/40 p-6 rounded-2xl space-y-4">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-zinc-200 font-mono uppercase tracking-wider">Workstation Compliance Audit Trail</h3>
                      <p className="text-xs text-zinc-500 mt-1">Real-time local event tracing for document uploads, security actions, and query history.</p>
                    </div>
                    <button 
                      onClick={handleExportAuditLogs}
                      className="px-4 py-2 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-semibold rounded-lg text-xs transition duration-150 flex items-center gap-1.5 cursor-pointer shrink-0"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Export Signed Audit Report
                    </button>
                  </div>
                  
                  <div className="border border-zinc-900 rounded-xl overflow-hidden bg-zinc-950/60 max-h-[400px] overflow-y-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-zinc-900 bg-zinc-900/40 text-zinc-400 font-mono uppercase text-[9px] tracking-wider">
                          <th className="p-3">Timestamp</th>
                          <th className="p-3">User Operator</th>
                          <th className="p-3">Action Type</th>
                          <th className="p-3">Target</th>
                          <th className="p-3">Details</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-900 font-sans text-zinc-300">
                        {auditLogs.map(log => (
                          <tr key={log.id} className="hover:bg-zinc-900/20 transition-colors">
                            <td className="p-3 font-mono text-[10px] text-zinc-500 shrink-0">{new Date(log.timestamp).toLocaleString()}</td>
                            <td className="p-3 font-mono text-zinc-400">{log.user_email}</td>
                            <td className="p-3">
                              <span className={`px-1.5 py-0.5 rounded font-mono text-[9px] border ${
                                log.action.includes("PANIC") ? "bg-rose-950/40 border-rose-900 text-rose-400" :
                                log.action.includes("DELETE") ? "bg-amber-955/40 border-amber-900 text-amber-400" :
                                "bg-zinc-800 border-zinc-700 text-zinc-400"
                              }`}>{log.action}</span>
                            </td>
                            <td className="p-3 font-mono text-[10px] text-zinc-500">{log.target_type} ({log.target_id || "N/A"})</td>
                            <td className="p-3 text-zinc-400 max-w-xs truncate" title={log.details}>{log.details || "No parameters recorded."}</td>
                          </tr>
                        ))}
                        {auditLogs.length === 0 && (
                          <tr>
                            <td colSpan={5} className="p-4 text-center text-xs text-zinc-500 italic">No audit records found on device.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* EMERGENCY PANIC MODAL CONFIG */}
              {showPanicModal && (
                <div className="fixed inset-0 bg-black/90 backdrop-filter backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in">
                  <div className="bg-zinc-950 border border-red-900/80 w-full max-w-lg p-6 rounded-2xl space-y-6 shadow-2xl shadow-red-950/20">
                    <div className="flex items-center gap-3 text-red-400">
                      <AlertTriangle className="w-8 h-8 animate-pulse" />
                      <div>
                        <h2 className="text-lg font-bold font-mono tracking-wide uppercase text-white">EMERGENCY PANIC DESTRUCTION MODE</h2>
                        <span className="text-[10px] text-red-500 font-mono font-bold block mt-0.5 tracking-wider">ACTION WIPE SYSTEM INITIATED</span>
                      </div>
                    </div>
                    
                    {!panicResult ? (
                      <>
                        <p className="text-xs text-zinc-300 leading-relaxed">
                          This protocol will completely scrub the current workstation environment. 
                          It runs a final AES-256 encrypted zip backup saved directly onto your desktop 
                          (<code className="font-mono bg-zinc-900 p-0.5 rounded text-red-300">Desktop/aegis_backup_*.enc</code>), 
                          and then immediately truncates and wipes all databases, client folders, matters, 
                          document vaults, and Chroma vector spaces from your device.
                        </p>
                        
                        <div className="p-3 bg-red-950/20 border border-red-900/30 rounded-xl text-[11px] text-red-300 leading-relaxed">
                          <strong>WARNING:</strong> Active files cannot be decrypted without the local master security key. 
                          Copy the key or backup archive safely to recover. Active workstation profiles will be completely blank after completion.
                        </div>

                        <div className="flex justify-end gap-3 font-medium">
                          <button 
                            onClick={() => setShowPanicModal(false)}
                            className="px-4 py-2 border border-zinc-800 hover:bg-zinc-900 rounded-lg text-xs text-zinc-400 hover:text-white cursor-pointer"
                          >
                            Cancel WIPE Signal
                          </button>
                          <button 
                            onClick={handlePanicWipe}
                            disabled={panicLoading}
                            className="px-4 py-2 bg-red-700 hover:bg-red-650 disabled:bg-zinc-900 text-white disabled:text-zinc-600 rounded-lg text-xs font-bold transition duration-150 flex items-center gap-1.5 shadow cursor-pointer"
                          >
                            {panicLoading ? "Executing wipe sequence..." : "Yes, Execute WIPE Protocol"}
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="p-4 bg-emerald-950/20 border border-emerald-900 text-emerald-400 rounded-xl text-xs space-y-2">
                          <h4 className="font-bold flex items-center gap-1.5">Wipe sequence completed successfully</h4>
                          <p className="text-[11px] leading-relaxed">Workstation data cleared from databases, directories, and vector spaces.</p>
                          <p className="text-[11px] font-mono mt-1 font-semibold text-zinc-200">
                            Encrypted Recovery Archive Created: {panicResult.message}
                          </p>
                        </div>
                        <div className="flex justify-end">
                          <button 
                            onClick={() => {
                              setShowPanicModal(false);
                              setPanicResult(null);
                              setActiveTab("dashboard");
                            }}
                            className="px-4 py-2 bg-white hover:bg-zinc-200 text-black rounded-lg text-xs font-bold cursor-pointer"
                          >
                            Close Protocol Window
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

            </div>
          )}

          {/* ====== TAB: BILLING & INVOICES ====== */}
          {activeTab === "billing" && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">{lang === "hi" ? "\u092c\u093f\u0932\u093f\u0902\u0917 \u0914\u0930 \u091a\u093e\u0932\u093e\u0928" : "Billing & Invoices"}</h1>
                <p className="text-sm text-zinc-400">Track billable hours, generate GST-compliant invoices, and manage payments.</p>
              </div>
              {selectedClient && (
                <div className="flex gap-4 items-center flex-wrap">
                  <select onChange={(e) => { const id = parseInt(e.target.value); setBillingMatterId(id); fetchTimeEntries(id); }}
                    className="p-2 text-xs rounded-lg glass-input text-zinc-300">
                    <option value="">-- Select Matter for Billing --</option>
                    {matters.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}
                  </select>
                  <button onClick={fetchInvoices} className="px-3 py-2 text-xs border border-zinc-700 rounded-lg text-zinc-300 hover:bg-zinc-800 transition">Load Invoices</button>
                </div>
              )}
              {!selectedClient && <div className="p-4 border border-zinc-800 rounded-xl text-xs text-zinc-500">Select a client from Matters & Context tab first.</div>}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {currentUser?.role !== "client" && (
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <h3 className="text-sm font-bold text-zinc-200">&#9200;&#65039; Time Tracker</h3>
                    <div className="flex items-center gap-4 p-4 bg-zinc-950/60 border border-zinc-800 rounded-xl">
                      <span className="text-2xl font-mono text-emerald-400 tabular-nums">{formatTimer(timerSeconds)}</span>
                      <div className="flex gap-2">
                        {!billingTimer?.running
                          ? <button onClick={startTimer} className="px-3 py-1.5 bg-emerald-800 hover:bg-emerald-700 text-white text-xs rounded-lg font-semibold transition">&#9654; Start</button>
                          : <button onClick={stopTimer} className="px-3 py-1.5 bg-rose-800 hover:bg-rose-700 text-white text-xs rounded-lg font-semibold transition">&#9209; Stop</button>
                        }
                      </div>
                    </div>
                    <div className="space-y-2">
                      <input value={newTimeEntry.description} onChange={e => setNewTimeEntry(p => ({...p, description: e.target.value}))}
                        placeholder="Work description (e.g. Court appearance)" className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950" />
                      <div className="grid grid-cols-3 gap-2">
                        <input value={newTimeEntry.hours} onChange={e => setNewTimeEntry(p => ({...p, hours: e.target.value}))}
                          type="number" step="0.5" placeholder="Hours" className="p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950" />
                        <input value={newTimeEntry.rate_per_hour} onChange={e => setNewTimeEntry(p => ({...p, rate_per_hour: e.target.value}))}
                          type="number" placeholder="&#8377; Rate/hr" className="p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950" />
                        <input value={newTimeEntry.date} onChange={e => setNewTimeEntry(p => ({...p, date: e.target.value}))}
                          type="date" className="p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950" />
                      </div>
                      <button onClick={handleAddTimeEntry} disabled={!billingMatterId}
                        className="w-full py-2 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-semibold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer">
                        + Log Time Entry
                      </button>
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {timeEntries.map((e, i) => (
                        <div key={i} className="flex justify-between items-center p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg text-xs">
                          <div>
                            <p className="text-zinc-200 font-medium">{e.description}</p>
                            <p className="text-zinc-500">{e.date} &middot; {e.hours}h &times; &#8377;{e.rate_per_hour}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-emerald-400 font-mono">&#8377;{e.amount}</span>
                            <button onClick={() => handleDeleteTimeEntry(e.id)}><Trash2 className="w-3 h-3 text-zinc-600 hover:text-rose-400 cursor-pointer" /></button>
                          </div>
                        </div>
                      ))}
                      {timeEntries.length === 0 && <p className="text-xs text-zinc-500 italic text-center">No time entries yet.</p>}
                    </div>
                    <div className="flex justify-between text-xs text-zinc-400 font-semibold border-t border-zinc-800 pt-2">
                      <span>Total Billable</span>
                      <span className="text-zinc-100">&#8377;{timeEntries.reduce((s, e) => s + parseFloat(e.amount || 0), 0).toFixed(2)}</span>
                    </div>
                  </div>
                )}
                
                <div className={`border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4 ${currentUser?.role === "client" ? "lg:col-span-2" : ""}`}>
                  {currentUser?.role !== "client" ? (
                    <>
                      <h3 className="text-sm font-bold text-zinc-200">&#129395; Invoice Generator (GST 18%)</h3>
                      <div className="p-4 bg-zinc-950/60 border border-zinc-800 rounded-xl space-y-2 text-xs">
                        <div className="flex justify-between"><span className="text-zinc-400">Subtotal</span><span>&#8377;{timeEntries.reduce((s, e) => s + parseFloat(e.amount || 0), 0).toFixed(2)}</span></div>
                        <div className="flex justify-between"><span className="text-zinc-400">GST @ 18%</span><span className="text-amber-400">&#8377;{(timeEntries.reduce((s, e) => s + parseFloat(e.amount || 0), 0) * 0.18).toFixed(2)}</span></div>
                        <div className="flex justify-between border-t border-zinc-700 pt-2 font-bold"><span>Grand Total</span><span className="text-emerald-400">&#8377;{(timeEntries.reduce((s, e) => s + parseFloat(e.amount || 0), 0) * 1.18).toFixed(2)}</span></div>
                      </div>
                      <button onClick={handleGenerateInvoice} disabled={isCreatingInvoice || !billingMatterId}
                        className="w-full py-2.5 bg-emerald-800 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer animate-pulse-glow">
                        {isCreatingInvoice ? "Generating..." : "&#128196; Generate Invoice + PDF"}
                      </button>
                    </>
                  ) : (
                    <div className="flex justify-between items-center border-b border-zinc-850 pb-2">
                      <h3 className="text-sm font-bold text-zinc-200">Your Case Invoices</h3>
                      <span className="text-[10px] text-zinc-500 font-mono">GST 18% INCLUDED</span>
                    </div>
                  )}
                  
                  <div className="space-y-2 max-h-[400px] overflow-y-auto pt-1">
                    <h4 className="text-[10px] text-zinc-500 font-bold uppercase">All Invoices</h4>
                    {invoices.map((inv, i) => (
                      <div key={i} className="flex justify-between items-center p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg text-xs hover:border-zinc-700 transition">
                        <div>
                          <p className="text-zinc-200 font-mono font-semibold">{inv.invoice_number}</p>
                          <p className="text-zinc-500">{new Date(inv.created_at).toLocaleDateString("en-IN")}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-emerald-400 font-semibold">&#8377;{inv.grand_total}</span>
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${inv.status === "paid" ? "bg-emerald-900/40 text-emerald-400 border border-emerald-800" : "bg-amber-900/40 text-amber-400 border border-amber-800"}`}>{inv.status.toUpperCase()}</span>
                          <button 
                            onClick={() => {
                              exportToPDF(
                                inv.invoice_number,
                                `INVOICE\n${inv.invoice_number}\nTotal: ₹${inv.total_amount}\nGST (18%): ₹${inv.gst_amount}\nGrand Total: ₹${inv.grand_total}\nStatus: ${inv.status}\nDate: ${new Date(inv.created_at).toLocaleDateString("en-IN")}`,
                                currentUser?.firm_name,
                                currentUser?.firm_logo
                              );
                            }}
                            title="Download Invoice PDF"
                            className="text-zinc-400 hover:text-white p-1 ml-1 transition cursor-pointer"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                    {invoices.length === 0 && <p className="text-xs text-zinc-500 italic text-center py-4">No invoices issued yet.</p>}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ====== TAB: ANALYTICS ====== */}
          {activeTab === "analytics" && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex justify-between items-start">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight">Practice Analytics</h1>
                  <p className="text-sm text-zinc-400">Revenue trends, matter status, and upcoming hearings at a glance.</p>
                </div>
                <button onClick={fetchAnalytics} className="px-3 py-2 text-xs border border-zinc-700 rounded-lg text-zinc-300 hover:bg-zinc-800 transition flex items-center gap-1.5"><RefreshCw className="w-3 h-3" /> Refresh</button>
              </div>
              {analyticsLoading && <div className="text-center text-xs text-zinc-400 animate-pulse py-8">Loading analytics...</div>}
              {analyticsData && (
                <>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                      { label: "Total Clients", value: analyticsData.total_clients, color: "text-blue-400", icon: "&#128100;" },
                      { label: "Active Matters", value: analyticsData.open_matters, color: "text-emerald-400", icon: "&#9878;&#65039;" },
                      { label: "Documents", value: analyticsData.total_documents, color: "text-violet-400", icon: "&#128196;" },
                      { label: "Total Revenue", value: `&#8377;${analyticsData.total_revenue_inr?.toLocaleString("en-IN")}`, color: "text-amber-400", icon: "&#128176;" },
                    ].map((stat, i) => (
                      <div key={i} className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-xl">
                        <p className="text-2xl mb-1" dangerouslySetInnerHTML={{__html: stat.icon}} />
                        <p className={`text-xl font-bold tabular-nums ${stat.color}`} dangerouslySetInnerHTML={{__html: String(stat.value)}} />
                        <p className="text-[11px] text-zinc-500 mt-1">{stat.label}</p>
                      </div>
                    ))}
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-xl space-y-3">
                      <h3 className="text-sm font-bold text-zinc-200">Revenue Overview</h3>
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between p-3 bg-emerald-950/30 border border-emerald-900/40 rounded-lg">
                          <span className="text-zinc-400">Collected Revenue</span>
                          <span className="text-emerald-400 font-bold">&#8377;{analyticsData.total_revenue_inr?.toLocaleString("en-IN")}</span>
                        </div>
                        <div className="flex justify-between p-3 bg-amber-950/30 border border-amber-900/40 rounded-lg">
                          <span className="text-zinc-400">Pending Invoices</span>
                          <span className="text-amber-400 font-bold">&#8377;{analyticsData.pending_revenue_inr?.toLocaleString("en-IN")}</span>
                        </div>
                      </div>
                      <h4 className="text-[10px] text-zinc-500 font-bold uppercase mt-2">Recent Invoices</h4>
                      {analyticsData.recent_invoices?.map((inv: any, i: number) => (
                        <div key={i} className="flex justify-between items-center py-1.5 border-b border-zinc-800/50 text-xs">
                          <span className="text-zinc-300 font-mono">{inv.invoice_number}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-zinc-100">&#8377;{inv.grand_total}</span>
                            <span className={`text-[9px] px-1 rounded ${inv.status === "paid" ? "text-emerald-400" : "text-amber-400"}`}>{inv.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-xl space-y-3">
                      <h3 className="text-sm font-bold text-zinc-200">Hearings (Next 7 Days)</h3>
                      {analyticsData.upcoming_hearings?.length === 0 && <p className="text-xs text-zinc-500 italic">No hearings in next 7 days.</p>}
                      {analyticsData.upcoming_hearings?.map((h: any, i: number) => (
                        <div key={i} className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg flex justify-between items-start text-xs">
                          <div>
                            <p className="text-zinc-200 font-semibold">{h.title}</p>
                            <p className="text-zinc-500">{new Date(h.target_date).toLocaleDateString("en-IN", {weekday: "short", day: "numeric", month: "short"})}</p>
                          </div>
                          <span className="text-[9px] px-1.5 py-0.5 rounded border border-zinc-700 text-zinc-400 uppercase">{h.schedule_type}</span>
                        </div>
                      ))}
                      <div className="pt-3 border-t border-zinc-800">
                        <div className="grid grid-cols-3 gap-2 text-center text-xs">
                          <div className="p-2 bg-zinc-950/60 rounded-lg"><p className="text-emerald-400 font-bold">{analyticsData.open_matters}</p><p className="text-zinc-500">Open</p></div>
                          <div className="p-2 bg-zinc-950/60 rounded-lg"><p className="text-amber-400 font-bold">{analyticsData.total_matters - analyticsData.open_matters - analyticsData.closed_matters}</p><p className="text-zinc-500">Pending</p></div>
                          <div className="p-2 bg-zinc-950/60 rounded-lg"><p className="text-zinc-400 font-bold">{analyticsData.closed_matters}</p><p className="text-zinc-500">Closed</p></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
              {!analyticsData && !analyticsLoading && (
                <div className="text-center py-12">
                  <button onClick={fetchAnalytics} className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm font-semibold transition">Load Analytics Dashboard</button>
                </div>
              )}
            </div>
          )}

          {/* ====== TAB: SETTINGS ====== */}
          {activeTab === "settings" && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
                <p className="text-sm text-zinc-400">Security settings, language preferences, and system configuration.</p>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-zinc-200">Two-Factor Authentication</h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded border font-bold ${twoFaEnabled ? "text-emerald-400 border-emerald-800 bg-emerald-950/30" : "text-zinc-500 border-zinc-700"}`}>{twoFaEnabled ? "ENABLED" : "DISABLED"}</span>
                  </div>
                  <p className="text-xs text-zinc-400">Protect your account with Google Authenticator or any TOTP app.</p>
                  {!twoFaEnabled && (
                    <>
                      <button onClick={handle2FASetup} disabled={twoFaLoading} className="w-full py-2 bg-violet-800 hover:bg-violet-700 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50">
                        {twoFaLoading ? "Setting up..." : "Set Up 2FA"}
                      </button>
                      {twoFaQr && (
                        <div className="space-y-3">
                          <p className="text-xs text-zinc-300">Scan this QR code with your authenticator app:</p>
                          <img src={`data:image/png;base64,${twoFaQr}`} alt="2FA QR Code" className="w-40 h-40 rounded-lg border border-zinc-700 mx-auto" />
                          <p className="text-[10px] text-zinc-500 text-center font-mono break-all">Manual key: {twoFaSecret}</p>
                          <input value={twoFaCode} onChange={e => setTwoFaCode(e.target.value)} placeholder="Enter 6-digit code"
                            className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200 font-mono tracking-widest text-center" maxLength={6} />
                          <button onClick={handle2FAEnable} disabled={twoFaCode.length !== 6} className="w-full py-2 bg-emerald-800 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs transition disabled:opacity-50">
                            Verify &amp; Enable 2FA
                          </button>
                        </div>
                      )}
                    </>
                  )}
                  {twoFaEnabled && <div className="p-3 bg-emerald-950/30 border border-emerald-900/40 rounded-xl text-xs text-emerald-300">2FA is active and protecting your account.</div>}
                </div>
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                  <h3 className="text-sm font-bold text-zinc-200">Language / &#2349;&#2366;&#2359;&#2366;</h3>
                  <div className="flex gap-3">
                    <button onClick={() => { setLang("en"); localStorage.setItem("aegis_lang","en"); }} className={`flex-1 py-3 rounded-xl text-sm font-semibold border transition ${lang === "en" ? "bg-zinc-100 text-zinc-900 border-zinc-300" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"}`}>English</button>
                    <button onClick={() => { setLang("hi"); localStorage.setItem("aegis_lang","hi"); }} className={`flex-1 py-3 rounded-xl text-sm font-semibold border transition ${lang === "hi" ? "bg-zinc-100 text-zinc-900 border-zinc-300" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"}`}>&#2361;&#2367;&#2306;&#2342;&#2368;</button>
                  </div>
                </div>
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-3">
                  <h3 className="text-sm font-bold text-zinc-200">Hearing Alerts</h3>
                  <p className="text-xs text-zinc-400">Desktop notifications for hearings within 48 hours.</p>
                  <p className="text-[11px] text-zinc-500">Upcoming (next 48h): {upcomingAlerts.length}</p>
                  {upcomingAlerts.slice(0, 3).map((a, i) => (
                    <div key={i} className="flex justify-between items-center text-xs p-2 bg-amber-950/20 border border-amber-900/30 rounded-lg">
                      <span className="text-amber-300">{a.title}</span>
                      <span className="text-zinc-500">{new Date(a.target_date).toLocaleDateString("en-IN")}</span>
                    </div>
                  ))}
                </div>
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-3">
                  <h3 className="text-sm font-bold text-zinc-200">Account Info</h3>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between p-2 bg-zinc-950/60 rounded-lg"><span className="text-zinc-500">Email</span><span className="text-zinc-200">{currentUser?.email}</span></div>
                    <div className="flex justify-between p-2 bg-zinc-950/60 rounded-lg"><span className="text-zinc-500">Role</span><span className="text-zinc-200 capitalize">{currentUser?.role}</span></div>
                    <div className="flex justify-between p-2 bg-zinc-950/60 rounded-lg"><span className="text-zinc-500">2FA</span><span className={twoFaEnabled ? "text-emerald-400" : "text-zinc-400"}>{twoFaEnabled ? "Enabled" : "Disabled"}</span></div>
                  </div>
                </div>
                
                <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                  <h3 className="text-sm font-bold text-zinc-200">Custom Firm Letterhead</h3>
                  <p className="text-xs text-zinc-400">Configure logo and title displayed on all generated PDFs &amp; Invoices.</p>
                  
                  <div className="space-y-3 text-xs">
                    <div>
                      <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Firm / Advocate Name</label>
                      <input 
                        type="text" 
                        value={firmName} 
                        onChange={(e) => setFirmName(e.target.value)} 
                        placeholder="e.g. Chambers of Aryan Yadav"
                        className="w-full p-2.5 rounded-lg glass-input text-zinc-200"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Firm Logo (PNG / JPG)</label>
                      <input 
                        type="file" 
                        accept="image/*"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            const reader = new FileReader();
                            reader.onload = (event) => {
                              if (event.target?.result) {
                                setFirmLogo(event.target.result as string);
                              }
                            };
                            reader.readAsDataURL(file);
                          }
                        }}
                        className="w-full text-xs text-zinc-400 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700 cursor-pointer"
                      />
                    </div>
                    
                    {firmLogo && (
                      <div className="space-y-1">
                        <span className="text-[10px] text-zinc-500 font-bold block uppercase font-mono">Logo Preview</span>
                        <div className="p-2 bg-zinc-950/60 rounded-lg inline-block">
                          <img src={firmLogo} alt="Logo preview" className="h-12 w-auto object-contain rounded" />
                        </div>
                      </div>
                    )}
                    
                    <button 
                      onClick={async () => {
                        try {
                          const res = await fetchWithAuth(`${API_BASE}/api/user/firm-settings`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ firm_name: firmName, firm_logo: firmLogo })
                          });
                          if (res.ok) {
                            showNotification("Firm configuration saved successfully!", "success");
                            setCurrentUser((prev: any) => ({ ...prev, firm_name: firmName, firm_logo: firmLogo }));
                          } else {
                            showNotification("Failed to save firm configuration", "error");
                          }
                        } catch (e: any) {
                          showNotification(e.message, "error");
                        }
                      }}
                      className="w-full py-2 bg-violet-800 hover:bg-violet-750 text-white font-bold rounded-lg transition text-xs cursor-pointer"
                    >
                      Save Configuration
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

        </main>

      </div>

      {/* Extracted Text Preview Drawer Modal */}
      {showPreviewModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-filter backdrop-blur-sm flex items-center justify-end z-50 animate-fade-in">
          <div className="w-full max-w-4xl h-screen glass-panel p-6 flex flex-col justify-between shadow-2xl relative">
            <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-transparent via-zinc-800 to-transparent" />
            
            <div className="space-y-4 flex-1 flex flex-col min-h-0">
              <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
                <div className="truncate">
                  <h2 className="text-sm font-bold text-white font-mono truncate">{previewDoc?.original_name}</h2>
                  <span className="text-[10px] text-zinc-500 font-mono">EXTRACTED EVIDENCE TEXT & ANNOTATIONS</span>
                </div>
                <button 
                  onClick={() => setShowPreviewModal(false)}
                  className="text-zinc-500 hover:text-white px-3 py-1.5 border border-zinc-850 rounded-lg text-xs font-medium cursor-pointer bg-zinc-950"
                >
                  Close Drawer
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
                {/* Column 1: Document text viewer */}
                <div className="flex flex-col min-h-0 h-full">
                  <span className="text-[10px] text-zinc-500 font-mono mb-2 uppercase">Document Text</span>
                  <div className="flex-1 overflow-y-auto bg-zinc-950/40 p-4 rounded-xl border border-zinc-900 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed select-text">
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
                <div className="flex flex-col min-h-0 h-full border-l border-zinc-900 pl-4 space-y-4">
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
                        className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[10px] font-semibold"
                      >
                        Grab Selected Text
                      </button>
                    </div>
                    
                    <textarea 
                      value={newAnnotationText} 
                      onChange={e => setNewAnnotationText(e.target.value)}
                      placeholder="Selected text segment..." 
                      rows={2}
                      className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 resize-none font-mono bg-zinc-950"
                    />
                    
                    <input 
                      value={newAnnotationNote} 
                      onChange={e => setNewAnnotationNote(e.target.value)}
                      placeholder="Type sticky note comment here..." 
                      className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950"
                    />

                    <div className="flex justify-between items-center">
                      <div className="flex gap-2">
                        {["yellow", "green", "pink"].map(c => (
                          <button 
                            key={c} 
                            onClick={() => setAnnotationColor(c)}
                            className={`w-4 h-4 rounded-full border ${annotationColor === c ? "border-white scale-110" : "border-transparent"}`}
                            style={{ backgroundColor: c === "yellow" ? "#eab308" : c === "green" ? "#22c55e" : "#ec4899" }}
                          />
                        ))}
                      </div>
                      
                      <button 
                        onClick={handleSaveAnnotation}
                        disabled={!newAnnotationText.trim()}
                        className="px-3 py-1.5 bg-zinc-100 hover:bg-zinc-300 disabled:opacity-50 text-zinc-900 font-bold rounded-lg text-[10px] transition"
                      >
                        Save Highlight
                      </button>
                    </div>
                  </div>

                  {/* Annotations List */}
                  <div className="flex-1 overflow-y-auto space-y-2">
                    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block">Saved Highlights</span>
                    {docAnnotations.map((ann, idx) => (
                      <div 
                        key={idx} 
                        className="p-3 border rounded-xl text-xs space-y-1 bg-zinc-950/20"
                        style={{ borderColor: ann.color === "yellow" ? "#854d0e" : ann.color === "green" ? "#166534" : "#9d174d" }}
                      >
                        <div className="flex justify-between items-start gap-2">
                          <span className="font-mono text-[10px] font-semibold italic bg-zinc-900 px-1 py-0.5 rounded truncate" style={{ color: ann.color === "yellow" ? "#fef08a" : ann.color === "green" ? "#bbf7d0" : "#fbcfe8" }}>
                            "{ann.selected_text}"
                          </span>
                          <button onClick={() => handleDeleteAnnotation(ann.id)} className="text-zinc-600 hover:text-rose-400 shrink-0">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {ann.note && <p className="text-zinc-300 font-sans text-xs">{ann.note}</p>}
                        <p className="text-[9px] text-zinc-600 font-mono">{new Date(ann.created_at).toLocaleTimeString()}</p>
                      </div>
                    ))}
                    {docAnnotations.length === 0 && (
                      <p className="text-xs text-zinc-500 italic text-center py-4">No highlights on this document yet.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Ollama Troubleshooting & Installation Onboarding Modal */}
      {showOllamaOnboarding && (
        <div className="fixed inset-0 bg-black/85 backdrop-filter backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-zinc-950 border border-zinc-800 w-full max-w-xl p-6 rounded-2xl space-y-6 shadow-2xl relative">
            <div className="flex items-center gap-3 border-b border-zinc-900 pb-3">
              <AlertTriangle className="w-6 h-6 text-rose-400 shrink-0" />
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">Local AI Runtime Troubleshooter</h2>
                <span className="text-[10px] text-zinc-500 font-mono">STEP-BY-STEP OLLAMA INITIALIZATION GUIDE</span>
              </div>
            </div>
            
            <p className="text-xs text-zinc-300 leading-relaxed font-sans">
              AegisAI runs fully offline and requires a running instance of <strong className="text-zinc-100">Ollama</strong> with the <strong className="text-zinc-100">deepseek-r1:8b</strong> model on your machine.
            </p>

            <div className="space-y-4">
              <div className="space-y-2 text-xs">
                <div className="font-semibold text-zinc-400 flex items-center gap-1.5 font-mono">1. Download & Launch Ollama</div>
                <p className="text-zinc-400 text-[11px] leading-relaxed">
                  First, download Ollama for Mac from <a href="https://ollama.com" target="_blank" rel="noreferrer" className="text-zinc-200 underline">ollama.com</a>. Once downloaded, open the application from your Applications folder so it runs in your status menu.
                </p>
              </div>

              <div className="space-y-2 text-xs">
                <div className="font-semibold text-zinc-400 flex items-center gap-1.5 font-mono">2. Alternative: Terminal Installation Commands</div>
                <p className="text-zinc-400 text-[11px] leading-relaxed">
                  Or run the following commands in your Terminal to fetch and start the server:
                </p>
                <div className="bg-zinc-900/60 p-3 rounded-lg border border-zinc-850 font-mono text-[11px] text-zinc-300 leading-relaxed relative group">
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText("curl -L https://ollama.com/download/ollama-darwin-arm64.zip -o ollama.zip");
                      showNotification("Download command copied!", "success");
                    }}
                    className="absolute top-2 right-2 px-2 py-1 text-[9px] bg-zinc-950 border border-zinc-800 text-zinc-400 rounded hover:text-white transition"
                  >
                    Copy
                  </button>
                  <span className="text-zinc-500"># Step 1: Install Ollama via curl</span><br />
                  curl -L https://ollama.com/download/ollama-darwin-arm64.zip -o ollama.zip
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="font-semibold text-zinc-400 flex items-center gap-1.5 font-mono">3. Install & Start deepseek-r1 Model</div>
                <p className="text-zinc-400 text-[11px] leading-relaxed">
                  Once Ollama is running, open a Terminal window and download the recommended reasoning engine:
                </p>
                <div className="bg-zinc-900/60 p-3 rounded-lg border border-zinc-850 font-mono text-[11px] text-zinc-300 leading-relaxed relative group">
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText("ollama run deepseek-r1:8b");
                      showNotification("Run command copied!", "success");
                    }}
                    className="absolute top-2 right-2 px-2 py-1 text-[9px] bg-zinc-950 border border-zinc-800 text-zinc-400 rounded hover:text-white transition"
                  >
                    Copy
                  </button>
                  <span className="text-zinc-500"># Step 2: Download local DeepSeek reasoning engine</span><br />
                  ollama run deepseek-r1:8b
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-zinc-900">
              <button 
                onClick={async () => {
                  await fetchSystemStatus();
                  if (systemStatus.ollama_connected) {
                    setShowOllamaOnboarding(false);
                    showNotification("AI Runtime connection established!", "success");
                  } else {
                    showNotification("Ollama is still disconnected. Verify service state in terminal.", "error");
                  }
                }}
                className="px-4 py-2 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-bold rounded-lg text-xs transition cursor-pointer"
              >
                Check Connection
              </button>
              <button 
                onClick={() => setShowOllamaOnboarding(false)}
                className="px-4 py-2 border border-zinc-800 hover:bg-zinc-900 rounded-lg text-xs text-zinc-400 hover:text-white cursor-pointer bg-zinc-950"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

