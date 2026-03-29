import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Target, FileText,
  Send, TrendingUp, Zap, Cpu, ShieldCheck
} from 'lucide-react'
import clsx from 'clsx'

import Dashboard from './pages/Dashboard'
import LeadsPage from './pages/LeadsPage'
import ProposalsPage from './pages/ProposalsPage'
import OutreachPage from './pages/OutreachPage'
import RevenuePage from './pages/RevenuePage'
import DeliveryPage from './pages/DeliveryPage'
import ApprovalQueuePage from './pages/ApprovalQueuePage'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/leads', label: 'Leads', icon: Target },
  { to: '/proposals', label: 'Proposals', icon: FileText },
  { to: '/approval-queue', label: 'Approval Queue', icon: ShieldCheck },
  { to: '/outreach', label: 'Outreach', icon: Send },
  { to: '/revenue', label: 'Revenue', icon: TrendingUp },
  { to: '/delivery', label: 'AI Delivery', icon: Cpu },
]

function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col min-h-screen">
      <div className="px-5 py-6 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Zap className="text-sky-400" size={20} />
          <span className="font-bold text-white text-sm">Revenue Agent</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">€2000/month target</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sky-900/60 text-sky-300'
                  : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-800 text-xs text-gray-600">
        v1.0.0 — 17yr Java Expert
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/leads" element={<LeadsPage />} />
            <Route path="/proposals" element={<ProposalsPage />} />
            <Route path="/approval-queue" element={<ApprovalQueuePage />} />
            <Route path="/outreach" element={<OutreachPage />} />
            <Route path="/revenue" element={<RevenuePage />} />
            <Route path="/delivery" element={<DeliveryPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
