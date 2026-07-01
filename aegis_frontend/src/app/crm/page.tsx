"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { CrmTab } from "../../components/CrmTab";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function CrmPage() {
  const { data: clients = [], refetch: fetchClients } = useQuery({
    queryKey: ["clients"],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/clients`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch clients");
    }
  });

  return (
    <CrmTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      clients={clients}
      fetchClients={() => { fetchClients(); return Promise.resolve(); }}
    />
  );
}
