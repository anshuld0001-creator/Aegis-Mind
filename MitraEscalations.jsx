import React, { useEffect, useState } from "react";
import { ShieldAlert, PhoneCall } from "lucide-react";
import AppShell from "../components/AppShell";
import { mitraListConsultantRequests, mitraUpdateConsultantRequest } from "../api/client";

const REASON_LABEL = {
  safety_flag: "Safety concern flagged by AI Mitra",
  user_requested: "User requested a human consultant",
  persistent_high_stress: "Persistent high stress/fatigue",
};

export default function MitraEscalations() {
  const [requests, setRequests] = useState([]);
  const [statusFilter, setStatusFilter] = useState("Pending");

  async function load() {
    const res = await mitraListConsultantRequests(statusFilter || undefined);
    setRequests(res.data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  async function handleUpdate(id, status) {
    await mitraUpdateConsultantRequest(id, status);
    load();
  }

  return (
    <AppShell>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aegis-navy tracking-tight">AI Mitra Escalations</h1>
          <p className="text-sm text-slate-500 mt-1">
            Human-in-the-loop follow-ups from the personal AI Mitra wellness companion.
          </p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white shadow-card"
        >
          <option value="">All statuses</option>
          <option value="Pending">Pending</option>
          <option value="Contacted">Contacted</option>
          <option value="Resolved">Resolved</option>
        </select>
      </header>

      <div className="space-y-3">
        {requests.map((r) => (
          <div key={r.id} className="bg-white rounded-xl border border-slate-200 shadow-card p-4 flex items-center justify-between">
            <div className="flex items-start gap-3">
              {r.reason === "safety_flag" ? (
                <ShieldAlert size={18} className="text-aegis-rose mt-0.5" />
              ) : (
                <PhoneCall size={18} className="text-aegis-teal mt-0.5" />
              )}
              <div>
                <p className="text-sm font-medium text-aegis-navy">
                  {REASON_LABEL[r.reason] || r.reason}
                </p>
                <p className="text-xs text-slate-400">
                  User #{r.user_id} · {new Date(r.created_at).toLocaleString()} · Status: {r.status}
                </p>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              {r.status !== "Contacted" && (
                <button
                  onClick={() => handleUpdate(r.id, "Contacted")}
                  className="text-xs font-medium bg-slate-100 hover:bg-slate-200 text-aegis-slate px-3 py-1.5 rounded-lg"
                >
                  Mark Contacted
                </button>
              )}
              {r.status !== "Resolved" && (
                <button
                  onClick={() => handleUpdate(r.id, "Resolved")}
                  className="text-xs font-medium bg-aegis-teal text-white px-3 py-1.5 rounded-lg"
                >
                  Mark Resolved
                </button>
              )}
            </div>
          </div>
        ))}
        {requests.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-10">No escalations match this filter.</p>
        )}
      </div>
    </AppShell>
  );
}
