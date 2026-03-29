import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, RefreshCw, MessageSquare, CheckCircle, Reply } from 'lucide-react'
import { getOutreach, approveOutreach, markReplied } from '../services/api'
import clsx from 'clsx'

const CHANNEL_ICONS: Record<string, string> = {
  upwork: '💼',
  linkedin: '🔗',
  email: '📧',
  freelancer: '🧑‍💻',
  direct: '📨',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-900 text-amber-300',
  sent: 'bg-sky-900 text-sky-300',
  failed: 'bg-rose-900 text-rose-300',
  replied: 'bg-emerald-900 text-emerald-300',
}

export default function OutreachPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['outreach', page, statusFilter],
    queryFn: () => getOutreach({ page, page_size: 20, status: statusFilter || undefined }),
  })

  const approveMutation = useMutation({
    mutationFn: approveOutreach,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['outreach'] }),
  })

  const replyMutation = useMutation({
    mutationFn: markReplied,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outreach'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const logs = data?.outreach_logs ?? []
  const total = data?.total ?? 0
  const pending = logs.filter((l: any) => l.status === 'pending').length

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Send size={20} className="text-emerald-400" /> Outreach
          </h1>
          <p className="text-gray-500 text-sm">
            {total} total
            {pending > 0 && (
              <span className="ml-2 badge bg-amber-900 text-amber-300">{pending} pending approval</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="bg-gray-800 text-gray-300 rounded-lg px-3 py-1.5 text-sm border border-gray-700"
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="sent">Sent</option>
            <option value="replied">Replied</option>
          </select>
          <button className="btn-secondary flex items-center gap-1 text-sm" onClick={() => refetch()}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-500 py-12">
          <RefreshCw className="animate-spin mx-auto mb-2" size={20} />
        </div>
      ) : logs.length === 0 ? (
        <div className="card text-center py-16 text-gray-500">
          <MessageSquare size={40} className="mx-auto mb-3 opacity-30" />
          <p>No outreach messages yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log: any) => (
            <div key={log.id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-base">{CHANNEL_ICONS[log.channel] ?? '📤'}</span>
                    <span className={clsx('badge', STATUS_COLORS[log.status] ?? 'bg-gray-800 text-gray-400')}>
                      {log.status}
                    </span>
                    <span className="badge bg-gray-800 text-gray-400 capitalize">{log.channel}</span>
                  </div>
                  <h3 className="font-semibold text-white truncate">{log.lead_title}</h3>
                  <p className="text-sm text-gray-500">{log.lead_company}</p>
                  {log.sent_at && (
                    <p className="text-xs text-gray-600 mt-0.5">
                      Sent: {new Date(log.sent_at).toLocaleString()}
                    </p>
                  )}
                  <p className="text-sm text-gray-400 mt-2 line-clamp-2">
                    {log.message}
                  </p>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  {log.status === 'pending' && (
                    <button
                      className="btn-success flex items-center gap-1 text-xs"
                      onClick={() => approveMutation.mutate(log.id)}
                      disabled={approveMutation.isPending}
                    >
                      <CheckCircle size={12} /> Send
                    </button>
                  )}
                  {log.status === 'sent' && (
                    <button
                      className="btn-secondary flex items-center gap-1 text-xs"
                      onClick={() => replyMutation.mutate(log.id)}
                    >
                      <Reply size={12} /> Got Reply
                    </button>
                  )}
                  <button
                    className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
                    onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                  >
                    {expandedId === log.id ? 'Hide' : 'Full msg'}
                  </button>
                </div>
              </div>
              {expandedId === log.id && (
                <div className="mt-3 pt-3 border-t border-gray-800">
                  <p className="text-sm text-gray-300 whitespace-pre-wrap">{log.message}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
