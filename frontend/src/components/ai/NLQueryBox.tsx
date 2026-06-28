import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { postNLQuery } from '@/api/endpoints'
import { Button } from '@/components/ui/button'
import { Send, Sparkles, Lock, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'

const SUGGESTED = [
  'What is the current flood risk for this AOI?',
  'Are there any active algal bloom warnings?',
  'Which choke points have the highest constriction score?',
  'Summarise oil slick detections from the last 7 days.',
]

interface Message {
  role: 'user' | 'assistant'
  text: string
  citations?: string[]
}

export function NLQueryBox({ className }: { className?: string }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: postNLQuery,
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.answer, citations: data.citations },
      ])
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Unable to process your question. Please try again.' },
      ])
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, mutation.isPending])

  function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed || mutation.isPending) return
    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setInput('')
    mutation.mutate({ question: trimmed })
    inputRef.current?.focus()
  }

  return (
    <div className={cn('flex flex-col rounded-xl border border-slate-800 bg-[#0f1623] overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-slate-800/60 shrink-0">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-600/15">
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
        </div>
        <p className="text-sm font-semibold text-slate-200 flex-1">AI Assistant</p>
        <div className="flex items-center gap-1 text-[10px] text-slate-600">
          <Lock className="h-2.5 w-2.5" />
          Read-only · Advisory
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0" role="log" aria-live="polite" aria-label="Conversation">
        {messages.length === 0 && (
          <div className="space-y-2 animate-fade-in">
            <p className="text-label text-slate-600 mb-3">Suggested questions</p>
            {SUGGESTED.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className={cn(
                  'w-full text-left flex items-center gap-2.5 rounded-lg border border-slate-800',
                  'bg-[#141d2e]/50 px-3 py-2.5',
                  'text-xs text-slate-400 hover:text-slate-200 hover:bg-[#141d2e] hover:border-slate-700',
                  'transition-all duration-150',
                )}
              >
                <ArrowRight className="h-3 w-3 text-slate-700 shrink-0" aria-hidden="true" />
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              'animate-fade-in-up',
              msg.role === 'user' ? 'flex justify-end' : 'flex justify-start',
            )}
          >
            {msg.role === 'assistant' && (
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600/15 mr-2 mt-0.5 shrink-0">
                <Sparkles className="h-3 w-3 text-blue-400" />
              </div>
            )}
            <div
              className={cn(
                'max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed',
                msg.role === 'user'
                  ? 'bg-blue-600/20 text-blue-100 border border-blue-600/20 rounded-tr-sm'
                  : 'bg-[#141d2e] text-slate-200 border border-slate-800/60 rounded-tl-sm',
              )}
            >
              <p>{msg.text}</p>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-slate-700/50">
                  <p className="text-label text-slate-600 mb-1.5">Sources</p>
                  <div className="flex flex-col gap-1">
                    {msg.citations.map((c, j) => (
                      <div key={j} className="flex items-center gap-1.5 text-[11px] text-slate-500" title={c}>
                        <span className="citation-badge">{j + 1}</span>
                        <span className="font-mono truncate">{c}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {mutation.isPending && (
          <div className="flex items-center gap-2 animate-fade-in">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600/15 shrink-0">
              <Sparkles className="h-3 w-3 text-blue-400" />
            </div>
            <div className="flex items-center gap-1 bg-[#141d2e] border border-slate-800/60 rounded-xl rounded-tl-sm px-4 py-3">
              <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-slate-500 inline-block" />
              <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-slate-500 inline-block" />
              <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-slate-500 inline-block" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-3 py-3 border-t border-slate-800/60 shrink-0">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(input)
            }
          }}
          placeholder="Ask about observations, risk, or trends…"
          aria-label="Ask a question about environmental data"
          disabled={mutation.isPending}
          className={cn(
            'flex-1 h-9 rounded-lg border border-[#1e293b] bg-[#141d2e]',
            'px-3 text-sm text-slate-200 placeholder:text-slate-700',
            'focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/15',
            'disabled:opacity-50 transition-colors',
          )}
        />
        <Button
          size="icon"
          onClick={() => send(input)}
          disabled={!input.trim() || mutation.isPending}
          aria-label="Send message"
          className="h-9 w-9 shrink-0"
        >
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
      <p className="text-center text-[10px] text-slate-700 pb-2">
        Enter to send · AI responses are advisory and require human review
      </p>
    </div>
  )
}
