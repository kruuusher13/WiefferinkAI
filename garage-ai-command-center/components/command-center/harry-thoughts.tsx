"use client"

import { useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Maximize2, Minimize2, Brain } from "lucide-react"
import { useGarageStore } from "@/lib/store"

export function HarryThoughts({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const thoughts = useGarageStore((s) => s.thoughts)
  const wsStatus = useGarageStore((s) => s.wsStatus)
  const scrollRef = useRef<HTMLDivElement>(null)

  const isActive = wsStatus === "connected"
  const hasThoughts = thoughts.length > 0

  // Auto-scroll to bottom on new thought
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }, [thoughts.length])

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-surface-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <Brain className="h-3.5 w-3.5 text-syntax-purple" />
          <h2 className="font-mono text-xs font-medium text-foreground">
            harry_thoughts
          </h2>
          {isActive ? (
            <span className="rounded-sm bg-syntax-purple/10 px-1.5 py-0.5 font-mono text-[10px] text-syntax-purple">
              LIVE
            </span>
          ) : (
            <span className="rounded-sm bg-muted-foreground/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              IDLE
            </span>
          )}
        </div>
        <button
          onClick={onToggleFocus}
          className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          aria-label={isFocused ? "Minimize" : "Maximize"}
        >
          {isFocused ? (
            <Minimize2 className="h-3.5 w-3.5" />
          ) : (
            <Maximize2 className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* Thoughts stream */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3">
        <div className="flex flex-col gap-1.5">
          {!hasThoughts && (
            <div className="flex items-center justify-center py-8">
              <span className="font-mono text-xs text-muted-foreground/50">
                {isActive ? "Waiting for Harry to think..." : "Connect to start"}
              </span>
            </div>
          )}
          <AnimatePresence mode="popLayout">
            {thoughts.map((thought) => (
              <motion.div
                key={thought.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="group flex gap-3 rounded-md px-2 py-1 transition-colors hover:bg-surface-2/50"
              >
                <span className="shrink-0 font-mono text-[10px] leading-5 text-muted-foreground/50">
                  {thought.timestamp}
                </span>
                <span className="font-mono text-[11px] leading-5 text-syntax-purple/70 italic">
                  {thought.text}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
