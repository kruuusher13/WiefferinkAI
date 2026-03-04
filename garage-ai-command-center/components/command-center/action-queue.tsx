"use client"

import { motion, AnimatePresence } from "framer-motion"
import { Check, Pencil, Maximize2, Minimize2, ExternalLink } from "lucide-react"
import { useGarageStore } from "@/lib/store"

function DiffView({
  current,
  proposed,
  status,
}: {
  current: Record<string, string>
  proposed: Record<string, string>
  status: string
}) {
  // Filter out the 'result' meta-field from display
  const displayKeys = Object.keys(proposed).filter((k) => k !== "result")

  return (
    <div className="mt-2.5 rounded-lg border border-border/50 bg-surface-2 p-2.5 font-mono text-[11px]">
      {displayKeys.map((key) => {
        const changed = current[key] !== proposed[key]
        return (
          <div key={key} className="flex items-center gap-2 py-0.5">
            <span className="w-24 shrink-0 text-muted-foreground">{key}</span>
            {changed && status === "pending" ? (
              <>
                {current[key] && (
                  <>
                    <span className="text-red-400 line-through">{current[key]}</span>
                    <span className="text-muted-foreground">{"-->"}</span>
                  </>
                )}
                <span className="text-green-600">{proposed[key]}</span>
              </>
            ) : (
              <span className={status === "accepted" ? "text-green-600" : "text-foreground/70"}>
                {proposed[key]}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function ActionQueue({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const proposals = useGarageStore((s) => s.proposals)
  const acceptProposal = useGarageStore((s) => s.acceptProposal)
  const editProposal = useGarageStore((s) => s.editProposal)
  const wsStatus = useGarageStore((s) => s.wsStatus)

  const pendingCount = proposals.filter((p) => p.status === "pending").length

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-[hsl(var(--card-border))] bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <h2 className="text-xs font-semibold text-foreground">
            Actions
          </h2>
          <span className="rounded-full bg-[#ea580c]/10 px-2 py-0.5 text-[10px] font-medium text-[#ea580c]">
            {pendingCount} PENDING
          </span>
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

      {/* Proposals List */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="flex flex-col gap-2.5">
          {proposals.length === 0 && (
            <div className="flex items-center justify-center py-8">
              <span className="text-xs text-muted-foreground/50">
                {wsStatus === "connected" ? "Waiting for actions..." : "Connect to start"}
              </span>
            </div>
          )}
          <AnimatePresence>
            {proposals.map((proposal, i) => (
              <motion.div
                key={proposal.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i * 0.05 }}
                className={`rounded-lg border p-3 transition-colors ${
                  proposal.status === "accepted"
                    ? "border-green-500/20 bg-green-50"
                    : "border-border/50 bg-surface-2"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full px-2 py-0.5 text-[10px] font-medium uppercase text-[#ea580c] bg-[#ea580c]/10">
                      appointment
                    </span>
                    <span className="text-xs font-medium text-foreground">
                      {proposal.title}
                    </span>
                  </div>
                  {proposal.status === "pending" && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => acceptProposal(proposal.id)}
                        className="rounded-lg p-1.5 text-green-600 transition-colors hover:bg-green-500/10"
                        aria-label="Accept proposal"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => editProposal(proposal.id)}
                        className="rounded-lg p-1.5 text-amber-600 transition-colors hover:bg-amber-500/10"
                        aria-label="Edit proposal"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                  {proposal.status === "accepted" && (
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-medium text-green-600">
                        ACCEPTED
                      </span>
                      {proposal.calendar_link && (
                        <a
                          href={proposal.calendar_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded-lg p-1 text-green-600 transition-colors hover:bg-green-500/10"
                          aria-label="Open in Google Calendar"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  )}
                  {proposal.status === "editing" && (
                    <span className="text-[10px] font-medium text-amber-600">
                      EDITING
                    </span>
                  )}
                </div>
                <DiffView
                  current={proposal.current}
                  proposed={proposal.proposed}
                  status={proposal.status}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
