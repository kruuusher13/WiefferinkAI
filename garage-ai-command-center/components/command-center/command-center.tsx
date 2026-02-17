"use client"

import { useState, useCallback, useEffect } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { StatusBar } from "./status-bar"
import { LiveStream } from "./live-stream"
import { HarryThoughts } from "./harry-thoughts"
import { VehicleContext } from "./vehicle-context"
import { ActionQueue } from "./action-queue"
import { VoiceWidget } from "./voice-widget"
import { CustomInstructions } from "./custom-instructions"
import { TranscriptHistory } from "./transcript-history"
import { useGarageStore } from "@/lib/store"

type FocusedPanel = "voice-widget" | "live-stream" | "harry-thoughts" | "vehicle-context" | "action-queue" | "custom-instructions" | "transcript-history" | null

function useCallTimer() {
  const callStartTime = useGarageStore((s) => s.callStartTime)
  const [display, setDisplay] = useState("00:00")

  useEffect(() => {
    if (!callStartTime) {
      setDisplay("00:00")
      return
    }
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - callStartTime) / 1000)
      const m = String(Math.floor(elapsed / 60)).padStart(2, "0")
      const s = String(elapsed % 60).padStart(2, "0")
      setDisplay(`${m}:${s}`)
    }, 1000)
    return () => clearInterval(interval)
  }, [callStartTime])

  return display
}

const panelTransition = { duration: 0.35, ease: [0.22, 1, 0.36, 1] }

export function CommandCenter() {
  const [focusedPanel, setFocusedPanel] = useState<FocusedPanel>(null)
  const callTime = useCallTimer()
  const customerName = useGarageStore((s) => s.customerName)
  const wsStatus = useGarageStore((s) => s.wsStatus)

  const toggleFocus = useCallback(
    (panel: FocusedPanel) => {
      setFocusedPanel((prev) => (prev === panel ? null : panel))
    },
    []
  )

  const isAnyFocused = focusedPanel !== null

  return (
    <div className="flex h-screen flex-col bg-surface-0">
      {/* Top header bar */}
      <header className="flex items-center justify-between border-b border-border bg-surface-1 px-4 py-2">
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs font-semibold tracking-wide text-syntax-cyan">
            GarageAI
          </span>
          <span className="font-mono text-[10px] text-muted-foreground/60">
            Command Center
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-muted-foreground">
            <span className="tabular-nums text-foreground">{callTime}</span>
          </span>
          <div className="h-4 w-px bg-border" />
          <span className="font-mono text-[11px] text-muted-foreground">
            <span className="text-syntax-cyan">
              {customerName || (wsStatus === "connected" ? "Identifying..." : "—")}
            </span>
          </span>
        </div>
      </header>

      {/* Main workspace */}
      <main className="flex-1 overflow-hidden p-3">
        <AnimatePresence mode="popLayout">
          {isAnyFocused ? (
            /* Focus mode: single expanded panel */
            <motion.div
              key="focused"
              className="h-full"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={panelTransition}
            >
              {focusedPanel === "voice-widget" && (
                <VoiceWidget
                  isFocused
                  onToggleFocus={() => toggleFocus("voice-widget")}
                />
              )}
              {focusedPanel === "live-stream" && (
                <LiveStream
                  isFocused
                  onToggleFocus={() => toggleFocus("live-stream")}
                />
              )}
              {focusedPanel === "harry-thoughts" && (
                <HarryThoughts
                  isFocused
                  onToggleFocus={() => toggleFocus("harry-thoughts")}
                />
              )}
              {focusedPanel === "vehicle-context" && (
                <VehicleContext
                  isFocused
                  onToggleFocus={() => toggleFocus("vehicle-context")}
                />
              )}
              {focusedPanel === "action-queue" && (
                <ActionQueue
                  isFocused
                  onToggleFocus={() => toggleFocus("action-queue")}
                />
              )}
              {focusedPanel === "custom-instructions" && (
                <CustomInstructions
                  isFocused
                  onToggleFocus={() => toggleFocus("custom-instructions")}
                />
              )}
              {focusedPanel === "transcript-history" && (
                <TranscriptHistory
                  isFocused
                  onToggleFocus={() => toggleFocus("transcript-history")}
                />
              )}
            </motion.div>
          ) : (
            /* Bento grid: 4 rows x 2 cols */
            <motion.div
              key="grid"
              className="grid h-full gap-3"
              style={{
                gridTemplateColumns: "1fr 1fr",
                gridTemplateRows: "2fr 2fr 2fr 1fr",
              }}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={panelTransition}
            >
              {/* Row 1: Voice Widget + Live Stream (conversation) */}
              <div className="min-h-0">
                <VoiceWidget
                  isFocused={false}
                  onToggleFocus={() => toggleFocus("voice-widget")}
                />
              </div>
              <div className="min-h-0">
                <LiveStream
                  isFocused={false}
                  onToggleFocus={() => toggleFocus("live-stream")}
                />
              </div>

              {/* Row 2: Harry's Thoughts + Vehicle Context */}
              <div className="min-h-0">
                <HarryThoughts
                  isFocused={false}
                  onToggleFocus={() => toggleFocus("harry-thoughts")}
                />
              </div>
              <div className="min-h-0">
                <VehicleContext
                  isFocused={false}
                  onToggleFocus={() => toggleFocus("vehicle-context")}
                />
              </div>

              {/* Row 3: Action Queue + Transcript History */}
              <div className="min-h-0">
                <ActionQueue
                  isFocused={false}
                  onToggleFocus={() => toggleFocus("action-queue")}
                />
              </div>
              <div className="min-h-0">
                <TranscriptHistory
                  isFocused={false}
                  onToggleFocus={() => toggleFocus("transcript-history")}
                />
              </div>

              {/* Row 4: Custom Instructions (full width) */}
              <div className="min-h-0 col-span-2">
                <CustomInstructions
                  isFocused={false}
                  onToggleFocus={() => toggleFocus("custom-instructions")}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Status bar */}
      <StatusBar />
    </div>
  )
}
