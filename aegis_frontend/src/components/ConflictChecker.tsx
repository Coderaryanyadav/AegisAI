import React, { useState } from "react";
import { AlertTriangle, Key, Users, Network, ShieldAlert, CheckCircle2 } from "lucide-react";
import { API_BASE } from "./AppShell";
import { fetchWithAuth } from "../utils/api";

interface ConflictCheckerProps {
  checkConflictClient: string;
  setCheckConflictClient: (val: string) => void;
  checkConflictOpponent: string;
  setCheckConflictOpponent: (val: string) => void;
  conflictResult: any;
  isCheckingConflict: boolean;
  handleConflictCheck: () => void;
}

export const ConflictChecker: React.FC<ConflictCheckerProps> = ({
  checkConflictClient,
  setCheckConflictClient,
  checkConflictOpponent,
  setCheckConflictOpponent,
  conflictResult,
  isCheckingConflict,
  handleConflictCheck,
}) => {
  const [showEntityGraph, setShowEntityGraph] = useState(false);
  const [graphData, setGraphData] = useState<any>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);

  const toggleEntityGraph = async () => {
    if (!showEntityGraph && !graphData) {
      setLoadingGraph(true);
      try {
        const res = await fetchWithAuth(`${API_BASE}/api/v1/crm/entity-graph`);
        if (res.ok) {
          const data = await res.json();
          setGraphData(data);
        }
      } catch (e) {
      } finally {
        setLoadingGraph(false);
      }
    }
    setShowEntityGraph(!showEntityGraph);
  };

  return (
    <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-2xl space-y-4 shadow-sm backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-amber-950/40 border border-amber-900/60 text-amber-500 rounded-xl">
            <AlertTriangle className="w-4.5 h-4.5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-zinc-100">Conflict of Interest Scanner</h3>
            <p className="text-[11px] text-zinc-400">Scan prospective client identities against opposing parties in all active matters to prevent regulatory bar compliance infractions.</p>
          </div>
        </div>
        <button
          onClick={toggleEntityGraph}
          className="px-3 py-1.5 rounded-lg border border-zinc-700 bg-zinc-800 hover:bg-zinc-750 text-zinc-200 text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
        >
          <Network className="w-3.5 h-3.5 text-blue-400" />
          {showEntityGraph ? "Hide Entity Map" : "Entity Relationship Map"}
        </button>
      </div>

      {showEntityGraph && (
        <div className="p-4 bg-zinc-950/80 border border-zinc-800 rounded-xl space-y-3 animate-fade-in">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
            <span className="text-xs font-bold text-zinc-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
              <Network className="w-3.5 h-3.5 text-emerald-400" />
              Firm Entity & Adverse Party Network
            </span>
            {graphData && (
              <span className="text-[10px] text-zinc-500 font-mono">
                {graphData.total_nodes} Entities • {graphData.total_edges} Relationships
              </span>
            )}
          </div>

          {loadingGraph ? (
            <div className="text-xs text-zinc-400 py-4 text-center">Analyzing entity relationship topology...</div>
          ) : graphData ? (
            <div className="space-y-3">
              {graphData.conflicts && graphData.conflicts.length > 0 ? (
                <div className="p-3 bg-red-950/30 border border-red-900/60 rounded-lg space-y-1">
                  <div className="flex items-center gap-1.5 text-red-400 font-bold text-xs">
                    <ShieldAlert className="w-4 h-4" />
                    Critical Adverse Conflict Detected!
                  </div>
                  {graphData.conflicts.map((conf: any, idx: number) => (
                    <p key={idx} className="text-[11px] text-zinc-300">
                      Party <strong className="text-red-300">"{conf.entity}"</strong> is currently registered as an adverse opponent in matter: <em>{conf.matter_title}</em>!
                    </p>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-955/20 border border-emerald-800/40 p-2.5 rounded-lg">
                  <CheckCircle2 className="w-4 h-4" />
                  No cross-matter adverse conflicts detected across active client entities.
                </div>
              )}

              {/* Entity Nodes Cloud */}
              <div className="flex flex-wrap gap-2 pt-1">
                {graphData.nodes.map((node: any) => (
                  <div
                    key={node.id}
                    className="px-2.5 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 font-mono shadow-sm"
                    style={{
                      borderColor: node.color + "55",
                      backgroundColor: node.color + "15",
                      color: node.color
                    }}
                  >
                    <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: node.color }} />
                    <span className="font-semibold">{node.label}</span>
                    <span className="text-[9px] text-zinc-400">({node.type})</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-xs text-zinc-500 py-2">No entity graph data available.</div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        <div className="space-y-1">
          <label className="text-[9px] font-bold text-zinc-450 uppercase font-mono tracking-wider">Prospective Client / Affiliate</label>
          <input 
            type="text" 
            value={checkConflictClient} 
            onChange={e => setCheckConflictClient(e.target.value)} 
            placeholder="e.g. Adani Power Ltd" 
            className="w-full p-2.5 text-xs rounded-xl bg-zinc-950 border border-zinc-850 text-zinc-200 focus:outline-none focus:border-amber-800 placeholder-zinc-650"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[9px] font-bold text-zinc-450 uppercase font-mono tracking-wider">Adversary Party</label>
          <input 
            type="text" 
            value={checkConflictOpponent} 
            onChange={e => setCheckConflictOpponent(e.target.value)} 
            placeholder="e.g. Reliance Infrastructure" 
            className="w-full p-2.5 text-xs rounded-xl bg-zinc-950 border border-zinc-850 text-zinc-200 focus:outline-none focus:border-amber-800 placeholder-zinc-650"
          />
        </div>
      </div>

      <button 
        onClick={handleConflictCheck}
        disabled={isCheckingConflict || (!checkConflictClient.trim() && !checkConflictOpponent.trim())}
        className="w-full py-2.5 font-bold text-xs bg-amber-600 hover:bg-amber-500 border border-amber-500 rounded-xl text-white transition flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
      >
        {isCheckingConflict ? "Scanning Case Database..." : "Verify Conflict Clearance"}
      </button>

      {conflictResult && (
        <div className={`p-4 rounded-2xl text-xs border ${
          conflictResult.conflict 
            ? "bg-rose-950/20 border-rose-900/60 text-rose-300 animate-pulse-glow-red" 
            : "bg-emerald-950/20 border-emerald-900/60 text-emerald-300"
        }`}>
          <div className="flex items-start gap-2.5">
            <AlertTriangle className={`w-4.5 h-4.5 shrink-0 ${conflictResult.conflict ? "text-rose-400" : "text-emerald-400"}`} />
            <div>
              <p className="font-bold text-[11px] uppercase tracking-wider mb-1 font-mono">
                {conflictResult.conflict ? "⚠️ Conflict Alert" : "✅ Clear Passage"}
              </p>
              {conflictResult.conflict ? (
                <div className="space-y-1">
                  <p className="leading-relaxed">{conflictResult.details}</p>
                  <p className="text-[10px] text-rose-400/80 font-medium">Clearance status: REJECT (Aegis database match detected opposing counsel overlaps).</p>
                </div>
              ) : (
                <p className="leading-relaxed">No direct or indirect advisory conflicts detected. Identity credentials checked against all active cases. Clearance status: APPROVED.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
