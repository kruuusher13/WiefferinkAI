"use client"

import { Maximize2 } from "lucide-react"
import { useRouter } from "next/navigation"

const calendarId = process.env.NEXT_PUBLIC_GOOGLE_CALENDAR_ID || "primary"
const embedUrl = `https://calendar.google.com/calendar/embed?src=${encodeURIComponent(calendarId)}&mode=WEEK&showTitle=0&showNav=1&showPrint=0&showTabs=0&showCalendars=0&ctz=Europe/Amsterdam`

export function CalendarEmbed({
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const router = useRouter()

  const connected = calendarId !== "primary"

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-[hsl(var(--card-border))] bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <h2 className="text-xs font-semibold text-foreground">Calendar</h2>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${connected ? "bg-green-500/10 text-green-600" : "bg-neutral-100 text-muted-foreground"}`}>
            {connected ? "CONNECTED" : "DEFAULT"}
          </span>
        </div>
        <button
          onClick={() => router.push("/calendar")}
          className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          aria-label="Open full calendar"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-hidden">
        {connected ? (
          <iframe
            src={embedUrl}
            className="h-full w-full border-0"
            title="Google Calendar"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center">
            <p className="text-xs text-muted-foreground">
              Set <code className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px]">NEXT_PUBLIC_GOOGLE_CALENDAR_ID</code> to embed your Google Calendar.
            </p>
            <p className="text-[10px] text-muted-foreground/60">
              Using default calendar. Click maximize to view full page.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
