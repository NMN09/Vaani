try:
    import audioop
except ImportError:
    import audioop_lts as audioop

# Twilio operates at 8000 Hz, Gemini Live API expects 16000 Hz PCM16
TWILIO_SAMPLE_RATE = 8000
GEMINI_SAMPLE_RATE = 16000

def twilio_to_gemini(ulaw_audio: bytes) -> bytes:
    """
    Converts 8kHz u-law audio from Twilio to 16kHz PCM audio for Gemini.
    """
    # 1. Convert u-law to 16-bit PCM (at 8kHz)
    pcm_8k = audioop.ulaw2lin(ulaw_audio, 2)
    
    # 2. Resample from 8kHz to 16kHz
    # audioop.ratecv(data, width, nchannels, inrate, outrate, state[, weightA[, weightB]])
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, TWILIO_SAMPLE_RATE, GEMINI_SAMPLE_RATE, None)
    return pcm_16k

def gemini_to_twilio(pcm_audio: bytes) -> bytes:
    """
    Converts 16kHz PCM audio from Gemini to 8kHz u-law audio for Twilio.
    """
    # 1. Resample from 16kHz to 8kHz
    pcm_8k, _ = audioop.ratecv(pcm_audio, 2, 1, GEMINI_SAMPLE_RATE, TWILIO_SAMPLE_RATE, None)
    
    # 2. Convert 16-bit PCM to u-law
    ulaw_audio = audioop.lin2ulaw(pcm_8k, 2)
    return ulaw_audio
