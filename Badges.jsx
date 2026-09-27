import React from "react";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";

const LEVEL_STYLES = {
  Low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Moderate: "bg-amber-50 text-amber-700 border-amber-200",
  High: "bg-orange-50 text-orange-700 border-orange-200",
  Critical: "bg-rose-50 text-rose-700 border-rose-200",
};

export function RiskBadge({ level }) {
  const cls = LEVEL_STYLES[level] || "bg-slate-100 text-slate-600 border-slate-200";
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-md border text-xs font-semibold tracking-wide ${cls}`}>
      {level || "Unknown"}
    </span>
  );
}

export function TrendTag({ trend }) {
  const map = {
    Increasing: { icon: ArrowUp, cls: "text-rose-600" },
    Decreasing: { icon: ArrowDown, cls: "text-emerald-600" },
    Stable: { icon: Minus, cls: "text-slate-500" },
  };
  const { icon: Icon, cls } = map[trend] || map.Stable;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${cls}`}>
      <Icon size={14} strokeWidth={2.5} />
      {trend || "Stable"}
    </span>
  );
}
