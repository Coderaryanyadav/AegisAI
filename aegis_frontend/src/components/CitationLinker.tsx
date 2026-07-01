"use client";

import React, { useState } from "react";
import { Link2, RefreshCw, BookOpen } from "lucide-react";

interface CitationLinkerProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
}

export const CitationLinker: React.FC<CitationLinkerProps> = ({
  API_BASE,
  fetchWithAuth,
  showNotification,
}) => {
  const [inputText, setInputText] = useState("");
  const [citations, setCitations] = useState<any[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<any>(null);
  const [isDetecting, setIsDetecting] = useState(false);

  const handleDetectCitations = async () => {
    if (!inputText.trim()) {
      showNotification("Paste legal text to scan for statutory citations", "error");
      return;
    }
    setIsDetecting(true);
    setSelectedCitation(null);
    try {
      const formData = new FormData();
      formData.append("text", inputText);
      const response = await fetchWithAuth(`${API_BASE}/api/v1/helper/detect-citations`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Citation detection failed");
      }
      const data = await response.json();
      setCitations(data.citations || []);
      if (data.count === 0) {
        showNotification("No statutory citations detected in the provided text", "info");
      } else {
        showNotification(`Detected ${data.count} statutory citation(s)`, "success");
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to detect citations", "error");
    } finally {
      setIsDetecting(false);
    }
  };

  const handleCitationClick = async (cite: any) => {
    setSelectedCitation(cite);
    if (cite.full_text) return;
    try {
      const response = await fetchWithAuth(
        `${API_BASE}/api/v1/helper/bare-act/${encodeURIComponent(cite.act)}/${encodeURIComponent(cite.section)}`
      );
      if (response.ok) {
        const data = await response.json();
        setSelectedCitation({ ...cite, ...data });
      }
    } catch {
      showNotification("Could not load Bare Act section text", "error");
    }
  };

  return (
    <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-2xl space-y-4 shadow-sm backdrop-blur-sm">
      <div className="flex items-center gap-2.5">
        <div className="p-2 bg-emerald-950/40 border border-emerald-900/60 text-emerald-400 rounded-xl">
          <Link2 className="w-4.5 h-4.5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-zinc-100">Bare Act Citation Linker</h3>
          <p className="text-[11px] text-zinc-400">
            Auto-detect IPC, BNS, CrPC, BNSS citations and link to local Bare Act sections.
          </p>
        </div>
      </div>

      <textarea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="Paste case brief text here... e.g. 'charged under Section 302 IPC' or 'S. 154 CrPC'"
        rows={4}
        className="w-full p-3 text-xs rounded-xl bg-zinc-950 border border-zinc-850 text-zinc-200 focus:outline-none focus:border-emerald-850 placeholder-zinc-650 font-mono leading-relaxed"
      />

      <button
        onClick={handleDetectCitations}
        disabled={isDetecting || !inputText.trim()}
        className="w-full py-2.5 px-4 font-bold text-xs bg-emerald-900/40 hover:bg-emerald-800/50 text-emerald-300 border border-emerald-800/60 rounded-xl transition flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
      >
        {isDetecting ? (
          <>
            <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Scanning...
          </>
        ) : (
          <>
            <BookOpen className="w-3.5 h-3.5" /> Detect & Link Citations
          </>
        )}
      </button>

      {citations.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
            Detected Citations ({citations.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {citations.map((cite, idx) => (
              <button
                key={`${cite.act}-${cite.section}-${idx}`}
                onClick={() => handleCitationClick(cite)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-mono border transition cursor-pointer ${
                  selectedCitation?.section === cite.section && selectedCitation?.act === cite.act
                    ? "bg-emerald-950/50 border-emerald-700 text-emerald-300"
                    : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-emerald-900 hover:text-emerald-400"
                }`}
              >
                {cite.matched_text}
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedCitation && (
        <div className="bg-zinc-950/80 border border-zinc-850 rounded-2xl p-4 space-y-3 animate-fade-in text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-900 pb-3">
            <span className="text-emerald-400 font-mono font-bold">
              {selectedCitation.act} Section {selectedCitation.section}
            </span>
            {selectedCitation.lookup?.mapping && (
              <span className="text-zinc-500">
                Maps to{" "}
                <strong className="text-emerald-400">
                  {selectedCitation.lookup.target_act} {selectedCitation.lookup.target_section}
                </strong>
              </span>
            )}
          </div>
          {selectedCitation.lookup?.mapping?.subject && (
            <p className="text-zinc-300 font-semibold">{selectedCitation.lookup.mapping.subject}</p>
          )}
          {selectedCitation.full_text ? (
            <pre className="whitespace-pre-wrap font-mono text-[10px] bg-zinc-950 border border-zinc-900 p-3 rounded-xl max-h-48 overflow-y-auto text-zinc-300 leading-relaxed">
              {selectedCitation.full_text}
            </pre>
          ) : (
            <p className="text-zinc-500 italic">Loading Bare Act provision...</p>
          )}
        </div>
      )}
    </div>
  );
};
