import axios from 'axios';

export interface Metrics {
  requests_total: number;
  requests_failed: number;
  avg_latency_ms: number;
  max_latency_ms: number;
  uptime_seconds: number;
  queue_depth?: number;
}

export interface Lead {
  id: string;
  name: string;
  email: string;
  status: string;
  created_at: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  company?: string;
}

export interface Campaign {
  id: string;
  name: string;
  status: string;
  metrics?: {
    sent: number;
    opened: number;
    clicked: number;
    converted?: number;
  };
  type?: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface HealthStatus {
  status: string;
  details?: string;
  uptime_seconds?: number;
  version?: string;
  database?: {
    status: string;
    details?: string;
  };
  queue?: {
    status: string;
    details?: string;
  };
  redis?: string;
  queue_depth?: number;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  steps?: any[];
  enabled?: boolean;
  status?: string;
  trigger_type?: string;
  last_run?: string;
}

const api = axios.create({
  baseURL: '/api',
});

export const systemAPI = {
  getMetrics: () => api.get<Metrics>('/metrics'),
  getDetailedHealth: () => api.get<HealthStatus>('/health/detailed'),
};

export const leadsAPI = {
  getAll: () => api.get<Lead[]>('/leads'),
  get: (id: string) => api.get<Lead>(`/leads/${id}`),
  create: (lead: Partial<Lead>) => api.post<Lead>('/leads', lead),
  update: (id: string, lead: Partial<Lead>) => api.put<Lead>(`/leads/${id}`, lead),
  delete: (id: string) => api.delete(`/leads/${id}`),
};

export const campaignsAPI = {
  getAll: () => api.get<Campaign[]>('/campaigns'),
  get: (id: string) => api.get<Campaign>(`/campaigns/${id}`),
  create: (campaign: Partial<Campaign>) => api.post<Campaign>('/campaigns', campaign),
  update: (id: string, campaign: Partial<Campaign>) => api.put<Campaign>(`/campaigns/${id}`, campaign),
  delete: (id: string) => api.delete(`/campaigns/${id}`),
};

export const authAPI = {
  login: (data: LoginRequest) => api.post<{ access_token: string; user: User }>('/auth/login', data),
  logout: () => api.post('/auth/logout', {}),
  me: () => api.get<User>('/auth/me'),
  getCurrentUser: () => api.get<User>('/auth/me'),
  getApiKeys: () => api.get<{ keys: string[] }>('/auth/api-keys'),
};

export const workflowsAPI = {
  getAll: () => api.get<Workflow[]>('/workflows'),
  get: (id: string) => api.get<Workflow>(`/workflows/${id}`),
  create: (workflow: Partial<Workflow>) => api.post<Workflow>('/workflows', workflow),
  update: (id: string, workflow: Partial<Workflow>) => api.put<Workflow>(`/workflows/${id}`, workflow),
  delete: (id: string) => api.delete(`/workflows/${id}`),
  trigger: (data: any) => api.post('/workflows/trigger', data),
};

export default api;
