"use client";

import React, { useState } from "react";
import { Trash2 } from "lucide-react";
import { ConflictChecker } from "./ConflictChecker";
import { ClientCard } from "./ClientCard";

import { useAppStore } from "../store/useAppStore";

interface CrmTabProps {
  API_BASE: string;
  fetchWithAuth: (url: string, options?: any) => Promise<any>;
  clients: any[];
  fetchClients: () => Promise<void>;
}

export function CrmTab({
  API_BASE,
  fetchWithAuth,
  clients,
  fetchClients
}: CrmTabProps) {
  const showNotification = useAppStore((state) => state.showNotification);
  const [newClient, setNewClient] = useState({ name: "", email: "", phone: "", notes: "" });
  const [isCreatingClient, setIsCreatingClient] = useState(false);

  // Conflict Checker local state
  const [checkConflictClient, setCheckConflictClient] = useState("");
  const [checkConflictOpponent, setCheckConflictOpponent] = useState("");
  const [conflictResult, setConflictResult] = useState<any>(null);
  const [isCheckingConflict, setIsCheckingConflict] = useState(false);

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClient.name.trim()) {
      showNotification("Client name is required", "error");
      return;
    }
    setIsCreatingClient(true);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/v1/clients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newClient)
      });
      if (response.ok) {
        showNotification("Client directory entry created", "success");
        setNewClient({ name: "", email: "", phone: "", notes: "" });
        fetchClients();
      } else {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to create client");
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to create client", "error");
    } finally {
      setIsCreatingClient(false);
    }
  };

  const handleDeleteClient = async (clientId: number) => {
    if (!confirm("Are you sure? This will permanently wipe this client and all associated case matters.")) return;
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/v1/clients/${clientId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        showNotification("Client record removed.");
        fetchClients();
      }
    } catch (err: any) {
      showNotification(err.message, "error");
    }
  };

  const handleCheckConflict = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!checkConflictClient.trim() || !checkConflictOpponent.trim()) {
      showNotification("Please enter both Prospective Client and Opponent Name", "error");
      return;
    }
    setIsCheckingConflict(true);
    setConflictResult(null);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/v1/matters/check-conflict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_name: checkConflictClient,
          opponent_name: checkConflictOpponent
        })
      });
      if (response.ok) {
        const data = await response.json();
        setConflictResult(data);
        if (data.conflict_detected) {
          showNotification(`Conflict detected: ${data.severity.toUpperCase()} severity`, "warning");
        } else {
          showNotification("No conflict of interest detected", "success");
        }
      } else {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to run conflict check");
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to connect to backend server for conflict check", "error");
    } finally {
      setIsCheckingConflict(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Client Directory CRM</h1>
        <p className="text-sm text-zinc-400">Writably encrypt new client profiles at rest in database.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left side sidebar column */}
        <div className="space-y-6">
          {/* Registration form */}
          <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-zinc-200">Register Client File</h3>
            <form onSubmit={handleCreateClient} className="space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Full Client Name</label>
                <input 
                  type="text" 
                  value={newClient.name}
                  onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
                  placeholder="Mr. Suresh Kumar"
                  className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                  required
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Email (Optional)</label>
                <input 
                  type="email" 
                  value={newClient.email}
                  onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                  placeholder="suresh@gmail.local"
                  className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Phone Number (Optional)</label>
                <input 
                  type="text" 
                  value={newClient.phone}
                  onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                  placeholder="+91 98765 43210"
                  className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1">Confidential Notes (AES-256 Encrypted)</label>
                <textarea 
                  value={newClient.notes}
                  onChange={(e) => setNewClient({ ...newClient, notes: e.target.value })}
                  placeholder="Enter highly sensitive remarks, fee parameters, or witness coordinates which will be encrypted..."
                  className="w-full p-2.5 text-xs rounded-lg glass-input text-zinc-200 h-24"
                />
              </div>
              <button 
                type="submit"
                className="w-full py-2.5 bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-medium rounded-lg text-xs shadow transition cursor-pointer"
                disabled={isCreatingClient}
              >
                Encrypt & Save Client
              </button>
            </form>
          </div>

          <ConflictChecker
            checkConflictClient={checkConflictClient}
            setCheckConflictClient={setCheckConflictClient}
            checkConflictOpponent={checkConflictOpponent}
            setCheckConflictOpponent={setCheckConflictOpponent}
            conflictResult={conflictResult}
            isCheckingConflict={isCheckingConflict}
            handleConflictCheck={() => handleCheckConflict()}
          />
        </div>

        {/* Directory list */}
        <div className="border border-zinc-800 bg-zinc-900/30 p-6 rounded-xl space-y-4 lg:col-span-2">
          <h3 className="text-sm font-bold text-zinc-200">Registered Directory Listings</h3>
          <div className="space-y-3">
            {clients.map(c => (
              <ClientCard key={c.id} client={c} onDelete={handleDeleteClient} />
            ))}
            {clients.length === 0 && (
              <div className="text-xs text-zinc-500 italic p-4 text-center">No client directories registered yet.</div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
