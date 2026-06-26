"use client";

import React, { useState } from "react";
import { 
  Users, FileText, Info, Calendar, Upload, 
  Trash2, Plus, MessageCircle, RefreshCw, Play, Download 
} from "lucide-react";

interface DashboardTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  currentUser: any;
  clients: any[];
  selectedClient: any;
  setSelectedClient: (client: any) => void;
  matters: any[];
  setMatters: (matters: any[]) => void;
  selectedMatter: any;
  setSelectedMatter: (matter: any) => void;
  schedules: any[];
  setSchedules: (schedules: any[]) => void;
  documents: any[];
  setDocuments: (documents: any[]) => void;
  fetchMatters: (clientId: string) => Promise<void>;
  fetchSchedules: (matterId: string) => Promise<void>;
  fetchDocuments: (matterId: string) => Promise<void>;
  fetchSystemStatus: () => Promise<void>;
  handleViewDocumentText: (doc: any) => void;
}

export function DashboardTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  currentUser,
  clients,
  selectedClient,
  setSelectedClient,
  matters,
  setMatters,
  selectedMatter,
  setSelectedMatter,
  schedules,
  setSchedules,
  documents,
  setDocuments,
  fetchMatters,
  fetchSchedules,
  fetchDocuments,
  fetchSystemStatus,
  handleViewDocumentText
}: DashboardTabProps) {
  // Local form states
  const [newSchedule, setNewSchedule] = useState({ title: "", schedule_type: "hearing", target_date: "", notes: "" });
  const [isCreatingSchedule, setIsCreatingSchedule] = useState(false);
  const [newMatter, setNewMatter] = useState({ title: "", case_number: "", court: "", judge: "", opponent_name: "", opposing_advocate: "", facts: "", cnr_number: "" });
  const [isCreatingMatter, setIsCreatingMatter] = useState(false);
  const [causeListUploadLoading, setCauseListUploadLoading] = useState(false);
  const [causeListMatches, setCauseListMatches] = useState<any[]>([]);

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

  const handleUploadDocument = async (e: any) => {
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
    } catch (err: any) {
      showNotification(err.message, "error");
    }
  };

  const handleDeleteDocument = async (docId: number) => {
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
    } catch (err: any) {
      showNotification(err.message, "error");
    }
  };

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMatter) {
      showNotification("Please select a matter before scheduling an event", "error");
      return;
    }
    if (!newSchedule.title.trim() || !newSchedule.target_date.trim()) {
      showNotification("Schedule title and target date are required", "error");
      return;
    }
    setIsCreatingSchedule(true);
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
      } else {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to create schedule");
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to create schedule", "error");
    } finally {
      setIsCreatingSchedule(false);
    }
  };

  const handleToggleSchedule = async (scheduleId: number, isCompleted: boolean) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/schedules/${scheduleId}/complete?completed=${isCompleted}`, {
        method: "PUT"
      });
      if (response.ok) {
        fetchSchedules(selectedMatter.id);
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    }
  };

  const handleWhatsAppReminder = async (scheduleId: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/whatsapp/reminder/${scheduleId}`);
      if (res.ok) {
        const d = await res.json();
        window.open(d.whatsapp_url, "_blank");
      }
    } catch (e: any) { 
      showNotification(e.message, "error"); 
    }
  };

  const handleCreateMatter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClient) {
      showNotification("Please select a client before creating a matter", "error");
      return;
    }
    if (!newMatter.title.trim()) {
      showNotification("Matter title is required", "error");
      return;
    }
    setIsCreatingMatter(true);
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
      } else {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to create matter");
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to create matter", "error");
    } finally {
      setIsCreatingMatter(false);
    }
  };

  return (
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
                onClick={() => {
                  setSelectedClient(c);
                  setSelectedMatter(null);
                  setSchedules([]);
                  setDocuments([]);
                }}
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
        <div className="border border-zinc-900 bg-zinc-955/40 p-5 rounded-2xl space-y-4">
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
                {causeListMatches.map((m) => (
                  <div key={m.matter_id} className="p-3 bg-emerald-950/20 border border-emerald-900/60 rounded-xl text-xs flex flex-col justify-between">
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
                  className="p-2.5 text-xs rounded-lg glass-input text-zinc-305 bg-zinc-955 border border-zinc-800"
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
                        className="w-3.5 h-3.5 rounded border-zinc-805 text-zinc-100 accent-zinc-800 focus:ring-0 disabled:opacity-50"
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
                      className="text-emerald-605 hover:text-emerald-400 transition shrink-0">
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
                className="px-4 py-2.5 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs shadow transition cursor-pointer"
                disabled={isCreatingMatter}
              >
                Create Matter File
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
