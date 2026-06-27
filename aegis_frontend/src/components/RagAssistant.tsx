import React from "react";
import { Search, RefreshCw } from "lucide-react";

interface RagAssistantProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  isSearching: boolean;
  ragResult: string;
  ragSources: any[];
  handleRagSearch: (e: React.FormEvent) => void;
}

export const RagAssistant = React.memo(function RagAssistant({
  searchQuery,
  setSearchQuery,
  isSearching,
  ragResult,
  ragSources,
  handleRagSearch
}: RagAssistantProps) {
  return (
    <div className="space-y-4">
      <form onSubmit={handleRagSearch} className="flex gap-2">
        <input 
          type="text" 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Ask the local AI about charge details, contract defaults, ratio decidendi..."
          className="flex-1 p-3 text-sm rounded-lg glass-input text-zinc-200 font-medium"
          required
        />
        <button 
          type="submit"
          disabled={isSearching}
          className="px-5 bg-zinc-50 hover:bg-zinc-200 disabled:bg-zinc-800 text-zinc-950 disabled:text-zinc-500 font-semibold rounded-lg text-sm transition flex items-center gap-1.5 shadow cursor-pointer"
        >
          {isSearching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Query RAG
        </button>
      </form>

      {/* LLM Result Box */}
      <div className="border border-zinc-800 bg-zinc-900/20 p-6 rounded-2xl min-h-[300px] flex flex-col justify-between">
        <div>
          <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-4 font-mono">Local AI Agent Response</h3>
          {ragResult ? (
            <div className="text-sm leading-relaxed text-zinc-200 whitespace-pre-wrap font-sans">
              {ragResult}
            </div>
          ) : (
            <div className="text-xs text-zinc-500 italic mt-8 text-center">
              {isSearching ? "Synthesizing answer from local index..." : "Awaiting your local query request."}
            </div>
          )}
        </div>
        {ragSources.length > 0 && (
          <div className="mt-8 pt-4 border-t border-zinc-800">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-2">Sources and Citations Recalled:</span>
            <div className="flex flex-wrap gap-2">
              {ragSources.map((s, idx) => (
                <div key={s.id} className="text-[10px] px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-zinc-400 font-mono">
                  [{idx + 1}] {s.metadata.filename || "CaseFile"}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});
