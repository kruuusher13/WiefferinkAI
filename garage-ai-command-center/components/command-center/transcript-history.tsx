"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Maximize2, Minimize2, ArrowLeft, Phone, Globe } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

interface TranscriptEntry {
  role: string
  text: string
  timestamp: string
  type: string
}

interface TranscriptSummary {
  id: string
  date: string
  channel: string
  duration: number
  preview: string
  message_count: number
}

interface TranscriptDetail {
  id: string
  channel: string
  date: string
  duration: number
  message_count: number
  transcript: TranscriptEntry[]
  tools_used: { name: string; args: Record<string, string>; timestamp: string }[]
  sentiments: string[]
}

function formatDuration(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleDateString("nl-NL", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
  } catch {
    return iso
  }
}

export function TranscriptHistory({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const [transcripts, setTranscripts] = useState<TranscriptSummary[]>([])
  const [selected, setSelected] = useState<TranscriptDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const fetchList = useCallback(async () => {
    try {
      const resp = await fetch("/api/transcripts")
      const data = await resp.json()
      setTranscripts(data)
    } catch {
      // Silently fail
    }
  }, [])

  useEffect(() => {
    fetchList()
  }, [fetchList])

  const openTranscript = useCallback(async (id: string) => {
    setLoading(true)
    try {
      const resp = await fetch(`/api/transcripts/${encodeURIComponent(id)}`)
      const data = await resp.json()
      setSelected(data)
    } catch {
      // Silently fail
    }
    setLoading(false)
  }, [])

  // Auto-scroll detail view
  useEffect(() => {
    if (scrollRef.current && selected) {
      scrollRef.current.scrollTo({ top: 0 })
    }
  }, [selected])

  const roleLabel = (role: string) => {
    if (role === "assistant") return "HARRY"
    if (role === "user") return "CALLER"
    return "SYSTEM"
  }

  const roleColor = (role: string) => {
    if (role === "assistant") return "text-syntax-cyan"
    if (role === "user") return "text-syntax-orange"
    return "text-muted-foreground"
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-surface-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <div className="flex items-center gap-2">
          {selected && (
            <button
              onClick={() => setSelected(null)}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
            >
              <ArrowLeft size={13} />
            </button>
          )}
          <span className="font-mono text-[11px] font-semibold tracking-wide text-muted-foreground">
            {selected ? `transcript/${selected.id.split("_")[2] || selected.channel}` : "transcript-history"}
          </span>
          {!selected && transcripts.length > 0 && (
            <span className="rounded-sm bg-muted-foreground/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              {transcripts.length}
            </span>
          )}
        </div>
        <button
          onClick={onToggleFocus}
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
        >
          {isFocused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
        </button>
      </div>

      {/* Body */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <span className="font-mono text-xs text-muted-foreground/50">Loading...</span>
          </div>
        )}

        {!loading && !selected && (
          <div className="flex flex-col">
            {transcripts.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <span className="font-mono text-xs text-muted-foreground/50">
                  No transcripts yet
                </span>
              </div>
            ) : (
              transcripts.map((t) => (
                <button
                  key={t.id}
                  onClick={() => openTranscript(t.id)}
                  className="flex items-center gap-3 border-b border-border/50 px-3 py-2 text-left transition-colors hover:bg-surface-2/50"
                >
                  <span className="shrink-0 text-muted-foreground">
                    {t.channel === "twilio" ? <Phone size={12} /> : <Globe size={12} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-foreground">
                        {formatDate(t.date)}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {formatDuration(t.duration)}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {t.message_count} msgs
                      </span>
                    </div>
                    {t.preview && (
                      <p className="truncate font-mono text-[10px] text-muted-foreground/70">
                        {t.preview}
                      </p>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        )}

        {!loading && selected && (
          <div className="flex flex-col gap-1 px-3 py-2">
            <AnimatePresence mode="popLayout">
              {selected.transcript.map((entry, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.15, delay: Math.min(i * 0.02, 0.5) }}
                  className="group flex gap-3 rounded-md px-2 py-1 transition-colors hover:bg-surface-2/50"
                >
                  <span className="shrink-0 font-mono text-[10px] leading-5 text-muted-foreground/60">
                    {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""}
                  </span>
                  <span className={`shrink-0 font-mono text-[10px] font-semibold leading-5 ${roleColor(entry.role)}`}>
                    {roleLabel(entry.role)}
                  </span>
                  <span className={`font-mono text-xs leading-5 ${entry.type === "tool_call" || entry.type === "tool_result" ? "text-muted-foreground/60 italic" : "text-foreground/80"}`}>
                    {entry.text}
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
