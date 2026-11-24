import React, { useState, useEffect } from "react";
import { Scale, Search, RefreshCw, CheckCircle2, ChevronRight } from "lucide-react";

interface StatutoryHelperProps {
  API_BASE?: string;
  fetchWithAuth?: (url: string, options?: any) => Promise<any>;
  helperAct?: string;
  setHelperAct?: (val: string) => void;
  helperSection?: string;
  setHelperSection?: (val: string) => void;
  helperResult?: any;
  isSearchingHelper?: boolean;
  handleSearchHelper?: () => void;
}

export const StatutoryHelper: React.FC<StatutoryHelperProps> = ({
  API_BASE = "http://localhost:8000",
  fetchWithAuth = fetch
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [crosswalkData, setCrosswalkData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

  const fetchCrosswalk = async (query: string = "") => {
    setLoading(true);
    try {
      const url = `${API_BASE}/api/v1/research/crosswalk?query=${encodeURIComponent(query)}`;
      const res = await fetchWithAuth(url);
      if (res.ok) {
        const data = await res.json();
        setCrosswalkData(data);
      }
    } catch (e) {
      console.error("Failed to load crosswalk data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCrosswalk(searchQuery);
  }, [searchQuery]);

  const filteredData = crosswalkData.filter(item => {
    if (selectedCategory === "all") return true;
    if (selectedCategory === "ipc" && item.old_act === "IPC") return true;
    if (selectedCategory === "crpc" && item.old_act === "CrPC") return true;
    if (selectedCategory === "iea" && item.old_act === "IEA") return true;
    return false;
  });

  return (
    <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-2xl space-y-4 shadow-sm backdrop-blur-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-850 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-violet-950/40 border border-violet-900/60 text-violet-400 rounded-xl">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
              Dual-Statute Sanhitas Cross-Walker
              <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-violet-950/60 text-violet-300 border border-violet-800/60">
                2024 ENFORCEMENT
              </span>
            </h3>
            <p className="text-[11px] text-zinc-400">Bidirectional concordance, substantive statutory deltas, and Supreme Court precedent validity.</p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 bg-zinc-950 p-1 rounded-xl border border-zinc-850 text-xs font-medium">
          <button
            onClick={() => setSelectedCategory("all")}
            className={`px-2.5 py-1 rounded-lg transition text-[11px] cursor-pointer ${selectedCategory === "all" ? "bg-zinc-800 text-white font-bold" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            All Acts
          </button>
          <button
            onClick={() => setSelectedCategory("ipc")}
            className={`px-2.5 py-1 rounded-lg transition text-[11px] cursor-pointer ${selectedCategory === "ipc" ? "bg-violet-900/60 text-violet-200 font-bold border border-violet-800" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            IPC ➔ BNS
          </button>
          <button
            onClick={() => setSelectedCategory("crpc")}
            className={`px-2.5 py-1 rounded-lg transition text-[11px] cursor-pointer ${selectedCategory === "crpc" ? "bg-blue-900/60 text-blue-200 font-bold border border-blue-800" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            CrPC ➔ BNSS
          </button>
          <button
            onClick={() => setSelectedCategory("iea")}
            className={`px-2.5 py-1 rounded-lg transition text-[11px] cursor-pointer ${selectedCategory === "iea" ? "bg-emerald-900/60 text-emerald-200 font-bold border border-emerald-800" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            IEA ➔ BSA
          </button>
        </div>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by section number or keyword (e.g. 302, 420, Anticipatory Bail, Electronic Evidence, FIR, Cheating)..."
          className="w-full pl-9 pr-4 py-2.5 text-xs rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-200 focus:outline-none focus:border-violet-600 placeholder-zinc-600 font-mono"
        />
        {loading && <RefreshCw className="w-3.5 h-3.5 text-zinc-500 absolute right-3.5 top-1/2 -translate-y-1/2 animate-spin" />}
      </div>

      {/* Results List */}
      <div className="space-y-3">
        {filteredData.length === 0 && !loading && (
          <div className="text-center py-8 text-zinc-500 text-xs">
            No statutory mappings found matching "{searchQuery}".
          </div>
        )}

        {filteredData.map((item, idx) => {
          const isExpanded = expandedIndex === idx;
          return (
            <div
              key={idx}
              className={`rounded-xl border transition-all ${isExpanded ? "bg-zinc-950 border-zinc-700 shadow-lg" : "bg-zinc-950/60 border-zinc-850/80 hover:border-zinc-750"}`}
            >
              {/* Card Summary Header */}
              <div
                onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                className="p-3.5 flex flex-wrap items-center justify-between gap-3 cursor-pointer select-none"
              >
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800 font-bold">
                      {item.old_act} § {item.old_section}
                    </span>
                    <span className="text-zinc-600 font-bold">➔</span>
                    <span className="px-2 py-0.5 rounded bg-violet-950/60 text-violet-300 border border-violet-800/60 font-bold">
                      {item.new_act} § {item.new_section}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-zinc-200">{item.old_title}</span>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold flex items-center gap-1 ${item.precedent_status === "Applicable" ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/60" : "bg-amber-950/60 text-amber-400 border border-amber-800/60"}`}>
                    <CheckCircle2 className="w-3 h-3" />
                    Precedent: {item.precedent_status}
                  </span>
                  <ChevronRight className={`w-4 h-4 text-zinc-500 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
                </div>
              </div>

              {/* Expanded Comparison & Judicial Notes */}
              {isExpanded && (
                <div className="p-4 pt-0 border-t border-zinc-900 mt-2 space-y-3 text-xs animate-fade-in">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                    <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-850 space-y-1">
                      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block font-bold">Substantive Delta & Changes</span>
                      <p className="text-zinc-300 text-[11px] leading-relaxed">{item.substantive_delta}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-850 space-y-1">
                      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block font-bold">Judicial Precedent Applicability</span>
                      <p className="text-zinc-300 text-[11px] leading-relaxed">{item.applicability_note}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
