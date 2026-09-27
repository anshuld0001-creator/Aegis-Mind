import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("aegis_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("aegis_token");
      localStorage.removeItem("aegis_role");
      localStorage.removeItem("aegis_personnel_code");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default client;

// ---------- Auth ----------
export const login = (username, password) => {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  return client.post("/api/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
};

export const registerPersonnel = (username, password) =>
  client.post("/api/auth/register", { username, password, role: "personnel" });

export const getMe = () => client.get("/api/auth/me");

// ---------- Check-in ----------
export const submitCheckin = (payload) => client.post("/api/checkin", payload);
export const myCheckinHistory = () => client.get("/api/checkin/history");
export const checkinHistoryFor = (code) => client.get(`/api/checkin/history/${code}`);

// ---------- Risk ----------
export const runRiskAssessment = (code) => client.post(`/api/risk/run/${code}`);
export const runBatchAssessment = () => client.post("/api/risk/run-batch");
export const latestRisk = (code) => client.get(`/api/risk/latest/${code}`);
export const riskHistory = (code) => client.get(`/api/risk/history/${code}`);

// ---------- Cases ----------
export const listCases = (status) =>
  client.get("/api/cases", { params: status ? { status } : {} });
export const getCase = (id) => client.get(`/api/cases/${id}`);
export const updateCaseStatus = (id, payload) => client.patch(`/api/cases/${id}/status`, payload);
export const logIntervention = (id, payload) => client.post(`/api/cases/${id}/interventions`, payload);
export const listInterventions = (id) => client.get(`/api/cases/${id}/interventions`);

// ---------- Analytics ----------
export const dashboardSummary = () => client.get("/api/analytics/dashboard");
export const modelPerformance = () => client.get("/api/analytics/model-performance");
export const personnelTrend = (code) => client.get(`/api/analytics/trend/${code}`);

// ---------- AI Mitra ----------
export const mitraChat = (sessionId, message) =>
  client.post("/api/mitra/chat", { session_id: sessionId, message });
export const mitraStartCheck = () => client.post("/api/mitra/wellness-check/start");
export const mitraQuickStressCheck = (payload) => client.post("/api/mitra/quick-stress-check", payload);
export const mitraAnswerCheck = (sessionId, message) =>
  client.post("/api/mitra/wellness-check/answer", { session_id: sessionId, message });
export const mitraAnalyzeImage = (file, sessionId) => {
  const form = new FormData();
  form.append("file", file);
  const params = sessionId ? { session_id: sessionId } : {};
  return client.post("/api/mitra/image-analyze", form, {
    params,
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const mitraToday = () => client.get("/api/mitra/today");
export const mitraHistory = (days = 30) => client.get("/api/mitra/history", { params: { days } });
export const mitraWeeklyReport = () => client.get("/api/mitra/weekly-report");
export const mitraRequestConsultant = (sessionId) =>
  client.post("/api/mitra/consultant-request", { session_id: sessionId });
export const mitraListConsultantRequests = (status) =>
  client.get("/api/mitra/consultant/requests", { params: status ? { status } : {} });
export const mitraUpdateConsultantRequest = (id, status, notes) =>
  client.patch(`/api/mitra/consultant/requests/${id}`, null, { params: { status, notes } });

// ---------- Heart Rate (camera/flash PPG) ----------
export const mitraLogHeartRate = (bpm, sessionId, signalQuality) =>
  client.post("/api/mitra/heart-rate", { bpm, session_id: sessionId, signal_quality: signalQuality });
export const mitraHeartRateHistory = (days = 14) =>
  client.get("/api/mitra/heart-rate/history", { params: { days } });
