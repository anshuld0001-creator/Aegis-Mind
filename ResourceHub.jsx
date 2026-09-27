import React from "react";
import { Phone, BookOpen, Users, Moon, AlertCircle } from "lucide-react";
import AppShell from "../components/AppShell";

const RESOURCES = [
  {
    icon: Phone,
    title: "Confidential counselling line",
    body: "Speak with an authorized welfare counsellor. Available in English and Hindi.",
    tag: "Support contact",
  },
  {
    icon: Users,
    title: "Peer support groups",
    body: "Unit-level peer support circles, coordinated through your welfare officer.",
    tag: "Community",
  },
  {
    icon: Moon,
    title: "Sleep & recovery guidance",
    body: "Practical guidance on managing shift-work sleep disruption and recovery routines.",
    tag: "Self-care",
  },
  {
    icon: BookOpen,
    title: "Stress-management library",
    body: "Short guides on workload pacing, breathing techniques, and burnout prevention.",
    tag: "Education",
  },
];

export default function ResourceHub() {
  return (
    <AppShell>
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-aegis-navy tracking-tight">Wellness Resource Hub</h1>
        <p className="text-sm text-slate-500 mt-1">
          Support that's available to you, independent of your check-in history.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {RESOURCES.map((r) => (
          <div key={r.title} className="bg-white rounded-xl border border-slate-200 shadow-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-9 h-9 rounded-lg bg-aegis-tealLight flex items-center justify-center">
                <r.icon size={18} className="text-aegis-teal" />
              </div>
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{r.tag}</span>
            </div>
            <h3 className="font-semibold text-aegis-navy mb-1.5">{r.title}</h3>
            <p className="text-sm text-slate-500 leading-relaxed">{r.body}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 bg-rose-50 border border-rose-200 rounded-xl p-5 flex gap-3">
        <AlertCircle size={20} className="text-aegis-rose shrink-0 mt-0.5" />
        <div>
          <h3 className="text-sm font-semibold text-aegis-rose mb-1">In an emergency</h3>
          <p className="text-sm text-aegis-slate leading-relaxed">
            If you or someone around you is in immediate distress, contact your unit's emergency
            support line or nearest medical officer right away. This platform is a preventive
            welfare tool — it does not replace emergency care.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
