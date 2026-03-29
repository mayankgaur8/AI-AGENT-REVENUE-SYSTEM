import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

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
