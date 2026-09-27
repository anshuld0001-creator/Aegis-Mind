import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Users, ShieldAlert, ClipboardCheck, TrendingUp } from "lucide-react";
import AppShell from "../components/AppShell";
import { KpiCard } from "../components/KpiCard";
import { dashboardSummary } from "../api/client";

const LEVEL_COLORS = { Low: "#0E8C7F", Moderate: "#C98A1E", High: "#E07A3F", Critical: "#B4453C" };

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    dashboardSummary().then((res) => setSummary(res.data));
  }, []);

  if (!summary) {
    return <AppShell><p className="text-sm text-slate-400">Loading...</p></AppShell>;
  }

  const riskData = Object.entries(summary.risk_distribution).map(([level, count]) => ({ level, count }));

  return (
    <AppShell>
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-aegis-navy tracking-tight">Organization Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">Aggregate, de-identified welfare indicators across the monitored organization.</p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Total personnel" value={summary.total_personnel} accent="navy" />
        <KpiCard label="Avg. risk score" value={summary.average_risk_score} accent="teal" />
        <KpiCard label="Pending interventions" value={summary.pending_interventions} accent="amber" />
        <KpiCard label="Anomaly alerts" value={summary.anomaly_alert_count} accent="rose" />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-card p-6 mb-6">
        <h2 className="font-semibold text-aegis-navy mb-4">Organization-wide risk distribution</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={riskData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
            <XAxis dataKey="level" tick={{ fontSize: 12, fill: "#7A8699" }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#7A8699" }} />
            <Tooltip />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {riskData.map((d) => <Cell key={d.level} fill={LEVEL_COLORS[d.level]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 flex items-start gap-3">
          <Users size={18} className="text-aegis-teal mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-aegis-navy">Data quality</p>
            <p className="text-xs text-slate-500 mt-1">All records synthetic/demo, clearly labeled, pseudonymous personnel IDs only.</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 flex items-start gap-3">
          <ShieldAlert size={18} className="text-aegis-amber mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-aegis-navy">Governance</p>
            <p className="text-xs text-slate-500 mt-1">Every access is written to the audit log. No automated disciplinary action is possible.</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 flex items-start gap-3">
          <ClipboardCheck size={18} className="text-aegis-navy mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-aegis-navy">Human-in-the-loop</p>
            <p className="text-xs text-slate-500 mt-1">Recommendations always route through welfare-officer review before any action.</p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
