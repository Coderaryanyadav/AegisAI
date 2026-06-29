import React from "react";
import { RefreshCw, Trash2 } from "lucide-react";
import { Document } from "../types";

interface Annotation {
  id: number;
  document_id: number;
  selected_text: string;
  note?: string;
  color: string;
  page_hint?: string;
  created_at: string;
}

interface DocumentPreviewDrawerProps {
  showPreviewModal: boolean;
  previewDoc: Document | null;
  previewText: string;
  previewLoading: boolean;
  docAnnotations: Annotation[];
  newAnnotationText: string;
  setNewAnnotationText: (val: string) => void;
  newAnnotationNote: string;
  setNewAnnotationNote: (val: string) => void;
  annotationColor: string;
  setAnnotationColor: (val: string) => void;
  handleClosePreview: () => void;
  handleSaveAnnotation: () => void;
  handleDeleteAnnotation: (id: number) => void;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
}

export function DocumentPreviewDrawer({
  showPreviewModal,
  previewDoc,
  previewText,
  previewLoading,
  docAnnotations,
  newAnnotationText,
  setNewAnnotationText,
  newAnnotationNote,
  setNewAnnotationNote,
  annotationColor,
  setAnnotationColor,
  handleClosePreview,
  handleSaveAnnotation,
  handleDeleteAnnotation,
  showNotification
}: DocumentPreviewDrawerProps) {
  if (!showPreviewModal) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-filter backdrop-blur-sm flex items-center justify-end z-50 animate-fade-in animate-duration-200">
      <div className="w-full max-w-4xl h-screen glass-panel p-6 flex flex-col justify-between shadow-2xl relative bg-zinc-950 border-l border-zinc-900">
        <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-transparent via-zinc-800 to-transparent" />
        
        <div className="space-y-4 flex-1 flex flex-col min-h-0">
          <div className="flex justify-between items-center border-b border-zinc-900/60 pb-3">
            <div className="truncate">
              <h2 className="text-sm font-bold text-white font-mono truncate">{previewDoc?.original_name}</h2>
              <span className="text-[10px] text-zinc-500 font-mono">EXTRACTED EVIDENCE TEXT & ANNOTATIONS</span>
            </div>
            <button 
              onClick={handleClosePreview}
              className="text-zinc-400 hover:text-white px-3 py-1.5 border border-zinc-850 rounded-lg text-xs font-medium cursor-pointer bg-zinc-900 hover:bg-zinc-800 transition"
            >
              Close Drawer
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
            {/* Column 1: Document text viewer */}
            <div className="flex flex-col min-h-0 h-full">
              <span className="text-[10px] text-zinc-500 font-mono mb-2 uppercase">Document Text</span>
              <div className="flex-1 overflow-y-auto bg-zinc-955 p-4 rounded-xl border border-zinc-900 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed select-text">
                {previewLoading ? (
                  <div className="flex items-center justify-center h-full gap-2 text-zinc-500 italic">
                    <RefreshCw className="w-4 h-4 animate-spin text-zinc-500" /> Loading text extraction...
                  </div>
                ) : (
                  previewText || "No text content extracted."
                )}
              </div>
            </div>

            {/* Column 2: Annotation sidebar */}
            <div className="flex flex-col min-h-0 h-full border-l border-zinc-900/60 pl-4 space-y-4">
              <span className="text-[10px] text-zinc-500 font-mono uppercase">Notes & Annotations</span>
              
              {/* Add annotation */}
              <div className="space-y-3 p-3 bg-zinc-900/20 border border-zinc-900 rounded-xl text-xs">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-zinc-300">Add Sticky Highlight</span>
                  <button 
                    onClick={() => {
                      const sel = window.getSelection()?.toString();
                      if (sel) {
                        setNewAnnotationText(sel);
                        showNotification("Selection grabbed!", "success");
                      } else {
                        showNotification("Select text in the preview window first", "warning");
                      }
                    }}
                    className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[10px] font-semibold cursor-pointer"
                  >
                    Grab Selected Text
                  </button>
                </div>
                
                <textarea 
                  value={newAnnotationText} 
                  onChange={e => setNewAnnotationText(e.target.value)}
                  placeholder="Selected text segment..." 
                  rows={2}
                  className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 resize-none font-mono bg-zinc-950 border border-zinc-805"
                />
                
                <input 
                  value={newAnnotationNote} 
                  onChange={e => setNewAnnotationNote(e.target.value)}
                  placeholder="Type sticky note comment here..." 
                  className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
                />

                <div className="flex justify-between items-center">
                  <div className="flex gap-2">
                    {["yellow", "green", "pink"].map(c => (
                      <button 
                        key={c} 
                        onClick={() => setAnnotationColor(c)}
                        className={`w-4 h-4 rounded-full border cursor-pointer ${annotationColor === c ? "border-white scale-110" : "border-transparent"}`}
                        style={{ backgroundColor: c === "yellow" ? "#eab308" : c === "green" ? "#22c55e" : "#ec4899" }}
                      />
                    ))}
                  </div>
                  
                  <button 
                    onClick={handleSaveAnnotation}
                    disabled={!newAnnotationText.trim()}
                    className="px-3 py-1.5 bg-zinc-100 hover:bg-zinc-300 disabled:opacity-50 text-zinc-900 font-bold rounded-lg text-[10px] transition cursor-pointer"
                  >
                    Save Highlight
                  </button>
                </div>
              </div>

              {/* Annotations List */}
              <div className="flex-1 overflow-y-auto space-y-2">
                <span className="text-[10px] text-zinc-550 font-bold uppercase tracking-wider block font-mono">Saved Highlights</span>
                {docAnnotations.map((ann) => (
                  <div 
                    key={ann.id} 
                    className="p-3 border rounded-xl text-xs space-y-1 bg-zinc-955"
                    style={{ borderColor: ann.color === "yellow" ? "#854d0e" : ann.color === "green" ? "#166534" : "#9d174d" }}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <span className="font-mono text-[10px] font-semibold italic bg-zinc-900 px-1 py-0.5 rounded truncate" style={{ color: ann.color === "yellow" ? "#fef08a" : ann.color === "green" ? "#bbf7d0" : "#fbcfe8" }}>
                        &quot;{ann.selected_text}&quot;
                      </span>
                      <button onClick={() => handleDeleteAnnotation(ann.id)} className="text-zinc-650 hover:text-rose-400 shrink-0 cursor-pointer">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {ann.note && <p className="text-zinc-300 font-sans text-xs">{ann.note}</p>}
                    <p className="text-[9px] text-zinc-650 font-mono">{new Date(ann.created_at).toLocaleTimeString()}</p>
                  </div>
                ))}
                {docAnnotations.length === 0 && (
                  <p className="text-xs text-zinc-550 italic text-center py-4">No highlights on this document yet.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
