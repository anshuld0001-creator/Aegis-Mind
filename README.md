# AEGIS MIND

**Predictive Welfare Intelligence for Those Who Serve.**

A working full-stack prototype for **SIH 2026 – Problem Statement ID 26186**
("AI-Based Predictive Personnel Stress and Welfare Monitoring System for
Uniformed Forces", Ministry of Home Affairs / CRPF).

> AEGIS MIND is an **AI-assisted preventive personnel welfare and early
> intervention** platform. It never diagnoses mental illness, never detects
> deception, never ranks personnel publicly, and never takes disciplinary
> action. Every meaningful decision passes through a human welfare officer.
> **All data in this repository is 100% synthetic/demo data.**

---

## 1. What's in the box

| Layer | Tech | What it does |
|---|---|---|
| Frontend | React + Vite + Tailwind + Recharts | Role-based dashboards (Personnel / Welfare Officer / Administrator) |
| Backend | FastAPI + SQLAlchemy | REST API, JWT auth, RBAC, audit logging |
| ML | scikit-learn, XGBoost, Isolation Forest, SHAP | Stress-risk classifier, anomaly detector, per-case explainability |
| Database | SQLite (default) / PostgreSQL-ready | Personnel profiles, check-ins, risk assessments, cases, interventions |

The database defaults to **SQLite** so the whole prototype runs with zero
external services. Swap `DATABASE_URL` in `backend/.env` to a PostgreSQL DSN
to run it the way the original brief specifies — no code changes needed,
since everything goes through SQLAlchemy.

### Project structure

```
aegis-mind/
├── backend/            FastAPI app, auth, RBAC, API routes
│   └── app/
│       ├── routers/    auth, checkin, risk, cases, analytics
│       ├── ml/         risk engine (loads trained models) + recommendation engine
│       └── utils/      security (JWT/bcrypt), RBAC dependencies
├── ml/                 Synthetic data generator + training pipeline (offline)
│   └── models/         Trained model artifacts + metrics.json (generated)
├── data/                Generated synthetic dataset (generated)
├── frontend/           React app (Vite + Tailwind + Recharts)
├── docker/, docker-compose.yml
└── docs/
```

---

## 2. Ethical guardrails (by design, not just policy)

- No mental-illness diagnosis, no lie detection, no combat/targeting/surveillance features.
- AI only **recommends**; every case status change and intervention is logged against a human account (`WelfareCase`, `InterventionLog`, `AuditLog`).
- Personnel are identified only by a pseudonymous `personnel_code` (e.g. `PID-04831`) in every ML/analytics table.
- The Risk Priority Board is authorized-access only and is never a public ranking.
- Wellness check-ins are voluntary and require consent on file (`consent_wellness_data`).
- All training/demo data is clearly labeled synthetic (`data_source = SYNTHETIC_DEMO_DATA`), and all reported model metrics are labeled as prototype/simulated results.

---

## 3. Quick start (local, no Docker)

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Generate the synthetic dataset and train the ML pipeline (one-time)
cd ../ml
python generate_synthetic_data.py
python train_models.py
cd ../backend

# Seed the database with demo accounts + synthetic personnel records
python seed_demo_data.py

# Run the API
uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://localhost:8000` (interactive docs at `/docs`).

**Demo credentials** (printed again at the end of `seed_demo_data.py`):

| Role | Username | Password |
|---|---|---|
| Personnel | `personnel1` | `Personnel@123` |
| Welfare Officer | `officer1` | `Officer@123` |
| Administrator | `admin1` | `Admin@123` |

### Frontend

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`, sign in with one of the demo accounts above
(the login screen has one-click buttons to fill each role's demo credentials).

---

## 4. Quick start (Docker)

```bash
cd backend && cp .env.example .env && cd ..
# Generate data + train models once, then seed, before/after first build:
docker compose up --build -d
docker compose exec backend python -m ml.generate_synthetic_data   # or run locally as above
```

> For simplicity, generating synthetic data, training, and seeding are
> designed to be run locally against the mounted backend volume before or
> after `docker compose up`. See `docker-compose.yml` for the commented-out
> PostgreSQL/Redis services matching the original production-style architecture.

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

---

## 5. Demo flow (matches the brief)

1. Log in as `officer1` → **Welfare Dashboard** shows organization KPIs, risk distribution, intervention status.
2. Open **Risk Priority Board** → click any case.
3. See Risk Score, Confidence, explainable-AI contributing factors (SHAP), trend chart, and anomaly flag.
4. The panel shows the engine's non-punitive recommended action.
5. Change case status (human review) and log an intervention with an outcome.
6. Log in as `admin1` → **Model Monitoring** shows accuracy/precision/recall/F1, confusion matrix, and global feature importance (all labeled prototype/simulated).
7. Log in as `personnel1` → submit a **Wellness Check-in**; a new risk assessment runs automatically and the personnel dashboard shows only their own supportive indicator, never a diagnosis.

---

## 6. Key API endpoints

| Method | Path | Access |
|---|---|---|
| POST | `/api/auth/login` | public |
| POST | `/api/auth/register` | public (personnel only) |
| POST | `/api/auth/provision` | administrator |
| POST | `/api/checkin` | personnel |
| POST | `/api/risk/run/{personnel_code}` | personnel (own) / officer / admin |
| POST | `/api/risk/run-batch` | administrator |
| GET | `/api/cases` | officer / admin |
| PATCH | `/api/cases/{id}/status` | officer / admin |
| POST | `/api/cases/{id}/interventions` | officer / admin |
| GET | `/api/analytics/dashboard` | officer / admin |
| GET | `/api/analytics/model-performance` | administrator |

Full interactive schema: `http://localhost:8000/docs`.

---

## 7. Notes on what's simplified for the student prototype

- **PostgreSQL / Redis**: the architecture is fully compatible (SQLAlchemy +
  a configurable `DATABASE_URL`), but the default run path uses SQLite and
  skips Redis caching, since a single-machine demo doesn't need them.
- **Hindi localization**: the UI copy and API are structured so translated
  strings can be swapped in; a full i18n library wasn't wired in to keep the
  prototype's surface area manageable in the time available.
- **Retraining**: `ml/train_models.py` is meant to be re-run manually after
  reviewing feedback, matching the brief's "do not auto-retrain without
  validation" requirement.

---

## 8. AI MITRA — personal AI wellness & fatigue consultant

AI Mitra is a **separate, personal** feature from the organizational Aegis
Risk Engine above — it's available to any logged-in user (Personnel,
Welfare Officer, or Administrator) as a private wellness companion, and its
data is never folded into the organizational welfare-case pipeline.

**Nav:** "AI Mitra" appears in the sidebar for every role → `/mitra`.

### What it actually does

- **Adaptive chat.** Free-form conversation in English, Hindi, or Hinglish.
  Mentioning a topic ("I'm stressed", "aaj bahut thak gaya hoon") triggers
  one relevant follow-up question, not a fixed questionnaire.
- **Structured wellness check.** "Start Wellness Check" walks through 6
  adaptive questions (sleep, energy, stress + source, mood, focus, fatigue)
  and returns a scored, explained summary with concrete recommendations.
- **Scoring engine** (`backend/app/mitra/scoring.py`): 0-100 scores per
  dimension, configurable weights, transparent band labels (Low/Moderate/
  High/Very High for stress & fatigue; Low/Fair/Good/Excellent for the
  rest) — never presented as a diagnosis.
- **Safety engine** (`backend/app/mitra/safety.py`): detects clear crisis
  language and immediately returns supportive, resource-forward guidance
  (India: KIRAN 1800-599-0019, iCall 9152987821, emergency 112) instead of
  continuing normal coaching, and auto-creates a human-consultant
  escalation.
- **Human consultant escalation**: any user can request one directly; it
  also fires automatically on a safety flag or persistently very-high
  stress/fatigue. Welfare Officers and Administrators see these under
  **"Mitra Escalations"** in their sidebar (`/officer/mitra-requests`).
- **Voice**: uses the **browser's built-in** Web Speech API
  (`SpeechRecognition` for mic input, `speechSynthesis` for spoken replies)
  — no speech vendor, no API key, works today in Chrome-based browsers.
  Falls back to a plain-text notice if the browser doesn't support it.
- **Image sharing**: users can attach an image; the backend validates,
  stores, and returns a general, clearly-labeled heuristic note. It does
  **not** run a real vision model in this deployment (see below) and never
  claims to assess anyone's health or mental state from an image.
- **Trend chart + weekly report**: `/api/mitra/history` and
  `/api/mitra/weekly-report` power a 14-day wellness trend chart and a
  weekly summary right on the AI Mitra page.

### Why it's rule-based, not an LLM call

No AI/LLM provider is configured for this deployment, and the brief asked
for a working feature rather than a dependency on a paid API this prototype
can't ship credentials for. So the whole conversation/scoring/safety
pipeline (`backend/app/mitra/`) is a transparent, deterministic
keyword-and-rules engine — it runs offline, at zero per-message cost, and
every decision it makes is inspectable in plain Python. The API surface
(`POST /api/mitra/chat`, etc.) is intentionally the seam where a real LLM or
vision provider could be swapped in later: see `AI_PROVIDER_API_KEY`,
`STT_API_KEY`, `TTS_API_KEY` in `backend/.env.example` — currently unused
placeholders, and never referenced from any frontend code.

### New backend pieces

```
backend/app/mitra/
├── safety.py            language + crisis detection, crisis resources
├── extraction.py        keyword/regex signal extraction (EN/HI/Hinglish)
├── scoring.py            0-100 scoring + band labels + wellness formula
├── recommendations.py   per-dimension recommendation engine
└── engine.py             adaptive chat + structured wellness-check flow
backend/app/routers/mitra.py    all /api/mitra/* endpoints
backend/app/schemas_mitra.py    request/response models
backend/uploads/mitra/           stored images (gitignored; never in DB as bytes)
```

New tables (see `backend/app/models.py`): `MitraConversation`,
`MitraMessage`, `MitraWellnessCheck`, `MitraImageAnalysis`,
`MitraConsultantRequest`, `MitraHeartRateReading` — all keyed to `user_id`,
isolated from other users' data by the same JWT auth used everywhere else
in the app.

### Heart Rate Check (Beta) — camera + flash PPG

An optional, self-measured heart-rate estimate, available from the
**"Check Heart Rate"** button on the AI Mitra page
(`frontend/src/components/HeartRateCheck.jsx`).

**How it works:** the user covers their rear camera + flash with a
fingertip; the browser samples the red-channel brightness of the video feed
~60 times/second for 15 seconds (entirely client-side — no video ever
leaves the device); a simple peak-detection algorithm turns the resulting
waveform into a beats-per-minute estimate and a quality rating
(good/fair/poor). Only the final bpm number is sent to the backend
(`POST /api/mitra/heart-rate`), which logs it and returns a plain-language,
explicitly non-diagnostic reference band (see `heart_rate_band()` in
`backend/app/mitra/scoring.py`).

**Honest limitations — please read before demoing:**
- **Works reliably only on Android Chrome** with a rear camera that has a
  flash. The Web API to control camera flash (`torch` constraint) **is not
  supported on iOS Safari at all**, and most laptop webcams have no flash
  hardware — the feature detects this and shows a clear fallback message
  rather than failing silently, but it simply won't produce a reading
  there.
- This is **not a medical-grade sensor**. Finger pressure, motion, and
  ambient light all affect accuracy. If fewer than 8 clear pulses are
  detected in the measurement window, the UI reports "couldn't get a clear
  reading" rather than showing a low-confidence number as if it were solid.
- I was not able to test the actual camera/flash capture end-to-end in this
  sandbox (no camera hardware, and the sandbox's network restrictions block
  downloading a headless-Chrome binary for automated testing). The backend
  endpoint and the client-side peak-detection math are tested and working;
  the camera capture path is implementation-reviewed but needs a real
  Android Chrome device for a final check before you rely on it in a demo.

### Try it

1. Log in as any demo account.
2. Click **AI Mitra** in the sidebar.
3. Type "I am feeling very tired today" and watch it ask a real follow-up
   ("was it more physical or mental tiredness?").
4. Click **Start Wellness Check** for the full 6-question flow and a scored
   result with recommendations.
5. Try typing something in Hinglish, e.g. "aaj kaafi stress hai kaam ki wajah se".
6. Click **Check Heart Rate** (best tried on an Android phone in Chrome) to
   try the camera-based pulse estimate.
7. As `officer1` or `admin1`, open **Mitra Escalations** to see any
   consultant requests raised above.
