import React from "react";
import { AlertTriangle, Key, Users } from "lucide-react";

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
  return (
    <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-2xl space-y-4 shadow-sm backdrop-blur-sm">
      <div className="flex items-center gap-2.5">
        <div className="p-2 bg-amber-950/40 border border-amber-900/60 text-amber-500 rounded-xl">
          <AlertTriangle className="w-4.5 h-4.5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-zinc-100">Conflict of Interest Scanner</h3>
          <p className="text-[11px] text-zinc-400">Scan prospective client identities against opposing parties in all active matters to prevent regulatory bar compliance infractions.</p>
        </div>
      </div>

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
