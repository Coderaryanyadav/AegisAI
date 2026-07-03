"use client";

import React, { useState, useEffect, useRef } from "react";
import { Trash2, Download } from "lucide-react";

const LANG: Record<string, Record<string, string>> = {
  en: { billing: "Billing & Invoices" },
  hi: { billing: "बिलिंग और चालान" }
};

interface BillingTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  currentUser: any;
  selectedClient: any;
  matters: any[];
  lang: "en" | "hi";
  exportToPDF: (title: string, content: string, firmName?: string, logoBase64?: string) => Promise<void>;
}

export function BillingTab({
  API_BASE,
  fetchWithAuth,
  showNotification,
  currentUser,
  selectedClient,
  matters,
  lang,
  exportToPDF
}: BillingTabProps) {
  const [billingMatterId, setBillingMatterId] = useState<number | null>(null);
  const [timeEntries, setTimeEntries] = useState<any[]>([]);
  const [newTimeEntry, setNewTimeEntry] = useState({ description: "", hours: "1", rate_per_hour: "5000", date: new Date().toISOString().split("T")[0] });
  const [invoices, setInvoices] = useState<any[]>([]);
  const [isCreatingInvoice, setIsCreatingInvoice] = useState(false);

  // Timer states local to component
  const [billingTimer, setBillingTimer] = useState<any>(null); // { start: number, running: boolean }
  const [timerSeconds, setTimerSeconds] = useState(0);
  const timerRef = useRef<any>(null);



  // Billing timer tick
  useEffect(() => {
    if (billingTimer?.running) {
      if (!timerRef.current) {
        timerRef.current = setInterval(() => setTimerSeconds(s => s + 1), 1000);
      }
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [billingTimer?.running]);

  const fetchTimeEntries = async (matterId: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/v1/billing/time-entries?matter_id=${matterId}`);
      if (res.ok) setTimeEntries(await res.json());
    } catch { }
  };

  const handleAddTimeEntry = async () => {
    if (!billingMatterId || !newTimeEntry.description) return;
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/v1/billing/time-entry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ matter_id: billingMatterId, ...newTimeEntry })
      });
      if (res.ok) {
        showNotification("Time entry logged", "success");
        fetchTimeEntries(billingMatterId);
        setNewTimeEntry({ description: "", hours: "1", rate_per_hour: "5000", date: new Date().toISOString().split("T")[0] });
      }
    } catch (e: any) {
      showNotification(e.message, "error");
    }
  };

  const handleDeleteTimeEntry = async (id: number) => {
    if (!confirm("Are you sure you want to delete this time entry?")) return;
    try {
      await fetchWithAuth(`${API_BASE}/api/v1/billing/time-entry/${id}`, { method: "DELETE" });
      showNotification("Time entry deleted.", "success");
      if (billingMatterId) fetchTimeEntries(billingMatterId);
    } catch (e: any) {
      showNotification(e.message || "Failed to delete time entry", "error");
    }
  };

  const handleGenerateInvoice = async () => {
    if (!billingMatterId || !selectedClient) return;
    setIsCreatingInvoice(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/v1/billing/invoice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: selectedClient.id, matter_id: billingMatterId })
      });
      if (res.ok) {
        const inv = await res.json();
        showNotification(`Invoice ${inv.invoice_number} generated!`, "success");
        fetchInvoices();
        // Auto PDF export
        exportToPDF(
          inv.invoice_number,
          `INVOICE\n${inv.invoice_number}\nClient: ${selectedClient?.name}\nTotal: ₹${inv.total_amount}\nGST (18%): ₹${inv.gst_amount}\nGrand Total: ₹${inv.grand_total}\nStatus: ${inv.status}\nDate: ${new Date().toLocaleDateString("en-IN")}`,
          currentUser?.firm_name,
          currentUser?.firm_logo
        );
      }
    } catch (e: any) {
      showNotification(e.message, "error");
    } finally {
      setIsCreatingInvoice(false);
    }
  };

  const fetchInvoices = async () => {
    try {
      const url = selectedClient ? `${API_BASE}/api/v1/billing/invoices?client_id=${selectedClient.id}` : `${API_BASE}/api/v1/billing/invoices`;
      const res = await fetchWithAuth(url);
      if (res.ok) setInvoices(await res.json());
    } catch { }
  };

  const startTimer = () => {
    setTimerSeconds(0);
    setBillingTimer({ running: true, start: Date.now() });
  };

  const stopTimer = () => {
    setBillingTimer((t: any) => ({ ...t, running: false }));
    const hours = (timerSeconds / 3600).toFixed(2);
    setNewTimeEntry(prev => ({ ...prev, hours }));
    showNotification(`Timer stopped: ${hours} hours logged`, "info");
  };

  const formatTimer = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const totalBillableAmount = timeEntries.reduce((s, e) => s + parseFloat(e.amount || 0), 0);

  useEffect(() => {
    setBillingMatterId(null);
    setTimeEntries([]);
    setInvoices([]);
    if (selectedClient) {
      fetchInvoices();
    }
  }, [selectedClient]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{LANG[lang]?.billing || LANG.en.billing}</h1>
        <p className="text-sm text-zinc-400">Track billable hours, generate GST-compliant invoices, and manage payments.</p>
      </div>
      {selectedClient && (
        <div className="flex gap-4 items-center flex-wrap">
          <select
            onChange={(e) => {
              const id = parseInt(e.target.value);
              setBillingMatterId(id || null);
              if (id) fetchTimeEntries(id);
            }}
            className="p-2 text-xs rounded-lg glass-input text-zinc-300 bg-zinc-950 border border-zinc-805"
          >
            <option value="">-- Select Matter for Billing --</option>
            {matters.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}
          </select>
          <button onClick={fetchInvoices} className="px-3 py-2 text-xs border border-zinc-700 rounded-lg text-zinc-300 hover:bg-zinc-800 transition cursor-pointer">Load Invoices</button>
        </div>
      )}
      {!selectedClient && <div className="p-4 border border-zinc-800 rounded-xl text-xs text-zinc-500">Select a client from Matters & Context tab first.</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {currentUser?.role !== "client" && (
          <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-zinc-200">⏱️ Time Tracker</h3>
            <div className="flex items-center gap-4 p-4 bg-zinc-955/60 border border-zinc-800 rounded-xl">
              <span className="text-2xl font-mono text-emerald-400 tabular-nums">{formatTimer(timerSeconds)}</span>
              <div className="flex gap-2">
                {!billingTimer?.running
                  ? <button onClick={startTimer} className="px-3 py-1.5 bg-emerald-800 hover:bg-emerald-700 text-white text-xs rounded-lg font-semibold transition cursor-pointer">▶ Start</button>
                  : <button onClick={stopTimer} className="px-3 py-1.5 bg-rose-800 hover:bg-rose-700 text-white text-xs rounded-lg font-semibold transition cursor-pointer">⏹ Stop</button>
                }
              </div>
            </div>
            <div className="space-y-2">
              <input
                value={newTimeEntry.description}
                onChange={e => setNewTimeEntry(p => ({ ...p, description: e.target.value }))}
                placeholder="Work description (e.g. Court appearance)"
                className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
              />
              <div className="grid grid-cols-3 gap-2">
                <input
                  value={newTimeEntry.hours}
                  onChange={e => setNewTimeEntry(p => ({ ...p, hours: e.target.value }))}
                  type="number"
                  step="0.5"
                  placeholder="Hours"
                  className="p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
                />
                <input
                  value={newTimeEntry.rate_per_hour}
                  onChange={e => setNewTimeEntry(p => ({ ...p, rate_per_hour: e.target.value }))}
                  type="number"
                  placeholder="₹ Rate/hr"
                  className="p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
                />
                <input
                  value={newTimeEntry.date}
                  onChange={e => setNewTimeEntry(p => ({ ...p, date: e.target.value }))}
                  type="date"
                  className="p-2 text-xs rounded-lg glass-input text-zinc-200 bg-zinc-950 border border-zinc-805"
                />
              </div>
              <button
                onClick={handleAddTimeEntry}
                disabled={!billingMatterId}
                className="w-full py-2 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-semibold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer"
              >
                + Log Time Entry
              </button>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {timeEntries.map((e) => (
                <div key={e.id} className="flex justify-between items-center p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg text-xs">
                  <div>
                    <p className="text-zinc-200 font-medium">{e.description}</p>
                    <p className="text-zinc-500">{e.date} &middot; {e.hours}h &times; ₹{e.rate_per_hour}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-emerald-400 font-mono">₹{e.amount}</span>
                    <button onClick={() => handleDeleteTimeEntry(e.id)} className="cursor-pointer">
                      <Trash2 className="w-3 h-3 text-zinc-600 hover:text-rose-400" />
                    </button>
                  </div>
                </div>
              ))}
              {timeEntries.length === 0 && <p className="text-xs text-zinc-500 italic text-center">No time entries yet.</p>}
            </div>
            <div className="flex justify-between text-xs text-zinc-400 font-semibold border-t border-zinc-800 pt-2">
              <span>Total Billable</span>
              <span className="text-zinc-100">₹{totalBillableAmount.toFixed(2)}</span>
            </div>
          </div>
        )}

        <div className={`border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4 ${currentUser?.role === "client" ? "lg:col-span-2" : ""}`}>
          {currentUser?.role !== "client" ? (
            <>
              <h3 className="text-sm font-bold text-zinc-200">🧾 Invoice Generator (GST 18%)</h3>
              <div className="p-4 bg-zinc-950/60 border border-zinc-800 rounded-xl space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-zinc-400">Subtotal</span><span>₹{totalBillableAmount.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-zinc-400">GST @ 18%</span><span className="text-amber-400">₹{(totalBillableAmount * 0.18).toFixed(2)}</span></div>
                <div className="flex justify-between border-t border-zinc-700 pt-2 font-bold"><span>Grand Total</span><span className="text-emerald-400">₹{(totalBillableAmount * 1.18).toFixed(2)}</span></div>
              </div>
              <button
                onClick={handleGenerateInvoice}
                disabled={isCreatingInvoice || !billingMatterId}
                className="w-full py-2.5 bg-emerald-800 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs transition disabled:opacity-50 cursor-pointer animate-pulse-glow"
              >
                {isCreatingInvoice ? "Generating..." : "📄 Generate Invoice + PDF"}
              </button>
            </>
          ) : (
            <div className="flex justify-between items-center border-b border-zinc-850 pb-2">
              <h3 className="text-sm font-bold text-zinc-200">Your Case Invoices</h3>
              <span className="text-[10px] text-zinc-500 font-mono">GST 18% INCLUDED</span>
            </div>
          )}

          <div className="space-y-2 max-h-[400px] overflow-y-auto pt-1">
            <h4 className="text-[10px] text-zinc-505 font-bold uppercase">All Invoices</h4>
            {invoices.map((inv) => (
              <div key={inv.id} className="flex justify-between items-center p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg text-xs hover:border-zinc-700 transition">
                <div>
                  <p className="text-zinc-200 font-mono font-semibold">{inv.invoice_number}</p>
                  <p className="text-zinc-505">{new Date(inv.created_at).toLocaleDateString("en-IN")}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-emerald-400 font-semibold">₹{inv.grand_total}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${inv.status === "paid" ? "bg-emerald-900/40 text-emerald-400 border border-emerald-800" : "bg-amber-900/40 text-amber-400 border border-amber-800"}`}>{inv.status.toUpperCase()}</span>
                  <button
                    onClick={() => {
                      exportToPDF(
                        inv.invoice_number,
                        `INVOICE\n${inv.invoice_number}\nTotal: ₹${inv.total_amount}\nGST (18%): ₹${inv.gst_amount}\nGrand Total: ₹${inv.grand_total}\nStatus: ${inv.status}\nDate: ${new Date(inv.created_at).toLocaleDateString("en-IN")}`,
                        currentUser?.firm_name,
                        currentUser?.firm_logo
                      );
                    }}
                    title="Download Invoice PDF"
                    className="text-zinc-400 hover:text-white p-1 ml-1 transition cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
            {invoices.length === 0 && <p className="text-xs text-zinc-500 italic text-center py-4">No invoices issued yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
