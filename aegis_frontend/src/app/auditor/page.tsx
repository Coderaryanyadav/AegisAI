"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { AuditorTab } from "../../components/AuditorTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function AuditorPage() {
  const currentUser = useAppStore(state => state.currentUser);
  const selectedMatter = useAppStore(state => state.selectedMatter);
  const selectedModel = useAppStore(state => state.selectedModel);
  const showNotification = useAppStore(state => state.showNotification);

  const { data: documents = [] } = useQuery({
    queryKey: ["documents", selectedMatter?.id],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/documents?matter_id=${selectedMatter?.id}`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch documents");
    },
    enabled: !!selectedMatter
  });

  // Export to PDF mock helper
  const exportToPDF = async () => {};

  return (
    <AuditorTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      showNotification={showNotification}
      selectedMatter={selectedMatter}
      documents={documents}
      currentUser={currentUser}
      selectedModel={selectedModel}
      exportToPDF={exportToPDF}
    />
  );
}
