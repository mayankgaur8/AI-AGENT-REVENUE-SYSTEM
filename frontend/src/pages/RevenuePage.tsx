import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { TrendingUp, Plus, RefreshCw, DollarSign, CheckCircle, XCircle, Clock } from 'lucide-react'
import { getDeals, createDeal, updateDeal, getRevenueStats } from '../services/api'
import clsx from 'clsx'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  pending: { label: 'Pending', color: 'text-amber-400', icon: Clock },
  won: { label: 'Won', color: 'text-emerald-400', icon: CheckCircle },
  lost: { label: 'Lost', color: 'text-rose-400', icon: XCircle },
}

function NewDealModal({ onClose, onSave }: { onClose: () => void; onSave: (d: any) => void }) {
  const [form, setForm] = useState({ lead_id: '', amount: '', status: 'pending', notes: '' })
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-bold text-white mb-4">Record Deal</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Lead ID</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
              placeholder="e.g. 1"
              value={form.lead_id}
              onChange={e => setForm({ ...form, lead_id: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Amount (€)</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
              placeholder="e.g. 800"
              type="number"
              value={form.amount}
              onChange={e => setForm({ ...form, amount: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Status</label>
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
              value={form.status}
              onChange={e => setForm({ ...form, status: e.target.value })}
            >
              <option value="pending">Pending</option>
              <option value="won">Won</option>
              <option value="lost">Lost</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Notes</label>
            <textarea
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white resize-none"
              rows={2}
              value={form.notes}
              onChange={e => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button className="btn-primary flex-1" onClick={() => {
            if (!form.lead_id || !form.amount) return
            onSave({ lead_id: Number(form.lead_id), amount: Number(form.amount), status: form.status, notes: form.notes })
          }}>
            Save Deal
          </button>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

export default function RevenuePage() {
  const qc = useQueryClient()
  const [showModal, setShowModal] = useState(false)

  const { data: statsData } = useQuery({ queryKey: ['revenue-stats'], queryFn: getRevenueStats })
  const { data: dealsData, isLoading } = useQuery({ queryKey: ['deals'], queryFn: () => getDeals() })

  const createMutation = useMutation({
    mutationFn: createDeal,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['deals'] }); qc.invalidateQueries({ queryKey: ['revenue-stats'] }); setShowModal(false) },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: any) => updateDeal(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['deals'] }); qc.invalidateQueries({ queryKey: ['revenue-stats'] }) },
  })

  const deals = dealsData?.deals ?? []
  const rev = statsData?.revenue ?? {}
  const target = rev.monthly_target_eur ?? 2000
  const earned = rev.total_earned_eur ?? 0
  const pipeline = rev.pipeline_value_eur ?? 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <TrendingUp size={20} className="text-amber-400" /> Revenue
        </h1>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowModal(true)}>
          <Plus size={14} /> Record Deal
        </button>
      </div>

      {/* Revenue summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="stat-card">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Earned</span>
          <p className="text-2xl font-bold text-emerald-400">€{earned.toLocaleString()}</p>
          <p className="text-xs text-gray-500">{rev.target_progress_pct ?? 0}% of target</p>
        </div>
        <div className="stat-card">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Pipeline</span>
          <p className="text-2xl font-bold text-amber-400">€{pipeline.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Pending deals</p>
        </div>
        <div className="stat-card">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Remaining</span>
          <p className="text-2xl font-bold text-sky-400">
            €{(rev.remaining_to_target_eur ?? target).toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">To €{target.toLocaleString()} target</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="card">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-400">Monthly Target Progress</span>
          <span className="text-white font-medium">€{earned.toLocaleString()} / €{target.toLocaleString()}</span>
        </div>
        <div className="h-4 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-amber-500 to-emerald-500 rounded-full transition-all"
            style={{ width: `${Math.min((earned / target) * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Deals list */}
      {isLoading ? (
        <div className="text-center text-gray-500 py-8"><RefreshCw className="animate-spin mx-auto" size={20} /></div>
      ) : deals.length === 0 ? (
        <div className="card text-center py-16 text-gray-500">
          <DollarSign size={40} className="mx-auto mb-3 opacity-30" />
          <p>No deals recorded yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {deals.map((deal: any) => {
            const cfg = STATUS_CONFIG[deal.status] ?? STATUS_CONFIG.pending
            const Icon = cfg.icon
            return (
              <div key={deal.id} className="card flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <Icon size={18} className={cfg.color} />
                  <div>
                    <h3 className="font-medium text-white">{deal.lead_title || `Lead #${deal.lead_id}`}</h3>
                    <p className="text-sm text-gray-500">{deal.lead_company}</p>
                    {deal.notes && <p className="text-xs text-gray-600 mt-0.5">{deal.notes}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-lg font-bold text-white">€{deal.amount.toLocaleString()}</span>
                  <select
                    className="bg-gray-800 text-gray-300 rounded px-2 py-1 text-xs border border-gray-700"
                    value={deal.status}
                    onChange={e => updateMutation.mutate({ id: deal.id, status: e.target.value })}
                  >
                    <option value="pending">Pending</option>
                    <option value="won">Won</option>
                    <option value="lost">Lost</option>
                  </select>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showModal && (
        <NewDealModal
          onClose={() => setShowModal(false)}
          onSave={data => createMutation.mutate(data)}
        />
      )}
    </div>
  )
}
