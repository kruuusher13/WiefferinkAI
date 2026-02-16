"use client"

import { ChevronRight } from "lucide-react"

const segments = ["Garage", "Live Calls", "+31 6 1234 5678"]

export function Breadcrumbs() {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 font-mono text-xs">
      {segments.map((segment, i) => (
        <span key={segment} className="flex items-center gap-1">
          {i > 0 && (
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          )}
          <span
            className={
              i === segments.length - 1
                ? "text-syntax-cyan"
                : "text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
            }
          >
            {segment}
          </span>
        </span>
      ))}
    </nav>
  )
}
