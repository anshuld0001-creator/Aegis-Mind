import React, { useEffect, useRef, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import {
  Send, Mic, MicOff, Volume2, VolumeX, ImagePlus, Sparkles, ShieldAlert,
  PhoneCall, Loader2, Heart,
} from "lucide-react";
import AppShell from "../components/AppShell";
import HeartRateCheck from "../components/HeartRateCheck";
import {
  mitraChat, mitraStartCheck, mitraAnswerCheck, mitraAnalyzeImage,
  mitraWeeklyReport, mitraHistory, mitraRequestConsultant,
} from "../api/client";

const WELCOME = {
  role: "ai",
  text: "Hello, I'm AI Mitra — your wellness companion. I can help you check your stress, fatigue, energy, sleep, mood and general wellness. You can type, speak, or share a relevant image. How are you feeling today?",
};

const STARTERS = ["I'm feeling stressed", "Help me sleep better", "I feel exhausted", "Start a wellness check"];

function ScoreBar({ label, value, invert }) {
  const good = invert ? 100 - value : value;
  const color = good >= 70 ? "#0E8C7F" : good >= 45 ? "#C98A1E" : "#B4453C";
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>{label}</span>
        <span className="font-mono-data">{Math.round(value)}/100</span>
      </div>
      <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

export default function AiMitra() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [mode, setMode] = useState("chat"); // "chat" | "wellness_check"
  const [sending, setSending] = useState(false);
  const [listening, setListening] = useState(false);
  const [speakEnabled, setSpeakEnabled] = useState(false);
  const [safetyActive, setSafetyActive] = useState(false);
  const [result, setResult] = useState(null);
  const [weekly, setWeekly] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHeartRate, setShowHeartRate] = useState(false);
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function loadReports() {
    try {
      const w = await mitraWeeklyReport();
      setWeekly(w.data);
    } catch { /* no-op */ }
    try {
      const h = await mitraHistory(14);
      setHistory(h.data.map((d) => ({
        date: new Date(d.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        Wellness: d.wellness_score,
      })));
    } catch { /* no-op */ }
  }

  function speak(text, lang) {
    if (!speakEnabled || !window.speechSynthesis) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = lang === "hi" ? "hi-IN" : "en-IN";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  }

  async function sendMessage(text) {
    if (!text.trim() || sending) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);
    try {
      if (mode === "wellness_check") {
        const res = await mitraAnswerCheck(sessionId, text);
        const { reply, done, result: r, safety_flag } = res.data;
        setMessages((m) => [...m, { role: "ai", text: reply }]);
        speak(reply, "en");
        if (safety_flag) setSafetyActive(true);
        if (done && r) {
          setResult(r);
          setMode("chat");
          loadReports();
        }
      } else {
        const res = await mitraChat(sessionId, text);
        const { session_id, reply, language, safety_flag } = res.data;
        setSessionId(session_id);
        setMessages((m) => [...m, { role: "ai", text: reply }]);
        speak(reply, language);
        if (safety_flag) setSafetyActive(true);
      }
    } catch {
      setMessages((m) => [...m, { role: "ai", text: "The AI service is temporarily unavailable. Please try again." }]);
    } finally {
      setSending(false);
    }
  }

  async function handleStartCheck() {
    setSending(true);
    setResult(null);
    try {
      const res = await mitraStartCheck();
      setSessionId(res.data.session_id);
      setMode("wellness_check");
      setMessages((m) => [...m, { role: "ai", text: res.data.reply }]);
      speak(res.data.reply, "en");
    } finally {
      setSending(false);
    }
  }

  function handleMic() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessages((m) => [...m, { role: "ai", text: "Voice input isn't supported in this browser. You can continue using text." }]);
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onerror = () => {
      setListening(false);
      setMessages((m) => [...m, { role: "ai", text: "Microphone access is unavailable. You can continue using text." }]);
    };
    recognition.onend = () => setListening(false);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendMessage(transcript);
    };
    recognitionRef.current = recognition;
    recognition.start();
  }

  async function handleImageUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setMessages((m) => [...m, { role: "user", text: `📎 Shared an image: ${file.name}` }]);
    setSending(true);
    try {
      const res = await mitraAnalyzeImage(file, sessionId);
      setMessages((m) => [...m, { role: "ai", text: res.data.analysis }]);
    } catch {
      setMessages((m) => [...m, { role: "ai", text: "We couldn't process that image. Please try another image." }]);
    } finally {
      setSending(false);
      e.target.value = "";
    }
  }

  async function handleRequestConsultant() {
    await mitraRequestConsultant(sessionId);
    setMessages((m) => [...m, { role: "ai", text: "I've requested a human consultant for you. Someone authorized will follow up. You're not alone in this." }]);
  }

  return (
    <AppShell>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aegis-navy tracking-tight flex items-center gap-2">
            <Sparkles size={22} className="text-aegis-teal" /> AI Mitra
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Fast, supportive wellness guidance for registered members — not a diagnosis or replacement for professional care.
          </p>
        </div>
        <button
          onClick={handleStartCheck}
          disabled={sending}
          className="text-sm font-medium bg-aegis-navy text-white px-4 py-2 rounded-lg shadow-card disabled:opacity-50"
        >
          Start Wellness Check
        </button>
      </header>

      {safetyActive && (
        <div className="mb-4 bg-rose-50 border border-rose-200 rounded-xl p-4 flex gap-3">
          <ShieldAlert size={20} className="text-aegis-rose shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-aegis-rose mb-1">You don't have to go through this alone</p>
            <p className="text-sm text-aegis-slate leading-relaxed mb-2">
              In India: KIRAN 1800-599-0019, iCall 9152987821, emergency 112. You can also contact Dr Saxena
              at 9453745228 or your trusted local support person. Please reach out now.
            </p>
            <button
              onClick={handleRequestConsultant}
              className="flex items-center gap-1.5 text-xs font-medium bg-aegis-rose text-white px-3 py-1.5 rounded-lg"
            >
              <PhoneCall size={13} /> Request human consultant now
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat column */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-card flex flex-col h-[560px]">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-aegis-navy text-white rounded-br-sm"
                      : "bg-aegis-tealLight text-aegis-navy rounded-bl-sm"
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-aegis-tealLight text-aegis-navy rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin" /> Mitra is thinking...
                </div>
              </div>
            )}
          </div>

          {messages.length === 1 && !sending && (
            <div className="px-4 pb-3 flex flex-wrap gap-2">
              {STARTERS.map((starter) => <button key={starter} onClick={() => starter === "Start a wellness check" ? handleStartCheck() : sendMessage(starter)} className="text-xs px-3 py-1.5 rounded-full bg-slate-100 text-aegis-slate hover:bg-aegis-tealLight">{starter}</button>)}
            </div>
          )}

          <div className="border-t border-slate-100 p-3">
            {listening && (
              <p className="text-xs text-aegis-teal font-medium mb-2 flex items-center gap-1.5">
                <Mic size={13} className="animate-pulse" /> Listening...
              </p>
            )}
            <div className="flex items-center gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                title="Share an image"
                className="p-2.5 rounded-lg text-slate-500 hover:bg-slate-100 shrink-0"
              >
                <ImagePlus size={18} />
              </button>
              <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleImageUpload} />

              <button
                onClick={handleMic}
                title="Voice input"
                className={`p-2.5 rounded-lg shrink-0 ${listening ? "bg-aegis-rose text-white" : "text-slate-500 hover:bg-slate-100"}`}
              >
                {listening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>

              <button
                onClick={() => setSpeakEnabled((v) => !v)}
                title="Toggle AI voice replies"
                className={`p-2.5 rounded-lg shrink-0 ${speakEnabled ? "bg-aegis-teal text-white" : "text-slate-500 hover:bg-slate-100"}`}
              >
                {speakEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>

              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
                placeholder="Type how you're feeling..."
                className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-aegis-teal"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={sending || !input.trim()}
                className="p-2.5 rounded-lg bg-aegis-navy text-white disabled:opacity-40 shrink-0"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar: results + trend */}
        <div className="space-y-6">
          {result && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5">
              <h3 className="text-sm font-semibold text-aegis-navy mb-1">Your Wellness Summary</h3>
              <p className="text-2xl font-bold font-mono-data text-aegis-navy mb-1">
                {result.wellness_score}<span className="text-sm text-slate-400 font-normal">/100</span>
              </p>
              <p className="text-xs text-slate-500 mb-3">{result.headline}</p>
              <div className="space-y-2.5 mb-4">
                <ScoreBar label={`Stress — ${result.stress_level}`} value={result.stress_score} invert />
                <ScoreBar label={`Fatigue — ${result.fatigue_level}`} value={result.fatigue_score} invert />
                <ScoreBar label={`Energy — ${result.energy_level}`} value={result.energy_score} />
                <ScoreBar label={`Sleep — ${result.sleep_level}`} value={result.sleep_score} />
                <ScoreBar label={`Mood — ${result.mood_level}`} value={result.mood_score} />
                <ScoreBar label={`Focus — ${result.focus_level}`} value={result.focus_score} />
              </div>
              <h4 className="text-xs font-semibold text-aegis-navy mb-1.5">Suggested actions</h4>
              <ul className="space-y-1.5">
                {result.recommendations.map((r, i) => (
                  <li key={i} className="text-xs text-slate-600 flex gap-1.5">
                    <span className="text-aegis-teal">•</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {history.length > 1 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5">
              <h3 className="text-sm font-semibold text-aegis-navy mb-3">Wellness trend (14 days)</h3>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#7A8699" }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#7A8699" }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="Wellness" stroke="#0E8C7F" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {weekly?.available && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-card p-5">
              <h3 className="text-sm font-semibold text-aegis-navy mb-3">This week</h3>
              <div className="grid grid-cols-2 gap-3 text-center mb-3">
                <div>
                  <p className="text-xl font-bold font-mono-data text-aegis-navy">{weekly.average_wellness_score}</p>
                  <p className="text-[11px] text-slate-400">Avg. wellness</p>
                </div>
                <div>
                  <p className="text-xl font-bold font-mono-data text-aegis-rose">{weekly.average_stress_score}</p>
                  <p className="text-[11px] text-slate-400">Avg. stress</p>
                </div>
              </div>
              {weekly.most_stressful_day && (
                <p className="text-xs text-slate-500">Most stressful day: <b>{weekly.most_stressful_day}</b></p>
              )}
              <p className="text-[10px] text-slate-400 mt-2">{weekly.note}</p>
            </div>
          )}

          <button
            onClick={() => setShowHeartRate(true)}
            className="w-full flex items-center justify-center gap-2 text-sm font-medium bg-white border border-slate-200 hover:border-aegis-rose hover:text-aegis-rose text-aegis-slate px-4 py-2.5 rounded-lg shadow-card transition-colors"
          >
            <Heart size={15} /> Check Heart Rate <span className="text-[10px] font-semibold uppercase tracking-wide bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded">Beta</span>
          </button>

          <button
            onClick={handleRequestConsultant}
            className="w-full flex items-center justify-center gap-2 text-sm font-medium bg-white border border-slate-200 hover:border-aegis-teal hover:text-aegis-teal text-aegis-slate px-4 py-2.5 rounded-lg shadow-card transition-colors"
          >
            <PhoneCall size={15} /> Talk to Human Consultant
          </button>
          <div className="bg-white rounded-xl border border-slate-200 p-4 text-xs text-slate-500 leading-relaxed">
            <p className="font-semibold text-aegis-navy mb-1">24/7 registered-member support</p>
            AI Mitra keeps your personal check-in history available whenever you sign in. For urgent human support: <a className="text-aegis-teal font-medium" href="tel:6306664667">6306664667</a> · Dr Saxena <a className="text-aegis-teal font-medium" href="tel:9453745228">9453745228</a> · Dr Shefali <a className="text-aegis-teal font-medium" href="tel:52255225">52255225</a>.
          </div>
        </div>
      </div>

      {showHeartRate && (
        <HeartRateCheck sessionId={sessionId} onClose={() => setShowHeartRate(false)} />
      )}
    </AppShell>
  );
}
