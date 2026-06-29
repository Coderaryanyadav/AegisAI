import React from "react";
import { Shield, Lock } from "lucide-react";

interface LoginViewProps {
  email: string;
  setEmail: (val: string) => void;
  password: string;
  setPassword: (val: string) => void;
  isRegisterMode: boolean;
  setIsRegisterMode: (val: boolean) => void;
  twoFactorRequired: boolean;
  totpCode: string;
  setTotpCode: (val: string) => void;
  handleLogin: (e: React.FormEvent) => void;
  handleRegister: (e: React.FormEvent) => void;
}

export function LoginView({
  email,
  setEmail,
  password,
  setPassword,
  isRegisterMode,
  setIsRegisterMode,
  twoFactorRequired,
  totpCode,
  setTotpCode,
  handleLogin,
  handleRegister
}: LoginViewProps) {
  return (
    <div className="min-h-screen flex items-center justify-center relative p-4 bg-[#030303] overflow-hidden bg-radial-glow">
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-zinc-800/10 opacity-30 blur-[130px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-zinc-800/15 opacity-20 blur-[130px]" />
      
      <div className="w-full max-w-md glass-panel p-8 rounded-2xl animate-fade-in z-10 shadow-2xl relative border border-zinc-850">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-[1px] bg-gradient-to-r from-transparent via-zinc-400/40 to-transparent" />
        
        <div className="flex flex-col items-center mb-8">
          <div className="p-3.5 bg-zinc-950 border border-zinc-800/80 rounded-2xl mb-3 shadow-inner relative animate-pulse-glow">
            <Shield className="w-8 h-8 text-white filter drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white premium-gradient-text">AegisAI</h1>
          <p className="text-xs font-semibold text-zinc-400 mt-1 uppercase tracking-widest font-mono">Offline Security Vault</p>
        </div>

        <form onSubmit={isRegisterMode ? handleRegister : handleLogin} className="space-y-5">
          <div>
            <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Advocate Email Address</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="advocate@firm.local"
              className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500 font-medium bg-zinc-950 border border-zinc-805"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Master Security PIN / Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500 bg-zinc-950 border border-zinc-805"
              required
            />
          </div>

          {twoFactorRequired && (
            <div>
              <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Two-Factor Authentication Code (TOTP)</label>
              <input 
                type="text" 
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="Enter 6-digit code"
                className="w-full p-3 rounded-lg glass-input text-zinc-200 text-sm focus:border-zinc-500 font-medium bg-zinc-950 border border-zinc-805"
                required
              />
            </div>
          )}

          <button 
            type="submit" 
            className="w-full py-3 bg-white hover:bg-zinc-200 text-black font-semibold rounded-lg text-sm transition-all duration-300 transform active:scale-[0.99] shadow-lg shadow-white/5 cursor-pointer flex items-center justify-center gap-2 font-bold"
          >
            <Lock className="w-4 h-4" />
            {isRegisterMode ? "Create Desktop Account" : twoFactorRequired ? "Verify Code & Enter" : "Access Security Vault"}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-zinc-900 flex flex-col space-y-3.5 text-center">
          <button 
            onClick={() => setIsRegisterMode(!isRegisterMode)}
            className="text-xs text-zinc-400 hover:text-zinc-200 transition font-medium cursor-pointer"
          >
            {isRegisterMode ? "Already registered? Sign in here" : "Need to initialize first client? Register here"}
          </button>
        </div>
        
        <div className="mt-6 text-center">
          <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest bg-zinc-900/50 px-2.5 py-1 rounded-full border border-zinc-900">
            🔒 Local Device Sandbox: 100% Encrypted
          </span>
        </div>
      </div>
    </div>
  );
}
