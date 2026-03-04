"use client"

import { Nav } from "@/components/nav"

const calendarId = process.env.NEXT_PUBLIC_GOOGLE_CALENDAR_ID || "primary"
const embedUrl = `https://calendar.google.com/calendar/embed?src=${encodeURIComponent(calendarId)}&showTitle=0&showPrint=0&showTabs=0&showCalendars=0`

export default function CalendarPage() {
  const connected = calendarId !== "primary"

  return (
    <div className="flex h-screen flex-col bg-background">
      <Nav />
      <main className="flex-1 overflow-hidden p-4">
        {connected ? (
          <iframe
            src={embedUrl}
            className="h-full w-full rounded-2xl border border-[hsl(var(--card-border))]"
            title="Google Calendar"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 rounded-2xl border border-[hsl(var(--card-border))] bg-card">
            <h2 className="text-sm font-semibold text-foreground">Connect Google Calendar</h2>
            <p className="max-w-md text-center text-xs text-muted-foreground">
              Set the <code className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px]">NEXT_PUBLIC_GOOGLE_CALENDAR_ID</code> environment variable to your Google Calendar ID to embed your calendar here.
            </p>
            <p className="text-[10px] text-muted-foreground/60">
              This should match the backend&apos;s <code className="rounded bg-surface-2 px-1 py-0.5">GOOGLE_CALENDAR_ID</code> value.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
