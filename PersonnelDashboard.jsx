import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { HeartPulse, Moon, Battery, Briefcase, Smile, CheckCircle2 } from "lucide-react";
import AppShell from "../components/AppShell";
import { RiskBadge, TrendTag } from "../components/Badges";
import { useAuth } from "../context/AuthContext";
import {
  submitCheckin,
  myCheckinHistory,
  runRiskAssessment,
  latestRisk,
} from "../api/client";

const FIELDS = [
  { key: "stress_level", label: "Stress level", icon: HeartPulse, help: "1 = very low, 5 = very high" },
  { key: "mood", label: "Mood", icon: Smile, help: "1 = very low, 5 = very good" },
  { key: "sleep_quality", label: "Sleep quality", icon: Moon, help: "1 = very poor, 5 = excellent" },
  { key: "fatigue_level", label: "Fatigue", icon: Battery, help: "1 = fully rested, 5 = exhausted" },
  { key: "perceived_workload", label: "Perceived workload", icon: Briefcase, help: "1 = very light, 5 = overwhelming" },
];

// Extended answers use the existing JSON field; existing model scales stay unchanged.
const EXTRA_FIELDS = [
  { key: "duty_hours_per_day", label: "Duty hours / day", min: 0, max: 24, step: 0.5, initial: 9, decimals: 2 },
  { key: "consecutive_duty_days", label: "Consecutive duty days", min: 0, max: 90, step: 1, initial: 5 },
  { key: "night_shifts_per_month", label: "Night shifts / month", min: 0, max: 31, step: 1, initial: 3 },
  { key: "days_since_last_leave", label: "Days since last leave", min: 0, max: 365, step: 1, initial: 12 },
  { key: "average_sleep_hours", label: "Average sleep hours", min: 0, max: 24, step: 0.25, initial: 7.5, decimals: 2 },
  { key: "deployment_intensity", label: "Deployment intensity", min: 1, max: 10, step: 1, initial: 4, help: "1 = very low, 10 = very high" },
  { key: "peer_family_support", label: "Peer/family support", min: 1, max: 10, step: 1, initial: 8, help: "1 = very low, 10 = very strong" },
];

export default function PersonnelDashboard() {
  const { auth } = useAuth();
  const [form, setForm] = useState({
    stress_level: 3, mood: 3, sleep_quality: 3, fatigue_level: 3, perceived_workload: 3,
  });
  const [extraInputs, setExtraInputs] = useState(() =>
    Object.fromEntries(EXTRA_FIELDS.map((field) => [field.key, field.initial]))
  );
  const [includeWellness, setIncludeWellness] = useState(true);
  const [history, setHistory] = useState([]);
  const [risk, setRisk] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function loadHistory() {
    const res = await myCheckinHistory();
    setHistory(res.data.slice().reverse());
  }

  async function loadRisk() {
    try {
      const res = await latestRisk(auth.personnelCode);
      setRisk(res.data);
    } catch {
      setRisk(null);
    }
  }

  useEffect(() => {
    loadHistory();
    loadRisk();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    // No check-in or risk request is sent when the user opts out.
    if (!includeWellness || loading) return;
    setLoading(true);
    try {
      await submitCheckin({
        ...form,
        questionnaire_json: {
          ...extraInputs,
          include_wellness_checkin: true,
        },
      });
      await runRiskAssessment(auth.personnelCode);
      await loadHistory();
      await loadRisk();
      setSubmitted(true);
      setTimeout(() => setSubmitted(false), 3500);
    } finally {
      setLoading(false);
    }
  }

  const chartData = history.map((h) => ({
    date: new Date(h.submitted_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    Stress: h.stress_level,
    Fatigue: h.fatigue_level,
    Sleep: h.sleep_quality,
  }));

  return (
    <AppShell>
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-aegis-navy tracking-tight">Wellness Check-in</h1>
        <p className="text-sm text-slate-500 mt-1">
          Your responses are voluntary and confidential. They feed the early-warning system only —
          no automated decision is ever taken on your record without human review.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-card p-6">
          <h2 className="font-semibold text-aegis-navy mb-5">How are you doing today?</h2>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-5">
              {EXTRA_FIELDS.map((f) => (
                <div key={f.key}>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <label htmlFor={f.key} className="text-sm font-medium text-aegis-slate">
                      {f.label}
                    </label>
                    <output htmlFor={f.key} className="text-sm font-semibold text-aegis-teal">
                      {f.decimals ? extraInputs[f.key].toFixed(f.decimals) : extraInputs[f.key]}
                    </output>
                  </div>
                  <input
                    id={f.key}
                    type="range"
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    value={extraInputs[f.key]}
                    onChange={(e) => setExtraInputs((prev) => ({ ...prev, [f.key]: Number(e.target.value) }))}
                    className="w-full accent-aegis-teal"
                    aria-describedby={`${f.key}-help`}
                  />
                  <div id={`${f.key}-help`} className="text-[11px] text-slate-400">
                    {f.help || `${f.min}–${f.max}`}
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-slate-200 pt-5">
              <label className="flex items-center gap-2 text-sm font-medium text-aegis-slate">
                <input
                  type="checkbox"
                  checked={includeWellness}
                  disabled={loading}
                  onChange={(e) => setIncludeWellness(e.target.checked)}
                  className="h-4 w-4 accent-aegis-teal"
                />
                Include voluntary wellness check-in
              </label>
              {!includeWellness && (
                <p className="mt-2 text-xs text-slate-500" role="status">
                  Check-in paused. Nothing will be submitted unless you choose to include the wellness check-in.
                </p>
              )}
            </div>

            {includeWellness && FIELDS.map((f) => (
              <div key={f.key}>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor={f.key} className="flex items-center gap-2 text-sm font-medium text-aegis-slate">
                    <f.icon size={16} className="text-aegis-teal" />
                    {f.label}
                  </label>
                  <span className="text-xs text-slate-400">{f.help}</span>
                </div>
                <input
                  id={f.key}
                  type="range"
                  min={1}
                  max={5}
                  value={form[f.key]}
                  onChange={(e) => setForm({ ...form, [f.key]: Number(e.target.value) })}
                  className="w-full accent-aegis-teal"
                />
                <div className="flex justify-between text-[11px] text-slate-400 px-0.5">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <span key={n} className={form[f.key] === n ? "text-aegis-teal font-semibold" : ""}>{n}</span>
                  ))}
                </div>
              </div>
            ))}

            <button
              type="submit"
              disabled={loading || !includeWellness}
              className="w-full bg-aegis-navy hover:bg-aegis-navyLight text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-60"
            >
              {loading ? "Submitting..." : "Submit check-in"}
            </button>

            {submitted && (
              <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
                <CheckCircle2 size={16} />
                Check-in received. Thank you for sharing.
              </div>
            )}
          </form>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5">
            <h3 className="text-sm font-semibold text-aegis-navy mb-3">Your latest indicator</h3>
            {risk ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <RiskBadge level={risk.risk_level} />
                  <TrendTag trend={risk.trend} />
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  This is a supportive indicator, not a diagnosis. A welfare officer reviews any
                  elevated result before any action is recommended to you.
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Submit your first check-in to see an indicator here.</p>
            )}
          </div>

          <div className="bg-aegis-tealLight rounded-xl p-5">
            <h3 className="text-sm font-semibold text-aegis-navy mb-2">Need to talk to someone now?</h3>
            <p className="text-xs text-aegis-slate leading-relaxed">
              Visit the Resource Hub for confidential counselling and support contacts available to you.
            </p>
          </div>
        </div>
      </div>

      {chartData.length > 1 && (
        <div className="mt-6 bg-white rounded-xl border border-slate-200 shadow-card p-6">
          <h2 className="font-semibold text-aegis-navy mb-4">Your wellness trend</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#7A8699" }} />
              <YAxis domain={[1, 5]} tick={{ fontSize: 12, fill: "#7A8699" }} />
              <Tooltip />
              <Line type="monotone" dataKey="Stress" stroke="#B4453C" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Fatigue" stroke="#C98A1E" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Sleep" stroke="#0E8C7F" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </AppShell>
  );
}