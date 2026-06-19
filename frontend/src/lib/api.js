import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

// Single axios instance with credentials so HTTP-only cookies are sent on every call.
const http = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// ---------------------------------------------------------------------------- //
// Auth
// ---------------------------------------------------------------------------- //
export const authApi = {
  register: async (payload) => (await http.post("/auth/register", payload)).data,
  login: async (payload) => (await http.post("/auth/login", payload)).data,
  logout: async () => http.post("/auth/logout"),
  me: async () => (await http.get("/auth/me")).data,
};

// ---------------------------------------------------------------------------- //
// Profile
// ---------------------------------------------------------------------------- //
export const profileApi = {
  get: async () => (await http.get("/profile")).data,
  update: async (payload) => (await http.put("/profile", payload)).data,
};

// ---------------------------------------------------------------------------- //
// Companies (Leads)
// ---------------------------------------------------------------------------- //
export const companiesApi = {
  list: async (search = "") => {
    const params = search ? { search } : {};
    const { data } = await http.get("/companies", { params });
    return data;
  },
  create: async (payload) => (await http.post("/companies", payload)).data,
  remove: async (id) => {
    await http.delete(`/companies/${id}`);
  },
  stats: async () => (await http.get("/companies/stats")).data,
  exportUrl: () => `${API_BASE}/companies/export.csv`,
};

// ---------------------------------------------------------------------------- //
// Opportunities
// ---------------------------------------------------------------------------- //
export const opportunitiesApi = {
  meta: async () => (await http.get("/opportunities/meta")).data,
  list: async (filters = {}) => {
    const params = {};
    Object.entries(filters).forEach(([k, v]) => {
      if (v === undefined || v === null) return;
      if (Array.isArray(v)) {
        if (v.length > 0) params[k] = v;
      } else if (v !== "") {
        params[k] = v;
      }
    });
    const { data } = await http.get("/opportunities", {
      params,
      paramsSerializer: { indexes: null },
    });
    return data;
  },
  create: async (payload) => (await http.post("/opportunities", payload)).data,
  remove: async (id) => {
    await http.delete(`/opportunities/${id}`);
  },
  updateStatus: async (id, status) =>
    (await http.patch(`/opportunities/${id}/status`, { status })).data,
  saveToLeads: async (id) => (await http.post(`/opportunities/${id}/save-to-leads`)).data,
  seed: async () => (await http.post("/opportunities/seed")).data,
};

// ---------------------------------------------------------------------------- //
// Outreach + history
// ---------------------------------------------------------------------------- //
export const outreachApi = {
  generate: async (payload) => (await http.post("/outreach/generate", payload)).data,
};

export const generatedEmailsApi = {
  list: async (opportunityId = null) => {
    const params = opportunityId ? { opportunity_id: opportunityId } : {};
    return (await http.get("/generated-emails", { params })).data;
  },
  remove: async (id) => {
    await http.delete(`/generated-emails/${id}`);
  },
};

// ---------------------------------------------------------------------------- //
// Resumes
// ---------------------------------------------------------------------------- //
export const resumesApi = {
  list: async () => (await http.get("/resumes")).data,
  active: async () => (await http.get("/resumes/active")).data,
  upload: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return (await http.post("/resumes/upload", fd)).data;
  },
  activate: async (id) => (await http.post(`/resumes/${id}/activate`)).data,
  remove: async (id) => {
    await http.delete(`/resumes/${id}`);
  },
  enrich: async (id) => (await http.post(`/resumes/${id}/enrich`)).data,
  downloadUrl: (id) => `${API_BASE}/resumes/${id}/download`,
};

// ---------------------------------------------------------------------------- //
// Match scores
// ---------------------------------------------------------------------------- //
export const matchesApi = {
  forOpportunity: async (oppId, { tfidf = false } = {}) =>
    (await http.get(`/matches/opportunity/${oppId}`, { params: tfidf ? { tfidf: true } : {} })).data,
  batch: async (opportunityIds) => {
    if (!opportunityIds || opportunityIds.length === 0) return [];
    return (await http.get("/matches/batch", {
      params: { opportunity_ids: opportunityIds },
      paramsSerializer: { indexes: null },
    })).data;
  },
  aiFor: async (oppId) => (await http.post(`/matches/opportunity/${oppId}/ai`)).data,
};

// ---------------------------------------------------------------------------- //
// Helpers
// ---------------------------------------------------------------------------- //
export function formatApiErrorDetail(detail) {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}
