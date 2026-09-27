import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const HOME_BY_ROLE = {
  personnel: "/personnel",
  welfare_officer: "/officer",
  administrator: "/admin",
};

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const role = await login(username, password);
      navigate(HOME_BY_ROLE[role] || "/login");
    } catch (err) {
      setError(
        err?.response?.data?.detail || "Incorrect username or password."
      );
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(role) {
    const creds = {
      personnel: ["personnel1", "Personnel@123"],
      welfare_officer: ["officer1", "Officer@123"],
      administrator: ["admin1", "Admin@123"],
    }[role];
    setUsername(creds[0]);
    setPassword(creds[1]);
  }

  return (
    <div className="min-h-screen bg-aegis-navy flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-aegis-teal/15 mb-4">
            <Shield size={28} className="text-aegis-teal" strokeWidth={2} />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AEGIS MIND</h1>
          <p className="text-sm text-white/50 mt-1">Predictive Welfare Intelligence for Those Who Serve.</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-aegis-slate mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aegis-teal focus:border-transparent text-sm"
                placeholder="e.g. officer1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-aegis-slate mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aegis-teal focus:border-transparent text-sm"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 text-sm text-aegis-rose bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                <ShieldAlert size={16} className="mt-0.5 shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-aegis-navy hover:bg-aegis-navyLight text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-60"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-slate-100">
            <p className="text-xs text-slate-400 mb-2.5">Demo access (synthetic data only)</p>
            <div className="flex gap-2">
              <button onClick={() => fillDemo("personnel")} className="flex-1 text-xs font-medium py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-aegis-slate transition-colors">
                Personnel
              </button>
              <button onClick={() => fillDemo("welfare_officer")} className="flex-1 text-xs font-medium py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-aegis-slate transition-colors">
                Welfare Officer
              </button>
              <button onClick={() => fillDemo("administrator")} className="flex-1 text-xs font-medium py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-aegis-slate transition-colors">
                Administrator
              </button>
            </div>
          </div>
        </div>

        <p className="text-center text-[11px] text-white/30 mt-6 leading-relaxed">
          Prototype for SIH 2026 · PS ID 26186 · Ministry of Home Affairs / Uniformed Forces<br />
          AI-assisted preventive personnel welfare and early intervention — human review required for all decisions.
        </p>
      </div>
    </div>
  );
}
