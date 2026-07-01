"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { ResearchTab } from "../../components/ResearchTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function ResearchPage() {
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

  return (
    <ResearchTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      showNotification={showNotification}
      selectedMatter={selectedMatter}
      documents={documents}
      selectedModel={selectedModel}
    />
  );
}
