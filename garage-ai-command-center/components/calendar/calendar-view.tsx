"use client"

import { useState, useEffect, useCallback } from "react"
import { ChevronLeft, ChevronRight, Clock, User, ExternalLink } from "lucide-react"
import {
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  format,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
  isToday,
} from "date-fns"
import { nl } from "date-fns/locale"

interface CalendarEvent {
  id: string
  summary: string
  start: string
  end: string
  description?: string
  htmlLink?: string
}

function parseCustomerName(description?: string): string | null {
  if (!description) return null
  const match = description.match(/(?:Klant|Customer|Naam):\s*(.+)/i)
  return match ? match[1].trim() : null
}

export function CalendarView() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [selectedDay, setSelectedDay] = useState<Date | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchEvents = useCallback(async () => {
    setLoading(true)
    try {
      const bridgeUrl = window.location.origin
      const resp = await fetch(`${bridgeUrl}/api/calendar/events?days=60`)
      const data = await resp.json()
      if (data.status === "success") {
        setEvents(data.events || [])
      } else {
        console.warn("Calendar fetch failed:", data)
      }
    } catch (err) {
      console.error("Calendar fetch error:", err)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const calendarStart = startOfWeek(monthStart, { weekStartsOn: 1 })
  const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: calendarStart, end: calendarEnd })

  const dayNames = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"]

  function getEventsForDay(day: Date): CalendarEvent[] {
    return events.filter((event) => {
      const eventDate = new Date(event.start)
      return isSameDay(eventDate, day)
    })
  }

  const selectedDayEvents = selectedDay ? getEventsForDay(selectedDay) : []

  return (
    <div className="flex h-full gap-4">
      {/* Calendar grid */}
      <div className="flex flex-1 flex-col rounded-2xl border border-[hsl(var(--card-border))] bg-card">
        {/* Month header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <button
            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <h2 className="text-sm font-semibold text-foreground capitalize">
            {format(currentMonth, "MMMM yyyy", { locale: nl })}
          </h2>
          <button
            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {/* Day names */}
        <div className="grid grid-cols-7 border-b border-border">
          {dayNames.map((name) => (
            <div key={name} className="py-2 text-center text-[10px] font-medium text-muted-foreground">
              {name}
            </div>
          ))}
        </div>

        {/* Day cells */}
        <div className="grid flex-1 grid-cols-7">
          {days.map((day) => {
            const dayEvents = getEventsForDay(day)
            const inMonth = isSameMonth(day, currentMonth)
            const today = isToday(day)
            const isSelected = selectedDay && isSameDay(day, selectedDay)

            return (
              <button
                key={day.toISOString()}
                onClick={() => setSelectedDay(day)}
                className={`relative flex flex-col items-center gap-1 border-b border-r border-border/30 px-1 py-2 text-xs transition-colors ${
                  !inMonth ? "text-muted-foreground/30" : "text-foreground"
                } ${isSelected ? "bg-[#ea580c]/5" : "hover:bg-surface-2/50"}`}
              >
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] ${
                    today
                      ? "bg-[#ea580c] font-semibold text-white"
                      : isSelected
                        ? "font-semibold text-[#ea580c]"
                        : ""
                  }`}
                >
                  {format(day, "d")}
                </span>
                {dayEvents.length > 0 && (
                  <div className="flex gap-0.5">
                    {dayEvents.slice(0, 3).map((_, i) => (
                      <span key={i} className="h-1 w-1 rounded-full bg-[#ea580c]" />
                    ))}
                    {dayEvents.length > 3 && (
                      <span className="text-[8px] text-[#ea580c]">+{dayEvents.length - 3}</span>
                    )}
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-4">
            <span className="text-xs text-muted-foreground/50">Laden...</span>
          </div>
        )}
      </div>

      {/* Day detail panel */}
      <div className="flex w-80 flex-col rounded-2xl border border-[hsl(var(--card-border))] bg-card">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-xs font-semibold text-foreground">
            {selectedDay
              ? format(selectedDay, "EEEE d MMMM", { locale: nl })
              : "Selecteer een dag"}
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          {!selectedDay && (
            <p className="py-8 text-center text-xs text-muted-foreground/50">
              Klik op een dag om afspraken te bekijken
            </p>
          )}
          {selectedDay && selectedDayEvents.length === 0 && (
            <p className="py-8 text-center text-xs text-muted-foreground/50">
              Geen afspraken
            </p>
          )}
          {selectedDayEvents.map((event) => {
            const customer = parseCustomerName(event.description)
            const startTime = format(new Date(event.start), "HH:mm")
            const endTime = format(new Date(event.end), "HH:mm")

            return (
              <div
                key={event.id}
                className="mb-2 rounded-xl border border-[#ea580c]/20 bg-[#ea580c]/5 p-3"
              >
                <p className="text-xs font-semibold text-foreground">{event.summary}</p>
                <div className="mt-1.5 flex flex-col gap-1">
                  <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {startTime} - {endTime}
                  </span>
                  {customer && (
                    <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      <User className="h-3 w-3" />
                      {customer}
                    </span>
                  )}
                </div>
                {event.htmlLink && (
                  <a
                    href={event.htmlLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 flex items-center gap-1 text-[10px] text-[#ea580c] hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Openen in Google Calendar
                  </a>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
