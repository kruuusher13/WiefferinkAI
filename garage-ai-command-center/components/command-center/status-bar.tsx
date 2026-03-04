"use client"

import { useGarageStore } from "@/lib/store"

export function StatusBar() {
  const wsStatus = useGarageStore((s) => s.wsStatus)
  const callState = useGarageStore((s) => s.callState)
  const isMicActive = useGarageStore((s) => s.isMicActive)

  const statusColor =
    wsStatus === "connected"
      ? "bg-green-500"
      : wsStatus === "connecting"
        ? "bg-amber-500"
        : "bg-neutral-400"

  const statusText =
    wsStatus === "connected"
      ? "Harry: Online"
      : wsStatus === "connecting"
        ? "Harry: Connecting..."
        : "Harry: Offline"

  const statusTextColor =
    wsStatus === "connected"
      ? "text-green-600"
      : wsStatus === "connecting"
        ? "text-amber-600"
        : "text-muted-foreground"

  return (
    <footer className="flex items-center justify-between border-t border-border bg-white px-4 py-1.5 text-[11px]">
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
          <span className="font-medium text-foreground">{callState}</span>
        </span>
        <span className="text-muted-foreground">
          Mic:{" "}
          <span className={isMicActive ? "font-medium text-green-600" : "text-muted-foreground"}>
            {isMicActive ? "Active" : "Off"}
          </span>
        </span>
      </div>
      <div className="flex items-center gap-4 text-muted-foreground">
        <span>TorxFlow v1.0.0</span>
        <span>NL-West</span>
      </div>
    </footer>
  )
}
