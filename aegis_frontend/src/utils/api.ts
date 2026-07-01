import { useAppStore } from "../store/useAppStore";
import { API_BASE } from "../components/AppShell";

export const fetchWithAuth = async (url: string, options: RequestInit = {}) => {
  const headers = (options.headers as Record<string, string>) || {};
  let token = useAppStore.getState().token;
  if (!token && typeof window !== "undefined") {
    token = localStorage.getItem("aegis_token") || "";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (response.status === 401) {
    const refreshToken = typeof window !== "undefined" ? localStorage.getItem("aegis_refresh_token") : null;
    if (refreshToken) {
      const refreshFormData = new URLSearchParams();
      refreshFormData.append("refresh_token", refreshToken);
      const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: refreshFormData.toString()
      });

      if (refreshResponse.ok) {
        const refreshData = await refreshResponse.json();
        if (typeof window !== "undefined") {
          localStorage.setItem("aegis_token", refreshData.access_token);
          localStorage.setItem("aegis_refresh_token", refreshData.refresh_token);
        }
        useAppStore.getState().setToken(refreshData.access_token);

        headers["Authorization"] = `Bearer ${refreshData.access_token}`;
        return fetch(url, { ...options, headers });
      }
    }

    if (typeof window !== "undefined") {
      localStorage.removeItem("aegis_token");
      localStorage.removeItem("aegis_refresh_token");
    }
    useAppStore.getState().setToken("");
    useAppStore.getState().setCurrentUser(null);
    throw new Error("Session expired. Please sign in again.");
  }

  return response;
};
