import React from "react";
import { Scale, RefreshCw } from "lucide-react";

interface StatutoryHelperProps {
  helperAct: string;
  setHelperAct: (val: string) => void;
  helperSection: string;
  setHelperSection: (val: string) => void;
  helperResult: any;
  isSearchingHelper: boolean;
  handleSearchHelper: () => void;
}

export const StatutoryHelper: React.FC<StatutoryHelperProps> = ({
  helperAct,
  setHelperAct,
  helperSection,
  setHelperSection,
  helperResult,
  isSearchingHelper,
  handleSearchHelper,
}) => {
  return (
    <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-2xl space-y-4 shadow-sm backdrop-blur-sm">
      <div className="flex items-center gap-2.5">
        <div className="p-2 bg-violet-950/40 border border-violet-900/60 text-violet-400 rounded-xl">
          <Scale className="w-4.5 h-4.5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-zinc-100">Statutory Law Converter (BNS / BNSS / BSA Mapping)</h3>
          <p className="text-[11px] text-zinc-400">Map traditional IPC, CrPC, and IEA offenses immediately to the new 2024 Bharatiya statutes.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <select 
          value={helperAct} 
          onChange={e => setHelperAct(e.target.value)} 
          className="p-2.5 text-xs rounded-xl bg-zinc-950 border border-zinc-850 text-zinc-300 focus:outline-none focus:border-violet-850"
        >
          <option value="ipc">Indian Penal Code (IPC) ➔ BNS</option>
          <option value="crpc">Code of Criminal Procedure (CrPC) ➔ BNSS</option>
          <option value="iea">Indian Evidence Act (IEA) ➔ BSA</option>
        </select>
        <input 
          type="text" 
          value={helperSection} 
          onChange={e => setHelperSection(e.target.value)} 
          placeholder="Enter Old Section (e.g. 302, 378, 154)" 
          className="p-2.5 text-xs rounded-xl bg-zinc-950 border border-zinc-850 text-zinc-200 focus:outline-none focus:border-violet-850 placeholder-zinc-650"
        />
        <button 
          onClick={handleSearchHelper}
          disabled={isSearchingHelper || !helperSection.trim()}
          className="py-2.5 px-4 font-bold text-xs bg-zinc-100 hover:bg-zinc-200 text-zinc-950 rounded-xl transition shadow flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          {isSearchingHelper ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Matching...
            </>
          ) : (
            "Lookup Equivalent"
          )}
        </button>
      </div>

      {helperResult && (
        <div className="bg-zinc-950/80 border border-zinc-850 rounded-2xl p-4.5 space-y-3.5 animate-fade-in text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-zinc-900 pb-3">
            <div>
              <span className="text-[10px] text-zinc-400 font-mono font-bold uppercase tracking-wider bg-zinc-900/60 px-2 py-0.5 border border-zinc-850 rounded-md">Original: {helperResult.old_section} ({helperAct.toUpperCase()})</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-zinc-400">Mapped Equivalent:</span>
              <strong className="text-emerald-400 bg-emerald-950/20 border border-emerald-900/60 px-2 py-0.5 rounded font-mono font-bold">{helperResult.new_section} ({helperResult.act})</strong>
            </div>
          </div>
          <div className="space-y-2 text-zinc-300">
            <div><strong className="text-zinc-500 block text-[10px] uppercase font-mono tracking-wider mb-0.5">Subject Matter</strong> <span className="font-semibold text-zinc-200">{helperResult.subject}</span></div>
            <div><span className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-850 rounded font-mono text-[9px] text-zinc-400 font-bold uppercase tracking-wider">{helperResult.change_type}</span></div>
            <p className="text-zinc-400 leading-relaxed mt-1 text-[11px] border-l border-zinc-800 pl-2.5 italic">{helperResult.description}</p>
            {helperResult.full_text && (
              <div className="mt-3.5 pt-3.5 border-t border-zinc-900">
                <strong className="text-zinc-500 block text-[10px] uppercase font-mono tracking-wider mb-1.5">Official Bare Act Provision</strong>
                <pre className="whitespace-pre-wrap font-mono text-[10px] bg-zinc-950 border border-zinc-900 p-3 rounded-xl max-h-40 overflow-y-auto text-zinc-300 leading-relaxed">{helperResult.full_text}</pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
