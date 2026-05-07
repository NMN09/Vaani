import os
import json
import base64
import websockets
from services.audio_utils import twilio_to_gemini, gemini_to_twilio
from services.rag_service import query_knowledge_base
from services.language_router import detect_language
from services.sentiment_handler import evaluate_intervention, trigger_discount_offer

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "DUMMY_KEY")
GEMINI_WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

def get_system_instruction(language="English"):
    """
    Returns the persona instructions for VaaniAI.
    """
    base_instructions = (
        "You are VaaniAI, a professional yet empathetic Relationship Manager. "
        "Your goal is to assist users with their product queries using the provided tools. "
        "CRITICAL: You must constantly monitor the user's vocal tone. If they sound Frustrated, Skeptical, or Angry, "
        "you MUST call the 'trigger_discount_offer' tool immediately to retain them. "
        "Keep your spoken responses brief (under 20 words) and conversational."
    )
    
    if language == "Hindi":
        lang_prompt = (
            "Aap VaaniAI hain. Humesha Hinglish (Hindi + English) mein baat karein. "
            "Respect ke liye 'Ji' aur 'Aap' ka istemaal karein. "
            "Example: 'Namaste Ji, main aapki kya madad kar sakti hoon?'"
        )
    elif language == "Tamil":
        lang_prompt = "You are VaaniAI. Speak in fluent, polite conversational Tamil. Use honorifics where appropriate."
    else:
        lang_prompt = "Speak in clear, professional English."
        
    return f"{lang_prompt} {base_instructions}"

def get_gemini_tools():
    """
    Returns the tool definitions for Gemini.
    """
    return [
        {
            "functionDeclarations": [
                {
                    "name": "query_knowledge_base",
                    "description": "Searches the product knowledge base for details. Call this for any product-specific questions.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "query": {"type": "STRING", "description": "The specific product question."}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "trigger_discount_offer",
                    "description": "Call this IMMEDIATELY if you detect user frustration, anger, or skepticism.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "sentiment": {"type": "STRING", "description": "The detected emotion (e.g., 'Frustrated')."}
                        },
                        "required": ["sentiment"]
                    }
                }
            ]
        }
    ]

async def connect_to_gemini():
    import ssl
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    print(f"Connecting to Gemini Live API...")
    gemini_ws = await websockets.connect(GEMINI_WS_URL, ssl=ssl_context)
    
    setup_msg = {
        "setup": {
            "model": "models/gemini-2.0-flash", # Using latest flash for low latency
            "systemInstruction": {
                "parts": [{"text": get_system_instruction("English")}]
            },
            "tools": get_gemini_tools(),
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": "Puck"} # 'Puck' is a good friendly voice
                    }
                }
            }
        }
    }
    await gemini_ws.send(json.dumps(setup_msg))
    setup_response = await gemini_ws.recv()
    # print("Gemini Setup Response:", setup_response)
    
    return gemini_ws

def prepare_gemini_audio_chunk(ulaw_payload: str) -> str:
    ulaw_bytes = base64.b64decode(ulaw_payload)
    pcm_bytes = twilio_to_gemini(ulaw_bytes)
    pcm_b64 = base64.b64encode(pcm_bytes).decode('utf-8')
    
    return json.dumps({
        "clientContent": {
            "turns": [{
                "role": "user",
                "parts": [{"inlineData": {"mimeType": "audio/pcm;rate=16000", "data": pcm_b64}}]
            }],
            "turnComplete": False
        }
    })

async def handle_gemini_message(gemini_ws, json_str: str, current_lang_state: dict, stream_sid: str = None):
    try:
        data = json.loads(json_str)
        
        # 1. Audio/Text Content
        if "serverContent" in data:
            model_turn = data["serverContent"].get("modelTurn", {})
            for part in model_turn.get("parts", []):
                if "text" in part and stream_sid:
                    from services.database import add_message
                    import uuid
                    add_message(stream_sid, str(uuid.uuid4()), "ai", part["text"])
                if "inlineData" in part and "data" in part["inlineData"]:
                    pcm_bytes = base64.b64decode(part["inlineData"]["data"])
                    return gemini_to_twilio(pcm_bytes), None

        # 2. Tool Calls
        elif "toolCall" in data:
            function_calls = data["toolCall"].get("functionCalls", [])
            for call in function_calls:
                name = call["name"]
                args = call.get("args", {})
                
                print(f"Executing Tool: {name} with args {args}")
                
                if name == "query_knowledge_base":
                    query = args.get("query", "")
                    
                    # Language Routing Check
                    detected_lang = detect_language(query)
                    if detected_lang != current_lang_state["lang"]:
                        current_lang_state["lang"] = detected_lang
                        # Inform Gemini of the switch
                        await gemini_ws.send(json.dumps({
                            "clientContent": {
                                "turns": [{"role": "user", "parts": [{"text": f"SYSTEM: Switch to {detected_lang} mode. {get_system_instruction(detected_lang)}"}]}],
                                "turnComplete": True
                            }
                        }))
                    
                    result = query_knowledge_base(query, current_lang_state["lang"])
                    await send_tool_response(gemini_ws, call["id"], name, {"result": result})
                    return None, current_lang_state["lang"]

                elif name == "trigger_discount_offer":
                    sentiment = args.get("sentiment", "Frustrated")
                    if stream_sid:
                        from services.database import update_call_score
                        update_call_score(stream_sid, 2) # Flag as high-risk lead
                    
                    if evaluate_intervention(sentiment):
                        offer = trigger_discount_offer()
                        # Inject tone override
                        await gemini_ws.send(json.dumps({
                            "clientContent": {
                                "turns": [{"role": "user", "parts": [{"text": "SYSTEM: User is frustrated. Be extremely apologetic and offer the following: " + offer}]}],
                                "turnComplete": True
                            }
                        }))
                        await send_tool_response(gemini_ws, call["id"], name, {"result": offer})
                    else:
                        await send_tool_response(gemini_ws, call["id"], name, {"result": "No intervention needed."})
                    
                    return None, current_lang_state["lang"]
                    
    except Exception as e:
        print(f"Error in handle_gemini_message [{type(e).__name__}]: {e}")
    return None, None

async def send_tool_response(ws, call_id, name, response_data):
    msg = {
        "toolResponse": {
            "functionResponses": [{
                "id": call_id,
                "name": name,
                "response": response_data
            }]
        }
    }
    await ws.send(json.dumps(msg))

async def transcribe_audio(chunk: bytes, language_code: str = "en-US") -> str:
    """
    Sends audio to Gemini REST API to transcribe it.
    """
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"Please transcribe this audio exactly as spoken. The spoken language is {language_code}. Just output the text, nothing else."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Part.from_bytes(data=chunk, mime_type='audio/webm'),
                prompt
            ]
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return ""

