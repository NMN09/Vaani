import edge_tts
import io

VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-MadhurNeural",
    "kn": "kn-IN-GaganNeural"
}

# Normalize language identifiers to BCP-47 codes used by edge-tts
def normalize_language_code(lang_input: str) -> str:
    lowered = lang_input.lower()
    if lowered.startswith("en"):
        return "en-US"
    if lowered.startswith("hi") or "hindi" in lowered:
        return "hi-IN"
    if lowered.startswith("kn") or "kannada" in lowered:
        return "kn-IN"
    return "en-US"

async def synthesize(text: str, language_code: str = "en-US") -> bytes:
    """
    Convert plain text to audio using the edge-tts library (Neural Voices).
    No API key required! Higher quality than gTTS.
    """
    # Use normalized BCP-47 code then extract short language prefix
    normalized = normalize_language_code(language_code)
    lang = normalized.split('-')[0]
    voice = VOICE_MAP.get(lang, "en-IN-NeerjaNeural")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        # Collect chunks into bytes
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    except Exception as e:
        print(f"Error in edge-tts synthesis: {e}")
        return b""
