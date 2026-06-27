"use client";

import React, { useState, useRef } from "react";
import { 
  RefreshCw, Play, Download, Clock, FileText, 
  Mic, MicOff, AlertTriangle 
} from "lucide-react";

interface AnalyzerTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  selectedMatter: any;
  documents: any[];
  currentUser: any;
  selectedModel: string;
  lang: "en" | "hi";
  exportToPDF: (title: string, content: string, firmName?: string, logoBase64?: string) => Promise<void>;
}

export function AnalyzerTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  selectedMatter,
  documents,
  currentUser,
  selectedModel,
  lang,
  exportToPDF
}: AnalyzerTabProps) {
  // Local states
  const [selectedDocForAnalysis, setSelectedDocForAnalysis] = useState<string>("");
  const [analyzerTimeline, setAnalyzerTimeline] = useState<any[]>([]);
  const [analyzerFacts, setAnalyzerFacts] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // FIR states
  const [firDocIds, setFirDocIds] = useState<number[]>([]);
  const [firResult, setFirResult] = useState<any>(null);
  const [isFirAnalyzing, setIsFirAnalyzing] = useState(false);

  // Predictive Outcome state
  const [predictFacts, setPredictFacts] = useState("");
  const [predictCourt, setPredictCourt] = useState("District Court");
  const [predictSections, setPredictSections] = useState("");
  const [predictResult, setPredictResult] = useState<any>(null);
  const [isPredicting, setIsPredicting] = useState(false);

  // Voice Dictation state
  const [isRecording, setIsRecording] = useState(false);
  const [transcribedText, setTranscribedText] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const handleAnalyzeDocument = async (docId: string) => {
    setIsAnalyzing(true);
    setAnalyzerTimeline([]);
    setAnalyzerFacts(null);
    try {
      // Timeline
      const timelineRes = await fetchWithAuth(`${API_BASE}/api/v1/analyze/extract-timeline?document_id=${docId}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (timelineRes.ok) {
        const timelineData = await timelineRes.json();
        setAnalyzerTimeline(Array.isArray(timelineData.timeline) ? timelineData.timeline : []);
      }

      // Facts
      const factsRes = await fetchWithAuth(`${API_BASE}/api/v1/analyze/facts?document_id=${docId}&model_name=${selectedModel}`, {
        method: "POST"
      });
      if (factsRes.ok) {
        const factsData = await factsRes.json();
        setAnalyzerFacts(factsData.facts);
      }
      showNotification("Document analysis completed", "success");
    } catch (err: any) {
      showNotification(err.message, "error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleFIRAnalysis = async () => {
    if (firDocIds.length === 0) { 
      showNotification("Select at least one document", "warning"); 
      return; 
    }
    setIsFirAnalyzing(true); 
    setFirResult(null);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/v1/analyze/fir`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_ids: firDocIds, model_name: selectedModel })
      });
      if (res.ok) { 
        setFirResult(await res.json()); 
        showNotification("FIR analysis complete", "success"); 
      } else { 
        showNotification("FIR analysis failed", "error"); 
      }
    } catch (e: any) { 
      showNotification(e.message, "error"); 
    } finally { 
      setIsFirAnalyzing(false); 
    }
  };

  const handlePredictOutcome = async () => {
    if (!predictFacts.trim()) { 
      showNotification("Enter case facts", "warning"); 
      return; 
    }
    setIsPredicting(true); 
    setPredictResult(null);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/v1/analyze/predict-outcome`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ facts: predictFacts, court: predictCourt, sections: predictSections, model_name: selectedModel })
      });
      if (res.ok) { 
        setPredictResult(await res.json()); 
        showNotification("Prediction complete", "success"); 
      } else { 
        showNotification("Prediction failed", "error"); 
      }
    } catch (e: any) { 
      showNotification(e.message, "error"); 
    } finally { 
      setIsPredicting(false); 
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      mr.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        const reader = new FileReader();
        reader.onloadend = async () => {
          const b64 = (reader.result as string).split(",")[1];
          try {
            const res = await fetchWithAuth(`${API_BASE}/api/v1/analyze/transcribe`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ audio_base64: b64, language: lang })
            });
            if (res.ok) {
              const d = await res.json();
              setTranscribedText(prev => prev + " " + (d.transcript || ""));
              if (d.warning) showNotification(d.warning, "warning");
              else showNotification("Transcribed!", "success");
            }
          } catch (e: any) { 
            showNotification(e.message, "error"); 
          }
        };
        reader.readAsDataURL(blob);
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setIsRecording(true);
    } catch {
      showNotification("Microphone access denied", "error");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Scanned Case Document Analyzer</h1>
        <p className="text-sm text-zinc-400">Wipe out manual reading. Feed FIRs or charge sheets to trigger automatic event timelines and statutory fact extractors.</p>
      </div>

      {/* Scoped selection check */}
      <div className="border border-zinc-800 bg-zinc-900/30 p-4 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div className="text-xs space-y-1">
          <div className="text-zinc-400">
            Active Scoped Matter Folder: <strong className="text-zinc-200">{selectedMatter ? selectedMatter.title : "None Selected (Set scope under Matters tab)"}</strong>
          </div>
          {selectedMatter && (
            <div className="flex gap-2">
              <label className="text-[10px] text-zinc-500 font-bold uppercase">Select Document to Analyze:</label>
              <select 
                value={selectedDocForAnalysis}
                onChange={(e) => setSelectedDocForAnalysis(e.target.value)}
                className="bg-transparent text-zinc-305 border-none outline-none focus:ring-0 p-0 text-[10px]"
              >
                <option value="">-- Choose file --</option>
                {documents.map(d => (
                  <option key={d.id} value={d.id}>{d.original_name}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {selectedDocForAnalysis && (
          <button 
            onClick={() => handleAnalyzeDocument(selectedDocForAnalysis)}
            disabled={isAnalyzing}
            className="px-4 py-2 bg-zinc-50 hover:bg-zinc-200 disabled:bg-zinc-800 text-zinc-950 disabled:text-zinc-500 font-semibold rounded-lg text-xs transition flex items-center gap-1.5 shadow cursor-pointer"
          >
            {isAnalyzing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
            Extract Case Outline
          </button>
        )}
      </div>

      {isAnalyzing && (
        <div className="p-8 border border-zinc-805 bg-zinc-900/10 rounded-xl text-center space-y-2">
          <RefreshCw className="w-8 h-8 animate-spin text-zinc-400 mx-auto" />
          <div className="text-xs text-zinc-300">Running legal NLP parsing pipelines over document text...</div>
          <div className="text-[10px] text-zinc-500">Wait time can take 1-2 minutes depending on GPU power.</div>
        </div>
      )}

      {/* ===== AI ANALYSIS TOOLKIT ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* FIR Analyzer */}
        <div className="border border-rose-900/40 bg-rose-950/10 p-5 rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-rose-400">🚨</span>
            <h3 className="text-sm font-bold text-rose-300">FIR / Criminal Analyzer</h3>
          </div>
          <p className="text-[11px] text-zinc-400">Detect contradictions across FIR, medical report & witness statements. Finds defense points automatically.</p>
          <div className="space-y-1">
            <p className="text-[10px] text-zinc-500 uppercase font-bold">Select documents to analyze:</p>
            {documents.map(d => (
              <label key={d.id} className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                <input type="checkbox" checked={firDocIds.includes(d.id)}
                  onChange={e => setFirDocIds(prev => e.target.checked ? [...prev, d.id] : prev.filter(x => x !== d.id))}
                  className="accent-rose-600" />
                {d.original_name}
              </label>
            ))}
          </div>
          <button onClick={handleFIRAnalysis} disabled={isFirAnalyzing || firDocIds.length === 0}
            className="w-full py-2 bg-rose-800 hover:bg-rose-700 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer">
            {isFirAnalyzing ? <span className="flex items-center justify-center gap-2"><RefreshCw className="w-3 h-3 animate-spin" /> Analyzing...</span> : "🔍 Analyze Criminal Docs"}
          </button>
        </div>

        {/* Predictive Outcome */}
        <div className="border border-blue-900/40 bg-blue-955/10 p-5 rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-blue-400">⚖️</span>
            <h3 className="text-sm font-bold text-blue-300">Case Outcome Predictor</h3>
          </div>
          <p className="text-[11px] text-zinc-400">AI-powered verdict prediction with Indian precedent analysis, risk factors, and confidence score.</p>
          <textarea value={predictFacts} onChange={e => setPredictFacts(e.target.value)} rows={3}
            placeholder="Paste key case facts here..." className="w-full p-2 text-xs rounded-lg glass-input text-zinc-200 resize-none bg-zinc-950" />
          <div className="grid grid-cols-2 gap-2">
            <select value={predictCourt} onChange={e => setPredictCourt(e.target.value)} className="p-2 text-xs rounded-lg glass-input text-zinc-305 bg-zinc-955 border border-zinc-800">
              {["Supreme Court", "High Court", "District Court", "Sessions Court", "Consumer Forum", "Tribunal"].map(c => <option key={c}>{c}</option>)}
            </select>
            <input value={predictSections} onChange={e => setPredictSections(e.target.value)} placeholder="BNS sections (opt.)" className="p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950" />
          </div>
          <button onClick={handlePredictOutcome} disabled={isPredicting || !predictFacts.trim()}
            className="w-full py-2 bg-blue-800 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer">
            {isPredicting ? <span className="flex items-center justify-center gap-2"><RefreshCw className="w-3 h-3 animate-spin" /> Predicting...</span> : "🎯 Predict Outcome"}
          </button>
        </div>

        {/* Voice Dictation */}
        <div className="border border-violet-900/40 bg-violet-955/10 p-5 rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-violet-400">🎙️</span>
            <h3 className="text-sm font-bold text-violet-300">Voice Dictation</h3>
          </div>
          <p className="text-[11px] text-zinc-400">Record audio to transcribe notes, client statements, or case summaries using local Whisper AI.</p>
          <div className="flex justify-center">
            <button onClick={isRecording ? stopRecording : startRecording}
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg cursor-pointer ${isRecording ? "bg-rose-600 animate-pulse scale-110" : "bg-violet-700 hover:bg-violet-650"}`}>
              {isRecording ? <MicOff className="w-8 h-8 text-white" /> : <Mic className="w-8 h-8 text-white" />}
            </button>
          </div>
          <p className="text-[10px] text-center text-zinc-500">{isRecording ? "🔴 Recording... click to stop" : "Click mic to start recording"}</p>
          {transcribedText && (
            <div className="p-2 bg-violet-955/30 border border-violet-800 rounded-lg">
              <p className="text-[10px] text-zinc-505 uppercase font-bold mb-1">Transcript</p>
              <p className="text-xs text-zinc-205 whitespace-pre-wrap">{transcribedText}</p>
              <button onClick={() => setTranscribedText("")} className="text-[10px] text-zinc-500 hover:text-zinc-300 mt-1 cursor-pointer">Clear</button>
            </div>
          )}
        </div>
      </div>

      {/* ===== AI ANALYSIS TOOLKIT RESULTS ===== */}
      {(firResult || predictResult) && (
        <div className="grid grid-cols-1 gap-6">
          {/* FIR Result */}
          {firResult && (
            <div className="border border-rose-900/50 bg-rose-955/5 p-6 rounded-xl space-y-4 animate-fade-in">
              <div className="flex justify-between items-center border-b border-rose-900/40 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-rose-400">🚨</span>
                  <h3 className="text-md font-bold text-rose-305">FIR & Criminal Contradiction Report</h3>
                </div>
                <button 
                  onClick={() => {
                    const content = `FIR & CRIMINAL CONTRADICTION REPORT\n\nOVERVIEW:\n${firResult.case_overview}\n\nCONTRADICTIONS:\n${firResult.contradictions?.map((c: any) => `- [${c.severity}] ${c.document_a} vs ${c.document_b}: ${c.contradiction_detail}`).join("\n")}\n\nDEFENSE POINTS:\n${firResult.defense_points?.map((d: any) => `- [Strength: ${d.strength}] ${d.point} (${d.legal_basis})`).join("\n")}\n\nGAPS IN EVIDENCE:\n${firResult.missing_evidence?.map((g: string) => `- ${g}`).join("\n")}\n\nAPPLICABLE BNS SECTIONS:\n${firResult.applicable_sections_bns?.join(", ")}`;
                    exportToPDF("FIR_Contradiction_Report", content, currentUser?.firm_name, currentUser?.firm_logo);
                  }}
                  className="px-3 py-1.5 bg-rose-900/50 hover:bg-rose-800 border border-rose-800 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" /> Export PDF
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <strong className="text-zinc-400 block mb-1">Case Overview:</strong>
                  <p className="text-zinc-300 leading-relaxed bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">{firResult.case_overview}</p>
                </div>

                {firResult.fir_timeline && firResult.fir_timeline.length > 0 && (
                  <div>
                    <strong className="text-zinc-400 block mb-1">Extracted FIR Timeline:</strong>
                    <div className="space-y-1.5 bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">
                      {firResult.fir_timeline.map((item: any, i: number) => (
                        <div key={i} className="flex gap-2 text-zinc-300">
                          <span className="text-rose-500 font-mono">[{item.timestamp || "TBD"}]</span>
                          <span>{item.event} <span className="text-zinc-500 font-mono">({item.source})</span></span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {firResult.contradictions && firResult.contradictions.length > 0 && (
                  <div>
                    <strong className="text-zinc-400 block mb-1">Contradictions Detected:</strong>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {firResult.contradictions.map((c: any, i: number) => (
                        <div key={i} className="p-3 bg-zinc-950/40 border rounded-lg border-zinc-900 space-y-1">
                          <div className="flex justify-between items-center">
                            <span className="text-[10px] font-bold text-zinc-500">{c.document_a} &harr; {c.document_b}</span>
                            <span className={`text-[9px] px-1 rounded font-bold ${c.severity === "High" ? "bg-rose-950 text-rose-400 border border-rose-900" : c.severity === "Medium" ? "bg-amber-955 text-amber-400 border border-amber-900" : "bg-zinc-800 text-zinc-400"}`}>{c.severity}</span>
                          </div>
                          <p className="text-zinc-303">{c.contradiction_detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {firResult.defense_points && firResult.defense_points.length > 0 && (
                  <div>
                    <strong className="text-zinc-400 block mb-1">Recommended Defense Points:</strong>
                    <div className="space-y-2">
                      {firResult.defense_points.map((d: any, i: number) => (
                        <div key={i} className="p-3 bg-rose-955/5 border border-rose-900/30 rounded-lg">
                          <div className="flex justify-between font-semibold text-zinc-202">
                            <span>{d.point}</span>
                            <span className="text-[10px] text-rose-400 font-mono">Strength: {d.strength}</span>
                          </div>
                          <p className="text-zinc-404 mt-1 text-[11px]">Legal Basis: {d.legal_basis}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {firResult.missing_evidence && firResult.missing_evidence.length > 0 && (
                    <div>
                      <strong className="text-zinc-400 block mb-1">Gaps in Evidence / Investigation:</strong>
                      <ul className="list-disc list-inside space-y-1 text-zinc-300">
                        {firResult.missing_evidence.map((g: string, i: number) => <li key={i}>{g}</li>)}
                      </ul>
                    </div>
                  )}
                  {firResult.applicable_sections_bns && firResult.applicable_sections_bns.length > 0 && (
                    <div>
                      <strong className="text-zinc-400 block mb-1">Applicable Sections (BNS):</strong>
                      <div className="flex gap-1.5 flex-wrap">
                        {firResult.applicable_sections_bns.map((s: string, i: number) => (
                          <span key={i} className="px-2 py-0.5 bg-rose-955/40 border border-rose-900 text-rose-300 rounded font-mono font-semibold">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Outcome Prediction Result */}
          {predictResult && (
            <div className="border border-blue-900/50 bg-blue-955/5 p-6 rounded-xl space-y-4 animate-fade-in">
              <div className="flex justify-between items-center border-b border-blue-900/40 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-blue-400">🎯</span>
                  <h3 className="text-md font-bold text-blue-300">Case Verdict Outcome Prediction</h3>
                </div>
                <button 
                  onClick={() => {
                    const content = `CASE OUTCOME PREDICTION REPORT\n\nPREDICTED OUTCOME: ${predictResult.predicted_outcome} (${predictResult.confidence_percentage}% Confidence)\n\nREASONING:\n${predictResult.reasoning?.map((r: string) => `- ${r}`).join("\n")}\n\nRISK FACTORS:\n${predictResult.risk_factors?.map((rf: string) => `- ${rf}`).join("\n")}\n\nSUGGESTIONS:\n${predictResult.strengthening_suggestions?.map((s: string) => `- ${s}`).join("\n")}\n\nPRECEDENTS:\n${predictResult.similar_precedents?.map((p: any) => `- ${p.case_name} (${p.citation}): ${p.relevance}`).join("\n")}\n\nESTIMATED TIMELINE: ${predictResult.estimated_timeline_months} months`;
                    exportToPDF("Case_Prediction_Report", content, currentUser?.firm_name, currentUser?.firm_logo);
                  }}
                  className="px-3 py-1.5 bg-blue-900/50 hover:bg-blue-800 border border-blue-800 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" /> Export PDF
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl text-center space-y-1">
                  <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">Predicted Outcome</span>
                  <p className={`text-sm font-bold uppercase ${predictResult.predicted_outcome === "Likely to Succeed" ? "text-emerald-400" : predictResult.predicted_outcome === "Likely to Fail" ? "text-rose-400" : "text-amber-400"}`}>{predictResult.predicted_outcome}</p>
                </div>
                <div className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl text-center space-y-1">
                  <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">AI Confidence Rating</span>
                  <p className="text-xl font-bold font-mono text-blue-400">{predictResult.confidence_percentage}%</p>
                </div>
                <div className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl text-center space-y-1">
                  <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">Estimated Timeline</span>
                  <p className="text-xl font-bold font-mono text-zinc-300">{predictResult.estimated_timeline_months} mos</p>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                {predictResult.reasoning && predictResult.reasoning.length > 0 && (
                  <div>
                    <strong className="text-zinc-400 block mb-1">Key Legal Reasoning:</strong>
                    <ul className="list-decimal list-inside space-y-1 text-zinc-300 leading-relaxed bg-zinc-955/40 p-3 rounded-lg border border-zinc-900">
                      {predictResult.reasoning.map((r: string, i: number) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {predictResult.risk_factors && predictResult.risk_factors.length > 0 && (
                    <div className="p-3.5 bg-rose-955/5 border border-rose-900/20 rounded-xl">
                      <strong className="text-rose-350 block mb-1.5">Identified Risk Factors:</strong>
                      <ul className="list-disc list-inside space-y-1.5 text-zinc-405 text-[11px]">
                        {predictResult.risk_factors.map((rf: string, i: number) => <li key={i}>{rf}</li>)}
                      </ul>
                    </div>
                  )}
                  {predictResult.strengthening_suggestions && predictResult.strengthening_suggestions.length > 0 && (
                    <div className="p-3.5 bg-emerald-955/5 border border-emerald-900/20 rounded-xl">
                      <strong className="text-emerald-305 block mb-1.5">Action Items to Strengthen Case:</strong>
                      <ul className="list-disc list-inside space-y-1.5 text-zinc-405 text-[11px]">
                        {predictResult.strengthening_suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}
                      </ul>
                    </div>
                  )}
                </div>

                {predictResult.similar_precedents && predictResult.similar_precedents.length > 0 && (
                  <div>
                    <strong className="text-zinc-400 block mb-1.5">Relevant Supreme Court / High Court Precedents:</strong>
                    <div className="space-y-2">
                      {predictResult.similar_precedents.map((p: any, i: number) => (
                        <div key={i} className="p-3 bg-zinc-950/40 border border-zinc-900 rounded-lg text-xs">
                          <div className="flex justify-between font-bold text-zinc-303 font-mono">
                            <span>{p.case_name}</span>
                            <span className="text-blue-450">{p.citation}</span>
                          </div>
                          <p className="text-zinc-405 mt-1">{p.relevance}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}


      {/* Analyzer Results Grid */}
      {!isAnalyzing && (analyzerTimeline.length > 0 || analyzerFacts) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Timeline */}
          <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-zinc-400" /> Chronological Event Timeline
            </h3>
            <div className="space-y-4 relative border-l border-zinc-800 pl-4 ml-2 max-h-[450px] overflow-y-auto pt-2">
              {analyzerTimeline.map((item, idx) => (
                <div key={idx} className="relative space-y-1">
                  <div className="absolute top-1.5 left-[-21px] w-2.5 h-2.5 rounded-full bg-zinc-700 border border-zinc-950" />
                  <span className="text-[10px] font-bold font-mono text-zinc-500">{item.date || "Date Unspecified"}</span>
                  <h4 className="text-xs font-semibold text-zinc-205">{item.description}</h4>
                  {item.involved_parties && (
                    <p className="text-[10px] text-zinc-400 italic">Parties: {item.involved_parties}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Fact sheet */}
          <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
              <FileText className="w-4 h-4 text-zinc-400" /> Fact Sheet extraction
            </h3>
            {analyzerFacts ? (
              <div className="text-xs space-y-3 font-sans text-zinc-300">
                <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                  <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Offence Description</strong>
                  <p className="text-zinc-200">{analyzerFacts.offence}</p>
                </div>
                <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                  <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Statutory Provisions Invoked</strong>
                  <p className="text-zinc-200 font-mono">{analyzerFacts.sections_invoked}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                    <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Accused Individuals</strong>
                    <p className="text-zinc-200">{analyzerFacts.accused}</p>
                  </div>
                  <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                    <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Victims / Complainants</strong>
                    <p className="text-zinc-200">{analyzerFacts.victims}</p>
                  </div>
                </div>
                <div className="p-3 bg-zinc-950/60 border border-zinc-900 rounded-lg">
                  <strong className="text-zinc-500 block text-[10px] uppercase mb-1">Case Narrative</strong>
                  <p className="text-zinc-303 leading-relaxed">{analyzerFacts.summary}</p>
                </div>
              </div>
            ) : (
              <div className="text-xs text-zinc-500 italic">No fact sheet extracted.</div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
