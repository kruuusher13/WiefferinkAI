"use client"

import { motion, AnimatePresence } from "framer-motion"
import { AlertTriangle, Maximize2, Minimize2 } from "lucide-react"
import { useGarageStore } from "@/lib/store"

const VALUE_COLORS: Record<string, string> = {
  merk: "text-syntax-cyan",
  model: "text-syntax-cyan",
  brandstof: "text-syntax-cyan",
  fuel_type: "text-syntax-cyan",
  handelsbenaming: "text-syntax-cyan",
  bouwjaar: "text-syntax-orange",
  year: "text-syntax-orange",
  eerste_toelating: "text-syntax-orange",
  apk_vervaldatum: "text-syntax-lime",
  apk_expiry: "text-syntax-lime",
  vervaldatum_apk: "text-syntax-lime",
  kenteken: "text-syntax-orange",
  kleur: "text-syntax-purple",
  status: "text-syntax-lime",
}

export function VehicleContext({
  isFocused,
  onToggleFocus,
}: {
  isFocused: boolean
  onToggleFocus: () => void
}) {
  const vehicleData = useGarageStore((s) => s.vehicleData)
  const vehicleAlerts = useGarageStore((s) => s.vehicleAlerts)
  const wsStatus = useGarageStore((s) => s.wsStatus)

  const hasData = vehicleData && Object.keys(vehicleData).length > 0

  // Filter apk_days_remaining from display — show as alert instead
  const apkDaysRemaining = hasData ? vehicleData!.apk_days_remaining : undefined
  const specs = hasData
    ? Object.entries(vehicleData!)
        .filter(([key]) => key !== "apk_days_remaining")
        .map(([key, value]) => ({
          key,
          value: `"${value}"`,
          color: VALUE_COLORS[key] || "text-foreground/70",
        }))
    : []

  // Build APK days alert
  const apkDaysAlert = (() => {
    if (!apkDaysRemaining) return null
    const days = parseInt(apkDaysRemaining, 10)
    if (isNaN(days)) return null
    if (days < 0) {
      return { message: `APK VERLOPEN (${Math.abs(days)} dagen geleden!)`, severity: "warning" as const }
    }
    if (days <= 30) {
      return { message: `APK verloopt over ${days} dagen — maak een afspraak!`, severity: "warning" as const }
    }
    if (days <= 60) {
      return { message: `APK verloopt over ${days} dagen`, severity: "info" as const }
    }
    return null
  })()

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-surface-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <h2 className="font-mono text-xs font-medium text-foreground">
            vehicle_context.inspect
          </h2>
          {hasData ? (
            <span className="rounded-sm bg-syntax-cyan/10 px-1.5 py-0.5 font-mono text-[10px] text-syntax-cyan">
              LOADED
            </span>
          ) : (
            <span className="rounded-sm bg-muted-foreground/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              {wsStatus === "connected" ? "AWAITING" : "EMPTY"}
            </span>
          )}
        </div>
        <button
          onClick={onToggleFocus}
          className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          aria-label={isFocused ? "Minimize" : "Maximize"}
        >
          {isFocused ? (
            <Minimize2 className="h-3.5 w-3.5" />
          ) : (
            <Maximize2 className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {/* JSON-like specs */}
        <div className="rounded-md border border-border/50 bg-surface-0 p-3">
          <div className="font-mono text-xs">
            <span className="text-muted-foreground">{"{"}</span>
            {hasData ? (
              <AnimatePresence>
                {specs.map((spec, i) => (
                  <motion.div
                    key={spec.key}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.15, delay: i * 0.03 }}
                    className="flex gap-1 pl-4"
                  >
                    <span className="text-foreground/60">{spec.key}</span>
                    <span className="text-muted-foreground">:</span>
                    <span className={spec.color}>{spec.value}</span>
                    {i < specs.length - 1 && (
                      <span className="text-muted-foreground">,</span>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            ) : (
              <div className="py-2 pl-4 text-muted-foreground/40">
                // awaiting vehicle lookup...
              </div>
            )}
            <span className="text-muted-foreground">{"}"}</span>
          </div>
        </div>

        {/* Alerts */}
        {(vehicleAlerts.length > 0 || apkDaysAlert) && (
          <div className="mt-4 flex flex-col gap-2">
            {apkDaysAlert && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className={`glow-border flex items-start gap-2.5 rounded-md p-3 ${
                  apkDaysAlert.severity === "warning"
                    ? "bg-syntax-orange/5"
                    : "bg-syntax-cyan/5"
                }`}
              >
                <AlertTriangle
                  className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                    apkDaysAlert.severity === "warning"
                      ? "text-syntax-orange"
                      : "text-syntax-cyan"
                  }`}
                />
                <span className="font-mono text-[11px] leading-4 text-foreground/80">
                  {apkDaysAlert.message}
                </span>
              </motion.div>
            )}
            {vehicleAlerts.map((alert, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className={`glow-border flex items-start gap-2.5 rounded-md p-3 ${
                  alert.severity === "warning"
                    ? "bg-syntax-orange/5"
                    : "bg-syntax-cyan/5"
                }`}
              >
                <AlertTriangle
                  className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                    alert.severity === "warning"
                      ? "text-syntax-orange"
                      : "text-syntax-cyan"
                  }`}
                />
                <span className="font-mono text-[11px] leading-4 text-foreground/80">
                  {alert.message}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
