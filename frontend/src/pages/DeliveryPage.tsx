import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Cpu, Send, RefreshCw, Copy, Check } from 'lucide-react'
import { generateDelivery } from '../services/api'
import clsx from 'clsx'

const TASK_TYPES = [
  { value: 'code', label: 'Code Generation', emoji: '💻' },
  { value: 'bugfix', label: 'Bug Fix', emoji: '🐛' },
  { value: 'api_design', label: 'API Design', emoji: '🔌' },
  { value: 'documentation', label: 'Documentation', emoji: '📝' },
  { value: 'general', label: 'General', emoji: '🤖' },
]

export default function DeliveryPage() {
  const [taskType, setTaskType] = useState('code')
  const [request, setRequest] = useState('')
  const [context, setContext] = useState('')
  const [copied, setCopied] = useState(false)

  const mutation = useMutation({
    mutationFn: () => generateDelivery({ task_type: taskType, request, context }),
  })

  const handleCopy = () => {
    if (mutation.data?.result) {
      navigator.clipboard.writeText(mutation.data.result)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Cpu size={20} className="text-violet-400" /> AI Delivery Assistant
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Accelerate gig delivery with AI-powered code, bug fixes, and docs
        </p>
      </div>

      {/* Task type selector */}
      <div className="flex gap-2 flex-wrap">
        {TASK_TYPES.map(t => (
          <button
            key={t.value}
            className={clsx(
              'px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5',
              taskType === t.value
                ? 'bg-violet-900 text-violet-200 border border-violet-700'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200 border border-transparent'
            )}
            onClick={() => setTaskType(t.value)}
          >
            <span>{t.emoji}</span> {t.label}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="card space-y-4">
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
            What do you need?
          </label>
          <textarea
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white resize-none focus:outline-none focus:border-violet-600"
            rows={4}
            placeholder={
              taskType === 'code' ? 'e.g. Create a Spring Boot REST endpoint for user registration with validation...' :
              taskType === 'bugfix' ? 'e.g. NullPointerException in UserService.findById() when user not in cache...' :
              taskType === 'api_design' ? 'e.g. Design a payment processing API with retry logic and webhooks...' :
              taskType === 'documentation' ? 'e.g. Write documentation for our Kafka consumer setup...' :
              'Describe your task...'
            }
            value={request}
            onChange={e => setRequest(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
            Context (optional)
          </label>
          <textarea
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white resize-none focus:outline-none focus:border-violet-600"
            rows={3}
            placeholder="Paste existing code, error messages, or additional context..."
            value={context}
            onChange={e => setContext(e.target.value)}
          />
        </div>
        <button
          className="btn-primary flex items-center gap-2 w-full justify-center"
          onClick={() => mutation.mutate()}
          disabled={!request.trim() || mutation.isPending}
        >
          {mutation.isPending ? (
            <><RefreshCw size={15} className="animate-spin" /> Generating...</>
          ) : (
            <><Send size={15} /> Generate</>
          )}
        </button>
      </div>

      {/* Result */}
      {mutation.isSuccess && mutation.data && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-violet-300">
              Result {mutation.data.tokens_used > 0 && (
                <span className="text-xs text-gray-600 ml-2">({mutation.data.tokens_used} tokens)</span>
              )}
            </span>
            <button
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
              onClick={handleCopy}
            >
              {copied ? <><Check size={13} className="text-emerald-400" /> Copied</> : <><Copy size={13} /> Copy</>}
            </button>
          </div>
          <pre className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed overflow-auto max-h-96 bg-gray-800/50 rounded-lg p-4">
            {mutation.data.result}
          </pre>
        </div>
      )}

      {mutation.isError && (
        <div className="card border-rose-800 text-rose-300 text-sm">
          Error: {(mutation.error as Error)?.message}
        </div>
      )}
    </div>
  )
}
