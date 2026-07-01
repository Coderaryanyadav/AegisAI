"use client";

import React from "react";
import { BillingTab } from "../../components/BillingTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function BillingPage() {
  const currentUser = useAppStore(state => state.currentUser);
  const showNotification = useAppStore(state => state.showNotification);

  return (
    <BillingTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
      showNotification={showNotification}
      currentUser={currentUser}
    />
  );
}
