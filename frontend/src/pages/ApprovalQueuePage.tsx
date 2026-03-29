import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, RefreshCw, ShieldAlert, Sparkles, XCircle } from 'lucide-react'

import {
  getActionQueue,
  approveOutreach,
  approveProposal,
  rejectOutreach,
  rejectProposal,
} from '../services/api'

function pct(value: number) {
  return `${Math.round((value ?? 0) * 100)}%`
}

export default function ApprovalQueuePage() {
  const qc = useQueryClient()
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['action-queue'],
    queryFn: getActionQueue,
    refetchInterval: 60_000,
  })

  const refreshAll = () => {
    qc.invalidateQueries({ queryKey: ['action-queue'] })
    qc.invalidateQueries({ queryKey: ['outreach'] })
    qc.invalidateQueries({ queryKey: ['proposals'] })
    qc.invalidateQueries({ queryKey: ['revenue-stats'] })
    qc.invalidateQueries({ queryKey: ['leads'] })
  }

  const approveProposalMutation = useMutation({
    mutationFn: approveProposal,
    onSuccess: refreshAll,
  })
  const sendMutation = useMutation({
    mutationFn: approveOutreach,
    onSuccess: refreshAll,
  })
  const rejectProposalMutation = useMutation({
    mutationFn: rejectProposal,
    onSuccess: refreshAll,
  })
  const rejectOutreachMutation = useMutation({
    mutationFn: rejectOutreach,
    onSuccess: refreshAll,
  })

  const items = data?.items ?? []
  const topFirst = useMemo(() => items.slice(0, 8), [items])
  const summary = data?.summary ?? {}
  const policy = data?.policy ?? {}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldAlert size={20} className="text-amber-400" /> Approval Queue
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Revenue-first review queue with channel safeguards before any real send.
          </p>
        </div>
        <button className="btn-secondary flex items-center gap-2" onClick={() => refetch()}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Auto-Send Ready</span>
          <p className="text-2xl font-bold text-white">{summary.auto_send_ready ?? 0}</p>
          <p className="text-xs text-gray-500">Trusted email/direct templates only</p>
        </div>
        <div className="stat-card">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Needs Manual Approval</span>
          <p className="text-2xl font-bold text-white">{summary.needs_manual_approval ?? 0}</p>
          <p className="text-xs text-gray-500">Upwork, LinkedIn, Freelancer are protected</p>
        </div>
        <div className="stat-card">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Best Variant Today</span>
          <p className="text-2xl font-bold text-white">{summary.best_variant_today ?? 'A'}</p>
          <p className="text-xs text-gray-500">Current A/B winner for new proposals</p>
        </div>
        <div className="stat-card">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Feedback Logged</span>
          <p className="text-2xl font-bold text-white">{summary.feedback_events_logged ?? 0}</p>
          <p className="text-xs text-gray-500">Persistent outcomes feeding optimization</p>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={15} className="text-sky-400" />
          <h2 className="text-sm font-semibold text-gray-300">Send Policy</h2>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm text-gray-300">
          {Object.entries(policy).map(([platform, rule]) => (
            <div key={platform} className="rounded-lg bg-gray-800/70 px-3 py-2 border border-gray-700">
              <p className="text-xs uppercase tracking-wide text-gray-500">{platform}</p>
              <p className="mt-1">{String(rule)}</p>
            </div>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="card text-gray-500 flex items-center justify-center gap-2 py-16">
          <RefreshCw size={16} className="animate-spin" /> Loading approval queue...
        </div>
      ) : topFirst.length === 0 ? (
        <div className="card text-center py-16 text-gray-500">
          No approval items waiting right now.
        </div>
      ) : (
        <div className="space-y-4">
          {topFirst.map((item: any, index: number) => (
            <div key={item.outreach_id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className="badge bg-sky-900 text-sky-300">Top {index + 1}</span>
                    <span className="badge bg-gray-800 text-gray-300 capitalize">{item.platform}</span>
                    <span className="badge bg-amber-900 text-amber-300">{item.policy_label}</span>
                    <span className="badge bg-violet-900 text-violet-300">Variant {item.chosen_variant}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                  <p className="text-sm text-gray-500">{item.company || 'Independent client'}</p>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Lead score</p>
                      <p className="text-sm text-white font-medium">{item.score}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Reply %</p>
                      <p className="text-sm text-white font-medium">{pct(item.reply_probability)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Deal %</p>
                      <p className="text-sm text-white font-medium">{pct(item.deal_probability)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Budget</p>
                      <p className="text-sm text-white font-medium">
                        {item.budget_value ? `EUR ${Math.round(item.budget_value)}` : item.budget || 'Unknown'}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-sky-300 mt-4">{item.reason_to_act}</p>
                  <div className="mt-3 space-y-2">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Proposal preview</p>
                      <p className="text-sm text-gray-300">{item.proposal_preview || 'No proposal preview available.'}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Outreach preview</p>
                      <p className="text-sm text-gray-300">{item.outreach_preview}</p>
                    </div>
                  </div>
                </div>
                <div className="shrink-0 flex flex-col gap-2 w-40">
                  <button
                    className="btn-success flex items-center justify-center gap-2"
                    onClick={() => {
                      if (item.proposal_id) approveProposalMutation.mutate(item.proposal_id)
                      sendMutation.mutate(item.outreach_id)
                    }}
                    disabled={approveProposalMutation.isPending || sendMutation.isPending}
                  >
                    <CheckCircle size={14} /> Send Now
                  </button>
                  <Link to="/proposals" className="btn-secondary text-center">
                    Edit
                  </Link>
                  <button
                    className="btn-danger flex items-center justify-center gap-2"
                    onClick={() => {
                      if (item.proposal_id) rejectProposalMutation.mutate(item.proposal_id)
                      rejectOutreachMutation.mutate(item.outreach_id)
                    }}
                    disabled={rejectProposalMutation.isPending || rejectOutreachMutation.isPending}
                  >
                    <XCircle size={14} /> Reject
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
