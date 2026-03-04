"use client"

import { Nav } from "@/components/nav"
import { TranscriptHistory } from "@/components/command-center/transcript-history"

export default function HistoryPage() {
  return (
    <div className="flex h-screen flex-col bg-background">
      <Nav />
      <main className="flex-1 overflow-hidden p-4">
        <TranscriptHistory isFocused={false} onToggleFocus={() => {}} />
      </main>
    </div>
  )
}
