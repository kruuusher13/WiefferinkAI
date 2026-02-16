"use client"

import { useState, useRef, useCallback } from "react"
import { motion } from "framer-motion"
import { Mic, MicOff, Phone, PhoneOff, Send, Maximize2, Minimize2 } from "lucide-react"
import { useGarageStore } from "@/lib/store"
import { Waveform } from "./waveform"

export function VoiceWidget({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const [textInput, setTextInput] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const wsStatus = useGarageStore((s) => s.wsStatus)
  const callState = useGarageStore((s) => s.callState)
  const sentiment = useGarageStore((s) => s.sentiment)
  const isMicActive = useGarageStore((s) => s.isMicActive)
  const audioLevel = useGarageStore((s) => s.audioLevel)
  const connect = useGarageStore((s) => s.connect)
  const disconnect = useGarageStore((s) => s.disconnect)
  const toggleMic = useGarageStore((s) => s.toggleMic)
  const sendText = useGarageStore((s) => s.sendText)

  const handleSend = useCallback(() => {
    if (textInput.trim()) {
      sendText(textInput)
      setTextInput("")
      inputRef.current?.focus()
    }
  }, [textInput, sendText])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  const isConnected = wsStatus === "connected"

  const stateLabel: Record<string, string> = {
    idle: "Listening",
    incoming: "Customer speaking",
    harry_talking: "Harry responding",
    processing: "Processing tool...",
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-surface-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <h2 className="font-mono text-xs font-medium text-foreground">
            voice_widget.talk
          </h2>
          {isConnected ? (
            <span className="rounded-sm bg-syntax-lime/10 px-1.5 py-0.5 font-mono text-[10px] text-syntax-lime">
              LIVE
            </span>
          ) : (
            <span className="rounded-sm bg-muted-foreground/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              OFFLINE
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg" title="Customer sentiment">{sentiment}</span>
          <button
            onClick={onToggleFocus}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
            aria-label={isFocused ? "Minimize" : "Maximize"}
          >
            {isFocused ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-4">
        {/* Status */}
        <div className="text-center">
          <p className="font-mono text-[11px] text-muted-foreground">
            {isConnected ? stateLabel[callState] || "Connected" : "Not connected"}
          </p>
        </div>

        {/* Waveform (shows real audio level when mic active) */}
        {isConnected && (
          <div className="w-full">
            <Waveform isActive={isMicActive} audioLevel={audioLevel} />
          </div>
        )}

        {/* Mic + Connect buttons */}
        <div className="flex items-center gap-3">
          {/* Connect/Disconnect */}
          <button
            onClick={isConnected ? disconnect : connect}
            className={`flex items-center gap-2 rounded-lg px-4 py-2.5 font-mono text-xs transition-colors ${
              isConnected
                ? "border border-destructive/30 bg-destructive/10 text-destructive hover:bg-destructive/20"
                : "border border-syntax-lime/30 bg-syntax-lime/10 text-syntax-lime hover:bg-syntax-lime/20"
            }`}
          >
            {isConnected ? (
              <>
                <PhoneOff className="h-4 w-4" /> Disconnect
              </>
            ) : (
              <>
                <Phone className="h-4 w-4" /> Connect
              </>
            )}
          </button>

          {/* Mic toggle */}
          {isConnected && (
            <motion.button
              onClick={toggleMic}
              whileTap={{ scale: 0.95 }}
              className={`flex items-center gap-2 rounded-lg px-4 py-2.5 font-mono text-xs transition-colors ${
                isMicActive
                  ? "border border-syntax-orange/30 bg-syntax-orange/10 text-syntax-orange hover:bg-syntax-orange/20"
                  : "border border-syntax-cyan/30 bg-syntax-cyan/10 text-syntax-cyan hover:bg-syntax-cyan/20"
              }`}
            >
              {isMicActive ? (
                <>
                  <MicOff className="h-4 w-4" /> Mute
                </>
              ) : (
                <>
                  <Mic className="h-4 w-4" /> Unmute
                </>
              )}
            </motion.button>
          )}
        </div>
      </div>

      {/* Text input */}
      {isConnected && (
        <div className="border-t border-border px-3 py-2">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message to Harry..."
              className="flex-1 rounded-md border border-border bg-surface-0 px-3 py-1.5 font-mono text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-syntax-cyan/50 focus:outline-none"
            />
            <button
              onClick={handleSend}
              disabled={!textInput.trim()}
              className="rounded-md p-1.5 text-syntax-cyan transition-colors hover:bg-syntax-cyan/10 disabled:text-muted-foreground/30"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
