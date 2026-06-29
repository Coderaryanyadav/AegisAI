"use client";

import React, { useState, useEffect } from "react";
import { Scale, RefreshCw, Download } from "lucide-react";

interface DraftingTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  currentUser: any;
  selectedModel: string;
  exportToPDF: (title: string, content: string, firmName?: string, logoBase64?: string) => Promise<void>;
}

export function DraftingTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  currentUser,
  selectedModel,
  exportToPDF
}: DraftingTabProps) {
  // Local drafting states
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null);
  const [templateFields, setTemplateFields] = useState<any>({});
  const [generatedDraft, setGeneratedDraft] = useState("");
  const [isDrafting, setIsDrafting] = useState(false);

  // Formatting states
  const [courtHeader, setCourtHeader] = useState("none");
  const [lineSpacing, setLineSpacing] = useState("1.5");
  const [marginSpaces, setMarginSpaces] = useState("4");
  const [isFormattingDraft, setIsFormattingDraft] = useState(false);


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

  const handleSelectTemplate = (template: any) => {
    setSelectedTemplate(template);
    const fields: any = {};
    template.fields.forEach((f: string) => {
      fields[f] = "";
    });
    setTemplateFields(fields);
    setGeneratedDraft("");
  };

  const handleGenerateDraft = async (e: React.FormEvent) => {
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
    } catch (err: any) {
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

  useEffect(() => {
    fetchDraftTemplates();
  }, []);

  return (
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
                className={`w-full text-left p-3 rounded-lg text-xs transition border cursor-pointer ${selectedTemplate?.id === t.id ? "bg-zinc-800 border-zinc-700 text-zinc-100 font-semibold" : "bg-transparent border-transparent text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                  }`}
              >
                {t.name}
              </button>
            ))}
          </div>

          {selectedTemplate && (
            <form onSubmit={handleGenerateDraft} className="space-y-3 pt-4 border-t border-zinc-800">
              <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Fill Variables</h4>
              {selectedTemplate.fields.map((field: string) => (
                <div key={field} className="space-y-1">
                  <label className="block text-[10px] text-zinc-500 font-bold uppercase">{field.replace(/_/g, ' ')}</label>
                  <input
                    type="text"
                    value={templateFields[field] || ""}
                    onChange={(e) => setTemplateFields({ ...templateFields, [field]: e.target.value })}
                    className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
                    required
                  />
                </div>
              ))}
              <button
                type="submit"
                disabled={isDrafting}
                className="w-full py-2 bg-zinc-50 hover:bg-zinc-200 disabled:bg-zinc-800 text-zinc-950 disabled:text-zinc-500 font-bold rounded-lg text-xs transition cursor-pointer"
              >
                {isDrafting ? "Drafting Document..." : "Generate AI Draft"}
              </button>
            </form>
          )}
        </div>

        {/* AI Draft Editor Workspace */}
        <div className="lg:col-span-2 border border-zinc-800 bg-zinc-900/10 p-6 rounded-2xl flex flex-col justify-between min-h-[450px]">
          <div className="space-y-4">
            <div className="flex justify-between items-center border-b border-zinc-805 pb-3">
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
  );
}
