// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore – axios is resolved at build time via node_modules
import axios from 'axios'

const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim().replace(/\/$/, '')
// Fallback: direct to localhost in dev, direct to Azure host in prod (no /api prefix)
const fallbackBaseUrl =
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://ai-agent-revenue-api-mayank-etcse3d6dbc8cddj.centralindia-01.azurewebsites.net'

export const API_BASE_URL = configuredBaseUrl || fallbackBaseUrl

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── Debug interceptors ────────────────────────────────────────────────────────
api.interceptors.request.use((config: any) => {
  const fullUrl = (config.baseURL ?? '') + (config.url ?? '')
  console.debug(`[API] → ${config.method?.toUpperCase()} ${fullUrl}`, config.params ?? '')
  return config
})

api.interceptors.response.use(
  (response: any) => response,
  (error: any) => {
    const url = (error.config?.baseURL ?? '') + (error.config?.url ?? '')
    const status = error.response?.status ?? 'network error'
    console.error(`[API] ✗ ${error.config?.method?.toUpperCase()} ${url} → ${status}`, error.response?.data ?? '')
    return Promise.reject(error)
  },
)

// ── Agents ──────────────────────────────────────────────────────────
export const runDailyPipeline = (useMock = true, maxLeads = 20) =>
  api.post('/agents/run-daily', { use_mock: useMock, max_leads: maxLeads }).then(r => r.data)

export const fetchLeads = (useMock = true) =>
  api.post(`/agents/leads/fetch?use_mock=${useMock}`).then(r => r.data)

export const generateProposal = (lead: Record<string, unknown>) =>
  api.post('/agents/proposal/generate', lead).then(r => r.data)

export const runFollowups = () =>
  api.post('/agents/followup/run').then(r => r.data)

export const sendFollowup = (id: number) =>
  api.post(`/agents/followup/${id}/send`).then(r => r.data)

export const getAgentRevenueStats = () =>
  api.get('/agents/revenue/stats').then(r => r.data)

export const getActionQueue = () =>
  api.get('/agents/action-queue').then(r => r.data)

export const generateDelivery = (payload: { task_type: string; request: string; context?: string }) =>
  api.post('/agents/delivery/generate', payload).then(r => r.data)

// ── Leads ────────────────────────────────────────────────────────────
export const getLeads = (params?: {
  page?: number
  page_size?: number
  status?: string
  min_score?: number
  source?: string
}) => api.get('/leads', { params }).then(r => r.data)

export const getLead = (id: number) =>
  api.get(`/leads/${id}`).then(r => r.data)

export const updateLead = (id: number, data: { status?: string; score?: number }) =>
  api.patch(`/leads/${id}`, data).then(r => r.data)

export const deleteLead = (id: number) =>
  api.delete(`/leads/${id}`).then(r => r.data)

// ── Proposals ────────────────────────────────────────────────────────
export const getProposals = (params?: {
  page?: number
  page_size?: number
  is_approved?: boolean
  is_sent?: boolean
}) => api.get('/proposals', { params }).then(r => r.data)

export const approveProposal = (id: number) =>
  api.post(`/proposals/${id}/approve`).then(r => r.data)

export const rejectProposal = (id: number) =>
  api.post(`/proposals/${id}/reject`).then(r => r.data)

export const updateProposal = (id: number, data: Record<string, unknown>) =>
  api.patch(`/proposals/${id}`, data).then(r => r.data)

// ── Outreach ─────────────────────────────────────────────────────────
export const getOutreach = (params?: {
  page?: number
  page_size?: number
  status?: string
  channel?: string
}) => api.get('/outreach', { params }).then(r => r.data)

export const approveOutreach = (id: number) =>
  api.post(`/outreach/${id}/approve`).then(r => r.data)

export const rejectOutreach = (id: number) =>
  api.post(`/outreach/${id}/reject`).then(r => r.data)

export const markReplied = (id: number) =>
  api.patch(`/outreach/${id}/replied`).then(r => r.data)

export const getOutreachStats = () =>
  api.get('/outreach/stats').then(r => r.data)

// ── Revenue ──────────────────────────────────────────────────────────
export const getRevenueStats = () =>
  api.get('/revenue/stats').then(r => r.data)

export const getDeals = (params?: { page?: number; status?: string }) =>
  api.get('/revenue', { params }).then(r => r.data)

export const createDeal = (data: { lead_id: number; amount: number; status?: string; notes?: string }) =>
  api.post('/revenue', data).then(r => r.data)

export const updateDeal = (id: number, data: Record<string, unknown>) =>
  api.patch(`/revenue/${id}`, data).then(r => r.data)
