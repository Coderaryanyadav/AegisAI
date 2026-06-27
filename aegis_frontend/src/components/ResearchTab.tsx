"use client";

import React, { useState } from "react";
import { Search, RefreshCw, Info, TrendingUp } from "lucide-react";
import { StatutoryHelper } from "./StatutoryHelper";
import { RagAssistant } from "./RagAssistant";

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

interface ResearchTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  selectedMatter: any;
  documents: any[];
  selectedModel: string;
}

export function ResearchTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  selectedMatter,
  documents,
  selectedModel
}: ResearchTabProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [ragResult, setRagResult] = useState("");
  const [ragSources, setRagSources] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPrecedent, setSelectedPrecedent] = useState<any>(null);

  // Statutory converter state
  const [helperAct, setHelperAct] = useState("ipc");
  const [helperSection, setHelperSection] = useState("");
  const [helperResult, setHelperResult] = useState<any>(null);
  const [isSearchingHelper, setIsSearchingHelper] = useState(false);

  const handleRagSearch = async (e: React.FormEvent) => {
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

      const response = await fetchWithAuth(`${API_BASE}/api/v1/research/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (response.ok) {
        const data = await response.json();
        setRagResult(data.answer);
        setRagSources(data.sources || []);
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsSearching(false);
    }
  };

  const handleConvertSection = async () => {
    if (!helperSection.trim()) return;
    setIsSearchingHelper(true);
    setHelperResult(null);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/v1/helper/ipc-bns?act=${helperAct}&section=${helperSection}`);
      if (!response.ok) {
        throw new Error("Section mapping not found.");
      }
      const data = await response.json();
      setHelperResult(data);
      setHelperSection("");
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsSearchingHelper(false);
    }
  };

  return (
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
          <RagAssistant
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            isSearching={isSearching}
            ragResult={ragResult}
            ragSources={ragSources}
            handleRagSearch={handleRagSearch}
          />

          {/* Precedent Mapping & Case Citation Graph */}
          <div className="border border-zinc-900 bg-zinc-955/40 p-6 rounded-2xl space-y-4">
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
                      <span className="px-1.5 py-0.5 bg-zinc-800 border border-zinc-700 rounded font-mono text-[9px] text-zinc-400 uppercase">{selectedPrecedent.court}</span>
                      <span className="px-1.5 py-0.5 bg-zinc-800 rounded font-mono text-[9px] text-amber-400 border border-zinc-700">{selectedPrecedent.citation}</span>
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
        <StatutoryHelper
          helperAct={helperAct}
          setHelperAct={setHelperAct}
          helperSection={helperSection}
          setHelperSection={setHelperSection}
          helperResult={helperResult}
          isSearchingHelper={isSearchingHelper}
          handleSearchHelper={handleConvertSection}
        />

      </div>
    </div>
  );
}
