"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Maximize2, Minimize2, Mic, MicOff, Send, AlertTriangle, Save, RotateCcw } from "lucide-react"
import { motion } from "framer-motion"
import { useGarageStore } from "@/lib/store"
import { Waveform } from "./waveform"

function useCallTimer() {
  const callStartTime = useGarageStore((s) => s.callStartTime)
  const [display, setDisplay] = useState("00:00")

  useEffect(() => {
    if (!callStartTime) {
      setDisplay("00:00")
      return
    }
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - callStartTime) / 1000)
      const m = String(Math.floor(elapsed / 60)).padStart(2, "0")
      const s = String(elapsed % 60).padStart(2, "0")
      setDisplay(`${m}:${s}`)
    }, 1000)
    return () => clearInterval(interval)
  }, [callStartTime])

  return display
}

export function CallStats({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const [whisperText, setWhisperText] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const callTime = useCallTimer()
  const wsStatus = useGarageStore((s) => s.wsStatus)
  const callState = useGarageStore((s) => s.callState)
  const sentiment = useGarageStore((s) => s.sentiment)
  const customerName = useGarageStore((s) => s.customerName)
  const isMicActive = useGarageStore((s) => s.isMicActive)
  const audioLevel = useGarageStore((s) => s.audioLevel)
  const isTakeover = useGarageStore((s) => s.isTakeover)
  const toggleMic = useGarageStore((s) => s.toggleMic)
  const startTakeover = useGarageStore((s) => s.startTakeover)
  const stopTakeover = useGarageStore((s) => s.stopTakeover)
  const sendText = useGarageStore((s) => s.sendText)

  // --- Instructions state ---
  const savedInstructions = useGarageStore((s) => s.customInstructions)
  const instrStatus = useGarageStore((s) => s.customInstructionsStatus)
  const loadCustomInstructions = useGarageStore((s) => s.loadCustomInstructions)
  const saveCustomInstructions = useGarageStore((s) => s.saveCustomInstructions)

  const [draft, setDraft] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const hasLoadedRef = useRef(false)

  useEffect(() => {
    if (!hasLoadedRef.current) {
      hasLoadedRef.current = true
      loadCustomInstructions()
    }
  }, [loadCustomInstructions])

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

  // Cmd+S shortcut for instructions
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
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

  const instrStatusBadge = (() => {
    switch (instrStatus) {
      case "saving":
        return <span className="text-[10px] font-medium text-amber-600">saving...</span>
      case "saved":
        return <span className="text-[10px] font-medium text-green-600">saved</span>
      case "error":
        return <span className="text-[10px] font-medium text-red-500">error</span>
      default:
        return hasChanges
          ? <span className="text-[10px] font-medium text-amber-600">unsaved</span>
          : null
    }
  })()

  const isConnected = wsStatus === "connected"

  const stateLabel: Record<string, string> = {
    idle: "Listening",
    incoming: "Customer speaking",
    harry_talking: "Harry responding",
    processing: "Processing tool...",
    takeover: "Owner speaking",
  }

  const badge = isTakeover
    ? { label: "TAKEOVER", className: "bg-red-500/10 text-red-500" }
    : isConnected
      ? { label: "LIVE", className: "bg-[#ea580c]/10 text-[#ea580c]" }
      : { label: "OFFLINE", className: "bg-neutral-100 text-muted-foreground" }

  const handleWhisper = useCallback(() => {
    if (whisperText.trim()) {
      sendText(whisperText)
      setWhisperText("")
      inputRef.current?.focus()
    }
  }, [whisperText, sendText])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleWhisper()
      }
    },
    [handleWhisper]
  )

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-[hsl(var(--card-border))] bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <h2 className="text-xs font-semibold text-foreground">Call Stats</h2>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.className}`}>
            {badge.label}
          </span>
        </div>
        <button
          onClick={onToggleFocus}
          className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          aria-label={isFocused ? "Minimize" : "Maximize"}
        >
          {isFocused ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* 2x2 stat grid */}
      <div className="p-2.5">
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-surface-2 px-3 py-2">
            <p className="text-[10px] text-muted-foreground">Duration</p>
            <p className="tabular-nums text-sm font-semibold text-foreground">{callTime}</p>
          </div>
          <div className="rounded-lg bg-surface-2 px-3 py-2">
            <p className="text-[10px] text-muted-foreground">Customer</p>
            <p className="truncate text-sm font-semibold text-foreground">
              {customerName || (isConnected ? "Identifying..." : "\u2014")}
            </p>
          </div>
          <div className="rounded-lg bg-surface-2 px-3 py-2">
            <p className="text-[10px] text-muted-foreground">Sentiment</p>
            <p className="text-lg">{sentiment}</p>
          </div>
          <div className="rounded-lg bg-surface-2 px-3 py-2">
            <p className="text-[10px] text-muted-foreground">State</p>
            <p className="text-xs font-medium text-foreground">
              {isConnected ? stateLabel[callState] || "Connected" : "Not connected"}
            </p>
          </div>
        </div>
      </div>

      {/* Controls section */}
      {isConnected && (
        <div className="border-t border-border px-3 py-2">
          {isTakeover ? (
            <div className="flex flex-col items-center gap-2">
              <motion.div
                className="rounded-full bg-red-500/10 px-4 py-1"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <span className="text-[10px] font-bold text-red-500">YOU ARE LIVE</span>
              </motion.div>
              <button
                onClick={stopTakeover}
                className="flex items-center gap-2 rounded-full border border-[#ea580c]/30 bg-[#ea580c]/10 px-4 py-1.5 text-xs font-medium text-[#ea580c] transition-all hover:bg-[#ea580c]/20"
              >
                Return to Harry
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <motion.button
                onClick={toggleMic}
                whileTap={{ scale: 0.95 }}
                className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-medium transition-all ${
                  isMicActive
                    ? "border border-amber-500/30 bg-amber-500/10 text-amber-600 hover:bg-amber-500/20"
                    : "border border-[#ea580c]/30 bg-[#ea580c]/10 text-[#ea580c] hover:bg-[#ea580c]/20"
                }`}
              >
                {isMicActive ? (
                  <><MicOff className="h-3.5 w-3.5" /> Mute</>
                ) : (
                  <><Mic className="h-3.5 w-3.5" /> Unmute</>
                )}
              </motion.button>
              <button
                onClick={startTakeover}
                className="flex items-center gap-1.5 rounded-full border border-red-500/30 px-4 py-1.5 text-xs font-medium text-red-500 transition-all hover:bg-red-500/10"
              >
                <AlertTriangle className="h-3 w-3" />
                Take Over
              </button>
            </div>
          )}
        </div>
      )}

      {/* Whisper input — shown when connected and NOT in takeover */}
      {isConnected && !isTakeover && (
        <div className="border-t border-border px-3 py-2">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={whisperText}
              onChange={(e) => setWhisperText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Whisper to Harry..."
              className="flex-1 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-[#ea580c]/50 focus:outline-none"
            />
            <button
              onClick={handleWhisper}
              disabled={!whisperText.trim()}
              className="rounded-lg p-1.5 text-[#ea580c] transition-colors hover:bg-[#ea580c]/10 disabled:text-muted-foreground/30"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Waveform */}
      {isConnected && (
        <div className="border-t border-border px-3 py-2">
          <Waveform isActive={isMicActive} audioLevel={audioLevel} />
        </div>
      )}

      {/* Instructions section */}
      <div className="flex min-h-0 flex-1 flex-col border-t border-border">
        <div className="flex items-center justify-between px-3 py-1.5">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Instructions</span>
            {instrStatusBadge}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleReset}
              disabled={!hasChanges}
              className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground disabled:opacity-30 disabled:hover:bg-transparent"
              title="Reset changes"
            >
              <RotateCcw size={12} />
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || instrStatus === "saving"}
              className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground disabled:opacity-30 disabled:hover:bg-transparent"
              title="Save (Cmd+S)"
            >
              <Save size={12} />
            </button>
          </div>
        </div>
        <div className="flex flex-1 flex-col overflow-hidden px-3 pb-2">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={`Give Harry real-time instructions, e.g.:\n- Ik ben niet bereikbaar om 12:30\n- We zijn maandag gesloten`}
            className="flex-1 resize-none rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-[#ea580c] focus:outline-none"
          />
        </div>
      </div>
    </div>
  )
}
