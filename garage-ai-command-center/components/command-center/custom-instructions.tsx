"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Maximize2, Minimize2, Save, RotateCcw } from "lucide-react"
import { useGarageStore } from "@/lib/store"

export function CustomInstructions({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const savedInstructions = useGarageStore((s) => s.customInstructions)
  const status = useGarageStore((s) => s.customInstructionsStatus)
  const loadCustomInstructions = useGarageStore((s) => s.loadCustomInstructions)
  const saveCustomInstructions = useGarageStore((s) => s.saveCustomInstructions)

  const [draft, setDraft] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const hasLoadedRef = useRef(false)

  // Load on mount
  useEffect(() => {
    if (!hasLoadedRef.current) {
      hasLoadedRef.current = true
      loadCustomInstructions()
    }
  }, [loadCustomInstructions])

  // Sync draft when saved instructions load
  useEffect(() => {
    setDraft(savedInstructions)
  }, [savedInstructions])

  const hasChanges = draft !== savedInstructions

  const handleSave = useCallback(() => {
    saveCustomInstructions(draft)
  }, [draft, saveCustomInstructions])

  const handleReset = useCallback(() => {
    setDraft(savedInstructions)
  }, [savedInstructions])

  // Cmd+S shortcut
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        // Only handle if our textarea is focused
        if (document.activeElement === textareaRef.current) {
          e.preventDefault()
          if (hasChanges) {
            saveCustomInstructions(draft)
          }
        }
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [draft, hasChanges, saveCustomInstructions])

  const statusBadge = (() => {
    switch (status) {
      case "saving":
        return <span className="font-mono text-[10px] text-syntax-yellow">saving...</span>
      case "saved":
        return <span className="font-mono text-[10px] text-syntax-green">saved</span>
      case "error":
        return <span className="font-mono text-[10px] text-syntax-red">error</span>
      default:
        return hasChanges
          ? <span className="font-mono text-[10px] text-syntax-yellow">unsaved</span>
          : null
    }
  })()

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-surface-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] font-semibold tracking-wide text-muted-foreground">
            custom-instructions
          </span>
          {statusBadge}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleReset}
            disabled={!hasChanges}
            className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground disabled:opacity-30 disabled:hover:bg-transparent"
            title="Reset changes"
          >
            <RotateCcw size={13} />
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || status === "saving"}
            className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground disabled:opacity-30 disabled:hover:bg-transparent"
            title="Save (Cmd+S)"
          >
            <Save size={13} />
          </button>
          <button
            onClick={onToggleFocus}
            className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            {isFocused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col gap-2 overflow-hidden p-3">
        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={`Give Harry real-time instructions, e.g.:\n- Ik ben niet bereikbaar om 12:30\n- We zijn maandag gesloten\n- Verwijs APK vragen door naar 0612345678`}
          className="flex-1 resize-none rounded border border-border bg-surface-0 px-3 py-2 font-mono text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-syntax-cyan focus:outline-none"
        />
        <p className="font-mono text-[10px] text-muted-foreground/60">
          These instructions are included in Harry&apos;s system prompt. Changes apply to new calls immediately and to active calls on save.
        </p>
      </div>
    </div>
  )
}
