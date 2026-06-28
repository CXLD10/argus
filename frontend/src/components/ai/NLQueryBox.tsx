import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { postNLQuery } from '@/api/endpoints'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { Send, BookOpen, Bot } from 'lucide-react'
import { cn } from '@/lib/utils'

const SUGGESTED = [
  'What is the current flood risk in this AOI?',
  'Are there any active algal bloom warnings?',
  'What are the top choke points by constriction score?',
  'How many oil slick detections this week?',
]

interface Message {
  role: 'user' | 'assistant'
  text: string
  citations?: string[]
  model?: string
}

export function NLQueryBox({ className }: { className?: string }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])

  const mutation = useMutation({
    mutationFn: postNLQuery,
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.answer, citations: data.citations, model: data.model },
      ])
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Sorry, an error occurred. Please try again.' },
      ])
    },
  })

  function send(text: string) {
    if (!text.trim()) return
    setMessages((prev) => [...prev, { role: 'user', text }])
    setInput('')
    mutation.mutate({ question: text })
  }

  return (
    <div className={cn('flex flex-col rounded-xl border border-slate-800 bg-slate-900', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
        <Bot className="h-4 w-4 text-blue-400" />
        <p className="text-sm font-medium text-slate-200">AI Assistant</p>
        <Badge variant="warning" className="ml-auto text-[10px]">Read-only</Badge>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0 max-h-96">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-500">Suggested questions:</p>
            {SUGGESTED.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="w-full text-left rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2
                  text-xs text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              'rounded-lg px-3 py-2.5 text-sm leading-relaxed',
              msg.role === 'user'
                ? 'bg-blue-600/20 text-blue-100 ml-8 border border-blue-600/20'
                : 'bg-slate-800 text-slate-200 mr-8',
            )}
          >
            <p>{msg.text}</p>
            {msg.citations && msg.citations.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {msg.citations.map((c, j) => (
                  <span
                    key={j}
                    className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-mono
                      bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    title={c}
                  >
                    <BookOpen className="h-2.5 w-2.5" />
                    {c.slice(0, 8)}…
                  </span>
                ))}
              </div>
            )}
            {msg.model && (
              <p className="text-[10px] text-slate-600 mt-1.5">Model: {msg.model}</p>
            )}
          </div>
        ))}

        {mutation.isPending && (
          <div className="flex items-center gap-2 text-xs text-slate-500 mr-8">
            <Spinner className="h-3 w-3" />
            Thinking…
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-4 py-3 border-t border-slate-800">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send(input))}
          placeholder="Ask about observations, risk, or trends…"
          className={cn(
            'flex-1 h-8 rounded-lg border border-slate-700 bg-slate-800',
            'px-3 text-sm text-slate-200 placeholder:text-slate-600',
            'focus:outline-none focus:border-blue-500/50',
          )}
          disabled={mutation.isPending}
        />
        <Button
          size="icon"
          onClick={() => send(input)}
          disabled={!input.trim() || mutation.isPending}
          className="h-8 w-8"
        >
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
