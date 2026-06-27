"use client";

import React, { useState, useEffect } from "react";
import { AlertTriangle, Lock, Download } from "lucide-react";

interface BackupTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  currentUser: any;
  systemStatus: any;
  fetchSystemStatus: () => Promise<void>;
  setClients: (clients: any[]) => void;
  setMatters: (matters: any[]) => void;
  setSchedules: (schedules: any[]) => void;
  setDocuments: (documents: any[]) => void;
  setSelectedClient: (client: any) => void;
  setSelectedMatter: (matter: any) => void;
}

export function BackupTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  currentUser,
  systemStatus,
  fetchSystemStatus,
  setClients,
  setMatters,
  setSchedules,
  setDocuments,
  setSelectedClient,
  setSelectedMatter
}: BackupTabProps) {
  // Local states
  const [backupHistory, setBackupHistory] = useState<any[]>([]);
  const [isBackupRunning, setIsBackupRunning] = useState(false);
  const [showPanicModal, setShowPanicModal] = useState(false);
  const [panicLoading, setPanicLoading] = useState(false);
  const [panicResult, setPanicResult] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);


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
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsBackupRunning(false);
    }
  };

  const handleTriggerRestore = async (backupPath: string) => {
    if (!confirm("Are you sure? Restoring will revert all active cases, files, and vector spaces to the chosen backup point.")) return;
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/backup/restore?backup_path=${encodeURIComponent(backupPath)}`, {
        method: "POST"
      });
      if (response.ok) {
        showNotification("Application state restored successfully. Reloading...", "success");
        setTimeout(() => window.location.reload(), 1500);
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    }
  };

  const handlePanicWipe = async () => {
    if (!confirm("⚠️ WARNING: You are triggering the SECURE PANIC WIPE.\n\nThis will immediately delete all local databases, documents, and vector store indices, and encrypt backups. This action is IRREVERSIBLE.\n\nAre you sure you want to proceed?")) return;
    if (!confirm("Are you ABSOLUTELY sure? This is your final warning.")) return;

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
        // Reset states in parent
        setClients([]);
        setSelectedClient(null);
        setMatters([]);
        setSelectedMatter(null);
        setSchedules([]);
        setDocuments([]);
        fetchSystemStatus();
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setPanicLoading(false);
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

  useEffect(() => {
    fetchBackupHistory();
    if (currentUser?.role === "admin") {
      fetchAuditLogs();
    }
  }, [currentUser]);

  return (
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
            className="px-4 py-2.5 bg-rose-900/30 hover:bg-rose-650 border border-rose-800 text-rose-300 hover:text-white font-bold rounded-lg text-xs transition duration-200 flex items-center gap-2 shadow-lg shadow-rose-950/20 cursor-pointer animate-pulse-glow-red"
          >
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            EMERGENCY PANIC WIPE
          </button>
        )}
      </div>

      {/* System parameters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5 border-zinc-805">
          <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Database Size</span>
          <span className="text-xl font-bold font-mono text-zinc-205">{(systemStatus.database_size_bytes / 1024).toFixed(1)} KB</span>
        </div>
        <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5 border-zinc-805">
          <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Clients Folder</span>
          <span className="text-xl font-bold font-mono text-zinc-205">{systemStatus.registered_clients}</span>
        </div>
        <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5 border-zinc-805">
          <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Active Matters</span>
          <span className="text-xl font-bold font-mono text-zinc-205">{systemStatus.registered_matters}</span>
        </div>
        <div className="p-4 border border-zinc-900 bg-zinc-950/60 rounded-xl text-center space-y-1.5 border-zinc-805">
          <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block font-mono">Vault Documents</span>
          <span className="text-xl font-bold font-mono text-zinc-205">{systemStatus.vault_document_count}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
        
        {/* Perform Backups widget */}
        <div className="border border-zinc-900 bg-zinc-955/50 p-6 rounded-xl space-y-4 h-fit">
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
        <div className="border border-zinc-900 bg-zinc-955/50 p-6 rounded-xl space-y-4 lg:col-span-2">
          <h3 className="text-sm font-bold text-zinc-200 font-mono uppercase tracking-wider">Snapshots Log history</h3>
          <div className="space-y-3.5 max-h-[300px] overflow-y-auto pr-1">
            {backupHistory.map(b => (
              <div key={b.id} className="p-3.5 bg-zinc-900/20 hover:bg-zinc-905 border border-zinc-805 rounded-xl flex items-center justify-between text-xs transition duration-150">
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
                  className="px-3.5 py-1.5 bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-303 font-semibold rounded-lg text-[10px] transition duration-150 cursor-pointer"
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
        <div className="border border-zinc-900 bg-zinc-955/40 p-6 rounded-2xl space-y-4">
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
              <tbody className="divide-y divide-zinc-900 font-sans text-zinc-303">
                {auditLogs.map(log => (
                  <tr key={log.id} className="hover:bg-zinc-900/20 transition-colors">
                    <td className="p-3 font-mono text-[10px] text-zinc-500 shrink-0">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="p-3 font-mono text-zinc-400">{log.user_email}</td>
                    <td className="p-3">
                      <span className={`px-1.5 py-0.5 rounded font-mono text-[9px] border ${
                        log.action.includes("PANIC") ? "bg-rose-955/40 border-rose-900 text-rose-455" :
                        log.action.includes("DELETE") ? "bg-amber-955/40 border-amber-900 text-amber-455" :
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
                <p className="text-xs text-zinc-350 leading-relaxed">
                  This protocol will completely scrub the current workstation environment. 
                  It runs a final AES-256 encrypted zip backup saved directly onto your desktop 
                  (<code className="font-mono bg-zinc-900 p-0.5 rounded text-red-300">Desktop/aegis_backup_*.enc</code>), 
                  and then immediately truncates and wipes all databases, client folders, matters, 
                  document vaults, and Chroma vector spaces from your device.
                </p>
                
                <div className="p-3 bg-red-955/20 border border-red-900/30 rounded-xl text-[11px] text-red-300 leading-relaxed">
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
                <div className="p-4 bg-emerald-955/20 border border-emerald-900 text-emerald-400 rounded-xl text-xs space-y-2">
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
                      window.location.reload();
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
  );
}
