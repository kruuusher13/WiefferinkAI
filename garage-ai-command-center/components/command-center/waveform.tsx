"use client"

import { useEffect, useRef } from "react"

const CYAN = { r: 102, g: 255, b: 255 } // hsl(180, 100%, 70%)

export function Waveform({
  isActive = true,
  audioLevel = 0,
}: {
  isActive?: boolean
  audioLevel?: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)
  const audioLevelRef = useRef(audioLevel)
  const smoothLevelRef = useRef(0)
  audioLevelRef.current = audioLevel

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1

    function resize() {
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()

    let time = 0

    function draw() {
      if (!canvas || !ctx) return
      const w = canvas.width / dpr
      const h = canvas.height / dpr

      // Smooth the audio level for fluid motion
      const targetLevel = audioLevelRef.current
      smoothLevelRef.current += (targetLevel - smoothLevelRef.current) * 0.12

      ctx.clearRect(0, 0, w, h)

      const level = smoothLevelRef.current
      const centerY = h / 2
      const maxAmplitude = (h / 2) - 2

      // Determine amplitude based on state
      let amplitude: number
      let speed: number
      let opacity: number

      if (isActive && level > 0.01) {
        amplitude = maxAmplitude * Math.min(level * 1.5, 1)
        speed = 0.06
        opacity = 0.6 + level * 0.4
      } else if (isActive) {
        amplitude = maxAmplitude * 0.08
        speed = 0.02
        opacity = 0.3
      } else {
        amplitude = maxAmplitude * 0.03
        speed = 0.01
        opacity = 0.15
      }

      time += speed

      // Draw glow layer (wider, more transparent)
      ctx.beginPath()
      ctx.moveTo(0, centerY)
      for (let x = 0; x < w; x++) {
        const normalizedX = x / w
        // Composite wave: primary + harmonic overtones
        const wave =
          Math.sin(normalizedX * Math.PI * 4 + time) * 0.6 +
          Math.sin(normalizedX * Math.PI * 7 + time * 1.3) * 0.25 +
          Math.sin(normalizedX * Math.PI * 11 + time * 0.7) * 0.15
        const y = centerY + wave * amplitude
        ctx.lineTo(x, y)
      }
      ctx.strokeStyle = `rgba(${CYAN.r}, ${CYAN.g}, ${CYAN.b}, ${opacity * 0.15})`
      ctx.lineWidth = 6
      ctx.lineCap = "round"
      ctx.lineJoin = "round"
      ctx.stroke()

      // Draw mid glow
      ctx.beginPath()
      ctx.moveTo(0, centerY)
      for (let x = 0; x < w; x++) {
        const normalizedX = x / w
        const wave =
          Math.sin(normalizedX * Math.PI * 4 + time) * 0.6 +
          Math.sin(normalizedX * Math.PI * 7 + time * 1.3) * 0.25 +
          Math.sin(normalizedX * Math.PI * 11 + time * 0.7) * 0.15
        const y = centerY + wave * amplitude
        ctx.lineTo(x, y)
      }
      ctx.strokeStyle = `rgba(${CYAN.r}, ${CYAN.g}, ${CYAN.b}, ${opacity * 0.35})`
      ctx.lineWidth = 3
      ctx.stroke()

      // Draw main waveform line
      ctx.beginPath()
      ctx.moveTo(0, centerY)
      for (let x = 0; x < w; x++) {
        const normalizedX = x / w
        const wave =
          Math.sin(normalizedX * Math.PI * 4 + time) * 0.6 +
          Math.sin(normalizedX * Math.PI * 7 + time * 1.3) * 0.25 +
          Math.sin(normalizedX * Math.PI * 11 + time * 0.7) * 0.15
        const y = centerY + wave * amplitude
        ctx.lineTo(x, y)
      }
      ctx.strokeStyle = `rgba(${CYAN.r}, ${CYAN.g}, ${CYAN.b}, ${opacity})`
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Draw center baseline (very subtle)
      ctx.beginPath()
      ctx.moveTo(0, centerY)
      ctx.lineTo(w, centerY)
      ctx.strokeStyle = `rgba(${CYAN.r}, ${CYAN.g}, ${CYAN.b}, 0.06)`
      ctx.lineWidth = 1
      ctx.stroke()

      animRef.current = requestAnimationFrame(draw)
    }

    animRef.current = requestAnimationFrame(draw)
    window.addEventListener("resize", resize)
    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener("resize", resize)
    }
  }, [isActive])

  return (
    <canvas
      ref={canvasRef}
      className="h-10 w-full"
      aria-label={isActive ? "Voice activity detected" : "Waiting for voice input"}
    />
  )
}
