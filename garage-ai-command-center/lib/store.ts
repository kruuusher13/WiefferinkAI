import { create } from "zustand"
import { AudioEngine } from "./audio-engine"

// --- Types ---

export interface TranscriptLine {
  id: number
  speaker: "customer" | "harry"
  text: string
  timestamp: string
  keywords?: string[]
}

export interface VehicleAlert {
  message: string
  severity: "warning" | "info"
}

export interface ActionProposal {
  id: number
  title: string
  type: "appointment" | "invoice" | "notification" | "part_check"
  current: Record<string, string>
  proposed: Record<string, string>
  status: "pending" | "accepted" | "editing"
  werkorder_id?: number
}

type WsStatus = "disconnected" | "connecting" | "connected"
type CallState = "idle" | "incoming" | "harry_talking" | "processing"

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
  // "Klant gevonden: Jan de Vries (KlantID: 5)"
  const match = result.match(/Klant gevonden:\s*(.+?)\s*\(/)
  return match ? match[1].trim() : null
}

function parseVehicleRdw(result: string): Record<string, string> | null {
  // Parse key: value pairs from RDW lookup result
  const data: Record<string, string> = {}
  const lines = result.split("\n").filter(Boolean)
  for (const line of lines) {
    const sep = line.indexOf(":")
    if (sep > 0) {
      const key = line.slice(0, sep).trim().toLowerCase().replace(/\s+/g, "_")
      const val = line.slice(sep + 1).trim()
      if (key && val) data[key] = val
    }
  }
  return Object.keys(data).length > 0 ? data : null
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

// --- Kenteken regex: matches Dutch license plates like AB-123-CD, 31-ZZ-ND, AB123CD ---
const KENTEKEN_REGEX = /\b([A-Z0-9]{1,3}[-\s]?[A-Z0-9]{2,3}[-\s]?[A-Z0-9]{1,3})\b/gi

function extractKenteken(text: string): string | null {
  const matches = text.match(KENTEKEN_REGEX)
  if (!matches) return null
  for (const m of matches) {
    const clean = m.replace(/[-\s]/g, "").toUpperCase()
    // Dutch plates are 6 chars, mix of letters and digits (not all letters, not all digits)
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
  if (get().vehicleData) return // Already loaded
  try {
    const resp = await fetch(`/api/rdw-lookup/${encodeURIComponent(kenteken)}`)
    const json = await resp.json()
    if (json.status === "success" && json.data && !get().vehicleData) {
      set({ vehicleData: json.data })
    }
  } catch {
    // Silently fail — tool_result fallback will handle
  }
}

// --- Map tool_call to proposal type ---

function toolToProposalType(name: string): ActionProposal["type"] | null {
  switch (name) {
    case "schedule_appointment": return "appointment"
    case "generate_payment_link": return "invoice"
    case "get_service_price": return "invoice"
    case "check_part_stock": return "part_check"
    default: return null
  }
}

function toolToProposalTitle(name: string, args: Record<string, string>): string {
  switch (name) {
    case "schedule_appointment": return `Schedule: ${args.description || "Appointment"}`
    case "generate_payment_link": return "Generate Payment Link"
    case "get_service_price": return `Price: ${args.service_type || "Service"}`
    case "check_part_stock": return `Part: ${args.part_name || "Unknown"}`
    default: return name
  }
}

// --- Store ---

interface GarageStore {
  // Connection
  wsStatus: WsStatus
  callState: CallState
  callStartTime: number | null
  customerName: string | null
  sentiment: string

  // Transcript
  transcript: TranscriptLine[]
  nextTranscriptId: number

  // Vehicle
  vehicleData: Record<string, string> | null
  vehicleAlerts: VehicleAlert[]

  // Actions
  proposals: ActionProposal[]
  nextProposalId: number

  // Audio
  audioLevel: number
  isMicActive: boolean

  // WebSocket + Audio internals
  _ws: WebSocket | null
  _audio: AudioEngine | null

  // Actions
  connect: () => void
  disconnect: () => void
  toggleMic: () => Promise<void>
  sendText: (text: string) => void
  acceptProposal: (id: number) => Promise<void>
  editProposal: (id: number) => void
}

let transcriptIdCounter = 0
let proposalIdCounter = 0

export const useGarageStore = create<GarageStore>((set, get) => ({
  wsStatus: "disconnected",
  callState: "idle",
  callStartTime: null,
  customerName: null,
  sentiment: "😐",
  transcript: [],
  nextTranscriptId: 1,
  vehicleData: null,
  vehicleAlerts: [],
  proposals: [],
  nextProposalId: 1,
  audioLevel: 0,
  isMicActive: false,
  _ws: null,
  _audio: null,

  connect: () => {
    const { _ws } = get()
    if (_ws && _ws.readyState <= WebSocket.OPEN) return

    set({ wsStatus: "connecting" })

    const bridgeUrl = process.env.NEXT_PUBLIC_BRIDGE_URL || "http://localhost:8000"
    const wsUrl = bridgeUrl.replace(/^http/, "ws") + "/ws/web"
    const ws = new WebSocket(wsUrl)
    const audio = new AudioEngine()
    audio.initPlayback()

    ws.onopen = () => {
      set({
        wsStatus: "connected",
        callStartTime: Date.now(),
        callState: "idle",
        transcript: [],
        vehicleData: null,
        vehicleAlerts: [],
        customerName: null,
        sentiment: "😐",
      })
      transcriptIdCounter = 0
    }

    ws.onclose = () => {
      set({ wsStatus: "disconnected", callState: "idle", callStartTime: null })
      audio.destroy()
    }

    ws.onerror = () => {
      set({ wsStatus: "disconnected" })
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      const state = get()

      switch (data.type) {
        case "audio":
          audio.playChunk(data.audio)
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

          // Proactive kenteken detection in transcript text
          if (!get().vehicleData) {
            const detected = extractKenteken(data.text)
            if (detected) {
              fetchRdwLookup(detected, set, get)
            }
          }
          break
        }

        case "vehicle_data": {
          // Structured vehicle data from backend WS
          if (data.data && !get().vehicleData) {
            set({ vehicleData: data.data })
          }
          break
        }

        case "sentiment": {
          // Backend sends either emoji ("🙂") or word ("happy")
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

          // Customer identification
          if (data.name === "identify_customer") {
            // Will be resolved on tool_result
          }

          // Proactive RDW lookup when tool_call arrives (don't wait for result)
          if (data.name === "lookup_vehicle_rdw" && data.args?.kenteken) {
            const cleanKt = data.args.kenteken.replace(/[-\s]/g, "").toUpperCase()
            fetchRdwLookup(cleanKt, set, get)
          }
          break
        }

        case "tool_result": {
          const result = data.result || ""

          // Update vehicle context based on tool
          if (data.name === "identify_customer") {
            const name = parseCustomerName(result)
            if (name) set({ customerName: name })
          }

          if (data.name === "lookup_vehicle_rdw") {
            // If vehicle_data already set by proactive lookup or WS message, skip
            if (!get().vehicleData) {
              const vd = parseVehicleRdw(result)
              if (vd) {
                set({ vehicleData: vd })
              }
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

          // Update proposal with result
          if (data.name === "check_werkorder_status") {
            const vd = parseVehicleRdw(result) // Same key:value format
            if (vd) {
              set({ vehicleData: { ...(get().vehicleData || {}), ...vd } })
            }
          }

          // Update latest matching proposal status
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
      audioLevel: 0,
    })
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

    // Add to transcript as user message
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

  acceptProposal: async (id: number) => {
    const proposal = get().proposals.find((p) => p.id === id)
    if (!proposal) return

    try {
      const resp = await fetch("/api/werkorder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: proposal.proposed.description || proposal.title,
          customer_name: proposal.proposed.customer_name || get().customerName || undefined,
          phone_number: proposal.proposed.phone_number || undefined,
          kenteken: proposal.proposed.kenteken || get().vehicleData?.kenteken || undefined,
          date_time: proposal.proposed.date_time || undefined,
        }),
      })
      const json = await resp.json()
      if (json.status === "success") {
        set({
          proposals: get().proposals.map((p) =>
            p.id === id ? { ...p, status: "accepted" as const, werkorder_id: json.werkorder_id } : p
          ),
        })
      }
    } catch {
      // Keep as pending on failure
    }
  },

  editProposal: (id: number) => {
    set({
      proposals: get().proposals.map((p) =>
        p.id === id ? { ...p, status: "editing" as const } : p
      ),
    })
  },
}))
