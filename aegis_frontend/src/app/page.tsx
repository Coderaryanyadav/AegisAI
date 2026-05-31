"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Shield, Scale, FileText, Calendar, Database, Search, 
  Trash2, Upload, AlertTriangle, Play, RefreshCw, Key, 
  Users, CheckSquare, Plus, Clock, FileDiff, Download, Info,
  Lock
} from "lucide-react";

const API_BASE = "http://localhost:8000";

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
  const [newMatter, setNewMatter] = useState({ title: "", case_number: "", court: "", judge: "", opponent_name: "", opposing_advocate: "", facts: "" });
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

  // RBAC Access Maps
  const ALLOWED_TABS: Record<string, string[]> = {
    admin: ["dashboard", "crm", "research", "analyzer", "auditor", "drafting", "backup"],
    lawyer: ["dashboard", "crm", "research", "analyzer", "drafting"],
    auditor: ["auditor", "research"]
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
  const fetchWithAuth = async (url, options = {}) => {
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
        setNewMatter({ title: "", case_number: "", court: "", judge: "", opponent_name: "", opposing_advocate: "", facts: "" });
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
      const body = {
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
          <span className="text-xs text-zinc-400 font-medium hidden sm:inline">{currentUser?.email}</span>
          <button 
            onClick={handleSignOut}
            className="text-xs border border-zinc-800 hover:bg-zinc-900 hover:text-white px-3.5 py-1.5 rounded-lg transition duration-200 font-medium cursor-pointer"
          >
            Sign Out
          </button>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Left Navigation Sidebar */}
        <aside className="w-64 border-r border-zinc-900/80 glass-panel p-4 flex flex-col justify-between hidden md:flex">
          <div className="space-y-1">
            {(currentUser?.role === "admin" || currentUser?.role === "lawyer") && (
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

              {/* Dynamic Context Documents Ingestor */}
              {selectedMatter && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* File Vault Uploader */}
                  <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
                    <h3 className="text-sm font-bold text-zinc-200">Ingest Document Evidence</h3>
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
                              <button 
                                onClick={() => handleDeleteDocument(d.id)}
                                className="text-zinc-500 hover:text-rose-400 p-1 transition"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
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

                    <form onSubmit={handleCreateSchedule} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <input 
                        type="text" 
                        value={newSchedule.title}
                        onChange={(e) => setNewSchedule({ ...newSchedule, title: e.target.value })}
                        placeholder="E.g., File Rejoinder Affidavit"
                        className="p-2.5 text-xs rounded-lg glass-input text-zinc-200 w-full"
                        required
                      />
                      <select 
                        value={newSchedule.schedule_type}
                        onChange={(e) => setNewSchedule({ ...newSchedule, schedule_type: e.target.value })}
                        className="p-2.5 text-xs rounded-lg glass-input text-zinc-300"
                      >
                        <option value="hearing">Court Hearing</option>
                        <option value="deadline">Filing Deadline</option>
                        <option value="meeting">Client Meeting</option>
                      </select>
                      <input 
                        type="date" 
                        value={newSchedule.target_date}
                        onChange={(e) => setNewSchedule({ ...newSchedule, target_date: e.target.value })}
                        className="p-2.5 text-xs rounded-lg glass-input text-zinc-300 w-full"
                        required
                      />
                      <button 
                        type="submit"
                        className="p-2.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs flex items-center justify-center gap-1 shadow transition"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add Task
                      </button>
                    </form>

                    <div className="space-y-2">
                      <div className="space-y-1.5 max-h-[220px] overflow-y-auto">
                        {schedules.map(s => (
                          <div key={s.id} className="flex items-center justify-between p-2 bg-zinc-900/60 border border-zinc-800/80 rounded-lg text-xs">
                            <div className="flex items-center gap-2.5">
                              <input 
                                type="checkbox"
                                checked={s.is_completed}
                                onChange={(e) => handleToggleSchedule(s.id, e.target.checked)}
                                className="w-3.5 h-3.5 rounded border-zinc-800 text-zinc-100 accent-zinc-800 focus:ring-0"
                              />
                              <div className={s.is_completed ? "line-through text-zinc-500" : "text-zinc-300"}>
                                <div className="font-semibold">{s.title}</div>
                                <div className="text-[10px] text-zinc-500 flex items-center gap-1.5 font-mono">
                                  <Calendar className="w-3 h-3" /> {s.target_date}
                                  <span className="uppercase text-[9px] px-1 bg-zinc-800 border border-zinc-700 rounded text-zinc-400">{s.schedule_type}</span>
                                </div>
                              </div>
                            </div>
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
              {selectedClient && (
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
                  <h3 className="text-sm font-bold text-zinc-200">Contract Risk Scanning</h3>
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
                          <span className={`px-2 py-0.5 rounded font-mono text-[9px] border ${
                            risk.risk_rating === "High" ? "bg-rose-950/40 border-rose-900 text-rose-400" :
                            risk.risk_rating === "Medium" ? "bg-amber-955/40 border-amber-900 text-amber-400" :
                            "bg-emerald-955/40 border-emerald-900 text-emerald-400"
                          }`}>{risk.risk_rating.toUpperCase()} RISK</span>
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
                        <button 
                          onClick={() => {
                            const blob = new Blob([generatedDraft], { type: "text/plain;charset=utf-8" });
                            const url = URL.createObjectURL(blob);
                            const link = document.createElement("a");
                            link.href = url;
                            link.download = `${selectedTemplate?.id || "draft"}_generated.txt`;
                            link.click();
                          }}
                          className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-200 transition"
                        >
                          <Download className="w-3 h-3" /> Save Draft Text
                        </button>
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

        </main>
      </div>

      {/* Extracted Text Preview Drawer Modal */}
      {showPreviewModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-filter backdrop-blur-sm flex items-center justify-end z-50 animate-fade-in">
          <div className="w-full max-w-2xl h-screen glass-panel p-6 flex flex-col justify-between shadow-2xl relative">
            <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-transparent via-zinc-800 to-transparent" />
            
            <div className="space-y-4 flex-1 flex flex-col min-h-0">
              <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
                <div className="truncate">
                  <h2 className="text-sm font-bold text-white font-mono truncate">{previewDoc?.original_name}</h2>
                  <span className="text-[10px] text-zinc-500 font-mono">EXTRACTED EVIDENCE TEXT</span>
                </div>
                <button 
                  onClick={() => setShowPreviewModal(false)}
                  className="text-zinc-500 hover:text-white px-3 py-1.5 border border-zinc-850 rounded-lg text-xs font-medium cursor-pointer bg-zinc-950"
                >
                  Close Drawer
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto bg-zinc-950/40 p-4 rounded-xl border border-zinc-900 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">
                {previewLoading ? (
                  <div className="flex items-center justify-center h-full gap-2 text-zinc-500 italic">
                    <RefreshCw className="w-4 h-4 animate-spin text-zinc-500" /> Loading text extraction...
                  </div>
                ) : (
                  previewText || "No text content extracted."
                )}
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
