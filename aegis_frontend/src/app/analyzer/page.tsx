"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { AnalyzerTab } from "../../components/AnalyzerTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function AnalyzerPage() {
  const currentUser = useAppStore(state => state.currentUser);
  const selectedMatter = useAppStore(state => state.selectedMatter);
  const selectedModel = useAppStore(state => state.selectedModel);
  const showNotification = useAppStore(state => state.showNotification);
  const lang = useAppStore(state => state.lang);

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
  const exportToPDF = async () => {
    alert("PDF export requires jsPDF which should be included in page.tsx. Function available in Analyzer component.");
  };

  return (
    <AnalyzerTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      showNotification={showNotification}
      selectedMatter={selectedMatter}
      documents={documents}
      currentUser={currentUser}
      selectedModel={selectedModel}
      lang={lang}
      exportToPDF={exportToPDF}
    />
  );
}
