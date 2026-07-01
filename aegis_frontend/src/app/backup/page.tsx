"use client";

import React from "react";
import { BackupTab } from "../../components/BackupTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function BackupPage() {
  const showNotification = useAppStore(state => state.showNotification);

  return (
    <BackupTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      showNotification={showNotification}
    />
  );
}
