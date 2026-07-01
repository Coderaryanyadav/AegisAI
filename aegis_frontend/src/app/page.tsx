"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "../store/useAppStore";

export default function Home() {
  const router = useRouter();
  const token = useAppStore(state => state.token);

  useEffect(() => {
    // If the token exists, redirect to dashboard.
    // If not, AppShell will render the LoginView anyway.
    if (token) {
      router.replace("/dashboard");
    }
  }, [token, router]);

  return null; // AppShell handles the layout and login view.
}
