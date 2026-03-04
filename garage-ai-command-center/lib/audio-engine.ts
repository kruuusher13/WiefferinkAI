/**
 * AudioEngine: Mic capture (16kHz PCM) + Playback (24kHz PCM)
 *
 * Mic: AudioWorklet captures at device rate → resampled to 16kHz → Int16 PCM → base64 → WebSocket
 * Playback: base64 PCM from WebSocket → Int16 → Float32 → AudioBuffer at 24kHz → speaker
 */

export type AudioLevelCallback = (level: number) => void

export class AudioEngine {
  private captureCtx: AudioContext | null = null
  private playbackCtx: AudioContext | null = null
  private micStream: MediaStream | null = null
  private workletNode: AudioWorkletNode | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private onAudioChunk: ((b64: string) => void) | null = null
  private onAudioLevel: AudioLevelCallback | null = null
  private playbackQueue: AudioBuffer[] = []
  private isPlaying = false
  private nextPlayTime = 0

  async initCapture(
    onChunk: (b64: string) => void,
    onLevel: AudioLevelCallback
  ): Promise<void> {
    this.onAudioChunk = onChunk
    this.onAudioLevel = onLevel

    // Capture at 16kHz directly (browser will resample from mic's native rate)
    this.captureCtx = new AudioContext({ sampleRate: 16000 })
    this.micStream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: { ideal: 16000 }, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    })

    await this.captureCtx.audioWorklet.addModule("/audio-worklet-processor.js")

    this.sourceNode = this.captureCtx.createMediaStreamSource(this.micStream)
    this.workletNode = new AudioWorkletNode(this.captureCtx, "mic-processor")

    this.workletNode.port.onmessage = (event: MessageEvent<Float32Array>) => {
      const float32 = event.data
      // Compute RMS audio level
      let sum = 0
      for (let i = 0; i < float32.length; i++) {
        sum += float32[i] * float32[i]
      }
      const rms = Math.sqrt(sum / float32.length)
      this.onAudioLevel?.(Math.min(1, rms * 5)) // Scale up for visibility

      // Convert Float32 [-1,1] to Int16 PCM
      const int16 = new Int16Array(float32.length)
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]))
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
      }

      // Base64 encode
      const bytes = new Uint8Array(int16.buffer)
      let binary = ""
      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i])
      }
      this.onAudioChunk?.(btoa(binary))
    }

    this.sourceNode.connect(this.workletNode)
    this.workletNode.connect(this.captureCtx.destination) // Needed for worklet to process
  }

  initPlayback(): void {
    // 24kHz for Gemini output audio
    try {
      this.playbackCtx = new AudioContext({ sampleRate: 24000 })
    } catch {
      // Fallback to default sample rate if 24kHz not supported
      this.playbackCtx = new AudioContext()
    }
  }

  playChunk(b64Pcm: string): void {
    if (!this.playbackCtx) this.initPlayback()
    const ctx = this.playbackCtx!

    // Decode base64 → Int16 PCM
    const binary = atob(b64Pcm)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    const int16 = new Int16Array(bytes.buffer)

    // Int16 → Float32
    const float32 = new Float32Array(int16.length)
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 0x8000
    }

    // Create AudioBuffer
    const buffer = ctx.createBuffer(1, float32.length, 24000)
    buffer.getChannelData(0).set(float32)

    // Schedule playback with seamless queuing
    const now = ctx.currentTime
    if (this.nextPlayTime < now) {
      this.nextPlayTime = now
    }

    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.start(this.nextPlayTime)
    this.nextPlayTime += buffer.duration
  }

  stopCapture(): void {
    this.workletNode?.disconnect()
    this.sourceNode?.disconnect()
    this.micStream?.getTracks().forEach((t) => t.stop())
    this.captureCtx?.close()
    this.workletNode = null
    this.sourceNode = null
    this.micStream = null
    this.captureCtx = null
  }

  stopPlayback(): void {
    this.playbackCtx?.close()
    this.playbackCtx = null
    this.nextPlayTime = 0
  }

  destroy(): void {
    this.stopCapture()
    this.stopPlayback()
  }
}
