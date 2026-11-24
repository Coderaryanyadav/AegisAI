import React from "react";
import { ShieldCheck, Lock, Download, Printer, X, CheckCircle, Cpu, HardDrive, WifiOff } from "lucide-react";

interface PrivilegeCertificateModalProps {
  certData: any;
  onClose: () => void;
  showNotification: (msg: string, type?: "info" | "success" | "error" | "warning") => void;
}

export function PrivilegeCertificateModal({ certData, onClose, showNotification }: PrivilegeCertificateModalProps) {
  if (!certData) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleCopyHash = () => {
    if (certData.cryptographic_signature) {
      navigator.clipboard.writeText(certData.cryptographic_signature);
      showNotification("HMAC cryptographic signature copied to clipboard!", "success");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-2xl bg-zinc-950 border border-zinc-800 rounded-3xl p-6 md:p-8 shadow-2xl relative space-y-6 max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-900 transition cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3.5 border-b border-zinc-850 pb-5">
          <div className="p-3 bg-emerald-950/40 border border-emerald-900/60 text-emerald-400 rounded-2xl">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">Privilege & Air-Gap Isolation Certificate</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                100% AIR-GAPPED
              </span>
            </div>
            <p className="text-xs text-zinc-400">Cryptographically verifiable attestation of zero-cloud legal confidentiality.</p>
          </div>
        </div>

        {/* Certificate Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-850 space-y-1">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block font-bold">Certificate ID</span>
            <span className="font-mono font-semibold text-zinc-200">{certData.certificate_id}</span>
          </div>
          <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-850 space-y-1">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block font-bold">Issued At</span>
            <span className="font-mono text-zinc-300">{new Date(certData.generated_at).toLocaleString()}</span>
          </div>
          <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-850 space-y-1">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block font-bold">Licensed Advocate</span>
            <span className="font-mono text-emerald-400 font-medium">{certData.licensed_advocate}</span>
          </div>
          <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-850 space-y-1">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block font-bold">Local Loopback Binding</span>
            <span className="font-mono text-zinc-300">{certData.workstation_environment?.local_binding}</span>
          </div>
        </div>

        {/* Isolation Verification Items */}
        <div className="space-y-2.5">
          <h4 className="text-xs font-mono text-zinc-400 font-bold uppercase tracking-wider">Verified Security Controls</h4>
          <div className="space-y-2 text-xs">
            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-zinc-900/30 border border-zinc-850/80">
              <WifiOff className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-zinc-200 block">External Egress Zero-Traffic Attestation</strong>
                <p className="text-zinc-400 text-[11px] mt-0.5">{certData.inference_isolation?.external_egress_traffic} — No outbound network packets transmitted during AI inference.</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-zinc-900/30 border border-zinc-850/80">
              <HardDrive className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-zinc-200 block">Encrypted SQLite FTS5 Local Storage</strong>
                <p className="text-zinc-400 text-[11px] mt-0.5">{certData.cryptographic_storage?.encryption_at_rest}</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-zinc-900/30 border border-zinc-850/80">
              <Cpu className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-zinc-200 block">Hardware Inference Isolation</strong>
                <p className="text-zinc-400 text-[11px] mt-0.5">Model execution runs strictly in device memory sandbox ({certData.workstation_environment?.hostname} / {certData.workstation_environment?.architecture}).</p>
              </div>
            </div>
          </div>
        </div>

        {/* Formal Legal Attestation Text */}
        <div className="p-3.5 rounded-xl bg-zinc-900/60 border border-zinc-800 text-zinc-300 text-xs leading-relaxed">
          <p className="italic font-serif">"{certData.attestation}"</p>
          <div className="mt-2 text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
            Legal Framework: {certData.legal_basis}
          </div>
        </div>

        {/* Cryptographic Signature */}
        <div className="p-3 rounded-xl bg-black border border-zinc-850 flex items-center justify-between text-xs font-mono">
          <div className="truncate pr-3">
            <span className="text-[10px] text-zinc-500 block uppercase font-bold">HMAC-SHA256 Digital Seal</span>
            <span className="text-zinc-400 truncate block text-[11px]">{certData.cryptographic_signature}</span>
          </div>
          <button
            onClick={handleCopyHash}
            className="px-2.5 py-1 text-[11px] bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded-lg border border-zinc-800 transition shrink-0 cursor-pointer"
          >
            Copy Seal
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={handlePrint}
            className="px-4 py-2 text-xs font-medium bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-800 rounded-xl transition flex items-center gap-1.5 cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" /> Print / Save PDF
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold bg-white hover:bg-zinc-200 text-black rounded-xl transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
