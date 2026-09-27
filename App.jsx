import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import PersonnelDashboard from "./pages/PersonnelDashboard";
import ResourceHub from "./pages/ResourceHub";
import OfficerDashboard from "./pages/OfficerDashboard";
import CaseBoard from "./pages/CaseBoard";
import AdminDashboard from "./pages/AdminDashboard";
import ModelMonitoring from "./pages/ModelMonitoring";
import AiMitra from "./pages/AiMitra";
import MitraEscalations from "./pages/MitraEscalations";
import StressDashboard from "./pages/StressDashboard";

const HOME_BY_ROLE = {
  personnel: "/personnel",
  welfare_officer: "/officer",
  administrator: "/admin",
};

function Protected({ roles, children }) {
  const { auth } = useAuth();
  if (!auth) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(auth.role)) return <Navigate to={HOME_BY_ROLE[auth.role]} replace />;
  return children;
}

function RootRedirect() {
  const { auth } = useAuth();
  if (!auth) return <Navigate to="/login" replace />;
  return <Navigate to={HOME_BY_ROLE[auth.role] || "/login"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route path="/personnel" element={<Protected roles={["personnel"]}><PersonnelDashboard /></Protected>} />
          <Route path="/personnel/resources" element={<Protected roles={["personnel"]}><ResourceHub /></Protected>} />
          <Route path="/stress-check" element={<Protected><StressDashboard /></Protected>} />

          <Route path="/officer" element={<Protected roles={["welfare_officer"]}><OfficerDashboard /></Protected>} />
          <Route path="/officer/cases" element={<Protected roles={["welfare_officer"]}><CaseBoard /></Protected>} />
          <Route path="/officer/mitra-requests" element={<Protected roles={["welfare_officer", "administrator"]}><MitraEscalations /></Protected>} />

          <Route path="/admin" element={<Protected roles={["administrator"]}><AdminDashboard /></Protected>} />
          <Route path="/admin/model" element={<Protected roles={["administrator"]}><ModelMonitoring /></Protected>} />

          <Route path="/mitra" element={<Protected><AiMitra /></Protected>} />

          <Route path="/" element={<RootRedirect />} />
          <Route path="*" element={<RootRedirect />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
