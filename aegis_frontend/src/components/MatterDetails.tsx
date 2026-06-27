import React from "react";
import { Info } from "lucide-react";

interface MatterDetailsProps {
  selectedMatter: any;
  selectedClient: any;
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  fetchMatters: (clientId: string) => Promise<void>;
  setSelectedMatter: (matter: any) => void;
  fetchSchedules: (matterId: string) => Promise<void>;
}

export const MatterDetails = React.memo(function MatterDetails({
  selectedMatter,
  selectedClient,
  API_BASE,
  fetchWithAuth,
  showNotification,
  fetchMatters,
  setSelectedMatter,
  fetchSchedules
}: MatterDetailsProps) {
  return (
    <div className="border border-zinc-800 bg-zinc-900/30 p-4 rounded-xl space-y-3">
      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
        <Info className="w-3.5 h-3.5" /> Case Details
      </h3>
      {selectedMatter ? (
        <div className="text-xs space-y-2 text-zinc-300">
          <div><strong className="text-zinc-500">Court:</strong> {selectedMatter.court || "Not specified"}</div>
          <div><strong className="text-zinc-500">Judge:</strong> {selectedMatter.judge || "Not specified"}</div>
          <div><strong className="text-zinc-500">Status:</strong> <span className="px-1.5 py-0.5 bg-zinc-800 rounded uppercase text-[10px] font-mono text-zinc-400">{selectedMatter.status}</span></div>
          
          {selectedMatter.cnr_number && (
            <div className="pt-1.5 flex items-center justify-between border-t border-zinc-850/60">
              <div>
                <strong className="text-zinc-500">CNR Number:</strong>
                <p className="font-mono text-zinc-300 text-[10px] mt-0.5">{selectedMatter.cnr_number}</p>
              </div>
              
              <div className="flex items-center gap-1.5">
                {selectedMatter.is_locked ? (
                  <span className="text-[9px] px-2 py-0.5 rounded-md border border-emerald-800/60 bg-emerald-950/20 text-emerald-400 font-bold tracking-wider font-mono">
                    LOCKED SECURE
                  </span>
                ) : (
                  <button 
                    onClick={async () => {
                      try {
                        showNotification("Connecting safely to eCourts platform...", "success");
                        const res = await fetchWithAuth(`${API_BASE}/api/v1/matters/${selectedMatter.id}/sync-ecourts`, {
                          method: "POST"
                        });
                        const data = await res.json();
                        if (res.ok && data.status === "success") {
                          showNotification(data.message, "success");
                          fetchMatters(selectedClient.id);
                          setSelectedMatter((prev: any) => ({ 
                            ...prev, 
                            court: data.court, 
                            judge: data.judge, 
                            is_locked: true 
                          }));
                          fetchSchedules(selectedMatter.id);
                        } else {
                          showNotification(data.message || "Failed to sync eCourts date", "error");
                        }
                      } catch (e: any) {
                        showNotification(e.message, "error");
                      }
                    }}
                    className="px-2.5 py-1 bg-violet-900/60 border border-violet-850 text-white font-semibold text-[9px] rounded-lg hover:bg-violet-800 transition cursor-pointer"
                  >
                    Sync eCourts
                  </button>
                )}
              </div>
            </div>
          )}
          
          <div className="pt-2 border-t border-zinc-800">
            <strong className="text-zinc-500">Case Facts Summary:</strong>
            <p className="text-[11px] text-zinc-400 mt-1 line-clamp-4">{selectedMatter.facts || "No encrypted facts summary saved."}</p>
          </div>
        </div>
      ) : (
        <div className="text-xs text-zinc-500 p-2 italic">Select a matter file to view details.</div>
      )}
    </div>
  );
});
