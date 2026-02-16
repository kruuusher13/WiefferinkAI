"use client"

import { motion, AnimatePresence } from "framer-motion"
import { Check, Pencil, Maximize2, Minimize2 } from "lucide-react"
import { useGarageStore } from "@/lib/store"

const TYPE_COLORS: Record<string, string> = {
  appointment: "text-syntax-cyan bg-syntax-cyan/10",
  invoice: "text-syntax-orange bg-syntax-orange/10",
  notification: "text-syntax-lime bg-syntax-lime/10",
  part_check: "text-syntax-purple bg-syntax-purple/10",
}

function DiffView({
  current,
  proposed,
  status,
}: {
  current: Record<string, string>
  proposed: Record<string, string>
  status: string
}) {
  return (
    <div className="mt-2.5 rounded-md border border-border/50 bg-surface-0 p-2.5 font-mono text-[11px]">
      {Object.keys(proposed).map((key) => {
        const changed = current[key] !== proposed[key]
        return (
          <div key={key} className="flex items-center gap-2 py-0.5">
            <span className="w-20 shrink-0 text-muted-foreground">{key}</span>
            {changed && status === "pending" ? (
              <>
                {current[key] && (
                  <>
                    <span className="text-destructive/60 line-through">{current[key]}</span>
                    <span className="text-muted-foreground">{"-->"}</span>
                  </>
                )}
                <span className="text-syntax-lime">{proposed[key]}</span>
              </>
            ) : (
              <span className={status === "accepted" ? "text-syntax-lime" : "text-foreground/70"}>
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
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-surface-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <h2 className="font-mono text-xs font-medium text-foreground">
            action_queue.proposals
          </h2>
          <span className="rounded-sm bg-syntax-purple/10 px-1.5 py-0.5 font-mono text-[10px] text-syntax-purple">
            {pendingCount} PENDING
          </span>
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

      {/* Proposals List */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="flex flex-col gap-2.5">
          {proposals.length === 0 && (
            <div className="flex items-center justify-center py-8">
              <span className="font-mono text-xs text-muted-foreground/50">
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
                className={`rounded-md border p-3 transition-colors ${
                  proposal.status === "accepted"
                    ? "border-syntax-lime/20 bg-syntax-lime/5"
                    : "border-border/50 bg-surface-0"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] uppercase ${
                        TYPE_COLORS[proposal.type] || "text-muted-foreground bg-muted-foreground/10"
                      }`}
                    >
                      {proposal.type}
                    </span>
                    <span className="font-mono text-xs text-foreground">
                      {proposal.title}
                    </span>
                  </div>
                  {proposal.status === "pending" && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => acceptProposal(proposal.id)}
                        className="rounded-md p-1.5 text-syntax-lime transition-colors hover:bg-syntax-lime/10"
                        aria-label="Accept proposal"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => editProposal(proposal.id)}
                        className="rounded-md p-1.5 text-syntax-orange transition-colors hover:bg-syntax-orange/10"
                        aria-label="Edit proposal"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                  {proposal.status === "accepted" && (
                    <span className="font-mono text-[10px] text-syntax-lime">
                      ACCEPTED
                    </span>
                  )}
                  {proposal.status === "editing" && (
                    <span className="font-mono text-[10px] text-syntax-orange">
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
