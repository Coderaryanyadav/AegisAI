"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User } from "../types";

interface AuthContextType {
    token: string;
    setToken: (token: string) => void;
    currentUser: User | null;
    setCurrentUser: (user: User | null) => void;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [token, setTokenState] = useState<string>("");
    const [currentUser, setCurrentUser] = useState<User | null>(null);

    useEffect(() => {
        if (typeof window !== "undefined") {
            const savedToken = localStorage.getItem("aegis_token");
            if (savedToken) {
                setTokenState(savedToken);
            }
        }
    }, []);

    const setToken = (newToken: string) => {
        setTokenState(newToken);
        if (typeof window !== "undefined") {
            localStorage.setItem("aegis_token", newToken);
        }
    };

    const logout = () => {
        setTokenState("");
        setCurrentUser(null);
        if (typeof window !== "undefined") {
            localStorage.removeItem("aegis_token");
        }
    };

    return (
        <AuthContext.Provider value={{ token, setToken, currentUser, setCurrentUser, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};
