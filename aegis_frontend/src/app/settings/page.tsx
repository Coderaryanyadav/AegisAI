"use client";

import React from "react";
import { SettingsTab } from "../../components/SettingsTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function SettingsPage() {
  const currentUser = useAppStore(state => state.currentUser);
  const showNotification = useAppStore(state => state.showNotification);
  const lang = useAppStore(state => state.lang);
  const setLang = useAppStore(state => state.setLang);

  return (
    <SettingsTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      showNotification={showNotification}
      currentUser={currentUser}
      lang={lang}
      setLang={setLang}
    />
  );
}
