import React, { createContext, useContext, useState, useCallback } from "react";
import { login as apiLogin, getMe } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem("aegis_token");
    const role = localStorage.getItem("aegis_role");
    const personnelCode = localStorage.getItem("aegis_personnel_code");
    const username = localStorage.getItem("aegis_username");
    return token ? { token, role, personnelCode, username } : null;
  });

  const login = useCallback(async (username, password) => {
    const res = await apiLogin(username, password);
    const { access_token, role, personnel_code } = res.data;
    localStorage.setItem("aegis_token", access_token);
    localStorage.setItem("aegis_role", role);
    localStorage.setItem("aegis_username", username);
    if (personnel_code) localStorage.setItem("aegis_personnel_code", personnel_code);
    setAuth({ token: access_token, role, personnelCode: personnel_code, username });
    return role;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("aegis_token");
    localStorage.removeItem("aegis_role");
    localStorage.removeItem("aegis_personnel_code");
    localStorage.removeItem("aegis_username");
    setAuth(null);
  }, []);

  return (
    <AuthContext.Provider value={{ auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
