"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { DashboardTab } from "../../components/DashboardTab";
import { useAppStore } from "../../store/useAppStore";
import { fetchWithAuth } from "../../utils/api";
import { API_BASE } from "../../components/AppShell";
import { Document } from "../../types";
import { DocumentPreviewDrawer } from "../../components/DocumentPreviewDrawer";

export default function DashboardPage() {
  const currentUser = useAppStore(state => state.currentUser);
  const selectedClient = useAppStore(state => state.selectedClient);
  const setSelectedClient = useAppStore(state => state.setSelectedClient);
  const selectedMatter = useAppStore(state => state.selectedMatter);
  const setSelectedMatter = useAppStore(state => state.setSelectedMatter);
  const showNotification = useAppStore(state => state.showNotification);

  const { data: clients = [], refetch: fetchClients } = useQuery({
    queryKey: ["clients"],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/clients`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch clients");
    }
  });

  const { data: matters = [], refetch: fetchMatters } = useQuery({
    queryKey: ["matters", selectedClient?.id],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/matters?client_id=${selectedClient?.id}`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch matters");
    },
    enabled: !!selectedClient
  });

  const { data: schedules = [], refetch: fetchSchedules } = useQuery({
    queryKey: ["schedules", selectedMatter?.id],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/schedules?matter_id=${selectedMatter?.id}`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch schedules");
    },
    enabled: !!selectedMatter
  });

  const { data: documents = [], refetch: fetchDocuments } = useQuery({
    queryKey: ["documents", selectedMatter?.id],
    queryFn: async () => {
      const res = await fetchWithAuth(`${API_BASE}/api/documents?matter_id=${selectedMatter?.id}`);
      if (res.ok) return res.json();
      throw new Error("Failed to fetch documents");
    },
    enabled: !!selectedMatter
  });

  const fetchSystemStatus = async () => {};

  // Local state for preview drawer since it's just for this tab
  const [showPreviewModal, setShowPreviewModal] = React.useState(false);
  const [previewDoc, setPreviewDoc] = React.useState<Document | null>(null);
  const [previewText, setPreviewText] = React.useState("");
  const [previewLoading, setPreviewLoading] = React.useState(false);
  const [docAnnotations, setDocAnnotations] = React.useState<any[]>([]);
  const [annotationDocId, setAnnotationDocId] = React.useState<number | null>(null);

  const fetchAnnotations = async (docId: number) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/api/annotations/${docId}`);
      if (res.ok) setDocAnnotations(await res.json());
    } catch {}
  };

  const handleViewDocumentText = async (doc: Document) => {
    setPreviewDoc(doc);
    setPreviewText("");
    setShowPreviewModal(true);
    setPreviewLoading(true);
    setAnnotationDocId(doc.id);
    fetchAnnotations(doc.id);
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/documents/${doc.id}/text`);
      if (response.ok) {
        const data = await response.json();
        setPreviewText(data.text);
      } else {
        throw new Error("Failed to load text.");
      }
    } catch (err: any) {
      showNotification(err.message, "error");
      setShowPreviewModal(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <>
      <DashboardTab
        API_BASE={API_BASE}
        fetchWithAuth={fetchWithAuth}
        showNotification={showNotification}
        currentUser={currentUser}
        clients={clients}
        selectedClient={selectedClient}
        setSelectedClient={setSelectedClient}
        matters={matters}
        setMatters={() => {}}
        selectedMatter={selectedMatter}
        setSelectedMatter={setSelectedMatter}
        schedules={schedules}
        setSchedules={() => {}}
        documents={documents}
        setDocuments={() => {}}
        fetchMatters={() => { fetchMatters(); return Promise.resolve(); }}
        fetchSchedules={() => { fetchSchedules(); return Promise.resolve(); }}
        fetchDocuments={() => { fetchDocuments(); return Promise.resolve(); }}
        fetchSystemStatus={() => { fetchSystemStatus(); return Promise.resolve(); }}
        handleViewDocumentText={handleViewDocumentText}
      />
      {showPreviewModal && previewDoc && (
        <DocumentPreviewDrawer
          doc={previewDoc}
          text={previewText}
          onClose={() => setShowPreviewModal(false)}
          loading={previewLoading}
          annotations={docAnnotations}
          onSaveAnnotation={async (text, note, color) => {
            if (!annotationDocId) return;
            try {
              const res = await fetchWithAuth(`${API_BASE}/api/annotations`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ document_id: annotationDocId, selected_text: text, note, color })
              });
              if (res.ok) fetchAnnotations(annotationDocId);
            } catch {}
          }}
          onDeleteAnnotation={async (id) => {
            try {
              const res = await fetchWithAuth(`${API_BASE}/api/annotations/${id}`, { method: "DELETE" });
              if (res.ok && annotationDocId) fetchAnnotations(annotationDocId);
            } catch {}
          }}
        />
      )}
    </>
  );
}
