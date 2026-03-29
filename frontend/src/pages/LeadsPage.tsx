import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Target, RefreshCw, ExternalLink, Star, Filter } from 'lucide-react'
import { getLeads, updateLead, deleteLead } from '../services/api'
import clsx from 'clsx'

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-gray-800 text-gray-300',
  scored: 'bg-sky-900 text-sky-300',
  proposal_sent: 'bg-violet-900 text-violet-300',
  responded: 'bg-emerald-900 text-emerald-300',
  closed_won: 'bg-emerald-700 text-white',
  closed_lost: 'bg-rose-900 text-rose-300',
  rejected: 'bg-gray-900 text-gray-600',
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 90 ? 'bg-emerald-700 text-white' :
    score >= 70 ? 'bg-sky-800 text-sky-200' :
    'bg-gray-800 text-gray-400'
  return (
    <span className={clsx('badge font-bold tabular-nums', color)}>
      {score}
    </span>
  )
}

export default function LeadsPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [minScore, setMinScore] = useState<number | undefined>(undefined)
  const [statusFilter, setStatusFilter] = useState('')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['leads', page, minScore, statusFilter],
    queryFn: () => getLeads({ page, page_size: 20, min_score: minScore, status: statusFilter || undefined }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      updateLead(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteLead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })

  const leads = data?.leads ?? []
  const total = data?.total ?? 0
  const pages = data?.pages ?? 1

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Target size={20} className="text-sky-400" /> Leads
          </h1>
          <p className="text-gray-500 text-sm">{total} total</p>
        </div>
        <button className="btn-secondary flex items-center gap-2" onClick={() => refetch()}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-gray-500" />
          <select
            className="bg-gray-800 text-gray-300 rounded-lg px-3 py-1.5 text-sm border border-gray-700"
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="scored">Scored</option>
            <option value="proposal_sent">Proposal Sent</option>
            <option value="responded">Responded</option>
            <option value="closed_won">Won</option>
          </select>
        </div>
        <select
          className="bg-gray-800 text-gray-300 rounded-lg px-3 py-1.5 text-sm border border-gray-700"
          value={minScore ?? ''}
          onChange={e => { setMinScore(e.target.value ? Number(e.target.value) : undefined); setPage(1) }}
        >
          <option value="">Min Score</option>
          <option value="70">≥ 70</option>
          <option value="80">≥ 80</option>
          <option value="90">≥ 90</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center text-gray-500 py-12">
          <RefreshCw className="animate-spin mx-auto mb-2" size={20} />
          Loading leads...
        </div>
      ) : leads.length === 0 ? (
        <div className="card text-center py-16 text-gray-500">
          <Target size={40} className="mx-auto mb-3 opacity-30" />
          <p>No leads yet. Run the pipeline to fetch opportunities.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {leads.map((lead: any) => (
            <div key={lead.id} className="card hover:border-gray-700 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <ScoreBadge score={lead.score} />
                    <span className={clsx('badge', STATUS_COLORS[lead.status] ?? 'bg-gray-800 text-gray-400')}>
                      {lead.status.replace('_', ' ')}
                    </span>
                    {lead.is_remote === 1 && (
                      <span className="badge bg-teal-900 text-teal-300">Remote</span>
                    )}
                    <span className="badge bg-gray-800 text-gray-400">{lead.source}</span>
                  </div>
                  <h3 className="font-semibold text-white mt-2 truncate">{lead.title}</h3>
                  <p className="text-sm text-gray-400">{lead.company || 'Unknown company'}</p>
                  {lead.budget && (
                    <p className="text-sm text-emerald-400 mt-0.5 font-medium">{lead.budget}</p>
                  )}
                  {lead.score_reasons?.length > 0 && (
                    <div className="flex gap-1.5 flex-wrap mt-2">
                      {lead.score_reasons.slice(0, 3).map((r: string, i: number) => (
                        <span key={i} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">
                          {r}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {lead.url && (
                    <a
                      href={lead.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded hover:bg-gray-800 text-gray-500 hover:text-gray-300 transition-colors"
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}
                  <select
                    className="bg-gray-800 text-gray-300 rounded px-2 py-1 text-xs border border-gray-700"
                    value={lead.status}
                    onChange={e => updateMutation.mutate({ id: lead.id, status: e.target.value })}
                  >
                    <option value="new">New</option>
                    <option value="scored">Scored</option>
                    <option value="proposal_sent">Sent</option>
                    <option value="responded">Responded</option>
                    <option value="closed_won">Won</option>
                    <option value="closed_lost">Lost</option>
                    <option value="rejected">Rejected</option>
                  </select>
                  <button
                    className="text-gray-600 hover:text-rose-400 transition-colors text-xs"
                    onClick={() => deleteMutation.mutate(lead.id)}
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button className="btn-secondary text-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
            Prev
          </button>
          <span className="text-gray-500 text-sm">{page} / {pages}</span>
          <button className="btn-secondary text-sm" disabled={page === pages} onClick={() => setPage(p => p + 1)}>
            Next
          </button>
        </div>
      )}
    </div>
  )
}
