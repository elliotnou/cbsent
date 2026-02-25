import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { LayoutDashboard, FileText, Send, Sun, Moon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
}

const TOOL_LABELS: Record<string, string> = {
  get_sentiment_summary: 'sentiment data',
  get_transcripts: 'transcripts',
  get_transcript_sentences: 'sentence detail',
  search_sentences: 'searched sentences',
  get_divergence: 'divergence data',
};

const SUGGESTED_PROMPTS = [
  "How has Fed sentiment changed over the past year?",
  "Compare the latest BoC and Fed stances",
  "Which transcripts were most hawkish?",
  "Search for sentences about inflation from the Fed",
];

const ChatPage = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const [light, setLight] = useState(() => document.documentElement.classList.contains('light'));
  const toggleTheme = () => {
    setLight(p => { document.documentElement.classList.toggle('light', !p); return !p; });
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (text?: string) => {
    const userMessage = (text || input).trim();
    if (!userMessage || loading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    const history = messages.map(m => ({ role: m.role, content: m.content }));

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120000);
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, history }),
        signal: controller.signal,
      });
      clearTimeout(timeout);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status}: ${text}`);
      }
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        toolCalls: data.tool_calls_made,
      }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      console.error('Chat error:', msg);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: msg.includes('aborted')
          ? 'Request timed out — the server may be waking up. Try again in a moment.'
          : `Something went wrong (${msg}). Please try again.`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="h-screen theme-bg theme-text flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 px-6 md:px-12 lg:px-16 pt-6 pb-4 border-b theme-border">
        <div className="max-w-[900px] mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold theme-heading tracking-tight">Policy Analyst</h1>
            <p className="theme-muted mt-1 text-[13px]">Ask questions about central bank sentiment data</p>
          </div>
          <div className="flex gap-1">
            <button
              onClick={toggleTheme}
              className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
              title={light ? 'Dark mode' : 'Light mode'}
            >
              {light ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            <Link
              to="/"
              className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
              title="Dashboard"
            >
              <LayoutDashboard size={16} />
            </Link>
            <Link
              to="/transcripts"
              className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
              title="Transcripts"
            >
              <FileText size={16} />
            </Link>
          </div>
        </div>
      </header>

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto px-6 md:px-12 lg:px-16 py-6">
        <div className="max-w-[900px] mx-auto space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] animate-fade-in">
              <div className="text-gray-600 text-sm mb-8">Ask anything about Fed and BoC monetary policy sentiment</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-[600px]">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => sendMessage(prompt)}
                    className="text-left px-4 py-3 card text-[13px] text-gray-400 hover:text-gray-200 transition-all duration-150"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-3 ${
                      msg.role === 'user'
                        ? `bg-blue-500/8 ${light ? 'text-gray-800' : 'text-gray-200'}`
                        : `card ${light ? 'text-gray-800' : 'text-gray-300'}`
                    }`}
                    style={msg.role === 'user' ? { boxShadow: '0 1px 2px rgba(0,0,0,0.2), inset 0 0 0 1px rgba(96,165,250,0.1)' } : undefined}
                  >
                    <div className={`text-[13px] leading-relaxed prose prose-sm max-w-none prose-p:my-1 prose-li:my-0.5 prose-ul:my-1 prose-ol:my-1 prose-headings:my-2 ${light ? 'prose-gray prose-strong:text-black' : 'prose-invert prose-strong:text-gray-200'}`}>
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/5">
                        {msg.toolCalls.map((tc, j) => (
                          <span
                            key={j}
                            className="inline-flex items-center px-2 py-0.5 text-[10px] font-medium bg-emerald-500/8 text-emerald-400/70 rounded"
                          >
                            {TOOL_LABELS[tc.tool] || tc.tool}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start animate-fade-in">
                  <div className="flex items-center gap-3 px-1 py-2">
                    <svg className="chat-draw" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      {/* outer hexagon */}
                      <path className="draw-hex" d="M12 2 L21.5 7.5 L21.5 16.5 L12 22 L2.5 16.5 L2.5 7.5 Z" />
                      {/* inner star */}
                      <path className="draw-star" d="M12 6 L13.5 10.5 L18 10.5 L14.5 13.5 L15.5 18 L12 15.5 L8.5 18 L9.5 13.5 L6 10.5 L10.5 10.5 Z" />
                      {/* center dot */}
                      <circle className="draw-dot" cx="12" cy="12" r="1.5" />
                    </svg>
                    <span className="text-[11px] text-gray-500">Thinking</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </main>

      {/* Input bar */}
      <div className="flex-shrink-0 px-6 md:px-12 lg:px-16 pb-6 pt-3">
        <div className="max-w-[900px] mx-auto">
          <div className="flex gap-3 card rounded-xl p-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about monetary policy sentiment..."
              disabled={loading}
              className="flex-1 bg-transparent text-[13px] text-gray-200 placeholder-gray-600 outline-none px-2 disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              className="p-2 text-gray-400 rounded-md hover:text-gray-200 hover:bg-white/10 transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Send size={14} />
            </button>
          </div>
          <div className="text-[10px] text-gray-700 mt-2 text-center">
            Powered by GPT-4o-mini with tool-use · Queries your sentiment database in real time
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
