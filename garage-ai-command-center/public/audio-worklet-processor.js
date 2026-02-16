/**
 * AudioWorklet processor for capturing microphone PCM at 16kHz.
 * Runs off the main thread for consistent audio capture.
 */
class MicProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]
    if (input && input[0] && input[0].length > 0) {
      // Clone Float32 samples and send to main thread
      this.port.postMessage(new Float32Array(input[0]))
    }
    return true
  }
}

registerProcessor("mic-processor", MicProcessor)
