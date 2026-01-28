
import numpy as np
import scipy.signal

class AudioResampler:
    """
    Handles audio resampling and format conversion for the GarageAI telephony bridge.
    
    Sample Rate Reference:
    ┌─────────────────────────┬──────────────┬───────────────┐
    │ Stream Direction        │ Format       │ Sample Rate   │
    ├─────────────────────────┼──────────────┼───────────────┤
    │ User Mic → Bridge       │ PCM Int16    │ 16,000 Hz     │
    │ Bridge → Gemini         │ PCM Int16    │ 16,000 Hz     │
    │ Gemini → Bridge         │ PCM Int16    │ 24,000 Hz     │
    │ Bridge → Speaker/Web    │ PCM Int16    │ 24,000 Hz     │
    │ Bridge → Twilio         │ Mu-law       │ 8,000 Hz      │
    │ Twilio → Bridge         │ Mu-law       │ 8,000 Hz      │
    └─────────────────────────┴──────────────┴───────────────┘
    
    Replaces deprecated `audioop` using robust numpy lookup tables for G.711 mu-law.
    """
    
    # Standard sample rates
    TWILIO_RATE = 8000       # Twilio mu-law
    INPUT_RATE = 16000       # Microphone input, Bridge → Gemini
    GEMINI_OUTPUT_RATE = 24000  # Gemini audio output
    
    def __init__(self):
        self.PCM_WIDTH = 2  # 16-bit audio
        
        # Initialize G.711 Mu-Law Lookup Tables
        self._build_tables()
        
    def _build_tables(self):
        """Build mu-law encode/decode lookup tables for fast conversion."""
        
        # 1. mu-law to linear (decode) - 8-bit mu-law to 16-bit PCM
        self.mu2lin_table = np.zeros(256, dtype=np.int16)
        for i in range(256):
            mu = ~i & 0xFF  # Invert bits (G.711 standard)
            sign = -1 if (mu & 0x80) else 1
            exponent = (mu >> 4) & 0x7
            mantissa = mu & 0xF
            sample = (((mantissa << 1) + 33) << exponent) - 33
            self.mu2lin_table[i] = sign * sample
            
        # Scale 14-bit values to 16-bit range
        self.mu2lin_table = (self.mu2lin_table * 4).astype(np.int16)

        # 2. linear to mu-law (encode) - 16-bit PCM to 8-bit mu-law
        self.lin2mu_table = np.zeros(65536, dtype=np.uint8)
        
        for i in range(65536):
            # Convert unsigned index to signed int16
            val = i if i < 32768 else i - 65536
            
            # G.711 encode logic
            sign = 0x80 if val < 0 else 0
            val = abs(val) >> 2  # Reduce to 14-bit
            val = min(val, 8159)  # Clip to valid range
            
            val += 33
            
            # Determine exponent
            if val > 0x1FFF: exponent = 7
            elif val > 0x0FFF: exponent = 6
            elif val > 0x07FF: exponent = 5
            elif val > 0x03FF: exponent = 4
            elif val > 0x01FF: exponent = 3
            elif val > 0x00FF: exponent = 2
            elif val > 0x007F: exponent = 1
            else: exponent = 0
            
            mantissa = (val >> (exponent + 1)) & 0xF
            byte = sign | (exponent << 4) | mantissa
            self.lin2mu_table[i] = ~byte & 0xFF

    # ============================================================
    # TWILIO INPUT PATH: 8kHz Mu-law → 16kHz PCM (for Gemini input)
    # ============================================================
    
    def mulaw_to_pcm_16k(self, mulaw_data: bytes) -> bytes:
        """
        Convert Twilio's 8kHz mu-law to 16kHz PCM for Gemini input.
        
        Path: Twilio (8kHz mu-law) → Bridge → Gemini (16kHz PCM)
        """
        if not mulaw_data:
            return b""
        
        # 1. Decode mu-law to 16-bit PCM at 8kHz
        indices = np.frombuffer(mulaw_data, dtype=np.uint8)
        pcm_8k = self.mu2lin_table[indices]
        
        # 2. Resample 8kHz → 16kHz (double the samples)
        target_samples = len(pcm_8k) * 2
        pcm_16k = scipy.signal.resample(pcm_8k, target_samples).astype(np.int16)
        
        return pcm_16k.tobytes()
    
    # Legacy alias for backwards compatibility
    def mulaw_to_pcm(self, mulaw_data: bytes) -> bytes:
        return self.mulaw_to_pcm_16k(mulaw_data)

    # ============================================================
    # TWILIO OUTPUT PATH: 24kHz PCM → 8kHz Mu-law (from Gemini output)
    # ============================================================
    
    def pcm_24k_to_mulaw(self, pcm_24k_data: bytes) -> bytes:
        """
        Convert Gemini's 24kHz PCM output to 8kHz mu-law for Twilio.
        
        Path: Gemini (24kHz PCM) → Bridge → Twilio (8kHz mu-law)
        
        This is the correct path for Twilio output - resample from 24kHz, NOT 16kHz!
        """
        if not pcm_24k_data:
            return b""
        
        # 1. Parse 24kHz PCM
        pcm_24k = np.frombuffer(pcm_24k_data, dtype=np.int16)
        
        # 2. Resample 24kHz → 8kHz (1/3 of samples)
        target_samples = len(pcm_24k) // 3
        if target_samples < 1:
            target_samples = 1
        pcm_8k = scipy.signal.resample(pcm_24k, target_samples).astype(np.int16)
        
        # 3. Encode to mu-law
        indices = pcm_8k.view(np.uint16)
        mulaw_bytes = self.lin2mu_table[indices]
        
        return mulaw_bytes.tobytes()
    
    # Legacy function - DEPRECATED, use pcm_24k_to_mulaw instead
    def pcm_to_mulaw(self, pcm_16k_data: bytes) -> bytes:
        """
        DEPRECATED: This assumes 16kHz input which is INCORRECT for Gemini output.
        Gemini outputs 24kHz audio. Use pcm_24k_to_mulaw() instead.
        
        Kept for backwards compatibility only.
        """
        if not pcm_16k_data:
            return b""
        
        pcm_16k = np.frombuffer(pcm_16k_data, dtype=np.int16)
        target_samples = len(pcm_16k) // 2
        if target_samples < 1:
            target_samples = 1
        pcm_8k = scipy.signal.resample(pcm_16k, target_samples).astype(np.int16)
        
        indices = pcm_8k.view(np.uint16)
        mulaw_bytes = self.lin2mu_table[indices]
        
        return mulaw_bytes.tobytes()

    # ============================================================
    # WEB OUTPUT PATH: Pass-through (24kHz PCM stays at 24kHz)
    # ============================================================
    
    def pass_through_24k(self, pcm_24k_data: bytes) -> bytes:
        """
        For web clients, Gemini's 24kHz output can be passed through directly.
        The client-side AudioContext must be set to 24kHz for playback.
        
        Path: Gemini (24kHz PCM) → Bridge → Web Client (24kHz PCM)
        """
        return pcm_24k_data

    # ============================================================
    # UTILITY METHODS
    # ============================================================
    
    @staticmethod
    def get_sample_rates():
        """Return a dict of all sample rates used in the system."""
        return {
            "twilio": 8000,
            "microphone_input": 16000,
            "gemini_input": 16000,
            "gemini_output": 24000,
            "web_playback": 24000,
        }
