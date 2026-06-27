"use client";

import React, { useState, useEffect } from "react";

interface SettingsTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  currentUser: any;
  setCurrentUser: (user: any) => void;
  lang: "en" | "hi";
  setLang: (lang: "en" | "hi") => void;
  upcomingAlerts: any[];
}

export function SettingsTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  currentUser,
  setCurrentUser,
  lang,
  setLang,
  upcomingAlerts
}: SettingsTabProps) {
  // Local 2FA states
  const [twoFaEnabled, setTwoFaEnabled] = useState(false);
  const [twoFaQr, setTwoFaQr] = useState("");
  const [twoFaSecret, setTwoFaSecret] = useState("");
  const [twoFaCode, setTwoFaCode] = useState("");
  const [twoFaLoading, setTwoFaLoading] = useState(false);

  // Local Firm Settings states
  const [firmName, setFirmName] = useState(currentUser?.firm_name || "");
  const [firmLogo, setFirmLogo] = useState(currentUser?.firm_logo || "");
  const [gstRate, setGstRate] = useState(currentUser?.gst_rate !== undefined ? currentUser.gst_rate : 18.0);



  const check2FAStatus = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/2fa/status`);
      if (res.ok) { 
        const d = await res.json(); 
        setTwoFaEnabled(d.enabled); 
      }
    } catch {}
  };

  const handle2FASetup = async () => {
    setTwoFaLoading(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/2fa/setup`, { method: "POST" });
      if (res.ok) {
        const d = await res.json();
        setTwoFaQr(d.qr_code_base64);
        setTwoFaSecret(d.secret);
      } else { 
        showNotification("2FA setup failed", "error"); 
      }
    } catch (e: any) { 
      showNotification(e.message, "error"); 
    } finally { 
      setTwoFaLoading(false); 
    }
  };

  const handle2FAEnable = async () => {
    if (!twoFaCode) return;
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/2fa/enable`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ totp_code: twoFaCode })
      });
      if (res.ok) {
        setTwoFaEnabled(true);
        setTwoFaQr("");
        setTwoFaCode("");
        showNotification("2FA enabled successfully!", "success");
      } else { 
        showNotification("Invalid TOTP code", "error"); 
      }
    } catch (e: any) { 
      showNotification(e.message, "error"); 
    }
  };

  const handleSaveFirmSettings = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/user/firm-settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ firm_name: firmName, firm_logo: firmLogo, gst_rate: gstRate })
      });
      if (res.ok) {
        showNotification("Firm configuration saved successfully!", "success");
        setCurrentUser({ ...currentUser, firm_name: firmName, firm_logo: firmLogo, gst_rate: gstRate });
      } else {
        showNotification("Failed to save firm configuration", "error");
      }
    } catch (e: any) {
      showNotification(e.message, "error");
    }
  };

  useEffect(() => {
    check2FAStatus();
  }, []);

  useEffect(() => {
    if (currentUser) {
      setFirmName(currentUser.firm_name || "");
      setFirmLogo(currentUser.firm_logo || "");
      setGstRate(currentUser.gst_rate !== undefined ? currentUser.gst_rate : 18.0);
    }
  }, [currentUser]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-zinc-400">Security settings, language preferences, and system configuration.</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-zinc-200">Two-Factor Authentication</h3>
            <span className={`text-[10px] px-2 py-0.5 rounded border font-bold ${twoFaEnabled ? "text-emerald-400 border-emerald-800 bg-emerald-950/30" : "text-zinc-500 border-zinc-700"}`}>{twoFaEnabled ? "ENABLED" : "DISABLED"}</span>
          </div>
          <p className="text-xs text-zinc-400">Protect your account with Google Authenticator or any TOTP app.</p>
          {!twoFaEnabled && (
            <>
              <button onClick={handle2FASetup} disabled={twoFaLoading} className="w-full py-2 bg-violet-800 hover:bg-violet-700 text-white font-semibold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer">
                {twoFaLoading ? "Setting up..." : "Set Up 2FA"}
              </button>
              {twoFaQr && (
                <div className="space-y-3">
                  <p className="text-xs text-zinc-300">Scan this QR code with your authenticator app:</p>
                  <img src={`data:image/png;base64,${twoFaQr}`} alt="2FA QR Code" className="w-40 h-40 rounded-lg border border-zinc-700 mx-auto" />
                  <p className="text-[10px] text-zinc-505 text-center font-mono break-all">Manual key: {twoFaSecret}</p>
                  <input value={twoFaCode} onChange={e => setTwoFaCode(e.target.value)} placeholder="Enter 6-digit code"
                    className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200 font-mono tracking-widest text-center bg-zinc-950 border border-zinc-805" maxLength={6} />
                  <button onClick={handle2FAEnable} disabled={twoFaCode.length !== 6} className="w-full py-2 bg-emerald-800 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer">
                    Verify &amp; Enable 2FA
                  </button>
                </div>
              )}
            </>
          )}
          {twoFaEnabled && <div className="p-3 bg-emerald-950/30 border border-emerald-900/40 rounded-xl text-xs text-emerald-303">2FA is active and protecting your account.</div>}
        </div>
        <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
          <h3 className="text-sm font-bold text-zinc-200">Language / भाषा</h3>
          <div className="flex gap-3">
            <button onClick={() => { setLang("en"); localStorage.setItem("aegis_lang","en"); }} className={`flex-1 py-3 rounded-xl text-sm font-semibold border transition cursor-pointer ${lang === "en" ? "bg-zinc-100 text-zinc-900 border-zinc-300" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"}`}>English</button>
            <button onClick={() => { setLang("hi"); localStorage.setItem("aegis_lang","hi"); }} className={`flex-1 py-3 rounded-xl text-sm font-semibold border transition cursor-pointer ${lang === "hi" ? "bg-zinc-100 text-zinc-900 border-zinc-300" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"}`}>हिन्दी</button>
          </div>
        </div>
        <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-3">
          <h3 className="text-sm font-bold text-zinc-200">Hearing Alerts</h3>
          <p className="text-xs text-zinc-400">Desktop notifications for hearings within 48 hours.</p>
          <p className="text-[11px] text-zinc-500 font-mono">Upcoming (next 48h): {upcomingAlerts.length}</p>
          {upcomingAlerts.slice(0, 3).map((a) => (
            <div key={a.id} className="flex justify-between items-center text-xs p-2 bg-amber-955/20 border border-amber-900/30 rounded-lg">
              <span className="text-amber-300 font-medium">{a.title}</span>
              <span className="text-zinc-500 font-mono">{new Date(a.target_date).toLocaleDateString("en-IN")}</span>
            </div>
          ))}
        </div>
        <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-3">
          <h3 className="text-sm font-bold text-zinc-200">Account Info</h3>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between p-2 bg-zinc-950/60 rounded-lg"><span className="text-zinc-500">Email</span><span className="text-zinc-202">{currentUser?.email}</span></div>
            <div className="flex justify-between p-2 bg-zinc-950/60 rounded-lg"><span className="text-zinc-505">Role</span><span className="text-zinc-202 capitalize">{currentUser?.role}</span></div>
            <div className="flex justify-between p-2 bg-zinc-950/60 rounded-lg"><span className="text-zinc-505">2FA</span><span className={twoFaEnabled ? "text-emerald-400" : "text-zinc-405"}>{twoFaEnabled ? "Enabled" : "Disabled"}</span></div>
          </div>
        </div>
        
        <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
          <h3 className="text-sm font-bold text-zinc-200">Custom Firm Letterhead</h3>
          <p className="text-xs text-zinc-400">Configure logo and title displayed on all generated PDFs &amp; Invoices.</p>
          
          <div className="space-y-3 text-xs">
            <div>
              <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Firm / Advocate Name</label>
              <input 
                type="text" 
                value={firmName} 
                onChange={(e) => setFirmName(e.target.value)} 
                placeholder="e.g. Chambers of Aryan Yadav"
                className="w-full p-2.5 rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
              />
            </div>
            
            <div>
              <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">GST Rate (%)</label>
              <input 
                type="number" 
                value={gstRate} 
                onChange={(e) => setGstRate(parseFloat(e.target.value) || 0)} 
                placeholder="18"
                min="0"
                max="100"
                step="0.01"
                className="w-full p-2.5 rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
              />
            </div>
            
            <div>
              <label className="block text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider font-mono">Firm Logo (PNG / JPG)</label>
              <input 
                type="file" 
                accept="image/*"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                      if (event.target?.result) {
                        setFirmLogo(event.target.result as string);
                      }
                    };
                    reader.readAsDataURL(file);
                  }
                }}
                className="w-full text-xs text-zinc-400 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-800 file:text-zinc-202 hover:file:bg-zinc-700 cursor-pointer"
              />
            </div>
            
            {firmLogo && (
              <div className="space-y-1">
                <span className="text-[10px] text-zinc-500 font-bold block uppercase font-mono">Logo Preview</span>
                <div className="p-2 bg-zinc-950/60 rounded-lg inline-block">
                  <img src={firmLogo} alt="Logo preview" className="h-12 w-auto object-contain rounded" />
                </div>
              </div>
            )}
            
            <button 
              onClick={handleSaveFirmSettings}
              className="w-full py-2 bg-violet-800 hover:bg-violet-750 text-white font-bold rounded-lg transition text-xs cursor-pointer"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
