import React, { useEffect, useRef, useState, useCallback } from "react";
import { Heart, Flashlight, X, RotateCcw, Save, TriangleAlert } from "lucide-react";
import { mitraLogHeartRate } from "../api/client";

const MEASURE_MS = 30000;
const SETTLE_MS = 3000;
const SAMPLE_INTERVAL_MS = 33; // avoid oversampling duplicate camera frames
const SAMPLE_PATCH = 24; // px region sampled from the center of the frame
const MIN_PEAKS = 12;

// ---- simple PPG peak-detection on the red-channel brightness signal ----
function estimateBpm(samples) {
  const usable = samples.filter((s) => s.t >= SETTLE_MS);
  if (usable.length < 120) return { ok: false };

  // light smoothing (moving average, window 3) to reduce camera sensor noise
  const smoothed = usable.map((s, i) => {
    const lo = Math.max(0, i - 3), hi = Math.min(usable.length - 1, i + 3);
    let sum = 0, n = 0;
    for (let j = lo; j <= hi; j++) { sum += samples[j].v; n++; }
    return { t: s.t, v: sum / n };
  });

  // Remove slow illumination drift (flash/camera auto-exposure) before detecting beats.
  const values = smoothed.map((s) => s.v);
  const baseline = values.reduce((a, b) => a + b, 0) / values.length;
  const centred = smoothed.map((s) => ({ ...s, v: s.v - baseline }));
  const amplitude = Math.max(...centred.map((s) => s.v)) - Math.min(...centred.map((s) => s.v));
  if (amplitude < 1.2) return { ok: false, reason: "weak_signal" };
  const threshold = amplitude * 0.08;

  const minPeakGapMs = 250; // corresponds to a max plausible ~240 bpm
  const peakTimes = [];
  let lastPeakT = -Infinity;
  for (let i = 1; i < centred.length - 1; i++) {
    const { t, v } = centred[i];
    if (v > threshold && v >= centred[i - 1].v && v >= centred[i + 1].v && t - lastPeakT > minPeakGapMs) {
      peakTimes.push(t);
      lastPeakT = t;
    }
  }

  if (peakTimes.length < MIN_PEAKS) return { ok: false, peakCount: peakTimes.length };

  let intervals = [];
  for (let i = 1; i < peakTimes.length; i++) intervals.push(peakTimes[i] - peakTimes[i - 1]);
  intervals.sort((a, b) => a - b);
  const median = intervals[Math.floor(intervals.length / 2)];
  // Ignore missed/double peaks far from the median before final BPM and quality.
  intervals = intervals.filter((i) => i > median * 0.65 && i < median * 1.35);
  if (intervals.length < MIN_PEAKS - 2) return { ok: false, peakCount: peakTimes.length };
  const bpm = Math.round(60000 / median);

  const intervalMean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
  const intervalStd = Math.sqrt(intervals.reduce((a, b) => a + (b - intervalMean) ** 2, 0) / intervals.length);
  const cv = intervalStd / intervalMean;
  const quality = cv < 0.15 ? "good" : cv < 0.3 ? "fair" : "poor";

  if (bpm < 35 || bpm > 220) return { ok: false, peakCount: peakTimes.length };

  return { ok: true, bpm, quality, peakCount: peakTimes.length };
}

const BAND_COLOR = {
  Low: "text-aegis-amber",
  "Typical resting range": "text-aegis-teal",
  Elevated: "text-aegis-amber",
  High: "text-aegis-rose",
};

export default function HeartRateCheck({ sessionId, onClose }) {
  const [status, setStatus] = useState("idle"); // idle | requesting | measuring | processing | result | failed | unsupported
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [saved, setSaved] = useState(false);
  const [torchOn, setTorchOn] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));
  const streamRef = useRef(null);
  const rafRef = useRef(null);
  const samplesRef = useRef([]);
  const startRef = useRef(0);
  const lastSampleRef = useRef(0);

  const stopStream = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  useEffect(() => () => stopStream(), [stopStream]);

  function sampleFrame(now) {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(sampleFrame);
      return;
    }
    if (now - lastSampleRef.current < SAMPLE_INTERVAL_MS) {
      rafRef.current = requestAnimationFrame(sampleFrame);
      return;
    }
    lastSampleRef.current = now;
    canvas.width = SAMPLE_PATCH;
    canvas.height = SAMPLE_PATCH;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const vw = video.videoWidth || 640, vh = video.videoHeight || 480;
    ctx.drawImage(
      video,
      vw / 2 - 40, vh / 2 - 40, 80, 80,
      0, 0, SAMPLE_PATCH, SAMPLE_PATCH
    );
    const { data } = ctx.getImageData(0, 0, SAMPLE_PATCH, SAMPLE_PATCH);
    let sum = 0;
    for (let i = 0; i < data.length; i += 4) sum += data[i]; // red channel
    const avgRed = sum / (data.length / 4);

    const elapsed = now - startRef.current;
    samplesRef.current.push({ t: elapsed, v: avgRed });
    setProgress(Math.min(100, Math.round((elapsed / MEASURE_MS) * 100)));

    if (elapsed < MEASURE_MS) {
      rafRef.current = requestAnimationFrame(sampleFrame);
    } else {
      finishMeasurement();
    }
  }

  function finishMeasurement() {
    stopStream();
    setStatus("processing");
    setTimeout(() => {
      const outcome = estimateBpm(samplesRef.current);
      if (!outcome.ok) {
        setStatus("failed");
      } else {
        setResult(outcome);
        setStatus("result");
      }
    }, 300);
  }

  async function startMeasurement() {
    setSaved(false);
    setResult(null);
    samplesRef.current = [];
    lastSampleRef.current = 0;
    setProgress(0);
    setStatus("requesting");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus("unsupported");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 320 }, height: { ideal: 240 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      const track = stream.getVideoTracks()[0];
      const caps = track.getCapabilities ? track.getCapabilities() : {};
      if (caps.torch) {
        try {
          await track.applyConstraints({ advanced: [{ torch: true }] });
          setTorchOn(true);
        } catch {
          setTorchOn(false);
        }
      } else {
        setTorchOn(false);
      }

      setStatus("measuring");
      startRef.current = performance.now();
      rafRef.current = requestAnimationFrame(sampleFrame);
    } catch {
      setStatus("unsupported");
    }
  }

  async function handleSave() {
    if (!result) return;
    await mitraLogHeartRate(result.bpm, sessionId, result.quality);
    setSaved(true);
  }

  function handleCancel() {
    stopStream();
    setStatus("idle");
    setProgress(0);
  }

  return (
    <div className="fixed inset-0 bg-aegis-navy/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6 relative">
        <button onClick={() => { stopStream(); onClose(); }} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600">
          <X size={18} />
        </button>

        <div className="flex items-center gap-2 mb-1">
          <Heart size={18} className="text-aegis-rose" />
          <h3 className="font-semibold text-aegis-navy">Heart Rate Check</h3>
          <span className="text-[10px] font-semibold uppercase tracking-wide bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">Beta</span>
        </div>
        <p className="text-xs text-slate-400 mb-5">
          Camera-based estimate, not a medical device. Works best on Android Chrome with a rear camera flash.
        </p>

        {status === "idle" && (
          <div className="text-center py-4">
            <p className="text-sm text-slate-600 mb-5">
              Gently cover your rear camera <b>and</b> flash with your fingertip, then tap Start and hold still for 30 seconds.
            </p>
            <button onClick={startMeasurement} className="bg-aegis-navy text-white text-sm font-medium px-5 py-2.5 rounded-lg">
              Start Measurement
            </button>
          </div>
        )}

        {status === "requesting" && (
          <div className="text-center py-8">
            <p className="text-sm text-slate-500">Requesting camera access...</p>
          </div>
        )}

        {status === "measuring" && (
          <div className="text-center py-4">
            <div className="relative w-28 h-28 mx-auto mb-4">
              <svg className="w-28 h-28 -rotate-90">
                <circle cx="56" cy="56" r="48" stroke="#EEF0F3" strokeWidth="8" fill="none" />
                <circle
                  cx="56" cy="56" r="48" stroke="#B4453C" strokeWidth="8" fill="none"
                  strokeDasharray={2 * Math.PI * 48}
                  strokeDashoffset={2 * Math.PI * 48 * (1 - progress / 100)}
                  strokeLinecap="round"
                />
              </svg>
              <Heart size={28} className="absolute inset-0 m-auto text-aegis-rose animate-pulse" />
            </div>
            {torchOn ? (
              <p className="text-xs text-aegis-teal flex items-center justify-center gap-1 mb-1">
                <Flashlight size={13} /> Flash on — hold your finger steady
              </p>
            ) : (
              <p className="text-xs text-aegis-amber mb-1">Flash unavailable on this device — hold finger steady in good light</p>
            )}
            <p className="text-sm text-slate-500 mb-4">{progress < 10 ? "Stabilizing camera…" : `Measuring… ${progress}%`}</p>
            <video ref={videoRef} className="hidden" muted playsInline />
            <button onClick={handleCancel} className="text-xs text-slate-400 underline">Cancel</button>
          </div>
        )}

        {status === "processing" && (
          <div className="text-center py-8">
            <p className="text-sm text-slate-500">Analyzing your pulse signal...</p>
          </div>
        )}

        {status === "result" && result && (
          <div className="text-center py-2">
            <p className={`text-5xl font-bold font-mono-data ${BAND_COLOR[bandForBpm(result)] || "text-aegis-navy"}`}>
              {result.bpm}
            </p>
            <p className="text-sm text-slate-400 mb-3">beats per minute (estimated)</p>
            <span className={`inline-block text-xs font-semibold px-2.5 py-1 rounded-md mb-4 ${
              result.quality === "good" ? "bg-emerald-50 text-emerald-700" :
              result.quality === "fair" ? "bg-amber-50 text-amber-700" : "bg-rose-50 text-rose-700"
            }`}>
              Signal quality: {result.quality}
            </span>
            <p className="text-xs text-slate-500 mb-5 leading-relaxed">
              This is a self-measured estimate, not a medical-grade reading. If it feels off, try again with steadier finger placement.
            </p>
            <div className="flex gap-2 justify-center">
              <button onClick={startMeasurement} className="flex items-center gap-1.5 text-sm font-medium bg-slate-100 text-aegis-slate px-4 py-2 rounded-lg">
                <RotateCcw size={14} /> Measure again
              </button>
              <button
                onClick={handleSave}
                disabled={saved}
                className="flex items-center gap-1.5 text-sm font-medium bg-aegis-teal text-white px-4 py-2 rounded-lg disabled:opacity-50"
              >
                <Save size={14} /> {saved ? "Saved" : "Save to log"}
              </button>
            </div>
          </div>
        )}

        {status === "failed" && (
          <div className="text-center py-4">
            <TriangleAlert size={28} className="text-aegis-amber mx-auto mb-2" />
            <p className="text-sm text-slate-600 mb-4">
              Couldn't detect a clear pulse. Make sure your fingertip fully covers both the camera lens and flash, and stay still.
            </p>
            <button onClick={startMeasurement} className="text-sm font-medium bg-aegis-navy text-white px-4 py-2 rounded-lg">
              Try Again
            </button>
          </div>
        )}

        {status === "unsupported" && (
          <div className="text-center py-4">
            <TriangleAlert size={28} className="text-aegis-amber mx-auto mb-2" />
            <p className="text-sm text-slate-600 mb-2">
              Camera access isn't available for this check on your current device or browser.
            </p>
            <p className="text-xs text-slate-400">
              This feature works best on Android Chrome with a rear camera flash. You can continue using the rest of AI Mitra normally.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function bandForBpm(result) {
  if (result.bpm < 50) return "Low";
  if (result.bpm <= 100) return "Typical resting range";
  if (result.bpm <= 120) return "Elevated";
  return "High";
}
