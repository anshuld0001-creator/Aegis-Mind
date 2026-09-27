import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Shield, LogOut, HeartPulse, LayoutDashboard, ListChecks, BookOpen, Activity, Sparkles, PhoneCall, Gauge } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const NAV_BY_ROLE = {
  personnel: [
    { to: "/personnel", label: "Wellness Check-in", icon: HeartPulse, end: true },
    { to: "/mitra", label: "AI Mitra", icon: Sparkles },
    { to: "/stress-check", label: "Quick Stress Check", icon: Gauge },
    { to: "/personnel/resources", label: "Resource Hub", icon: BookOpen },
  ],
  welfare_officer: [
    { to: "/officer", label: "Welfare Dashboard", icon: LayoutDashboard, end: true },
    { to: "/officer/cases", label: "Risk Priority Board", icon: ListChecks },
    { to: "/officer/mitra-requests", label: "Mitra Escalations", icon: PhoneCall },
    { to: "/mitra", label: "AI Mitra", icon: Sparkles },
    { to: "/stress-check", label: "Quick Stress Check", icon: Gauge },
  ],
  administrator: [
    { to: "/admin", label: "Organization Analytics", icon: LayoutDashboard, end: true },
    { to: "/admin/model", label: "Model Monitoring", icon: Activity },
    { to: "/mitra", label: "AI Mitra", icon: Sparkles },
    { to: "/stress-check", label: "Quick Stress Check", icon: Gauge },
  ],
};

const ROLE_LABEL = {
  personnel: "Personnel",
  welfare_officer: "Welfare Officer",
  administrator: "Administrator",
};

export default function AppShell({ children }) {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();
  const items = NAV_BY_ROLE[auth?.role] || [];

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen flex bg-aegis-sand">
      <aside className="w-64 shrink-0 bg-aegis-navy text-white flex flex-col">
        <div className="px-5 py-6 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Shield size={22} className="text-aegis-teal" strokeWidth={2.2} />
            <span className="font-bold tracking-tight text-lg">AEGIS MIND</span>
          </div>
          <p className="text-[11px] text-white/50 mt-1 leading-snug">
            Predictive Welfare Intelligence for Those Who Serve
          </p>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-aegis-teal/15 text-aegis-teal"
                    : "text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <item.icon size={17} strokeWidth={2} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-white/10">
          <div className="px-3 pb-3">
            <p className="text-xs text-white/40">Signed in as</p>
            <p className="text-sm font-medium">{auth?.username}</p>
            <p className="text-[11px] text-aegis-teal">{ROLE_LABEL[auth?.role]}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-white/70 hover:bg-white/5 hover:text-white transition-colors"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <div className="max-w-6xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
