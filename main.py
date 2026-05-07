import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from services.gemini_stream import connect_to_gemini, prepare_gemini_audio_chunk, handle_gemini_message
from services.post_call_service import generate_post_call_data, send_whatsapp_followup
from services.database import init_db, get_calls, get_messages, get_call_by_id, create_call, update_call_status
from services.firebase_service import init_firebase, sync_call_to_firestore, send_push_notification
import random
import os
import sys

# 1. Startup Environment Validation
REQUIRED_ENV_VARS = ["GEMINI_API_KEY", "PINECONE_API_KEY"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
if missing_vars:
    print(f"CRITICAL ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set them in your .env file or environment.")
    # In a real app we might sys.exit(1), but for FastAPI we'll just log loudly
    # sys.exit(1)

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="VaaniAI RM Intelligence Server")

# Serve static PDFs
app.mount("/docs", StaticFiles(directory="data/docs"), name="docs")

@app.on_event("startup")
async def startup_event():
    init_db()
    init_firebase()
    print("Database and Firebase initialized.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PostCallRequest(BaseModel):
    call_id: str

@app.get("/api/calls")
async def fetch_calls():
    return get_calls()

@app.get("/api/calls/{call_id}/messages")
async def fetch_messages(call_id: str):
    return get_messages(call_id)

@app.delete("/api/calls")
async def clear_history():
    from services.database import clear_all_data
    clear_all_data()
    return {"status": "success", "message": "All history cleared"}

@app.post("/api/calls/simulate")
async def simulate_call_api():
    from services.database import create_call
    import uuid
    import random
    
    names = ["Kavitha Rao", "Mahesh Patil", "Priya Singh", "Ganesh Hegde", "Sunita Devi"]
    name = random.choice(names)
    phone = f"+91 {random.randint(60000, 99999)} {random.randint(10000, 99999)}"
    call_id = f"call_{str(uuid.uuid4())[:8]}"
    
    create_call(call_id, name, phone)
    return {"status": "success", "call_id": call_id}

@app.post("/api/post-call")
async def handle_post_call(request: PostCallRequest):
    call_info = get_call_by_id(request.call_id)
    if not call_info:
        return {"error": "Call not found"}
        
    messages = get_messages(request.call_id)
    transcript = "\n".join([f"{'Agent' if m['sender']=='ai' else 'Customer'}: {m['text']}" for m in messages])
    
    print(f"Post-call triggered for {call_info['customerName']}")
    data = generate_post_call_data(transcript, call_info['customerName'])
    success = send_whatsapp_followup(data["whatsapp_message"], call_info['phone'])
    data["whatsapp_sent"] = success
    return data

KB_DATA = [
    {
        "id": "prod_1", 
        "title": "Tractor Loans (Kisan Tractor)", 
        "content": "Loans for top brands like Mahindra, John Deere, and Swaraj. 8.5% interest rate, up to 7 years repayment. Minimum down payment required is only 15%."
    },
    {
        "id": "prod_2", 
        "title": "Crop Insurance (PMFBY)", 
        "content": "Kharif (2%) and Rabi (1.5%) crop protection against natural calamities. 30-day claim settlement for yield loss. Coverage includes post-harvest losses for up to 14 days."
    },
    {
        "id": "prod_3", 
        "title": "Kisan Credit Card (KCC)", 
        "content": "Credit limit up to 3 Lakh at 7% interest. Get 3% interest subvention for timely repayment, making the effective rate 4%. Flexible credit line for farm inputs."
    },
    {
        "id": "prod_4", 
        "title": "Animal Husbandry & Dairy Loan", 
        "content": "Dedicated loans for Dairy, Poultry, and Fisheries. Zero collateral up to 1.6 Lakh. Repayment linked to milk collection cycles for dairy farmers."
    },
    {
        "id": "prod_5", 
        "title": "Solar Pump Subsidy (PM-KUSUM)", 
        "content": "Get up to 60% subsidy on standalone solar water pumps. Central Govt provides 30%, and State Govt provides 30%. Farmers only pay 40% of the cost."
    },
    {
        "id": "prod_6", 
        "title": "Organic Farming Support (PKVY)", 
        "content": "Financial assistance of ₹50,000 per hectare for 3 years. Covers organic inputs, certification, and marketing support for farmer clusters."
    },
]

@app.get("/api/knowledge-base")
async def fetch_knowledge_base():
    return KB_DATA

class KBItem(BaseModel):
    title: str
    content: str

@app.post("/api/knowledge-base")
async def add_knowledge_base_item(item: KBItem):
    import uuid
    new_item = {
        "id": f"kb_{str(uuid.uuid4())[:8]}",
        "title": item.title,
        "content": item.content
    }
    KB_DATA.append(new_item)
    return new_item

@app.websocket("/twilio-stream")
async def twilio_stream(websocket: WebSocket):
    await websocket.accept()
    print("Twilio WebSocket connected!")
    
    gemini_ws = None
    stream_sid = None
    # State object to track language across the session
    current_lang_state = {"lang": "English"}
    
    try:
        # Establish connection to Gemini
        gemini_ws = await connect_to_gemini()
        
        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)
                    event = msg.get("event")
                    
                    if event == "start":
                        stream_sid = msg["start"]["streamSid"]
                        
                        # Create a demo lead entry in DB
                        # For hackathon demo, we use a predictable lead if not provided
                        demo_names = ["Ramesh Singh", "Sunita Devi", "Amit Patel", "Priya Sharma"]
                        demo_phones = ["+91 98765 43210", "+91 91234 56780", "+91 99887 77665", "+91 98765 11223"]
                        idx = random.randint(0, len(demo_names)-1)
                        
                        create_call(stream_sid, demo_names[idx], demo_phones[idx])
                        
                        # Add initial greeting message to DB
                        from services.database import add_message
                        import uuid
                        greeting = f"Namaste {demo_names[idx]} Ji! Main VaaniAI se baat kar rahi hoon. Kya main aapki madad kar sakti hoon?"
                        add_message(stream_sid, str(uuid.uuid4()), 'ai', greeting)
                        
                        print(f"Started Media Stream: {stream_sid} for {demo_names[idx]}")
                        
                    elif event == "media":
                        payload = msg["media"]["payload"]
                        # Forward audio chunk to Gemini
                        gemini_chunk = prepare_gemini_audio_chunk(payload)
                        await gemini_ws.send(gemini_chunk)
                        
                    elif event == "stop":
                        print(f"Stream stopped by Twilio: {stream_sid}")
                        break
                        
            except WebSocketDisconnect:
                print("Twilio WebSocket disconnected")
            except Exception as e:
                print("Error in receive_from_twilio:", e)

        async def receive_from_gemini():
            try:
                while True:
                    gemini_response = await gemini_ws.recv()
                    ulaw_bytes, _ = await handle_gemini_message(gemini_ws, gemini_response, current_lang_state, stream_sid)
                    
                    if ulaw_bytes and stream_sid:
                        # Send audio back to Twilio
                        out_payload = base64.b64encode(ulaw_bytes).decode('utf-8')
                        twilio_msg = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": out_payload
                            }
                        }
                        await websocket.send_text(json.dumps(twilio_msg))
                        
            except websockets.exceptions.ConnectionClosed:
                print("Gemini WebSocket closed")
            except Exception as e:
                print("Error in receive_from_gemini:", e)

        # Run both loops concurrently
        await asyncio.gather(
            receive_from_twilio(),
            receive_from_gemini()
        )
        
    except Exception as e:
        print("Error setting up stream:", e)
    finally:
        if gemini_ws and not gemini_ws.closed:
            await gemini_ws.close()
        if stream_sid:
            update_call_status(stream_sid, False)
            # Sync final state to Firestore
            call_data = get_call_by_id(stream_sid)
            if call_data:
                sync_call_to_firestore(call_data)
                send_push_notification(
                    "Call Concluded", 
                    f"Relationship Manager session with {call_data['customerName']} ended."
                )
        print("Session ended.")

from services.tts_service import synthesize
from services.gemini_stream import transcribe_audio
from google import genai
import websockets

@app.websocket("/voice-stream")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()
    print("Voice WebSocket connected!")

    try:
        from services.database import add_message
        import uuid
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not found in environment!")
            await websocket.send_text(json.dumps({"event": "transcript", "text": "SYSTEM ERROR: API Key missing."}))
            await websocket.close()
            return
        
        client = genai.Client(api_key=api_key)
        
        def get_local_response(query: str, lang: str = "en-US"):
            query = query.lower()
            
            # Match keywords and find policy
            for item in KB_DATA:
                if any(word in query for word in item["title"].lower().split()):
                    if lang == "hi-IN":
                        return f"हमारे {item['title']} पॉलिसी के आधार पर: {item['content']}"
                    elif lang == "kn-IN":
                        return f"{item['title']} ಪಾಲಿಸಿಯ ಆಧಾರದ ಮೇಲೆ: {item['content']}"
                    return f"Based on our {item['title']} policy: {item['content']}"
            
            # Varied fallback responses (randomized to avoid repetition)
            en_fb = [
                "I am VaaniAI, your Relationship Manager. I can help with Tractor Loans, Crop Insurance, KCC, Animal Husbandry, and Solar Pump subsidies. What would you like to know?",
                "Thank you for reaching out! I specialize in agricultural financial products like Tractor Loans, Crop Insurance, and Kisan Credit Card. Which interests you?",
                "Happy to help! We offer Tractor Loans at 8.5%, Crop Insurance under PMFBY, KCC up to 3 Lakh, Dairy Loans, and Solar Pump subsidies. Tell me more about what you need.",
                "Welcome! I can provide details on our agricultural loans, insurance schemes, and government subsidies. Please tell me which product you'd like to explore.",
            ]
            hi_fb = [
                "मैं वाणी एआई हूँ Ji! ट्रैक्टर लोन, फसल बीमा, केसीसी, पशुपालन और सोलर पंप सब्सिडी में मदद कर सकती हूँ। किसके बारे में जानना चाहते हैं?",
                "आपके सवाल के लिए शुक्रिया Ji! हमारे पास ट्रैक्टर लोन, PMFBY फसल बीमा, KCC और सोलर पंप सब्सिडी उपलब्ध है। कौन सा प्रोडक्ट जानना चाहेंगे?",
                "Namaste Ji! कृपया बताइए कि ट्रैक्टर लोन, फसल बीमा, या किसान क्रेडिट कार्ड में से किसके बारे में जानना चाहते हैं?",
            ]
            kn_fb = [
                "ನಾನು ವಾಣಿ ಎಐ. ಟ್ರ್ಯಾಕ್ಟರ್ ಸಾಲ, ಬೆಳೆ ವಿಮೆ, ಕೆಸಿಸಿ, ಪಶುಸಂಗೋಪನೆ ಮತ್ತು ಸೋಲಾರ್ ಪಂಪ್ ಸಬ್ಸಿಡಿ ಬಗ್ಗೆ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ. ಯಾವುದರ ಬಗ್ಗೆ ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಿ?",
                "ನಿಮ್ಮ ಪ್ರಶ್ನೆಗೆ ಧನ್ಯವಾದ! ಕೃಷಿ ಸಾಲ, PMFBY ವಿಮೆ, ಕೆಸಿಸಿ ಕಾರ್ಡ್ ಅಥವಾ PM-KUSUM ಸೋಲಾರ್ ಸಬ್ಸಿಡಿ ಬಗ್ಗೆ ತಿಳಿಸಿ.",
            ]
            
            if lang == "hi-IN":
                return random.choice(hi_fb)
            elif lang == "kn-IN":
                return random.choice(kn_fb)
            return random.choice(en_fb)

        # Conversation history for multi-turn context
        MAX_HISTORY = 20
        conversation_history = []

        while True:
            try:
                data = await websocket.receive_text()
                payload = json.loads(data)
                call_id = payload.get("call_id")
                if call_id == "undefined" or not call_id:
                    call_id = None

                event = payload.get("event")
                lang = payload.get("lang", "en-US")

                if event == "audio":
                    print(f"DEBUG: Audio received for {call_id} in {lang}")
                    audio_bytes = base64.b64decode(payload["payload"])
                    text = await transcribe_audio(audio_bytes, lang)
                    
                    if text:
                        print(f"STT: {text}")
                        await websocket.send_text(json.dumps({"event": "transcript", "text": text}))
                        if call_id:
                            add_message(call_id, str(uuid.uuid4()), "customer", text)
                        
                        system_prompt = f"You are VaaniAI, a professional Relationship Manager for rural India. Answer the following query concisely and clearly in the {lang} language. Keep the response brief, around 1-3 sentences. Ensure you use respectful terms."
                        
                        ai_text = None
                        conversation_history.append({"role": "user", "parts": [{"text": text}]})
                        print(f"Calling Gemini (2.0-flash) for {lang}: {text}")
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.0-flash',
                                contents=conversation_history[-MAX_HISTORY:],
                                config={"system_instruction": system_prompt}
                            )
                            ai_text = response.text
                            conversation_history.append({"role": "model", "parts": [{"text": ai_text}]})
                            print(f"Gemini Success: {ai_text}")
                        except Exception as gem_err:
                            print(f"Gemini Error [{type(gem_err).__name__}]: {gem_err}")
                            ai_text = get_local_response(text, lang)
                            conversation_history.append({"role": "model", "parts": [{"text": ai_text}]})
                        
                        if ai_text:
                            if call_id:
                                add_message(call_id, str(uuid.uuid4()), "ai", ai_text)
                            
                            print(f"Synthesizing {lang} voice for: {ai_text[:50]}...")
                            tts_bytes = await synthesize(ai_text, language_code=lang)
                            if tts_bytes:
                                audio_b64 = base64.b64encode(tts_bytes).decode("utf-8")
                                await websocket.send_text(json.dumps({"event": "audio", "payload": audio_b64, "text": ai_text}))
                                print("Sent audio response.")
                            else:
                                await websocket.send_text(json.dumps({"event": "transcript", "text": ai_text}))

                elif event == "text":
                    text = payload.get("payload", "")
                    if text:
                        print(f"DEBUG: Text input received: {text} in {lang}")
                        await websocket.send_text(json.dumps({"event": "transcript", "text": text}))
                        if call_id:
                            add_message(call_id, str(uuid.uuid4()), "customer", text)
                        
                        system_prompt = f"You are VaaniAI, a professional Relationship Manager for rural India. Answer the following query concisely and clearly in the {lang} language. Keep the response brief, around 1-3 sentences. Ensure you use respectful terms."
                        
                        ai_text = None
                        conversation_history.append({"role": "user", "parts": [{"text": text}]})
                        print(f"Calling Gemini (2.0-flash) for {lang}: {text}")
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.0-flash',
                                contents=conversation_history[-MAX_HISTORY:],
                                config={"system_instruction": system_prompt}
                            )
                            ai_text = response.text
                            conversation_history.append({"role": "model", "parts": [{"text": ai_text}]})
                            print(f"Gemini Success: {ai_text}")
                        except Exception as gem_err:
                            print(f"Gemini Error [{type(gem_err).__name__}]: {gem_err}")
                            ai_text = get_local_response(text, lang)
                            conversation_history.append({"role": "model", "parts": [{"text": ai_text}]})
                        
                        if ai_text:
                            if call_id:
                                add_message(call_id, str(uuid.uuid4()), "ai", ai_text)
                            
                            print(f"Synthesizing {lang} voice for: {ai_text[:50]}...")
                            tts_bytes = await synthesize(ai_text, language_code=lang)
                            if tts_bytes:
                                audio_b64 = base64.b64encode(tts_bytes).decode("utf-8")
                                await websocket.send_text(json.dumps({"event": "audio", "payload": audio_b64, "text": ai_text}))
                                print("Sent audio response.")
                            else:
                                await websocket.send_text(json.dumps({"event": "transcript", "text": ai_text}))
                            
            except WebSocketDisconnect:
                print("Voice WebSocket disconnected in loop")
                break
            except Exception as e:
                print(f"Error in message processing loop: {e}")
                if "disconnect" in str(e).lower() or "close" in str(e).lower():
                    break
                
    except WebSocketDisconnect:
        print("Voice WebSocket disconnected")
    except Exception as e:
        print(f"Fatal error in voice_stream: {e}")

# Serve Frontend - Must be at the end to not catch API routes
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.exists(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")
    
    # Optional: Catch-all for SPA routing (React Router)
    @app.exception_handler(404)
    async def not_found(request, exc):
        from fastapi.responses import FileResponse
        index_path = os.path.join(FRONTEND_PATH, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Not Found"}
else:
    @app.get("/")
    async def root():
        return {"status": "Backend running", "frontend": "Not built yet"}
