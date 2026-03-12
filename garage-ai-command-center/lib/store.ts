import { create } from "zustand"
import { AudioEngine } from "./audio-engine"

// --- Bridge URL (runtime, not build-time) ---

function getBridgeUrl(): string {
  if (process.env.NEXT_PUBLIC_BRIDGE_URL) return process.env.NEXT_PUBLIC_BRIDGE_URL
  if (typeof window !== "undefined") return window.location.origin
  return "http://localhost:8000"
}

// --- Types ---

export interface TranscriptLine {
  id: number
  speaker: "customer" | "harry"
  text: string
  timestamp: string
  keywords?: string[]
}

export interface ThoughtLine {
  id: number
  text: string
  timestamp: string
}

export interface VehicleAlert {
  message: string
  severity: "warning" | "info"
}

export interface ActionProposal {
  id: number
  title: string
  type: "appointment"
  current: Record<string, string>
  proposed: Record<string, string>
  status: "pending" | "accepted" | "editing"
  calendar_event_id?: string
  calendar_link?: string
}

type WsStatus = "disconnected" | "connecting" | "connected"
type CallState = "idle" | "harry_talking" | "processing" | "takeover"

// --- Keyword detection for syntax highlighting ---

const DUTCH_KEYWORDS = [
  "afspraak", "kosten", "klaar", "morgen", "auto", "reparatie",
  "band", "olie", "apk", "betaling", "kenteken", "beurt", "remmen",
]

function detectKeywords(text: string): string[] {
  const lower = text.toLowerCase()
  return DUTCH_KEYWORDS.filter((kw) => lower.includes(kw))
}

// --- Tool result parsers ---

function parseCustomerName(result: string): string | null {
  const match = result.match(/Klant gevonden:\s*(.+?)\s*\(/)
  return match ? match[1].trim() : null
}

function parseApkAlert(result: string): VehicleAlert | null {
  if (!result || result.toLowerCase().includes("niet gevonden")) return null
  const severity = result.toLowerCase().includes("verlop") || result.toLowerCase().includes("warning")
    ? "warning" : "info"
  return { message: result.slice(0, 120), severity }
}

function parseRecallAlert(result: string): VehicleAlert | null {
  if (!result || result.toLowerCase().includes("geen") || result.toLowerCase().includes("niet gevonden")) return null
  return { message: result.slice(0, 120), severity: "warning" }
}

// --- Kenteken regex ---
const KENTEKEN_REGEX = /\b([A-Z0-9]{1,3}[-\s]?[A-Z0-9]{2,3}[-\s]?[A-Z0-9]{1,3})\b/gi

function extractKenteken(text: string): string | null {
  const matches = text.match(KENTEKEN_REGEX)
  if (!matches) return null
  for (const m of matches) {
    const clean = m.replace(/[-\s]/g, "").toUpperCase()
    if (clean.length === 6 && /[A-Z]/.test(clean) && /[0-9]/.test(clean)) {
      return clean
    }
  }
  return null
}

// --- Reusable vehicle data fetcher ---

async function fetchRdwLookup(
  kenteken: string,
  set: (partial: Partial<GarageStore>) => void,
  get: () => GarageStore
) {
  if (get().vehicleData) return
  try {
    const bridgeUrl = getBridgeUrl()
    const resp = await fetch(`${bridgeUrl}/api/rdw-lookup/${encodeURIComponent(kenteken)}`)
    const json = await resp.json()
    if (json.status === "success" && json.data) {
      set({ vehicleData: json.data })
    }
  } catch (err) {
    console.error("[RDW Lookup] fetch failed:", err)
  }
}

// --- Map tool_call to proposal type ---

function toolToProposalType(name: string): ActionProposal["type"] | null {
  if (name === "request_appointment") return "appointment"
  return null
}

function toolToProposalTitle(name: string, args: Record<string, string>): string {
  if (name === "request_appointment") return `Appointment: ${args.description || "Request"}`
  return name
}

// --- Store ---

interface GarageStore {
  // Connection
  wsStatus: WsStatus
  callState: CallState
  callStartTime: number | null
  customerName: string | null
  sentiment: string

  // Takeover
  isTakeover: boolean

  // Transcript
  transcript: TranscriptLine[]
  nextTranscriptId: number

  // Harry's internal thoughts
  thoughts: ThoughtLine[]

  // Vehicle
  vehicleData: Record<string, string> | null
  vehicleAlerts: VehicleAlert[]

  // Actions
  proposals: ActionProposal[]
  nextProposalId: number

  // Audio
  audioLevel: number
  isMicActive: boolean

  // Calendar
  calendarConnected: boolean
  calendarLoading: boolean

  // Custom Instructions
  customInstructions: string
  customInstructionsStatus: "idle" | "saving" | "saved" | "error"

  // Mode
  mode: "talk" | "monitor"

  // WebSocket + Audio internals
  _ws: WebSocket | null
  _audio: AudioEngine | null
  _monitorWs: WebSocket | null

  // Actions
  connect: () => void
  disconnect: () => void
  connectMonitor: () => void
  disconnectMonitor: () => void
  toggleMic: () => Promise<void>
  sendText: (text: string) => void
  startTakeover: () => Promise<void>
  stopTakeover: () => void
  acceptProposal: (id: number) => Promise<void>
  editProposal: (id: number) => void
  checkCalendarStatus: () => Promise<void>
  disconnectCalendar: () => Promise<void>
  loadCustomInstructions: () => Promise<void>
  saveCustomInstructions: (text: string) => Promise<void>
}

let transcriptIdCounter = 0
let proposalIdCounter = 0

export const useGarageStore = create<GarageStore>((set, get) => ({
  wsStatus: "disconnected",
  callState: "idle",
  callStartTime: null,
  customerName: null,
  sentiment: "😐",
  isTakeover: false,
  transcript: [],
  nextTranscriptId: 1,
  thoughts: [],
  vehicleData: null,
  vehicleAlerts: [],
  proposals: [],
  nextProposalId: 1,
  audioLevel: 0,
  isMicActive: false,
  calendarConnected: false,
  calendarLoading: false,
  customInstructions: "",
  customInstructionsStatus: "idle",
  mode: "monitor",
  _ws: null,
  _audio: null,
  _monitorWs: null,

  connect: () => {
    const { _ws } = get()
    if (_ws && _ws.readyState <= WebSocket.OPEN) return

    set({ wsStatus: "connecting" })

    let ws: WebSocket
    let audio: AudioEngine
    try {
      const bridgeUrl = getBridgeUrl()
      const wsUrl = bridgeUrl.replace(/^http/, "ws") + "/ws/web"
      ws = new WebSocket(wsUrl)
      audio = new AudioEngine()
      audio.initPlayback()
    } catch (err) {
      console.error("Failed to connect:", err)
      set({ wsStatus: "disconnected" })
      return
    }

    ws.onopen = () => {
      set({
        wsStatus: "connected",
        callStartTime: Date.now(),
        callState: "idle",
        mode: "talk",
        transcript: [],
        thoughts: [],
        vehicleData: null,
        vehicleAlerts: [],
        customerName: null,
        sentiment: "😐",
        isTakeover: false,
      })
      transcriptIdCounter = 0
    }

    ws.onclose = () => {
      set({ wsStatus: "disconnected", callState: "idle", callStartTime: null, isTakeover: false })
      audio.destroy()
    }

    ws.onerror = () => {
      set({ wsStatus: "disconnected" })
    }

    ws.onmessage = (event) => {
      let data: any
      try {
        data = JSON.parse(event.data)
      } catch { return }
      const state = get()

      switch (data.type) {
        case "audio":
          audio.playChunk(data.audio)
          break

        case "audio_clear":
          audio.clearQueue()
          break

        case "transcript": {
          const speaker = data.role === "assistant" ? "harry" : "customer"
          const now = new Date()
          const ts = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`
          const keywords = detectKeywords(data.text)
          transcriptIdCounter++
          set({
            transcript: [
              ...state.transcript,
              { id: transcriptIdCounter, speaker, text: data.text, timestamp: ts, keywords },
            ],
          })

          // Proactive kenteken detection
          if (!get().vehicleData) {
            const detected = extractKenteken(data.text)
            if (detected) {
              fetchRdwLookup(detected, set, get)
            }
          }
          break
        }

        case "thought": {
          const now2 = new Date()
          const ts2 = `${String(now2.getHours()).padStart(2, "0")}:${String(now2.getMinutes()).padStart(2, "0")}:${String(now2.getSeconds()).padStart(2, "0")}`
          transcriptIdCounter++
          set({
            thoughts: [
              ...state.thoughts,
              { id: transcriptIdCounter, text: data.text, timestamp: ts2 },
            ],
          })
          break
        }

        case "vehicle_data": {
          if (data.data) {
            set({ vehicleData: data.data })
          }
          break
        }

        case "sentiment": {
          const sentimentMap: Record<string, string> = {
            happy: "🙂", neutral: "😐", frustrated: "😠", sad: "😢",
          }
          const emoji = sentimentMap[data.emoji] || data.emoji || "😐"
          set({ sentiment: emoji })
          break
        }

        case "call_state":
          set({ callState: data.state as CallState })
          break

        case "tool_call": {
          const pType = toolToProposalType(data.name)
          if (pType) {
            proposalIdCounter++
            const proposal: ActionProposal = {
              id: proposalIdCounter,
              title: toolToProposalTitle(data.name, data.args || {}),
              type: pType,
              current: {},
              proposed: data.args || {},
              status: "pending",
            }
            set({ proposals: [...state.proposals, proposal] })
          }

          // Extract customer name from request_appointment args
          if (data.name === "request_appointment" && data.args?.customer_name) {
            set({ customerName: data.args.customer_name })
          }

          // Proactive RDW lookup
          if (data.name === "lookup_vehicle_rdw" && data.args?.kenteken) {
            const cleanKt = data.args.kenteken.replace(/[-\s]/g, "").toUpperCase()
            fetchRdwLookup(cleanKt, set, get)
          }
          break
        }

        case "tool_result": {
          const result = data.result || ""

          if (data.name === "lookup_vehicle_rdw") {
            if (!get().vehicleData) {
              // Try to parse from result text
              const vd: Record<string, string> = {}
              const lines = result.split("\n").filter(Boolean)
              for (const line of lines) {
                const sep = line.indexOf(":")
                if (sep > 0) {
                  const key = line.slice(0, sep).trim().toLowerCase().replace(/\s+/g, "_")
                  const val = line.slice(sep + 1).trim()
                  if (key && val) vd[key] = val
                }
              }
              if (Object.keys(vd).length > 0) set({ vehicleData: vd })
            }
          }

          if (data.name === "check_apk_status") {
            const alert = parseApkAlert(result)
            if (alert) set({ vehicleAlerts: [...get().vehicleAlerts, alert] })
          }

          if (data.name === "get_vehicle_recalls") {
            const alert = parseRecallAlert(result)
            if (alert) set({ vehicleAlerts: [...get().vehicleAlerts, alert] })
          }

          // Update latest matching proposal with result
          const pType = toolToProposalType(data.name)
          if (pType) {
            const proposals = [...get().proposals]
            for (let i = proposals.length - 1; i >= 0; i--) {
              if (proposals[i].type === pType && proposals[i].status === "pending") {
                proposals[i] = {
                  ...proposals[i],
                  proposed: { ...proposals[i].proposed, result: result.slice(0, 100) },
                }
                break
              }
            }
            set({ proposals })
          }
          break
        }
      }
    }

    set({ _ws: ws, _audio: audio })
  },

  disconnect: () => {
    const { _ws, _audio } = get()
    _ws?.close()
    _audio?.destroy()
    set({
      _ws: null,
      _audio: null,
      wsStatus: "disconnected",
      callState: "idle",
      callStartTime: null,
      isMicActive: false,
      isTakeover: false,
      audioLevel: 0,
      mode: "monitor",
    })
  },

  connectMonitor: () => {
    const { _monitorWs } = get()
    if (_monitorWs && _monitorWs.readyState <= WebSocket.OPEN) return

    const bridgeUrl = getBridgeUrl()
    const wsUrl = bridgeUrl.replace(/^http/, "ws") + "/ws/web?mode=monitor"
    let ws: WebSocket
    try {
      ws = new WebSocket(wsUrl)
    } catch (err) {
      console.error("[Monitor] Failed to connect:", err)
      return
    }

    ws.onopen = () => {
      console.log("[Monitor] Connected")
    }

    ws.onclose = () => {
      console.log("[Monitor] Disconnected")
      set({ _monitorWs: null })
      // Auto-reconnect after 3s
      setTimeout(() => {
        const state = get()
        if (!state._monitorWs && state.mode === "monitor") {
          state.connectMonitor()
        }
      }, 3000)
    }

    ws.onerror = () => {
      console.error("[Monitor] WebSocket error")
    }

    ws.onmessage = (event) => {
      let data: any
      try {
        data = JSON.parse(event.data)
      } catch { return }
      const state = get()

      switch (data.type) {
        case "call_state":
          set({ callState: data.state as CallState })
          if (data.state === "harry_talking") {
            set({ callStartTime: state.callStartTime || Date.now() })
          }
          if (data.state === "idle") {
            set({
              callStartTime: null,
              // Reset call data when call ends
              transcript: [],
              thoughts: [],
              vehicleData: null,
              vehicleAlerts: [],
              customerName: null,
              sentiment: "😐",
              proposals: [],
              isTakeover: false,
            })
            transcriptIdCounter = 0
          }
          break

        case "transcript": {
          const speaker = data.role === "assistant" ? "harry" : "customer"
          const now = new Date()
          const ts = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`
          const keywords = detectKeywords(data.text)
          transcriptIdCounter++
          set({
            transcript: [
              ...state.transcript,
              { id: transcriptIdCounter, speaker, text: data.text, timestamp: ts, keywords },
            ],
          })
          if (!get().vehicleData) {
            const detected = extractKenteken(data.text)
            if (detected) fetchRdwLookup(detected, set, get)
          }
          break
        }

        case "thought": {
          const now2 = new Date()
          const ts2 = `${String(now2.getHours()).padStart(2, "0")}:${String(now2.getMinutes()).padStart(2, "0")}:${String(now2.getSeconds()).padStart(2, "0")}`
          transcriptIdCounter++
          set({
            thoughts: [
              ...state.thoughts,
              { id: transcriptIdCounter, text: data.text, timestamp: ts2 },
            ],
          })
          break
        }

        case "vehicle_data":
          if (data.data) set({ vehicleData: data.data })
          break

        case "sentiment": {
          const sentimentMap: Record<string, string> = {
            happy: "🙂", neutral: "😐", frustrated: "😠", sad: "😢",
          }
          const emoji = sentimentMap[data.emoji] || data.emoji || "😐"
          set({ sentiment: emoji })
          break
        }

        case "tool_call": {
          const pType = toolToProposalType(data.name)
          if (pType) {
            proposalIdCounter++
            const proposal: ActionProposal = {
              id: proposalIdCounter,
              title: toolToProposalTitle(data.name, data.args || {}),
              type: pType,
              current: {},
              proposed: data.args || {},
              status: "pending",
            }
            set({ proposals: [...state.proposals, proposal] })
          }
          if (data.name === "request_appointment" && data.args?.customer_name) {
            set({ customerName: data.args.customer_name })
          }
          if (data.name === "lookup_vehicle_rdw" && data.args?.kenteken) {
            const cleanKt = data.args.kenteken.replace(/[-\s]/g, "").toUpperCase()
            fetchRdwLookup(cleanKt, set, get)
          }
          break
        }

        case "tool_result": {
          const result = data.result || ""
          if (data.name === "lookup_vehicle_rdw" && !get().vehicleData) {
            const vd: Record<string, string> = {}
            const lines = result.split("\n").filter(Boolean)
            for (const line of lines) {
              const sep = line.indexOf(":")
              if (sep > 0) {
                const key = line.slice(0, sep).trim().toLowerCase().replace(/\s+/g, "_")
                const val = line.slice(sep + 1).trim()
                if (key && val) vd[key] = val
              }
            }
            if (Object.keys(vd).length > 0) set({ vehicleData: vd })
          }
          if (data.name === "check_apk_status") {
            const alert = parseApkAlert(result)
            if (alert) set({ vehicleAlerts: [...get().vehicleAlerts, alert] })
          }
          if (data.name === "get_vehicle_recalls") {
            const alert = parseRecallAlert(result)
            if (alert) set({ vehicleAlerts: [...get().vehicleAlerts, alert] })
          }
          const pType = toolToProposalType(data.name)
          if (pType) {
            const proposals = [...get().proposals]
            for (let i = proposals.length - 1; i >= 0; i--) {
              if (proposals[i].type === pType && proposals[i].status === "pending") {
                proposals[i] = {
                  ...proposals[i],
                  proposed: { ...proposals[i].proposed, result: result.slice(0, 100) },
                }
                break
              }
            }
            set({ proposals })
          }
          break
        }
      }
    }

    set({ _monitorWs: ws })
  },

  disconnectMonitor: () => {
    const { _monitorWs } = get()
    _monitorWs?.close()
    set({ _monitorWs: null })
  },

  toggleMic: async () => {
    const { isMicActive, _audio, _ws } = get()
    if (!_audio || !_ws || _ws.readyState !== WebSocket.OPEN) return

    if (isMicActive) {
      _audio.stopCapture()
      set({ isMicActive: false, audioLevel: 0 })
    } else {
      await _audio.initCapture(
        (b64) => {
          if (_ws.readyState === WebSocket.OPEN) {
            _ws.send(JSON.stringify({ type: "audio", data: b64 }))
          }
        },
        (level) => {
          set({ audioLevel: level })
        }
      )
      set({ isMicActive: true })
    }
  },

  sendText: (text: string) => {
    const { _ws } = get()
    if (!_ws || _ws.readyState !== WebSocket.OPEN || !text.trim()) return
    _ws.send(JSON.stringify({ type: "text", text: text.trim() }))

    const now = new Date()
    const ts = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`
    transcriptIdCounter++
    set({
      transcript: [
        ...get().transcript,
        { id: transcriptIdCounter, speaker: "customer", text, timestamp: ts, keywords: detectKeywords(text) },
      ],
    })
  },

  startTakeover: async () => {
    const { _ws, _monitorWs, _audio, mode } = get()
    // Use monitor WS if in monitor mode, otherwise use talk WS
    const ws = mode === "monitor" ? _monitorWs : _ws
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    ws.send(JSON.stringify({ type: "takeover", action: "start" }))

    // Start mic capture, send as takeover_audio
    let audio = _audio
    if (!audio) {
      audio = new AudioEngine()
      audio.initPlayback()
      set({ _audio: audio })
    }

    await audio.initCapture(
      (b64) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "takeover_audio", data: b64 }))
        }
      },
      (level) => {
        set({ audioLevel: level })
      }
    )

    set({ isTakeover: true, callState: "takeover", isMicActive: true })
  },

  stopTakeover: () => {
    const { _ws, _monitorWs, _audio, mode } = get()
    const ws = mode === "monitor" ? _monitorWs : _ws
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    ws.send(JSON.stringify({ type: "takeover", action: "stop" }))

    if (_audio) {
      _audio.stopCapture()
    }

    set({ isTakeover: false, callState: "harry_talking", isMicActive: false, audioLevel: 0 })
  },

  acceptProposal: async (id: number) => {
    const proposal = get().proposals.find((p) => p.id === id)
    if (!proposal) return

    try {
      const bridgeUrl = getBridgeUrl()
      const payload = {
        description: proposal.proposed.description || proposal.title,
        date_time: proposal.proposed.date_time || "",
        customer_name: proposal.proposed.customer_name || get().customerName || "",
        customer_phone: proposal.proposed.phone_number || "",
        customer_email: proposal.proposed.customer_email || "",
        kenteken: proposal.proposed.kenteken || get().vehicleData?.kenteken || "",
        duration_minutes: 60,
      }
      console.log("[AcceptProposal] Sending:", payload)
      const resp = await fetch(`${bridgeUrl}/api/appointment/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      const json = await resp.json()
      console.log("[AcceptProposal] Response:", json)
      if (json.status === "success") {
        set({
          proposals: get().proposals.map((p) =>
            p.id === id
              ? {
                  ...p,
                  status: "accepted" as const,
                  calendar_event_id: json.calendar_event_id,
                  calendar_link: json.calendar_link,
                }
              : p
          ),
        })
      } else {
        console.error("[AcceptProposal] Failed:", json.message || json)
        // Mark as error so user sees feedback
        set({
          proposals: get().proposals.map((p) =>
            p.id === id
              ? { ...p, proposed: { ...p.proposed, _error: json.message || "Failed to accept" } }
              : p
          ),
        })
      }
    } catch (err) {
      console.error("[AcceptProposal] Error:", err)
    }
  },

  editProposal: (id: number) => {
    set({
      proposals: get().proposals.map((p) =>
        p.id === id ? { ...p, status: "editing" as const } : p
      ),
    })
  },

  checkCalendarStatus: async () => {
    set({ calendarLoading: true })
    try {
      const resp = await fetch("/api/calendar/status")
      const json = await resp.json()
      set({ calendarConnected: json.connected === true })
    } catch {
      set({ calendarConnected: false })
    } finally {
      set({ calendarLoading: false })
    }
  },

  disconnectCalendar: async () => {
    try {
      await fetch("/api/calendar/disconnect", { method: "POST" })
      set({ calendarConnected: false })
    } catch {
      // Silently fail
    }
  },

  loadCustomInstructions: async () => {
    try {
      const resp = await fetch("/api/custom-instructions")
      const json = await resp.json()
      set({ customInstructions: json.instructions || "" })
    } catch {
      // Silently fail on load
    }
  },

  saveCustomInstructions: async (text: string) => {
    set({ customInstructionsStatus: "saving" })
    try {
      const resp = await fetch("/api/custom-instructions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instructions: text }),
      })
      const json = await resp.json()
      if (json.status === "success") {
        set({ customInstructions: text, customInstructionsStatus: "saved" })
        const ws = get()._ws
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "update_prompt", prompt: text }))
        }
        setTimeout(() => set({ customInstructionsStatus: "idle" }), 2000)
      } else {
        set({ customInstructionsStatus: "error" })
      }
    } catch {
      set({ customInstructionsStatus: "error" })
    }
  },
}))
