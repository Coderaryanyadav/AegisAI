"use client";

import React, { useState, useEffect } from "react";
import { RefreshCw } from "lucide-react";

interface AnalyticsTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
}

export function AnalyticsTab({
  API_BASE,
  fetchWithAuth
}: AnalyticsTabProps) {
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/analytics/summary`);
      if (res.ok) {
        setAnalyticsData(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Practice Analytics</h1>
          <p className="text-sm text-zinc-400">Revenue trends, matter status, and upcoming hearings at a glance.</p>
        </div>
        <button 
          onClick={fetchAnalytics} 
          className="px-3 py-2 text-xs border border-zinc-700 rounded-lg text-zinc-305 hover:bg-zinc-800 transition flex items-center gap-1.5 cursor-pointer bg-zinc-950"
        >
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {analyticsLoading && <div className="text-center text-xs text-zinc-400 animate-pulse py-8">Loading analytics...</div>}
      
      {analyticsData && !analyticsLoading && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Total Clients", value: analyticsData.total_clients, color: "text-blue-400", icon: "👤" },
              { label: "Active Matters", value: analyticsData.open_matters, color: "text-emerald-400", icon: "⚖️" },
              { label: "Documents", value: analyticsData.total_documents, color: "text-violet-400", icon: "📄" },
              { label: "Total Revenue", value: `₹${analyticsData.total_revenue_inr?.toLocaleString("en-IN")}`, color: "text-amber-400", icon: "💰" },
            ].map((stat, i) => (
              <div key={i} className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-xl">
                <p className="text-2xl mb-1">{stat.icon}</p>
                <p className={`text-xl font-bold tabular-nums ${stat.color}`}>{stat.value}</p>
                <p className="text-[11px] text-zinc-505 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-xl space-y-3">
              <h3 className="text-sm font-bold text-zinc-200">Revenue Overview</h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between p-3 bg-emerald-955/30 border border-emerald-900/40 rounded-lg">
                  <span className="text-zinc-400">Collected Revenue</span>
                  <span className="text-emerald-400 font-bold">₹{analyticsData.total_revenue_inr?.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between p-3 bg-amber-955/30 border border-amber-900/40 rounded-lg">
                  <span className="text-zinc-400">Pending Invoices</span>
                  <span className="text-amber-400 font-bold">₹{analyticsData.pending_revenue_inr?.toLocaleString("en-IN")}</span>
                </div>
              </div>
              <h4 className="text-[10px] text-zinc-500 font-bold uppercase mt-2">Recent Invoices</h4>
              {analyticsData.recent_invoices?.map((inv: any) => (
                <div key={inv.id} className="flex justify-between items-center py-1.5 border-b border-zinc-800/50 text-xs">
                  <span className="text-zinc-300 font-mono">{inv.invoice_number}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-100">₹{inv.grand_total}</span>
                    <span className={`text-[9px] px-1 rounded ${inv.status === "paid" ? "text-emerald-400" : "text-amber-400"}`}>{inv.status}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="border border-zinc-800 bg-zinc-900/30 p-5 rounded-xl space-y-3">
              <h3 className="text-sm font-bold text-zinc-200">Hearings (Next 7 Days)</h3>
              {analyticsData.upcoming_hearings?.length === 0 && <p className="text-xs text-zinc-500 italic">No hearings in next 7 days.</p>}
              {analyticsData.upcoming_hearings?.map((h: any) => (
                <div key={h.id} className="p-3 bg-zinc-905 border border-zinc-805 rounded-lg flex justify-between items-start text-xs">
                  <div>
                    <p className="text-zinc-200 font-semibold">{h.title}</p>
                    <p className="text-zinc-505">{new Date(h.target_date).toLocaleDateString("en-IN", {weekday: "short", day: "numeric", month: "short"})}</p>
                  </div>
                  <span className="text-[9px] px-1.5 py-0.5 rounded border border-zinc-700 text-zinc-400 uppercase">{h.schedule_type}</span>
                </div>
              ))}
              <div className="pt-3 border-t border-zinc-800">
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 bg-zinc-950/60 rounded-lg"><p className="text-emerald-400 font-bold">{analyticsData.open_matters}</p><p className="text-zinc-505">Open</p></div>
                  <div className="p-2 bg-zinc-950/60 rounded-lg"><p className="text-amber-400 font-bold">{analyticsData.total_matters - analyticsData.open_matters - analyticsData.closed_matters}</p><p className="text-zinc-505">Pending</p></div>
                  <div className="p-2 bg-zinc-950/60 rounded-lg"><p className="text-zinc-400 font-bold">{analyticsData.closed_matters}</p><p className="text-zinc-505">Closed</p></div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
      {!analyticsData && !analyticsLoading && (
        <div className="text-center py-12">
          <button 
            onClick={fetchAnalytics} 
            className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm font-semibold transition cursor-pointer"
          >
            Load Analytics Dashboard
          </button>
        </div>
      )}
    </div>
  );
}
