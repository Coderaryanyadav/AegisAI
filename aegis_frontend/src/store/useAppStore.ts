import { create } from 'zustand';

interface User {
  id: number;
  email: string;
  role: string;
}

interface NotificationType {
  message: string;
  type: "success" | "error" | "info" | "warning";
}

interface AppState {
  token: string;
  setToken: (token: string) => void;
  
  currentUser: User | null;
  setCurrentUser: (user: User | null) => void;
  
  activeTab: string;
  setActiveTab: (tab: string) => void;

  selectedClient: any | null;
  setSelectedClient: (client: any | null) => void;

  selectedMatter: any | null;
  setSelectedMatter: (matter: any | null) => void;

  notification: NotificationType | null;
  showNotification: (message: string, type?: "info" | "success" | "error" | "warning") => void;
  clearNotification: () => void;

  isOnlineMode: boolean;
  setIsOnlineMode: (online: boolean) => void;

  lang: "en" | "hi";
  setLang: (lang: "en" | "hi") => void;

  selectedModel: string;
  setSelectedModel: (model: string) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("aegis_token") || "" : "",
  setToken: (token) => set({ token }),
  
  currentUser: null,
  setCurrentUser: (user) => set({ currentUser: user }),
  
  activeTab: "dashboard",
  setActiveTab: (tab) => set({ activeTab: tab }),

  selectedClient: null,
  setSelectedClient: (client) => set({ selectedClient: client }),

  selectedMatter: null,
  setSelectedMatter: (matter) => set({ selectedMatter: matter }),

  notification: null,
  clearNotification: () => set({ notification: null }),
  showNotification: (message, type = "info") => {
    set({ notification: { message, type } });
    setTimeout(() => {
      if (get().notification?.message === message) {
        set({ notification: null });
      }
    }, 5000);
  },

  isOnlineMode: false,
  setIsOnlineMode: (online) => set({ isOnlineMode: online }),

  lang: (typeof window !== "undefined" ? (localStorage.getItem("aegis_lang") as "en" | "hi") : "en") || "en",
  setLang: (lang) => {
    if (typeof window !== "undefined") localStorage.setItem("aegis_lang", lang);
    set({ lang });
  },

  selectedModel: "deepseek-r1:8b",
  setSelectedModel: (model) => set({ selectedModel: model }),
}));
