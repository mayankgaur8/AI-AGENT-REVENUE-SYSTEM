import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar
} from 'recharts'
import {
  Play, RefreshCw, Target, FileText, Send, TrendingUp,
  CheckCircle, AlertCircle, Clock, Zap, ShieldCheck, Sparkles, XCircle
} from 'lucide-react'
import { getRevenueStats, runDailyPipeline, API_BASE_URL, getActionQueue } from '../services/api'
import clsx from 'clsx'

function StatCard({
  label, value, sub, icon: Icon, color = 'sky'
}: {
  label: string; value: string | number; sub?: string
  icon: React.ElementType; color?: string
}) {
  const colors: Record<string, string> = {
    sky: 'text-sky-400 bg-sky-900/30',
    emerald: 'text-emerald-400 bg-emerald-900/30',
    amber: 'text-amber-400 bg-amber-900/30',
    rose: 'text-rose-400 bg-rose-900/30',
    violet: 'text-violet-400 bg-violet-900/30',
  }
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
        <div className={clsx('p-1.5 rounded-lg', colors[color] ?? colors.sky)}>
          <Icon size={14} className={colors[color]?.split(' ')[0]} />
        </div>
      </div>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </div>
  )
}

function HealthBadge({ health }: { health: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    excellent: { label: 'Excellent', cls: 'bg-emerald-900 text-emerald-300' },
    good: { label: 'Good', cls: 'bg-sky-900 text-sky-300' },
    building: { label: 'Building', cls: 'bg-amber-900 text-amber-300' },
    starting: { label: 'Starting', cls: 'bg-violet-900 text-violet-300' },
    needs_leads: { label: 'Needs Leads', cls: 'bg-rose-900 text-rose-300' },
  }
  const { label, cls } = map[health] ?? { label: health, cls: 'bg-gray-800 text-gray-300' }
  return <span className={clsx('badge', cls)}>{label}</span>
}

export default function Dashboard() {
  const qc = useQueryClient()
  const [runLog, setRunLog] = useState<string | null>(null)

  const { data: stats, isLoading, isError: statsError } = useQuery({
    queryKey: ['revenue-stats'],
    queryFn: getRevenueStats,
    refetchInterval: 60_000,
    retry: 1,
  })

  const { data: actionQueue } = useQuery({
    queryKey: ['action-queue'],
    queryFn: getActionQueue,
    refetchInterval: 60_000,
  })

  const runMutation = useMutation({
    mutationFn: () => runDailyPipeline(true, 20),
    onSuccess: (data) => {
      setRunLog(JSON.stringify(data.summary, null, 2))
      qc.invalidateQueries({ queryKey: ['revenue-stats'] })
      qc.invalidateQueries({ queryKey: ['action-queue'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['proposals'] })
      qc.invalidateQueries({ queryKey: ['outreach'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <RefreshCw className="animate-spin mr-2" size={16} /> Loading...
      </div>
    )
  }

  if (statsError) {
    return (
      <div className="card border-rose-800 text-rose-300 text-sm space-y-2">
        <div className="flex items-center gap-2 font-semibold">
          <AlertCircle size={16} /> Backend unreachable
        </div>
        <p className="text-rose-400 text-xs">
          Failed to load stats from: <code className="bg-gray-800 px-1 rounded">{API_BASE_URL}/revenue/stats</code>
        </p>
        <p className="text-gray-500 text-xs">
          Check browser console for the exact error. Verify Azure is running and CORS allows this origin.
        </p>
      </div>
    )
  }

  const s = stats?.summary ?? {}
  const rev = stats?.revenue ?? {}
  const rates = stats?.rates ?? {}
  const health = stats?.health ?? 'needs_leads'
  const queueSummary = actionQueue?.summary ?? {}
  const topActionLeads = actionQueue?.top_action_leads ?? []

  const barData = [
    { name: 'Leads', value: s.total_leads ?? 0, fill: '#0ea5e9' },
    { name: 'Qualified', value: s.qualified_leads ?? 0, fill: '#38bdf8' },
    { name: 'Proposals', value: s.proposals_sent ?? 0, fill: '#818cf8' },
    { name: 'Responses', value: s.responses_received ?? 0, fill: '#34d399' },
    { name: 'Won', value: s.deals_won ?? 0, fill: '#10b981' },
  ]

  const targetPct = Math.min(rev.target_progress_pct ?? 0, 100)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">
            Target: €{rev.monthly_target_eur?.toLocaleString()} / month
            <span className="ml-3"><HealthBadge health={health} /></span>
          </p>
        </div>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
        >
          {runMutation.isPending ? (
            <><RefreshCw size={15} className="animate-spin" /> Running...</>
          ) : (
            <><Play size={15} /> Run Agents</>
          )}
        </button>
      </div>

      {/* Revenue progress */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-300">Monthly Revenue Progress</span>
          <span className="text-sm text-gray-400">{targetPct}%</span>
        </div>
        <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-sky-600 to-emerald-500 rounded-full transition-all"
            style={{ width: `${targetPct}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>€{rev.total_earned_eur?.toLocaleString() ?? 0} earned</span>
          <span>€{rev.remaining_to_target_eur?.toLocaleString() ?? rev.monthly_target_eur} remaining</span>
        </div>
        {(rev.pipeline_value_eur ?? 0) > 0 && (
          <p className="text-xs text-amber-400 mt-1">
            + €{rev.pipeline_value_eur?.toLocaleString()} in pipeline
          </p>
        )}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Leads" value={s.total_leads ?? 0} icon={Target} color="sky" />
        <StatCard label="Proposals Sent" value={s.proposals_sent ?? 0} icon={FileText} color="violet" />
        <StatCard
          label="Response Rate"
          value={`${rates.response_rate_pct ?? 0}%`}
          sub={`${s.responses_received ?? 0} replies`}
          icon={Send}
          color="emerald"
        />
        <StatCard
          label="Conversion"
          value={`${rates.conversion_rate_pct ?? 0}%`}
          sub={`${s.deals_won ?? 0} won`}
          icon={TrendingUp}
          color="amber"
        />
      </div>

      <div className="card">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-300">Best Action Workflow</h2>
            <p className="text-xs text-gray-500 mt-1">
              What to send next, what must be reviewed, and which variant is winning today.
            </p>
          </div>
          <Link to="/approval-queue" className="btn-secondary text-sm">
            Open Queue
          </Link>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Auto-Send Ready"
            value={queueSummary.auto_send_ready ?? 0}
            sub="Trusted email/direct only"
            icon={Sparkles}
            color="emerald"
          />
          <StatCard
            label="Needs Manual Approval"
            value={queueSummary.needs_manual_approval ?? 0}
            sub="Safeguard for Upwork, LinkedIn, Freelancer"
            icon={ShieldCheck}
            color="amber"
          />
          <StatCard
            label="Rejected by Predictor"
            value={queueSummary.rejected_by_predictor ?? 0}
            sub="Saved for future analysis"
            icon={XCircle}
            color="rose"
          />
          <StatCard
            label="Best Variant Today"
            value={queueSummary.best_variant_today ?? 'A'}
            sub="Current recommended proposal style"
            icon={Zap}
            color="violet"
          />
        </div>
      </div>

      {/* Pipeline chart */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Pipeline Funnel</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={barData} barSize={36}>
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {barData.map((entry, i) => (
                <rect key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Deal status mini cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card flex items-center gap-3">
          <CheckCircle className="text-emerald-400 shrink-0" size={20} />
          <div>
            <p className="text-lg font-bold text-white">{s.deals_won ?? 0}</p>
            <p className="text-xs text-gray-500">Deals Won</p>
          </div>
        </div>
        <div className="card flex items-center gap-3">
          <Clock className="text-amber-400 shrink-0" size={20} />
          <div>
            <p className="text-lg font-bold text-white">{s.deals_pending ?? 0}</p>
            <p className="text-xs text-gray-500">Pending</p>
          </div>
        </div>
        <div className="card flex items-center gap-3">
          <AlertCircle className="text-rose-400 shrink-0" size={20} />
          <div>
            <p className="text-lg font-bold text-white">{s.deals_lost ?? 0}</p>
            <p className="text-xs text-gray-500">Lost</p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-300">Top 5 Leads To Act On First</h2>
            <p className="text-xs text-gray-500 mt-1">
              Revenue-first queue ranked by budget, stack fit, speed, and predicted conversion.
            </p>
          </div>
          <span className="badge bg-sky-900 text-sky-300">{topActionLeads.length} visible</span>
        </div>
        {topActionLeads.length === 0 ? (
          <p className="text-sm text-gray-500">Run the pipeline to generate reviewable leads.</p>
        ) : (
          <div className="space-y-3">
            {topActionLeads.map((lead: any, index: number) => (
              <div key={lead.outreach_id} className="rounded-xl border border-gray-800 bg-gray-800/60 px-4 py-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="badge bg-gray-950 text-gray-300">#{index + 1}</span>
                      <span className="badge bg-violet-900 text-violet-300">Variant {lead.chosen_variant}</span>
                      <span className="badge bg-amber-900 text-amber-300 capitalize">{lead.platform}</span>
                    </div>
                    <p className="font-medium text-white">{lead.title}</p>
                    <p className="text-sm text-gray-500">{lead.company || 'Independent client'}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-semibold text-white">{Math.round((lead.deal_probability ?? 0) * 100)}% deal</p>
                    <p className="text-xs text-gray-500">{Math.round((lead.reply_probability ?? 0) * 100)}% reply</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 mt-3 text-xs text-gray-400">
                  <span>Score: <span className="text-gray-200">{lead.score}</span></span>
                  <span>Budget: <span className="text-gray-200">{lead.budget_value ? `EUR ${Math.round(lead.budget_value)}` : lead.budget || 'Unknown'}</span></span>
                  <span>Action: <span className="text-sky-300">{lead.policy_label}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Run log */}
      {runMutation.isSuccess && runLog && (
        <div className="card border-emerald-800">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={14} className="text-emerald-400" />
            <span className="text-sm font-medium text-emerald-300">Pipeline Run Complete</span>
          </div>
          <pre className="text-xs text-gray-400 whitespace-pre-wrap">{runLog}</pre>
        </div>
      )}
      {runMutation.isError && (
        <div className="card border-rose-800 text-rose-300 text-sm space-y-1">
          <div className="font-semibold">Pipeline failed: {(runMutation.error as Error)?.message}</div>
          <div className="text-rose-400 text-xs">
            Endpoint: <code className="bg-gray-800 px-1 rounded">{API_BASE_URL}/agents/run-daily</code>
          </div>
          <div className="text-gray-500 text-xs">Check browser console (F12 → Network) for the full error.</div>
        </div>
      )}
    </div>
  )
}
