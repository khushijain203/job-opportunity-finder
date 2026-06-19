import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const http = axios.create({ baseURL: API_BASE });

export const companiesApi = {
  list: async (search = "") => {
    const params = search ? { search } : {};
    const { data } = await http.get("/companies", { params });
    return data;
  },
  create: async (payload) => {
    const { data } = await http.post("/companies", payload);
    return data;
  },
  remove: async (id) => {
    await http.delete(`/companies/${id}`);
  },
  stats: async () => {
    const { data } = await http.get("/companies/stats");
    return data;
  },
  exportUrl: () => `${API_BASE}/companies/export.csv`,
};

export const opportunitiesApi = {
  meta: async () => (await http.get("/opportunities/meta")).data,
  list: async (filters = {}) => {
    // axios serializes arrays as `skills=a&skills=b` by default (repeat keys) - matches FastAPI List[str] Query
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

export const outreachApi = {
  generate: async (payload) => (await http.post("/outreach/generate", payload)).data,
};
