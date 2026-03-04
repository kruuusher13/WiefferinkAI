"use client"

import { Nav } from "@/components/nav"
import { CommandCenter } from "@/components/command-center/command-center"

export default function Page() {
  return (
    <div className="flex h-screen flex-col bg-background">
      <Nav />
      <CommandCenter />
    </div>
  )
}
