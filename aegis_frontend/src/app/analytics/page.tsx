"use client";

import React from "react";
import { AnalyticsTab } from "../../components/AnalyticsTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";

export default function AnalyticsPage() {
  return (
    <AnalyticsTab
      API_BASE={API_BASE}
      fetchWithAuth={fetchWithAuth}
    />
  );
}
