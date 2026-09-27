import React, { useState } from "react";
import { Activity, CheckCircle2, HeartHandshake, Loader2 } from "lucide-react";
import AppShell from "../components/AppShell";
import { mitraQuickStressCheck, mitraRequestConsultant } from "../api/client";

const QUESTIONS = [
  { key: "stress_level", label: "How stressed do you feel?", low: "Calm", high: "Overwhelmed" },
  { key: "sleep_quality", label: "How was your sleep?", low: "Very poor", high: "Restful" },
  { key: "fatigue_level", label: "How tired do you feel?", low: "Rested", high: "Exhausted" },
  { key: "perceived_workload", label: "How manageable is your workload?", low: "Light", high: "Overwhelming" },
  { key: "mood", label: "How is your mood?", low: "Very low", high: "Very good" },
];

export default function StressDashboard() {
  const [form, setForm] = useState({ stress_level: 3, sleep_quality: 3, fatigue_level: 3, perceived_workload: 3, mood: 3 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [requested, setRequested] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setRequested(false);
    try {
      const res = await mitraQuickStressCheck(form);
      setResult(res.data);
    } finally { setLoading(false); }
  }

  async function requestHuman() {
    await mitraRequestConsultant();
    setRequested(true);
  }

  const levelStyle = result?.stress_level === "Very High" || result?.stress_level === "High"
    ? "text-aegis-rose bg-rose-50 border-rose-200" : result?.stress_level === "Moderate"
      ? "text-aegis-amber bg-amber-50 border-amber-200" : "text-aegis-teal bg-teal-50 border-teal-200";

  return <AppShell>
    <header className="mb-7">
      <div className="flex items-center gap-2"><Activity className="text-aegis-teal" size={23} /><h1 className="text-2xl font-bold text-aegis-navy">Quick Stress Check</h1></div>
      <p className="text-sm text-slate-500 mt-1">Answer five simple questions. Your personal stress result appears immediately.</p>
    </header>
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <form onSubmit={submit} className="lg:col-span-3 bg-white rounded-xl border border-slate-200 shadow-card p-6 space-y-6">
        {QUESTIONS.map((q) => <div key={q.key}>
          <div className="flex justify-between gap-3 mb-2"><label className="text-sm font-medium text-aegis-slate">{q.label}</label><span className="font-mono-data text-aegis-teal text-sm">{form[q.key]}/5</span></div>
          <input className="w-full accent-aegis-teal" type="range" min="1" max="5" value={form[q.key]} onChange={(e) => setForm({ ...form, [q.key]: Number(e.target.value) })} />
          <div className="flex justify-between text-[11px] text-slate-400"><span>{q.low}</span><span>{q.high}</span></div>
        </div>)}
        <button disabled={loading} className="w-full py-3 bg-aegis-navy text-white font-medium rounded-lg disabled:opacity-50 flex justify-center items-center gap-2">
          {loading ? <><Loader2 size={16} className="animate-spin" /> Calculating…</> : "See my stress result"}
        </button>
        <p className="text-[11px] text-slate-400 text-center">This supportive self-check is not a medical or clinical diagnosis.</p>
      </form>
      <aside className="lg:col-span-2 space-y-4">
        {result ? <div className="bg-white rounded-xl border border-slate-200 shadow-card p-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Your current result</p>
          <p className="mt-2 text-4xl font-bold font-mono-data text-aegis-navy">{Math.round(result.stress_score)}<span className="text-base font-normal text-slate-400">/100</span></p>
          <span className={`inline-block mt-3 px-3 py-1 rounded-full border text-sm font-semibold ${levelStyle}`}>{result.stress_level} stress</span>
          <p className="text-sm text-slate-600 leading-relaxed mt-4">{result.headline}</p>
          <h2 className="text-sm font-semibold text-aegis-navy mt-5 mb-2">What may help now</h2>
          <ul className="space-y-2">{result.recommendations.map((tip) => <li key={tip} className="text-xs text-slate-600 flex gap-2"><CheckCircle2 size={14} className="text-aegis-teal shrink-0" />{tip}</li>)}</ul>
          {(result.needs_human_follow_up || requested) && <div className="mt-5 rounded-lg bg-aegis-tealLight p-3 text-xs text-aegis-slate">{requested ? "Your human follow-up request has been logged." : "A confidential human follow-up is available if you would like one."}</div>}
          {!requested && <button onClick={requestHuman} className="mt-5 w-full py-2.5 rounded-lg border border-aegis-teal text-aegis-teal text-sm font-medium flex justify-center gap-2"><HeartHandshake size={16} />Talk to a human</button>}
        </div> : <div className="bg-aegis-tealLight rounded-xl p-6"><p className="font-semibold text-aegis-navy">Private, immediate feedback</p><p className="text-sm text-aegis-slate mt-2">Your score and supportive next steps will show here after you submit.</p></div>}
        <div className="bg-white rounded-xl border border-slate-200 p-5"><p className="text-sm font-semibold text-aegis-navy">Human support contacts</p><p className="text-xs text-slate-500 mt-2">Personal contact: <a className="text-aegis-teal font-medium" href="tel:6306664667">6306664667</a></p><p className="text-xs text-slate-500 mt-1">Dr Saxena: <a className="text-aegis-teal font-medium" href="tel:9453745228">9453745228</a></p><p className="text-xs text-slate-500 mt-1">Dr Shefali: <a className="text-aegis-teal font-medium" href="tel:52255225">52255225</a></p><p className="text-[11px] text-slate-400 mt-3">Welfare Officer support is routed through the approved toll-free/local line configured by your organization.</p></div>
      </aside>
    </div>
  </AppShell>;
}
