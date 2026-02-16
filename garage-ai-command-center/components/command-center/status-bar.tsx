"use client"

import { useGarageStore } from "@/lib/store"

export function StatusBar() {
  const wsStatus = useGarageStore((s) => s.wsStatus)
  const callState = useGarageStore((s) => s.callState)
  const isMicActive = useGarageStore((s) => s.isMicActive)

  const statusColor =
    wsStatus === "connected"
      ? "bg-syntax-lime"
      : wsStatus === "connecting"
        ? "bg-syntax-orange"
        : "bg-muted-foreground"

  const statusText =
    wsStatus === "connected"
      ? "Harry: Online"
      : wsStatus === "connecting"
        ? "Harry: Connecting..."
        : "Harry: Offline"

  const statusTextColor =
    wsStatus === "connected"
      ? "text-syntax-lime"
      : wsStatus === "connecting"
        ? "text-syntax-orange"
        : "text-muted-foreground"

  return (
    <footer className="flex items-center justify-between border-t border-border bg-surface-1 px-4 py-1.5 font-mono text-[11px]">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            {wsStatus === "connected" && (
              <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${statusColor} opacity-75`} />
            )}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${statusColor}`} />
          </span>
          <span className={statusTextColor}>{statusText}</span>
        </span>
        <span className="text-muted-foreground">
          State:{" "}
          <span className="text-syntax-cyan">{callState}</span>
        </span>
        <span className="text-muted-foreground">
          Mic:{" "}
          <span className={isMicActive ? "text-syntax-lime" : "text-muted-foreground"}>
            {isMicActive ? "Active" : "Off"}
          </span>
        </span>
      </div>
      <div className="flex items-center gap-4 text-muted-foreground">
        <span>GarageAI v2.4.1</span>
        <span>NL-West</span>
      </div>
    </footer>
  )
}
