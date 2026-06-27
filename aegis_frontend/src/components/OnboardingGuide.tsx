import React, { useState } from "react";
import { Info, HelpCircle, Key, RefreshCw, CheckCircle2, ChevronRight, Play } from "lucide-react";

interface OnboardingGuideProps {
  onClose: () => void;
  ollamaConnected: boolean;
  availableModels: string[];
  refreshDiagnostics: () => void;
  totpSecret?: string;
}

export const OnboardingGuide: React.FC<OnboardingGuideProps> = ({
  onClose,
  ollamaConnected,
  availableModels,
  refreshDiagnostics,
  totpSecret,
}) => {
  const [step, setStep] = useState(1);

  return (
    <div className="fixed inset-0 z-[250] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
      <div className="bg-zinc-950 border border-zinc-800 rounded-3xl p-6.5 max-w-xl w-full shadow-2xl space-y-5 animate-fade-in">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-900 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-violet-950/40 border border-violet-900/60 text-violet-400 rounded-xl">
              <HelpCircle className="w-4.5 h-4.5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">AegisAI Interactive Onboarding Guide</h2>
              <p className="text-[11px] text-zinc-400">Configure your local secure offline legal workspace.</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-xs text-zinc-400 hover:text-white border border-zinc-800 hover:bg-zinc-900 px-3 py-1.5 rounded-lg transition cursor-pointer"
          >
            Close Guide
          </button>
        </div>

        {/* Steps Navigation */}
        <div className="flex items-center justify-between bg-zinc-900/30 border border-zinc-900 p-2 rounded-2xl">
          {[1, 2, 3].map((s) => (
            <button
              key={s}
              onClick={() => setStep(s)}
              className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-xl transition cursor-pointer ${
                step === s 
                  ? "bg-zinc-100 text-zinc-950 font-extrabold shadow-sm" 
                  : "text-zinc-400 hover:bg-zinc-900/50 hover:text-zinc-200"
              }`}
            >
              Step {s}: {s === 1 ? "Ollama Runtime" : s === 2 ? "Legal Models" : "MFA Recovery Key"}
            </button>
          ))}
        </div>

        {/* Step Content */}
        <div className="min-h-[220px] bg-zinc-900/10 border border-zinc-900/60 p-5 rounded-2xl">
          {step === 1 && (
            <div className="space-y-4 animate-fade-in text-xs">
              <h3 className="font-bold text-zinc-200 text-sm flex items-center gap-1.5">
                1. Local Ollama Service Configuration
              </h3>
              <p className="text-zinc-400 leading-relaxed text-[11px]">
                AegisAI runs completely offline. To enable generative legal reasoning (RAG) and contract auditing, you must run the Ollama service locally on your host OS.
              </p>
              
              <div className="bg-zinc-950/90 border border-zinc-900 rounded-xl p-3.5 space-y-2 text-[10px] font-mono text-zinc-300">
                <p className="text-zinc-450">{"// Instructions to start local Ollama service:"}</p>
                <p>1. Download & Install Ollama from <a href="https://ollama.com" target="_blank" rel="noreferrer" className="text-violet-400 underline">https://ollama.com</a></p>
                <p>2. Open your system shell and verify execution:</p>
                <p className="text-amber-400 select-all">ollama serve</p>
                <p>3. If using Docker containers, ensure host connectivity ports are bridged.</p>
              </div>

              <div className="flex items-center justify-between border-t border-zinc-900/80 pt-3.5">
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${ollamaConnected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
                  <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
                    Status: {ollamaConnected ? "Connected Successfully" : "Connection Not Detected"}
                  </span>
                </div>
                <button 
                  onClick={refreshDiagnostics}
                  className="px-3.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-white font-bold text-[10px] rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3 animate-spin" /> Retry Connection
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4 animate-fade-in text-xs">
              <h3 className="font-bold text-zinc-200 text-sm flex items-center gap-1.5">
                2. Install Local Reasoning Weights
              </h3>
              <p className="text-zinc-400 leading-relaxed text-[11px]">
                AegisAI is fine-tuned to compile queries against **DeepSeek-R1** and **Mistral** open-weight models. Run the pull command locally:
              </p>

              <div className="bg-zinc-950/90 border border-zinc-900 rounded-xl p-3.5 space-y-2 text-[10px] font-mono text-zinc-300">
                <p className="text-zinc-450">{"# Command to download deepseek reasoning model:"}</p>
                <p className="text-amber-400 select-all">ollama pull deepseek-r1:8b</p>
                <p className="text-zinc-450">{"# Command to download mistral model:"}</p>
                <p className="text-amber-400 select-all">ollama pull mistral:latest</p>
              </div>

              <div>
                <strong className="text-[9px] uppercase font-mono tracking-wider text-zinc-500 block mb-1">Local Installed Models:</strong>
                <div className="flex flex-wrap gap-1.5">
                  {availableModels.length > 0 ? (
                    availableModels.map((m) => (
                      <span key={m} className="px-2.5 py-1 bg-violet-950/20 border border-violet-900/40 text-violet-400 rounded-md font-mono text-[9px] font-bold">
                        {m}
                      </span>
                    ))
                  ) : (
                    <span className="text-[10px] text-zinc-500 italic">No models pulled yet. The system will operate with fallback mock heuristics.</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4 animate-fade-in text-xs">
              <h3 className="font-bold text-zinc-200 text-sm flex items-center gap-1.5">
                3. Secure 2FA Offline Recovery Key
              </h3>
              <p className="text-zinc-400 leading-relaxed text-[11px]">
                Because this application runs in offline sandboxes, you cannot perform remote password resets. If you lose your TOTP generator device, you **must use your offline recovery code** to bypass lockouts.
              </p>

              <div className="bg-zinc-950 border border-amber-900/30 rounded-2xl p-4.5 space-y-2 text-zinc-300">
                <div className="flex items-center gap-2 text-amber-400 text-[10px] uppercase font-mono font-bold tracking-wider mb-1">
                  <Key className="w-4 h-4" /> Keep This Key in Safe Storage
                </div>
                <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-xl text-center font-mono font-bold text-sm text-zinc-100 select-all tracking-wider break-all shadow-inner">
                  {totpSecret || "2FA_SECRET_NOT_CONFIGURED"}
                </div>
                <p className="text-[10px] text-zinc-500 leading-relaxed mt-1.5">
                  Write this key down on physical paper or store it inside an encrypted hardware security manager (HSM) key storage system. If locked out, enter this key as your 2FA authentication token.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-2 border-t border-zinc-900">
          <button
            onClick={() => setStep((prev) => Math.max(1, prev - 1))}
            disabled={step === 1}
            className="px-4 py-2 border border-zinc-850 hover:bg-zinc-900 rounded-xl text-xs text-zinc-400 hover:text-white cursor-pointer disabled:opacity-50"
          >
            Back
          </button>
          
          {step < 3 ? (
            <button
              onClick={() => setStep((prev) => Math.min(3, prev + 1))}
              className="px-5 py-2 font-bold text-xs bg-zinc-100 hover:bg-zinc-200 text-zinc-950 rounded-xl transition flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              Next Step <ChevronRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-5 py-2 font-bold text-xs bg-violet-700 hover:bg-violet-650 border border-violet-650 text-white rounded-xl transition flex items-center gap-1.5 cursor-pointer shadow-sm shadow-violet-950/20"
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> Finish Onboarding
            </button>
          )}
        </div>

      </div>
    </div>
  );
};
