import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Info } from "lucide-react";
import AppShell from "../components/AppShell";
import { KpiCard } from "../components/KpiCard";
import { modelPerformance } from "../api/client";

export default function ModelMonitoring() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    modelPerformance().then((res) => setMetrics(res.data));
  }, []);

  if (!metrics) {
    return <AppShell><p className="text-sm text-slate-400">Loading...</p></AppShell>;
  }

  if (!metrics.available) {
    return (
      <AppShell>
        <p className="text-sm text-slate-500">{metrics.message}</p>
      </AppShell>
    );
  }

  const importanceData = Object.entries(metrics.feature_importance || {})
    .map(([feature, value]) => ({ feature, value }))
    .sort((a, b) => b.value - a.value);

  const [[tn, fp], [fn, tp]] = metrics.confusion_matrix;

  return (
    <AppShell>
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-aegis-navy tracking-tight">Model Monitoring</h1>
        <p className="text-sm text-slate-500 mt-1">Offline evaluation of the stress-risk classifier on held-out synthetic data.</p>
      </header>

      <div className="flex items-start gap-3 bg-aegis-tealLight rounded-xl p-4 mb-6">
        <Info size={18} className="text-aegis-teal shrink-0 mt-0.5" />
        <p className="text-sm text-aegis-slate leading-relaxed">{metrics.note}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Accuracy" value={`${Math.round(metrics.accuracy * 100)}%`} accent="navy" />
        <KpiCard label="Precision" value={`${Math.round(metrics.precision * 100)}%`} accent="teal" />
        <KpiCard label="Recall" value={`${Math.round(metrics.recall * 100)}%`} accent="amber" />
        <KpiCard label="F1 score" value={metrics.f1_score} accent="rose" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-6">
          <h2 className="font-semibold text-aegis-navy mb-4">Confusion matrix</h2>
          <div className="grid grid-cols-2 gap-3 text-center">
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
              <p className="text-2xl font-bold font-mono-data text-emerald-700">{tn}</p>
              <p className="text-xs text-slate-500 mt-1">True negatives</p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-2xl font-bold font-mono-data text-amber-700">{fp}</p>
              <p className="text-xs text-slate-500 mt-1">False positives</p>
            </div>
            <div className="bg-rose-50 border border-rose-200 rounded-lg p-4">
              <p className="text-2xl font-bold font-mono-data text-rose-700">{fn}</p>
              <p className="text-xs text-slate-500 mt-1">False negatives</p>
            </div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
              <p className="text-2xl font-bold font-mono-data text-emerald-700">{tp}</p>
              <p className="text-xs text-slate-500 mt-1">True positives</p>
            </div>
          </div>
          <div className="mt-4 flex justify-between text-xs text-slate-500">
            <span>False positive rate: <b>{Math.round(metrics.false_positive_rate * 100)}%</b></span>
            <span>False negative rate: <b>{Math.round(metrics.false_negative_rate * 100)}%</b></span>
          </div>
          <p className="text-[11px] text-slate-400 mt-3">
            n_train={metrics.n_train} · n_test={metrics.n_test}
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-6">
          <h2 className="font-semibold text-aegis-navy mb-4">Global feature importance</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={importanceData} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#7A8699" }} />
              <YAxis type="category" dataKey="feature" width={150} tick={{ fontSize: 10, fill: "#7A8699" }} />
              <Tooltip />
              <Bar dataKey="value" fill="#0E8C7F" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </AppShell>
  );
}
