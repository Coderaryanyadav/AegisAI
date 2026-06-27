"use client";

import React, { useState } from "react";
import { Download } from "lucide-react";

interface AuditorTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  selectedMatter: any;
  documents: any[];
  currentUser: any;
  selectedModel: string;
  exportToPDF: (title: string, content: string, firmName?: string, logoBase64?: string) => Promise<void>;
}

export function AuditorTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  selectedMatter,
  documents,
  currentUser,
  selectedModel,
  exportToPDF
}: AuditorTabProps) {
  const [selectedContractForAudit, setSelectedContractForAudit] = useState<string>("");
  const [auditRisks, setAuditRisks] = useState<any[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);

  // Clause comparator states
  const [contractDocA, setContractDocA] = useState("");
  const [contractDocB, setContractDocB] = useState("");
  const [compareResults, setCompareResults] = useState<any[]>([]);
  const [isComparing, setIsComparing] = useState(false);

  // Simplify states
  const [showSimplifyModal, setShowSimplifyModal] = useState(false);
  const [simplifyClauseText, setSimplifyClauseText] = useState("");
  const [simplifyResult, setSimplifyResult] = useState<any>(null);
  const [isSimplifying, setIsSimplifying] = useState(false);

  const handleAuditContract = async (docId: string) => {
    setIsAuditing(true);
    setAuditRisks([]);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/v1/audit/risk-scan?document_id=${docId}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (response.ok) {
        const data = await response.json();
        setAuditRisks(Array.isArray(data.risks) ? data.risks : []);
        showNotification("Contract risk scan completed", "success");
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsAuditing(false);
    }
  };

  const handleCompareContracts = async () => {
    if (!contractDocA || !contractDocB) {
      showNotification("Please select both documents to run comparison audit", "warning");
      return;
    }
    setIsComparing(true);
    setCompareResults([]);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/v1/audit/compare?doc_id_a=${contractDocA}&doc_id_b=${contractDocB}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (response.ok) {
        const data = await response.json();
        setCompareResults(Array.isArray(data.comparison) ? data.comparison : []);
        showNotification("Clause variance audit completed", "success");
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsComparing(false);
    }
  };

  const handleSimplifyClause = async () => {
    if (!simplifyClauseText.trim()) {
      showNotification("Please enter clause text to simplify", "warning");
      return;
    }
    setIsSimplifying(true);
    setSimplifyResult(null);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/v1/audit/simplify`, {
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
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsSimplifying(false);
    }
  };

  return (
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
                value={selectedContractForAudit}
                onChange={(e) => setSelectedContractForAudit(e.target.value)}
                className="p-2 text-xs rounded-lg glass-input text-zinc-300 bg-zinc-950 border border-zinc-805"
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
                  className="px-4 py-2 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-semibold rounded-lg text-xs transition cursor-pointer"
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
                      className="px-2 py-0.5 rounded text-[9px] font-semibold bg-violet-900/40 border border-violet-700 text-violet-300 hover:bg-violet-800/60 transition cursor-pointer"
                      title="Simplify this clause in plain language"
                    >✨ Simplify</button>
                    <span className={`px-2 py-0.5 rounded font-mono text-[9px] border ${
                      risk.risk_rating === "High" ? "bg-rose-955/40 border-rose-900 text-rose-400" :
                      risk.risk_rating === "Medium" ? "bg-amber-955/40 border-amber-900 text-amber-400" :
                      "bg-emerald-955/40 border-emerald-900 text-emerald-400"
                    }`}>{risk.risk_rating.toUpperCase()} RISK</span>
                  </div>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">{risk.summary}</p>
                <div className="text-[11px] text-zinc-400 italic bg-zinc-950/40 p-2 rounded border border-zinc-900">
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
                  className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-300 bg-zinc-950 border border-zinc-805"
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
                  className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-300 bg-zinc-955 border border-zinc-805"
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
                className="w-full py-2.5 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs shadow transition cursor-pointer"
              >
                {isComparing ? "Comparing..." : "Run Variance Check"}
              </button>
            </div>
          )}

          {/* Comparison output */}
          <div className="space-y-3 pt-2 max-h-[300px] overflow-y-auto">
            {compareResults.map((c, idx) => (
              <div key={idx} className="p-3 bg-zinc-905 border border-zinc-805 rounded-lg text-xs space-y-1.5">
                <div className="flex justify-between items-center">
                  <strong className="text-zinc-200 font-semibold">{c.clause_title}</strong>
                  <span className="text-[9px] px-1 bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono uppercase">{c.variance_type}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px] text-zinc-400 pt-1">
                  <div><strong>Doc A:</strong> {c.doc_a_provision}</div>
                  <div><strong>Doc B:</strong> {c.doc_b_provision}</div>
                </div>
                <div className="text-[10px] text-zinc-400 border-t border-zinc-800/80 pt-1">
                  <span className="text-zinc-500 font-bold uppercase">Risk Scan:</span> {c.risk_assessment}
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
      <div className="border border-violet-900/50 bg-violet-955/10 p-5 rounded-xl space-y-3">
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
          className="w-full p-3 text-xs rounded-lg glass-input text-zinc-200 resize-none bg-zinc-950 border border-zinc-805"
        />
        <button
          onClick={() => { setSimplifyResult(null); setShowSimplifyModal(true); handleSimplifyClause(); }}
          disabled={isSimplifying || !simplifyClauseText.trim()}
          className="px-4 py-2 bg-violet-700 hover:bg-violet-650 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer"
        >
          {isSimplifying ? "Simplifying..." : "Simplify Clause"}
        </button>
      </div>

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
                className="text-zinc-500 hover:text-zinc-200 text-lg leading-none transition cursor-pointer"
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
                className="w-full p-3 text-xs rounded-lg glass-input text-zinc-200 resize-none bg-zinc-900 border border-zinc-805"
              />
            </div>

            <button
              onClick={handleSimplifyClause}
              disabled={isSimplifying || !simplifyClauseText.trim()}
              className="w-full py-2.5 bg-violet-700 hover:bg-violet-650 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer"
            >
              {isSimplifying ? "Simplifying with AI..." : "✨ Simplify Now"}
            </button>

            {isSimplifying && (
              <div className="p-4 text-center text-xs text-violet-300 animate-pulse">AI is rewriting the clause in plain language...</div>
            )}

            {simplifyResult && !isSimplifying && (
              <div className="space-y-3">
                <div className="p-4 bg-violet-955/30 border border-violet-900/50 rounded-xl">
                  <p className="text-[10px] font-bold text-violet-400 uppercase mb-2">Plain-Language Version</p>
                  <p className="text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap">{simplifyResult.simplified}</p>
                </div>
                {simplifyResult.key_obligations && simplifyResult.key_obligations.length > 0 && (
                  <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-xl">
                    <p className="text-[10px] font-bold text-zinc-400 uppercase mb-2">Key Obligations</p>
                    <ul className="space-y-1">
                      {simplifyResult.key_obligations.map((ob: any, i: number) => (
                        <li key={i} className="text-xs text-zinc-300 flex gap-2"><span className="text-violet-455">→</span>{ob}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {simplifyResult.risk_flags && simplifyResult.risk_flags.length > 0 && (
                  <div className="p-3 bg-rose-955/20 border border-rose-900/40 rounded-xl">
                    <p className="text-[10px] font-bold text-rose-400 uppercase mb-2">Risk Flags</p>
                    <ul className="space-y-1">
                      {simplifyResult.risk_flags.map((flag: any, i: number) => (
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

    </div>
  );
}
