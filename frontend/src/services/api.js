import axios from "axios";

// In Docker: requests go through CRA proxy to backend
// In manual dev: set REACT_APP_API_URL=http://localhost:8000
const API_URL = process.env.REACT_APP_API_URL || "";

const api = axios.create({ baseURL: API_URL, timeout: 60000 });

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Global 401 handler
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ───────────────────────────────────────────────────────────────────
export const login    = (email, password) => api.post("/auth/login",   { email, password });
export const register = (data)            => api.post("/auth/register", data);
export const getMe    = ()                => api.get("/auth/me");

// ── Applications ───────────────────────────────────────────────────────────
export const getApplications   = ()     => api.get("/applications/");
export const getApplication    = (id)   => api.get(`/applications/${id}`);
export const createApplication = (data) => api.post("/applications/", data);
export const deleteApplication = (id)   => api.delete(`/applications/${id}`);

// ── Documents ──────────────────────────────────────────────────────────────
export const uploadDocument  = (formData) =>
  api.post("/documents/upload", formData, { headers: { "Content-Type": "multipart/form-data" } });
export const processDocument = (docId)   => api.post(`/documents/process/${docId}`);
export const getDocuments    = (appId)   => api.get(`/documents/${appId}`);

// ── Verification ───────────────────────────────────────────────────────────
export const runVerification = (appId) => api.post(`/verify/${appId}`);

// Agentic (CrewAI multi-agent) verification — can take longer due to
// multiple sequential LLM calls across 5 agents, so use an extended timeout.
export const runAgenticVerification = (appId) =>
  api.post(`/verify/${appId}/agentic`, null, { timeout: 5 * 60 * 1000 });

// ── Reports ────────────────────────────────────────────────────────────────
export const getReport       = (appId) => api.get(`/report/${appId}`);
export const downloadReport  = (appId) => `${API_URL}/report/${appId}/download`;
export const downloadPDF     = (appId) => api.get(`/report/${appId}/download`, { responseType: 'blob' });
export const regeneratePdf   = (appId) => api.post(`/report/${appId}/regenerate-pdf`);

// ── Dashboard ─────────────────────────────────────────────────────────────
export const getDashboardStats = (branch = "") => api.get(`/dashboard/stats${branch ? `?branch=${encodeURIComponent(branch)}` : ""}`);

export const submitSiteVerification = (appId, data) => api.post(`/applications/${appId}/site_verification`, data);

export const submitJointApplicant = (appId, data) => api.post(`/applications/${appId}/joint_applicants`, data);

export const submitPropertyDetails = (appId, data) => api.post(`/applications/${appId}/property_details`, data);

export const submitGovVerification = (appId, data) => api.post(`/applications/${appId}/gov_verification`, data);

export const updateApplicantDetails = (appId, data) => api.put(`/applications/${appId}/applicant_details`, data);

export default api;

