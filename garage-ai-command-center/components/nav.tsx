"use client"

import { useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Headphones, PhoneOff, Calendar, X } from "lucide-react"
import { useGarageStore } from "@/lib/store"

function TorxFlowLogo() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2L21.66 7.5V16.5L12 22L2.34 16.5V7.5L12 2Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="2" fill="currentColor" />
    </svg>
  )
}

const navLinks = [
  { href: "/", label: "Dashboard" },
  { href: "/calendar", label: "Calendar" },
  { href: "/history", label: "History" },
]

export function Nav() {
  const pathname = usePathname()
  const wsStatus = useGarageStore((s) => s.wsStatus)
  const connect = useGarageStore((s) => s.connect)
  const disconnect = useGarageStore((s) => s.disconnect)
  const calendarConnected = useGarageStore((s) => s.calendarConnected)
  const calendarLoading = useGarageStore((s) => s.calendarLoading)
  const checkCalendarStatus = useGarageStore((s) => s.checkCalendarStatus)
  const disconnectCalendar = useGarageStore((s) => s.disconnectCalendar)

  const isConnected = wsStatus === "connected"

  // Check status on mount + after OAuth redirect
  useEffect(() => {
    checkCalendarStatus()
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("calendar") === "connected") {
      window.history.replaceState({}, "", window.location.pathname)
    }
  }, [checkCalendarStatus])

  const bridgeUrl = typeof window !== "undefined" ? window.location.origin : ""

  return (
    <header className="flex items-center justify-between border-b border-border bg-white px-4 py-2">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <span className="text-[#ea580c]">
            <TorxFlowLogo />
          </span>
          <span className="text-lg font-semibold tracking-tight text-foreground">
            TorxFlow
          </span>
        </div>
        <nav className="flex items-center gap-1">
          {navLinks.map((link) => {
            const isActive = pathname === link.href
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? "text-[#ea580c] bg-[#ea580c]/5"
                    : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                }`}
              >
                {link.label}
                {isActive && (
                  <span className="block h-0.5 mt-0.5 rounded-full bg-[#ea580c]" />
                )}
              </Link>
            )
          })}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        {/* Calendar connection */}
        {calendarLoading ? null : calendarConnected ? (
          <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-600">
            <Calendar className="h-3.5 w-3.5" />
            Calendar
            <button
              onClick={disconnectCalendar}
              className="ml-1 rounded-full p-0.5 hover:bg-emerald-500/20 transition-colors"
              title="Disconnect Google Calendar"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <a
            href={`${bridgeUrl}/api/calendar/auth`}
            className="flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-surface-3"
          >
            <Calendar className="h-3.5 w-3.5" />
            Connect Calendar
          </a>
        )}

        {/* Call connection */}
        {isConnected ? (
          <button
            onClick={disconnect}
            className="flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-500 transition-colors hover:bg-red-500/20"
          >
            <PhoneOff className="h-3.5 w-3.5" />
            Talking to Harry
          </button>
        ) : (
          <button
            onClick={connect}
            className="flex items-center gap-1.5 rounded-full bg-[#ea580c] px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-colors hover:bg-[#dc4f08]"
          >
            <Headphones className="h-3.5 w-3.5" />
            Talk to Harry
          </button>
        )}
      </div>
    </header>
  )
}
