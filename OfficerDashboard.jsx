import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { AlertTriangle, Users, ClipboardList, Gauge } from "lucide-react";
import AppShell from "../components/AppShell";
import { KpiCard } from "../components/KpiCard";
import { dashboardSummary, runBatchAssessment } from "../api/client";

const LEVEL_COLORS = { Low: "#0E8C7F", Moderate: "#C98A1E", High: "#E07A3F", Critical: "#B4453C" };

export default function OfficerDashboard() {
  const [summary, setSummary] = useState(null);
  const [rescoring, setRescoring] = useState(false);

  async function load() {
    const res = await dashboardSummary();
    setSummary(res.data);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRescore() {
    setRescoring(true);
    try {
      await runBatchAssessment();
      await load();
    } finally {
      setRescoring(false);
    }
  }

  if (!summary) {
    return (
      <AppShell>
        <p className="text-sm text-slate-400">Loading dashboard...</p>
      </AppShell>
    );
  }

  const riskData = Object.entries(summary.risk_distribution).map(([level, count]) => ({ level, count }));
  const statusData = Object.entries(summary.intervention_status_counts).map(([status, count]) => ({ status, count }));

  return (
    <AppShell>
      <header className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aegis-navy tracking-tight">Welfare Intelligence Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Organization-level welfare risk overview · synthetic data</p>
        </div>
        <button
          onClick={handleRescore}
          disabled={rescoring}
          className="text-sm font-medium bg-white border border-slate-200 hover:border-aegis-teal hover:text-aegis-teal text-aegis-slate px-4 py-2 rounded-lg shadow-card transition-colors disabled:opacity-60"
        >
          {rescoring ? "Re-scoring..." : "Run batch risk assessment"}
        </button>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Personnel monitored" value={summary.total_personnel} accent="navy" />
        <KpiCard label="High-risk cases" value={summary.high_risk_count} accent="amber" />
        <KpiCard label="Critical-risk cases" value={summary.critical_risk_count} accent="rose" />
        <KpiCard label="Pending interventions" value={summary.pending_interventions} accent="teal" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <KpiCard label="Average risk score" value={summary.average_risk_score} sub="out of 100" accent="navy" />
        <KpiCard label="Anomaly alerts" value={summary.anomaly_alert_count} sub="deviating from historical pattern" accent="amber" />
        <KpiCard label="Dominant trend" value={summary.stress_trend} accent="teal" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Gauge size={16} className="text-aegis-teal" />
            <h2 className="font-semibold text-aegis-navy">Risk distribution</h2>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={riskData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
              <XAxis dataKey="level" tick={{ fontSize: 12, fill: "#7A8699" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#7A8699" }} />
              <Tooltip />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {riskData.map((d) => (
                  <Cell key={d.level} fill={LEVEL_COLORS[d.level]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <ClipboardList size={16} className="text-aegis-teal" />
            <h2 className="font-semibold text-aegis-navy">Intervention status</h2>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={statusData} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: "#7A8699" }} />
              <YAxis type="category" dataKey="status" width={130} tick={{ fontSize: 11, fill: "#7A8699" }} />
              <Tooltip />
              <Bar dataKey="count" fill="#0E1B2C" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {summary.anomaly_alert_count > 0 && (
        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-xl p-5 flex gap-3">
          <AlertTriangle size={20} className="text-aegis-amber shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-aegis-amber mb-1">
              {summary.anomaly_alert_count} anomaly {summary.anomaly_alert_count === 1 ? "alert" : "alerts"} detected
            </h3>
            <p className="text-sm text-aegis-slate leading-relaxed">
              These personnel show patterns that deviate unusually from historical organizational
              norms. Review them on the Risk Priority Board.
            </p>
          </div>
        </div>
      )}
    </AppShell>
  );
}
