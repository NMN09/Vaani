import React, { useState, useRef, useEffect } from "react";
import { decodeBase64ToBlob } from "../lib/audio";
import { Mic, MicOff, Send } from "lucide-react";

const getWsUrl = () => {
  if (import.meta.env.VITE_BACKEND_URL) return `${import.meta.env.VITE_BACKEND_URL}/voice-stream`;
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/voice-stream`;
};
const WS_URL = getWsUrl();

// For TypeScript
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export const VoiceChat: React.FC<{ callId?: string }> = ({ callId }) => {
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [lang, setLang] = useState<string>(
    (import.meta.env.VITE_DEFAULT_VOICE_LANG as string) ?? "en-US"
  );
  
  const ws = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const recognitionRef = useRef<any>(null);

  // ----- WebSocket handling -------------------------------------------------
  const startWebSocket = () => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) return;
    ws.current = new WebSocket(WS_URL);
    ws.current.onopen = () => console.log("Voice WS opened");
    ws.current.onmessage = async (ev) => {
      const data = JSON.parse(ev.data);
      if (data.event === "transcript") {
        // Backend confirms it received the text
      } else if (data.event === "audio") {
        // Render the AI's text response in the UI
        if (data.text) {
          setAiResponse(data.text);
        }
        // Received AI‑generated audio (base64) – play it
        const blob = decodeBase64ToBlob(data.payload, "audio/mp3");
        if (audioRef.current) {
          audioRef.current.src = URL.createObjectURL(blob);
          audioRef.current.play().catch(e => console.error("Audio playback failed:", e));
        }
      }
    };
    ws.current.onerror = (e) => console.error("Voice WS error:", e);
    ws.current.onclose = () => console.log("Voice WS closed");
  };

  // ----- Recording via SpeechRecognition -------------------------------------
  const initSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support Speech Recognition. Please use Chrome or Edge.");
      return null;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event: any) => {
      let currentTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        currentTranscript += event.results[i][0].transcript;
      }
      setTranscript(currentTranscript);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error", event.error);
    };

    return recognition;
  };

  const startRecording = () => {
    if (!recognitionRef.current) {
      recognitionRef.current = initSpeechRecognition();
    }
    if (recognitionRef.current) {
      recognitionRef.current.lang = lang; // update lang if changed
      try {
        recognitionRef.current.start();
        setRecording(true);
        setTranscript(""); // clear previous
        setAiResponse(""); // clear previous AI reply
      } catch (e) {
        console.error("Failed to start recognition", e);
      }
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current && recording) {
      recognitionRef.current.stop();
      setRecording(false);
      
      // Send the final transcript to the backend
      if (transcript.trim() && ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(
          JSON.stringify({ event: "text", payload: transcript.trim(), lang, call_id: callId })
        );
      } else if (transcript.trim() && ws.current?.readyState !== WebSocket.OPEN) {
        // Fallback: reconnect and send
        startWebSocket();
        setTimeout(() => {
          ws.current?.send(
            JSON.stringify({ event: "text", payload: transcript.trim(), lang, call_id: callId })
          );
        }, 500);
      }
    }
  };

  // ----- UI ---------------------------------------------------------------
  useEffect(() => {
    startWebSocket();
    return () => {
      if (ws.current) ws.current.close();
      if (recognitionRef.current) recognitionRef.current.stop();
    };
  }, []);

  return (
    <div className="bg-gray-800 p-4 rounded-xl shadow-lg border border-gray-700 max-w-2xl mx-auto my-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Multilingual Voice Chat</h3>
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          className="bg-gray-700 text-white border border-gray-600 rounded-md px-3 py-1 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
        >
          <option value="en-US">English</option>
          <option value="hi-IN">Hindi (हिंदी)</option>
          <option value="kn-IN">Kannada (ಕನ್ನಡ)</option>
        </select>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <button
            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-full font-medium transition-all w-full select-none
              ${recording 
                ? 'bg-red-500/20 text-red-500 border border-red-500/50 animate-pulse' 
                : 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-md hover:shadow-lg'}`}
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onMouseLeave={recording ? stopRecording : undefined}
            onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
            onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
            aria-label="Hold to talk"
          >
            {recording ? (
              <>
                <MicOff className="w-5 h-5" />
                <span>Listening... Release to send</span>
              </>
            ) : (
              <>
                <Mic className="w-5 h-5" />
                <span>Hold to speak</span>
              </>
            )}
          </button>
        </div>

        {!recording && (
          <div className="relative">
            <textarea
              placeholder={`Or type here in ${lang === 'hi-IN' ? 'Hindi' : lang === 'kn-IN' ? 'Kannada' : 'English'}...`}
              rows={2}
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none pr-12"
              onKeyDown={async (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  const target = e.target as HTMLTextAreaElement;
                  const txt = target.value.trim();
                  if (!txt) return;
                  if (ws.current?.readyState !== WebSocket.OPEN) startWebSocket();
                  
                  ws.current?.send(
                    JSON.stringify({ event: "text", payload: txt, lang, call_id: callId })
                  );
                  setTranscript(txt);
                  setAiResponse(""); // clear previous
                  target.value = "";
                }
              }}
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
              <Send className="w-4 h-4" />
            </div>
          </div>
        )}

        {transcript && (
          <div className="bg-gray-900/50 rounded-lg p-4 mt-2">
            <p className="text-sm text-gray-400 mb-1">You said:</p>
            <p className="text-white text-sm leading-relaxed">{transcript}</p>
          </div>
        )}
        
        {aiResponse && (
          <div className="bg-emerald-900/20 border border-emerald-500/30 rounded-lg p-4 mt-2">
            <p className="text-sm text-emerald-400 mb-1">VaaniAI Replied:</p>
            <p className="text-emerald-50 text-sm leading-relaxed">{aiResponse}</p>
          </div>
        )}
      </div>

      <audio ref={audioRef} hidden />
    </div>
  );
};
