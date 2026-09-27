import React from "react";

export function KpiCard({ label, value, sub, accent = "teal" }) {
  const accentCls = {
    teal: "text-aegis-teal",
    rose: "text-aegis-rose",
    amber: "text-aegis-amber",
    navy: "text-aegis-navy",
  }[accent];

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5 flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</span>
      <span className={`text-3xl font-bold font-mono-data ${accentCls}`}>{value}</span>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
    </div>
  );
}
