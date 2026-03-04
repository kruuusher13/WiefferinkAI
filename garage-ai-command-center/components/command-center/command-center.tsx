"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { AnimatePresence, motion } from "framer-motion"
import { StatusBar } from "./status-bar"
import { LiveStream } from "./live-stream"
import { VehicleContext } from "./vehicle-context"
import { ActionQueue } from "./action-queue"
import { CallStats } from "./call-stats"
import { CalendarEmbed } from "./calendar-embed"

type FocusedPanel = "call-stats" | "live-stream" | "vehicle-context" | "action-queue" | "calendar-embed" | null

const panelTransition = { duration: 0.35, ease: [0.22, 1, 0.36, 1] }

export function CommandCenter() {
  const [focusedPanel, setFocusedPanel] = useState<FocusedPanel>(null)
  const router = useRouter()

  const toggleFocus = useCallback(
    (panel: FocusedPanel) => {
      if (panel === "calendar-embed") {
        router.push("/calendar")
        return
      }
      setFocusedPanel((prev) => (prev === panel ? null : panel))
    },
    [router]
  )

  const isAnyFocused = focusedPanel !== null

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
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
              {focusedPanel === "call-stats" && (
                <CallStats isFocused onToggleFocus={() => toggleFocus("call-stats")} />
              )}
              {focusedPanel === "live-stream" && (
                <LiveStream isFocused onToggleFocus={() => toggleFocus("live-stream")} />
              )}
              {focusedPanel === "vehicle-context" && (
                <VehicleContext isFocused onToggleFocus={() => toggleFocus("vehicle-context")} />
              )}
              {focusedPanel === "action-queue" && (
                <ActionQueue isFocused onToggleFocus={() => toggleFocus("action-queue")} />
              )}
            </motion.div>
          ) : (
            /* 2-column grid: Left 2fr / Right 3fr */
            <motion.div
              key="grid"
              className="grid h-full gap-3"
              style={{
                gridTemplateColumns: "2fr 3fr",
                gridTemplateRows: "1fr",
              }}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={panelTransition}
            >
              {/* Left column: CallStats (auto) + LiveStream (1fr) */}
              <div className="grid min-h-0 grid-rows-[auto_1fr] gap-3">
                <div className="min-h-0">
                  <CallStats isFocused={false} onToggleFocus={() => toggleFocus("call-stats")} />
                </div>
                <div className="min-h-0">
                  <LiveStream isFocused={false} onToggleFocus={() => toggleFocus("live-stream")} />
                </div>
              </div>

              {/* Right column: Vehicle + Actions + Calendar */}
              <div className="grid min-h-0 grid-rows-[1fr_1fr_1fr] gap-3">
                <div className="min-h-0">
                  <VehicleContext isFocused={false} onToggleFocus={() => toggleFocus("vehicle-context")} />
                </div>
                <div className="min-h-0">
                  <ActionQueue isFocused={false} onToggleFocus={() => toggleFocus("action-queue")} />
                </div>
                <div className="min-h-0">
                  <CalendarEmbed isFocused={false} onToggleFocus={() => toggleFocus("calendar-embed")} />
                </div>
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
