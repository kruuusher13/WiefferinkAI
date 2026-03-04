"use client"

import { useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Maximize2, Minimize2 } from "lucide-react"
import { Waveform } from "./waveform"
import { useGarageStore } from "@/lib/store"

const KEYWORD_COLORS: Record<string, string> = {
  afspraak: "text-[#ea580c]",
  kosten: "text-amber-600",
  klaar: "text-green-600",
  morgen: "text-violet-600",
  auto: "text-pink-600",
  reparatie: "text-[#ea580c]",
  band: "text-amber-600",
  olie: "text-green-600",
  apk: "text-violet-600",
  betaling: "text-pink-600",
  kenteken: "text-[#ea580c]",
  beurt: "text-amber-600",
  remmen: "text-green-600",
}

function highlightKeywords(text: string, keywords?: string[]) {
  if (!keywords || keywords.length === 0) return text

  const parts: { text: string; color?: string }[] = []
  let remaining = text.toLowerCase()
  let originalRemaining = text

  while (originalRemaining.length > 0) {
    let earliestMatch = -1
    let earliestKeyword = ""
    let earliestColor = ""

    for (const keyword of keywords) {
      const idx = remaining.indexOf(keyword)
      if (idx !== -1 && (earliestMatch === -1 || idx < earliestMatch)) {
        earliestMatch = idx
        earliestKeyword = keyword
        earliestColor = KEYWORD_COLORS[keyword] || "text-[#ea580c]"
      }
    }

    if (earliestMatch === -1) {
      parts.push({ text: originalRemaining })
      break
    }

    if (earliestMatch > 0) {
      parts.push({ text: originalRemaining.slice(0, earliestMatch) })
    }

    parts.push({
      text: originalRemaining.slice(earliestMatch, earliestMatch + earliestKeyword.length),
      color: earliestColor,
    })

    originalRemaining = originalRemaining.slice(earliestMatch + earliestKeyword.length)
    remaining = remaining.slice(earliestMatch + earliestKeyword.length)
  }

  return parts.map((part, i) =>
    part.color ? (
      <span key={i} className={`${part.color} font-semibold`}>
        {part.text}
      </span>
    ) : (
      <span key={i}>{part.text}</span>
    )
  )
}

export function LiveStream({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const transcript = useGarageStore((s) => s.transcript)
  const callState = useGarageStore((s) => s.callState)
  const audioLevel = useGarageStore((s) => s.audioLevel)
  const wsStatus = useGarageStore((s) => s.wsStatus)
  const scrollRef = useRef<HTMLDivElement>(null)

  const isActive = wsStatus === "connected"
  const hasTranscript = transcript.length > 0

  // Auto-scroll to bottom on new transcript
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }, [transcript.length])

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-[hsl(var(--card-border))] bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className={`h-3 w-3 rounded-full ${isActive ? "bg-red-500" : "bg-neutral-200"}`} />
            <span className={`h-3 w-3 rounded-full ${isActive ? "bg-amber-500" : "bg-neutral-200"}`} />
            <span className={`h-3 w-3 rounded-full ${isActive ? "bg-green-500" : "bg-neutral-200"}`} />
          </div>
          <h2 className="text-xs font-semibold text-foreground">
            Live Transcript
          </h2>
          {isActive ? (
            <span className="rounded-full bg-[#ea580c]/10 px-2 py-0.5 text-[10px] font-medium text-[#ea580c]">
              ACTIVE
            </span>
          ) : (
            <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              WAITING
            </span>
          )}
        </div>
        <button
          onClick={onToggleFocus}
          className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          aria-label={isFocused ? "Minimize" : "Maximize"}
        >
          {isFocused ? (
            <Minimize2 className="h-3.5 w-3.5" />
          ) : (
            <Maximize2 className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* Transcript */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3">
        <div className="flex flex-col gap-1">
          {!hasTranscript && (
            <div className="flex items-center justify-center py-8">
              <span className="text-xs text-muted-foreground/50">
                {isActive ? "Waiting for conversation..." : "Connect to start"}
              </span>
            </div>
          )}
          <AnimatePresence mode="popLayout">
            {transcript.map((line) => (
              <motion.div
                key={line.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="group flex gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-surface-2/50"
              >
                <span className="shrink-0 font-mono text-[10px] leading-5 text-muted-foreground">
                  {line.timestamp}
                </span>
                <span
                  className={`shrink-0 text-[10px] font-semibold leading-5 ${
                    line.speaker === "harry"
                      ? "text-[#ea580c]"
                      : "text-amber-600"
                  }`}
                >
                  {line.speaker === "harry" ? "HARRY" : "CALLER"}
                </span>
                <span className="text-xs leading-5 text-foreground/80">
                  {highlightKeywords(line.text, line.keywords)}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing indicator when Harry is processing */}
          <AnimatePresence>
            {callState === "processing" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-3 px-2 py-1.5"
              >
                <span className="shrink-0 font-mono text-[10px] text-muted-foreground/40">
                  {"      "}
                </span>
                <span className="shrink-0 text-[10px] font-semibold text-[#ea580c]/50">
                  HARRY
                </span>
                <span className="flex items-center gap-1">
                  <span className="h-1 w-1 animate-pulse rounded-full bg-muted-foreground/40" />
                  <span className="h-1 w-1 animate-pulse rounded-full bg-muted-foreground/40" style={{ animationDelay: "0.2s" }} />
                  <span className="h-1 w-1 animate-pulse rounded-full bg-muted-foreground/40" style={{ animationDelay: "0.4s" }} />
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Waveform */}
      <div className="border-t border-border px-4 py-2">
        <Waveform isActive={callState === "harry_talking"} audioLevel={audioLevel} />
      </div>
    </div>
  )
}
