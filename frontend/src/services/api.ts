import axios from 'axios';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    username: string;
    role: string;
  };
}

export interface User {
  username: string;
  role: string;
  email?: string;
}

export interface Lead {
  id: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  status?: string;
  source?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Campaign {
  id: string;
  name: string;
  status: string;
  type?: string;
  created_at?: string;
  metrics?: {
    sent: number;
    opened: number;
    clicked: number;
    converted: number;
  };
}

<<<<<<< HEAD
=======
export interface CampaignMetricsUpdate {
  sent?: number;
  opened?: number;
  clicked?: number;
  converted?: number;
}

>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
export interface Workflow {
  id: string;
  name: string;
  status: string;
  trigger_type?: string;
  created_at?: string;
  last_run?: string;
}

<<<<<<< HEAD
=======
export type WorkflowTriggerPayload =
  | {
      workflow_id: string;
      data?: Record<string, unknown>;
    }
  | {
      name: string;
      description?: string;
      steps: Array<{
        id: string;
        type: 'trigger' | 'action' | 'condition';
        label: string;
        config: Record<string, unknown>;
      }>;
      enabled: boolean;
    };

>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
export interface HealthStatus {
  status: string;
  version: string;
  redis?: string;
  queue_depth?: number;
}

export interface Metrics {
  requests_total: number;
  requests_failed: number;
  avg_latency_ms: number;
  max_latency_ms: number;
  uptime_seconds: number;
  queue_depth?: number;
}

// Auth API
export const authAPI = {
  login: (data: LoginRequest) => api.post<LoginResponse>('/auth/login', data),
  getCurrentUser: () => api.get<User>('/auth/me'),
  getApiKeys: () => api.get('/auth/keys'),
};

// Leads API
export const leadsAPI = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Lead[]>('/leads', { params }),
  getById: (id: string) => api.get<Lead>(`/leads/${id}`),
  create: (data: Partial<Lead>) => api.post<Lead>('/leads', data),
  update: (id: string, data: Partial<Lead>) => api.put<Lead>(`/leads/${id}`, data),
  delete: (id: string) => api.delete(`/leads/${id}`),
};

// Campaigns API
export const campaignsAPI = {
  getAll: () => api.get<Campaign[]>('/campaigns'),
  getById: (id: string) => api.get<Campaign>(`/campaigns/${id}`),
  create: (data: Partial<Campaign>) => api.post<Campaign>('/campaigns', data),
<<<<<<< HEAD
  updateMetrics: (id: string, metrics: any) => 
=======
  updateMetrics: (id: string, metrics: CampaignMetricsUpdate) =>
>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
    api.post(`/campaigns/${id}/metrics`, metrics),
};

// Workflows API
export const workflowsAPI = {
  getAll: () => api.get<Workflow[]>('/workflows'),
<<<<<<< HEAD
  trigger: (data: any) => api.post('/workflows', data),
=======
  trigger: (data: WorkflowTriggerPayload) => api.post('/workflows', data),
>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
  getStatus: (id: string) => api.get(`/workflows/${id}/status`),
};

// System API
export const systemAPI = {
  getHealth: () => api.get<HealthStatus>('/health'),
  getDetailedHealth: () => api.get<HealthStatus>('/health/detailed'),
  getMetrics: () => api.get<Metrics>('/metrics'),
};

export default api;
