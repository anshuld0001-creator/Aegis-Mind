import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, LineChart, Line } from "recharts";
import { X, ShieldCheck, PlusCircle } from "lucide-react";
import AppShell from "../components/AppShell";
import { RiskBadge, TrendTag } from "../components/Badges";
import {
  listCases,
  latestRisk,
  riskHistory,
  listInterventions,
  updateCaseStatus,
  logIntervention,
} from "../api/client";

const STATUSES = ["New", "Under Review", "Recommendation Made", "Intervention Completed", "Follow-up Due", "Resolved"];

export default function CaseBoard() {
  const [cases, setCases] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState(null);

  async function load() {
    const res = await listCases(statusFilter || undefined);
    setCases(res.data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  return (
    <AppShell>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aegis-navy tracking-tight">Risk Priority Board</h1>
          <p className="text-sm text-slate-500 mt-1">Authorized view only. Never used for public ranking of personnel.</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white shadow-card"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </header>

      <div className="bg-white rounded-xl border border-slate-200 shadow-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-400">
              <th className="px-5 py-3 font-semibold">Priority</th>
              <th className="px-5 py-3 font-semibold">Personnel</th>
              <th className="px-5 py-3 font-semibold">Risk score</th>
              <th className="px-5 py-3 font-semibold">Level</th>
              <th className="px-5 py-3 font-semibold">Confidence</th>
              <th className="px-5 py-3 font-semibold">Trend</th>
              <th className="px-5 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr
                key={c.id}
                onClick={() => setSelected(c)}
                className="border-t border-slate-100 hover:bg-aegis-tealLight/40 cursor-pointer transition-colors"
              >
                <td className="px-5 py-3 font-mono-data font-semibold text-aegis-navy">P{c.priority}</td>
                <td className="px-5 py-3 font-mono-data text-aegis-slate">{c.personnel_code}</td>
                <td className="px-5 py-3 font-mono-data font-semibold">{c.risk_score ?? "—"}</td>
                <td className="px-5 py-3"><RiskBadge level={c.risk_level} /></td>
                <td className="px-5 py-3 text-slate-500">{c.confidence ? `${Math.round(c.confidence * 100)}%` : "—"}</td>
                <td className="px-5 py-3"><TrendTag trend={c.trend} /></td>
                <td className="px-5 py-3 text-slate-600">{c.status}</td>
              </tr>
            ))}
            {cases.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-slate-400 text-sm">No cases match this filter.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <CaseDetail
          caseItem={selected}
          onClose={() => setSelected(null)}
          onUpdated={() => { load(); }}
        />
      )}
    </AppShell>
  );
}

function CaseDetail({ caseItem, onClose, onUpdated }) {
  const [factors, setFactors] = useState([]);
  const [history, setHistory] = useState([]);
  const [interventions, setInterventions] = useState([]);
  const [status, setStatus] = useState(caseItem.status);
  const [actionTaken, setActionTaken] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  async function loadAll() {
    try {
      const r = await latestRisk(caseItem.personnel_code);
      setFactors(
        r.data.contributing_factors
          .slice()
          .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
      );
    } catch { /* no-op */ }
    try {
      const h = await riskHistory(caseItem.personnel_code);
      setHistory(h.data.map((d) => ({
        date: new Date(d.assessed_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        risk: d.risk_score,
      })));
    } catch { /* no-op */ }
    try {
      const iv = await listInterventions(caseItem.id);
      setInterventions(iv.data);
    } catch { /* no-op */ }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseItem.id]);

  async function handleStatusSave() {
    setSaving(true);
    try {
      await updateCaseStatus(caseItem.id, { status });
      onUpdated();
    } finally {
      setSaving(false);
    }
  }

  async function handleLogIntervention(e) {
    e.preventDefault();
    if (!actionTaken.trim()) return;
    setSaving(true);
    try {
      await logIntervention(caseItem.id, { action_taken: actionTaken, notes });
      setActionTaken("");
      setNotes("");
      await loadAll();
      onUpdated();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-aegis-navy/40 flex justify-end z-50" onClick={onClose}>
      <div className="w-full max-w-xl bg-aegis-sand h-full overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-xs text-slate-400 font-mono-data">{caseItem.personnel_code}</p>
            <h2 className="text-xl font-bold text-aegis-navy">Case #{caseItem.id}</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-500">
            <X size={20} />
          </button>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 mb-5">
          <div className="flex items-center gap-3 mb-3">
            <RiskBadge level={caseItem.risk_level} />
            <TrendTag trend={caseItem.trend} />
            <span className="text-xs text-slate-400 ml-auto">Confidence {Math.round((caseItem.confidence || 0) * 100)}%</span>
          </div>
          <p className="text-3xl font-bold font-mono-data text-aegis-navy">{caseItem.risk_score}<span className="text-base text-slate-400 font-normal">/100</span></p>
          <p className="text-sm text-slate-500 mt-2">{caseItem.recommended_action}</p>
        </div>

        {factors.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 mb-5">
            <h3 className="text-sm font-semibold text-aegis-navy mb-3">Main contributing factors (explainable AI)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={factors} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
                <XAxis type="number" tick={{ fontSize: 11, fill: "#7A8699" }} />
                <YAxis type="category" dataKey="feature" width={150} tick={{ fontSize: 10, fill: "#7A8699" }} />
                <Tooltip />
                <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
                  {factors.map((f, i) => (
                    <Cell key={i} fill={f.impact > 0 ? "#B4453C" : "#0E8C7F"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="text-[11px] text-slate-400 mt-2">Red bars increase risk, teal bars reduce it (SHAP contribution).</p>
          </div>
        )}

        {history.length > 1 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 mb-5">
            <h3 className="text-sm font-semibold text-aegis-navy mb-3">Risk score trend</h3>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#7A8699" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#7A8699" }} />
                <Tooltip />
                <Line type="monotone" dataKey="risk" stroke="#0E1B2C" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 mb-5">
          <h3 className="text-sm font-semibold text-aegis-navy mb-3">Case status</h3>
          <div className="flex gap-2">
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2"
            >
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <button
              onClick={handleStatusSave}
              disabled={saving || status === caseItem.status}
              className="flex items-center gap-1.5 text-sm font-medium bg-aegis-navy text-white px-4 py-2 rounded-lg disabled:opacity-40"
            >
              <ShieldCheck size={15} /> Save
            </button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Status changes are attributed to your account and recorded in the audit log. All final decisions remain human-made.
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5">
          <h3 className="text-sm font-semibold text-aegis-navy mb-3">Intervention log</h3>
          <div className="space-y-3 mb-4">
            {interventions.length === 0 && <p className="text-xs text-slate-400">No interventions logged yet.</p>}
            {interventions.map((iv) => (
              <div key={iv.id} className="border border-slate-100 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-aegis-navy">{iv.action_taken}</span>
                  <span className="text-[11px] text-slate-400">{new Date(iv.logged_at).toLocaleDateString()}</span>
                </div>
                {iv.notes && <p className="text-xs text-slate-500">{iv.notes}</p>}
                {iv.outcome && <p className="text-[11px] text-aegis-teal mt-1">Outcome: {iv.outcome}</p>}
              </div>
            ))}
          </div>

          <form onSubmit={handleLogIntervention} className="space-y-2 border-t border-slate-100 pt-4">
            <input
              type="text"
              placeholder="Action taken (e.g. Welfare officer review scheduled)"
              value={actionTaken}
              onChange={(e) => setActionTaken(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2"
              required
            />
            <textarea
              placeholder="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2"
              rows={2}
            />
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-1.5 text-sm font-medium bg-aegis-teal text-white px-4 py-2 rounded-lg disabled:opacity-40"
            >
              <PlusCircle size={15} /> Log intervention
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
