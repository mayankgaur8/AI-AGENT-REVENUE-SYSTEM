import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, RefreshCw, CheckCircle, Send, ChevronDown, ChevronUp } from 'lucide-react'
import { getProposals, approveProposal } from '../services/api'
import clsx from 'clsx'

export default function ProposalsPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'sent'>('all')

  const params: Record<string, unknown> = { page, page_size: 20 }
  if (filter === 'pending') { params.is_approved = false; params.is_sent = false }
  if (filter === 'approved') { params.is_approved = true; params.is_sent = false }
  if (filter === 'sent') { params.is_sent = true }

  const { data, isLoading } = useQuery({
    queryKey: ['proposals', page, filter],
    queryFn: () => getProposals(params as any),
  })

  const approveMutation = useMutation({
    mutationFn: approveProposal,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['proposals'] }),
  })

  const proposals = data?.proposals ?? []
  const total = data?.total ?? 0

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText size={20} className="text-violet-400" /> Proposals
          </h1>
          <p className="text-gray-500 text-sm">{total} total</p>
        </div>
        <div className="flex gap-2">
          {(['all', 'pending', 'approved', 'sent'] as const).map(f => (
            <button
              key={f}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                filter === f
                  ? 'bg-violet-900 text-violet-300'
                  : 'bg-gray-800 text-gray-400 hover:text-gray-200'
              )}
              onClick={() => { setFilter(f); setPage(1) }}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-500 py-12">
          <RefreshCw className="animate-spin mx-auto mb-2" size={20} />
        </div>
      ) : proposals.length === 0 ? (
        <div className="card text-center py-16 text-gray-500">
          <FileText size={40} className="mx-auto mb-3 opacity-30" />
          <p>No proposals yet. Run the pipeline first.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map((p: any) => (
            <div key={p.id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    {p.is_sent && <span className="badge bg-emerald-900 text-emerald-300">Sent</span>}
                    {p.is_approved && !p.is_sent && <span className="badge bg-sky-900 text-sky-300">Approved</span>}
                    {!p.is_approved && <span className="badge bg-gray-800 text-gray-400">Pending Review</span>}
                    <span className="text-xs text-gray-500">{p.word_count} words</span>
                  </div>
                  <h3 className="font-semibold text-white truncate">{p.lead_title}</h3>
                  <p className="text-sm text-gray-500">{p.lead_company} · Score: {p.lead_score}</p>
                  {p.short_pitch && (
                    <p className="text-sm text-sky-300 mt-2 italic">"{p.short_pitch}"</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {!p.is_approved && (
                    <button
                      className="btn-success flex items-center gap-1"
                      onClick={() => approveMutation.mutate(p.id)}
                      disabled={approveMutation.isPending}
                    >
                      <CheckCircle size={13} /> Approve
                    </button>
                  )}
                  <button
                    className="p-1.5 rounded hover:bg-gray-800 text-gray-500 transition-colors"
                    onClick={() => setExpanded(expanded === p.id ? null : p.id)}
                  >
                    {expanded === p.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>
              </div>

              {expanded === p.id && (
                <div className="mt-4 space-y-4 border-t border-gray-800 pt-4">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Proposal</p>
                    <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                      {p.proposal_text}
                    </p>
                  </div>
                  {p.technical_approach && (
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Technical Approach</p>
                      <p className="text-sm text-gray-400 whitespace-pre-wrap">{p.technical_approach}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
