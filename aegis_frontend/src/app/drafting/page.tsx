"use client";

import React from "react";
import { DraftingTab } from "../../components/DraftingTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function DraftingPage() {
  const currentUser = useAppStore(state => state.currentUser);
  const selectedModel = useAppStore(state => state.selectedModel);
  const showNotification = useAppStore(state => state.showNotification);
  
  const exportToPDF = async () => {};

  return (
    <DraftingTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      showNotification={showNotification}
      currentUser={currentUser}
      selectedModel={selectedModel}
      exportToPDF={exportToPDF}
    />
  );
}
