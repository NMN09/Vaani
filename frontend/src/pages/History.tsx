import { useState, useEffect } from 'react';
import { History as HistoryIcon, MessageSquare, Star, Clock } from 'lucide-react';

export function History() {
  const [calls, setCalls] = useState<any[]>([]);
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/calls')
      .then(res => res.json())
      .then(data => setCalls(data));
  }, []);

  useEffect(() => {
    if (selectedCallId) {
      fetch(`/api/calls/${selectedCallId}/messages`)
        .then(res => res.json())
        .then(data => setMessages(data));
    }
  }, [selectedCallId]);

  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to delete all call history? This cannot be undone.")) return;
    try {
      const res = await fetch('/api/calls', { method: 'DELETE' });
      if (res.ok) {
        setCalls([]);
        setSelectedCallId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
  };

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto h-full">
      <header className="glass-panel p-6 rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-md shadow-2xl flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <HistoryIcon className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Call History
            </h1>
            <p className="text-slate-400 text-sm mt-1">Review past intelligence and conversations</p>
          </div>
        </div>
        <button 
          onClick={handleClearHistory}
          className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl hover:bg-red-500 hover:text-white transition-all text-sm font-medium"
        >
          Clear All History
        </button>
      </header>

      <div className="flex flex-col md:flex-row gap-6 flex-1 min-h-0">
        {/* Call List */}
        <div className="md:w-1/3 glass-panel rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-800/30">
            <h2 className="font-semibold text-slate-200">Recent Logs</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {calls.map((call) => (
              <button
                key={call.id}
                onClick={() => setSelectedCallId(call.id)}
                className={`w-full p-4 text-left border-b border-slate-800/50 transition-all hover:bg-slate-800/40 ${selectedCallId === call.id ? 'bg-indigo-500/10 border-l-4 border-l-indigo-500' : ''}`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-bold text-slate-200">{call.customerName}</span>
                  <div className="flex items-center gap-1 text-amber-400">
                    <Star size={12} fill="currentColor" />
                    <span className="text-xs">{call.score}</span>
                  </div>
                </div>
                <div className="text-xs text-slate-400 flex items-center gap-2">
                  <Clock size={12} /> {call.duration} • {call.phone}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Transcript Details */}
        <div className="flex-1 glass-panel rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden flex flex-col">
          {selectedCallId ? (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
                <h2 className="font-semibold text-slate-200 flex items-center gap-2">
                  <MessageSquare size={18} className="text-indigo-400" />
                  Transcript Details
                </h2>
                <span className="text-xs text-slate-500 font-mono">ID: {selectedCallId.slice(0, 8)}...</span>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex flex-col ${msg.sender === 'customer' ? 'items-end' : 'items-start'}`}>
                    <span className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                      {msg.sender === 'ai' ? 'VaaniAI' : 'Customer'}
                    </span>
                    <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${msg.sender === 'ai' ? 'bg-slate-800 text-slate-200 border border-slate-700' : 'bg-indigo-600/20 text-indigo-100 border border-indigo-500/30'}`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-center flex-col items-center justify-center p-12 text-center">
              <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-4">
                <HistoryIcon className="text-slate-600" size={32} />
              </div>
              <h3 className="text-slate-400 font-medium">Select a log to view details</h3>
              <p className="text-slate-500 text-sm mt-1">Past call transcripts and AI analysis will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
