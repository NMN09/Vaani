import { useState, useEffect } from 'react';
import { Database, Search, FileText, ChevronRight } from 'lucide-react';

export function KnowledgeBase() {
  const [kbItems, setKbItems] = useState<any[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchKb = () => {
    fetch('/api/knowledge-base')
      .then(res => res.json())
      .then(data => setKbItems(data));
  };

  useEffect(() => {
    fetchKb();
  }, []);

  const handleAddKb = async () => {
    if (!newTitle || !newContent) return;
    try {
      const res = await fetch('/api/knowledge-base', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle, content: newContent })
      });
      if (res.ok) {
        setIsModalOpen(false);
        setNewTitle("");
        setNewContent("");
        fetchKb();
      }
    } catch (e) { console.error(e); }
  };

  const filteredItems = kbItems.filter(item => 
    item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto h-full">
      <header className="glass-panel p-6 rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-md shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/20">
            <Database className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
              Knowledge Base
            </h1>
            <p className="text-slate-400 text-sm mt-1">Manage the expertise powering VaaniAI RAG</p>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-3 glass-panel p-4 rounded-xl border border-slate-800 bg-slate-900/30 flex items-center gap-3">
          <Search className="text-slate-500" size={20} />
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search product expertise..." 
            className="bg-transparent border-none outline-none flex-1 text-slate-200 placeholder:text-slate-600"
          />
        </div>

        {/* Featured Resources Section */}
        <div className="lg:col-span-3 mt-4">
          <h2 className="text-lg font-bold text-slate-300 mb-4 flex items-center gap-2">
            <Search size={18} className="text-amber-500" />
            Featured Training Resources
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-panel p-4 rounded-xl border border-slate-800 bg-slate-800/20 hover:bg-slate-800/40 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400">
                  <FileText size={20} />
                </div>
                <div>
                  <p className="font-bold text-slate-200 text-sm">PM Fasal Bima Yojana Guide</p>
                  <p className="text-xs text-slate-500 uppercase font-mono">PDF • 2.4 MB</p>
                </div>
              </div>
              <a 
                href="/docs/crop_insurance.pdf" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs font-bold text-amber-500 opacity-0 group-hover:opacity-100 transition-opacity hover:underline"
              >
                DOWNLOAD
              </a>
            </div>
            
            <div className="glass-panel p-4 rounded-xl border border-slate-800 bg-slate-800/20 hover:bg-slate-800/40 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
                  <FileText size={20} />
                </div>
                <div>
                  <p className="font-bold text-slate-200 text-sm">Kisan Credit Card (KCC) Policy</p>
                  <p className="text-xs text-slate-500 uppercase font-mono">PDF • 1.1 MB</p>
                </div>
              </div>
              <a 
                href="/docs/kcc_policy.pdf" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs font-bold text-amber-500 opacity-0 group-hover:opacity-100 transition-opacity hover:underline"
              >
                DOWNLOAD
              </a>
            </div>
          </div>
        </div>

        {filteredItems.map((item) => (
          <div key={item.id} className="glass-panel p-6 rounded-2xl border border-slate-800 bg-slate-900/50 hover:border-amber-500/30 transition-all group flex flex-col gap-4">
            <div className="flex items-start justify-between">
              <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-amber-400 group-hover:bg-amber-500/20 transition-colors">
                <FileText size={20} />
              </div>
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-tighter bg-slate-800/50 px-2 py-1 rounded">Source</span>
            </div>
            <div>
              <h3 className="font-bold text-slate-200 text-lg mb-2">{item.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed line-clamp-3">{item.content}</p>
            </div>
            <button className="mt-auto flex items-center gap-1 text-xs font-bold text-amber-400 hover:text-amber-300 transition-colors uppercase tracking-widest">
              View Full Source <ChevronRight size={14} />
            </button>
          </div>
        ))}

        <div 
          onClick={() => setIsModalOpen(true)}
          className="glass-panel p-6 rounded-2xl border border-dashed border-slate-700 bg-slate-900/10 flex flex-col items-center justify-center text-center gap-3 hover:bg-slate-800/20 transition-all cursor-pointer group"
        >
          <div className="w-12 h-12 rounded-full border border-dashed border-slate-600 flex items-center justify-center text-slate-500 group-hover:border-amber-500 group-hover:text-amber-500 transition-colors">
            +
          </div>
          <span className="text-slate-400 font-medium group-hover:text-slate-200">Add New Knowledge</span>
          <p className="text-slate-600 text-xs">Enter Product or Policy details</p>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-panel w-full max-w-md p-6 rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl">
            <h2 className="text-xl font-bold text-slate-200 mb-4">Add Product Expertise</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Product Title</label>
                <input 
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  type="text" 
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-amber-500" 
                  placeholder="e.g. Poultry Farm Loan"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Knowledge Content</label>
                <textarea 
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 h-32 focus:outline-none focus:border-amber-500" 
                  placeholder="Describe the product or policy details..."
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-700 text-slate-400 hover:bg-slate-800 transition-all font-bold"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleAddKb}
                  className="flex-1 px-4 py-3 rounded-xl bg-amber-500 text-white hover:bg-amber-400 transition-all font-bold shadow-lg shadow-amber-500/20"
                >
                  Add to Vault
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
