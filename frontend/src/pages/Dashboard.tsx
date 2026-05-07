import { useState, useEffect } from 'react';
import { ActiveCallFeed } from '../components/ActiveCallFeed';
import { TranscriptView } from '../components/TranscriptView';
import { PostCallSummary } from '../components/PostCallSummary';
import { VoiceChat } from '../components/VoiceChat';
import { PhoneOff, Activity, MessageCircle } from 'lucide-react';

export function Dashboard() {
  const [calls, setCalls] = useState<any[]>([]);
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [isCallEnded, setIsCallEnded] = useState(false);
  const [postCallData, setPostCallData] = useState<any>(null);

  const activeCall = calls.find(c => c.id === activeCallId);

  // Poll for calls
  useEffect(() => {
    const fetchCalls = async () => {
      try {
        const res = await fetch('/api/calls');
        const data = await res.json();
        setCalls(data);
        if (data.length > 0 && !activeCallId) {
          setActiveCallId(data[0].id);
        }
      } catch (e) { console.error("Poll calls error:", e); }
    };
    fetchCalls();
    const interval = setInterval(fetchCalls, 2000);
    return () => clearInterval(interval);
  }, [activeCallId]);

  // Poll for messages
  useEffect(() => {
    if (!activeCallId) return;
    setIsCallEnded(false);
    setPostCallData(null);
    
    const fetchMessages = async () => {
      try {
        const res = await fetch(`/api/calls/${activeCallId}/messages`);
        const data = await res.json();
        setMessages(data);
      } catch (e) { console.error("Poll messages error:", e); }
    };
    fetchMessages();
    const interval = setInterval(fetchMessages, 1500);
    return () => clearInterval(interval);
  }, [activeCallId]);

  const handleEndCall = async () => {
    if (!activeCall) return;
    setIsCallEnded(true);
    
    try {
      const res = await fetch('/api/post-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          call_id: activeCall.id
        })
      });
      const data = await res.json();
      setPostCallData(data);
    } catch (e) {
      console.error("Post-call error:", e);
      setPostCallData({
        summary: "Error communicating with backend API.",
        next_steps: ["Ensure FastAPI server is running on port 8000"],
        whatsapp_message: "Error...",
        whatsapp_sent: false
      });
    }
  };

  const handleSimulateCall = async () => {
    try {
      const res = await fetch('/api/calls/simulate', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        // Refresh calls
        const freshCalls = await fetch('/api/calls').then(r => r.json());
        setCalls(freshCalls);
        setActiveCallId(data.call_id);
      }
    } catch (err) {
      console.error("Simulation failed:", err);
    }
  };

  const handleSendWhatsApp = async () => {
    if (!activeCall) return;
    try {
      const res = await fetch('/api/post-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ call_id: activeCall.id })
      });
      const data = await res.json();
      setPostCallData(data);
      alert("WhatsApp summary generated and sent successfully!");
    } catch (e) { console.error(e); }
  };

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto h-full">
      <header className="glass-panel p-6 rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-md shadow-2xl flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Activity className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              Live Intelligence
            </h1>
            <p className="text-slate-400 text-sm mt-1">Real-time Call Monitoring & Analysis</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 bg-slate-800/50 rounded-xl border border-slate-700/50 flex items-center gap-3">
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Status</span>
              <span className={`text-xs font-mono ${activeCall?.isActive ? 'text-emerald-400' : 'text-slate-400'}`}>
                {activeCall?.isActive ? 'LIVE' : 'DISCONNECTED'}
              </span>
            </div>
            <div className="w-px h-8 bg-slate-700"></div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Score</span>
              <span className="text-xs font-mono text-amber-400">{activeCall?.score || 0}/10</span>
            </div>
          </div>
          
          <button 
            onClick={handleSendWhatsApp}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-white rounded-xl transition-all border border-emerald-500/20 text-sm font-medium"
          >
            <MessageCircle size={18} />
            Send WhatsApp
          </button>
          
          <button 
            onClick={handleEndCall}
            className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white rounded-xl transition-all border border-red-500/20 text-sm font-medium"
          >
            <PhoneOff size={18} />
            End Call
          </button>
        </div>
      </header>

      <div className="flex flex-col md:flex-row gap-6 flex-1 min-h-0">
        <div className="md:w-1/3 flex flex-col gap-4">
          <VoiceChat callId={activeCallId || undefined} />
          <ActiveCallFeed 
            calls={calls} 
            activeId={activeCallId || ''} 
            onSelect={setActiveCallId} 
            onSimulate={handleSimulateCall}
          />
        </div>
        <div className="flex-1 flex flex-col gap-4 min-h-0 relative">
          {isCallEnded ? (
            <PostCallSummary data={postCallData} />
          ) : (
            <TranscriptView messages={messages} />
          )}
        </div>
      </div>
    </div>
  );
}
