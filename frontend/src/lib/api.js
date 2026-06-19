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
