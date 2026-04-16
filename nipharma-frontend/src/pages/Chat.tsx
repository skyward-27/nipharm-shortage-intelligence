import { useState, useRef, useEffect } from "react";
import { chatWithGroq, healthCheck, ChatMessage } from "../api";

const MAX_CHARS = 500;

const QUICK_QUESTIONS = [
  "Which drugs are on NHS concessions this month?",
  "Top 5 drugs at highest shortage risk right now?",
  "How does GBP/INR affect UK drug import costs?",
  "What bulk buying opportunities exist for Amoxicillin?",
  "Show Metformin concession price history",
  "What are the latest MHRA shortage alerts?",
];

interface ChatMessageWithTime extends ChatMessage {
  timestamp: Date;
}

// ── Markdown renderer ────────────────────────────────────────────────────────
function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<div style="font-size:13px;font-weight:800;color:#0f172a;margin:14px 0 5px;text-transform:uppercase;letter-spacing:0.5px">$1</div>')
    .replace(/^## (.+)$/gm, '<div style="font-size:15px;font-weight:800;color:#0f172a;margin:16px 0 6px">$1</div>')
    .replace(/^# (.+)$/gm, '<div style="font-size:17px;font-weight:800;color:#0f172a;margin:18px 0 8px">$1</div>')
    .replace(/^\d+\.\s(.+)$/gm, '<div style="display:flex;gap:8px;margin:5px 0;line-height:1.5"><span style="color:#3b82f6;font-weight:700;min-width:18px;flex-shrink:0">•</span><span>$1</span></div>')
    .replace(/^[-•]\s(.+)$/gm, '<div style="display:flex;gap:8px;margin:5px 0;line-height:1.5"><span style="color:#3b82f6;font-weight:700;flex-shrink:0">•</span><span>$1</span></div>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Welcome screen (shown when no messages) ──────────────────────────────────
function WelcomeScreen({ onAsk }: { onAsk: (q: string) => void }) {
  return (
    <div className="welcome-wrap">
      <div className="welcome-icon">
        <svg width={32} height={32} viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
      </div>
      <h2 className="welcome-title">NiPharm AI Assistant</h2>
      <p className="welcome-sub">
        Ask about NHS drug shortages, concession prices, bulk buying opportunities, or MHRA alerts.
        Powered by Groq · <span style={{ color: "#8b5cf6" }}>llama-3.3-70b</span>
      </p>
      <div className="welcome-grid">
        {QUICK_QUESTIONS.map(q => (
          <button key={q} className="welcome-chip" onClick={() => onAsk(q)}>
            <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, opacity: 0.6 }}>
              <circle cx={12} cy={12} r={10}/><line x1={12} y1={8} x2={12} y2={12}/><line x1={12} y1={16} x2="12.01" y2={16}/>
            </svg>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="msg-row msg-row-ai">
      <div className="msg-avatar msg-avatar-ai">
        <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
      </div>
      <div className="msg-bubble msg-bubble-ai">
        <div className="typing-dots">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}

// ── Single message bubble ────────────────────────────────────────────────────
function MessageBubble({ msg, idx, onCopy, copied }: { msg: ChatMessageWithTime; idx: number; onCopy: (i: number, t: string) => void; copied: number | null }) {
  const isUser = msg.role === "user";
  return (
    <div className={`msg-row ${isUser ? "msg-row-user" : "msg-row-ai"}`}>
      {!isUser && (
        <div className="msg-avatar msg-avatar-ai">
          <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
      )}
      <div className={`msg-bubble-wrap ${isUser ? "msg-bubble-wrap-user" : ""}`}>
        <div className={`msg-bubble ${isUser ? "msg-bubble-user" : "msg-bubble-ai"}`}>
          {isUser ? (
            <span>{msg.content}</span>
          ) : (
            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
          )}
        </div>
        <div className={`msg-meta ${isUser ? "msg-meta-right" : ""}`}>
          <span className="msg-time">{formatTime(msg.timestamp)}</span>
          {!isUser && (
            <button className="msg-copy" onClick={() => onCopy(idx, msg.content)} title="Copy response">
              {copied === idx ? (
                <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth={2.5} strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              ) : (
                <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"><rect x={9} y={9} width={13} height={13} rx={2}/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
              )}
              {copied === idx ? "Copied" : "Copy"}
            </button>
          )}
        </div>
      </div>
      {isUser && (
        <div className="msg-avatar msg-avatar-user">
          <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx={12} cy={7} r={4}/>
          </svg>
        </div>
      )}
    </div>
  );
}

// ── Main Chat Component ──────────────────────────────────────────────────────
export default function Chat() {
  const [messages,  setMessages]  = useState<ChatMessageWithTime[]>([]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const [copied,    setCopied]    = useState<number | null>(null);
  const [tavilyOn,  setTavilyOn]  = useState(false);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef    = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    healthCheck()
      .then((d: any) => { setTavilyOn(!!d?.tavily_configured); setBackendOk(true); })
      .catch(() => setBackendOk(false));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 120) + "px"; }
  }, [input]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMessageWithTime = { role: "user", content: trimmed, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const apiHistory: ChatMessage[] = messages.map(({ role, content }) => ({ role, content }));
      const res = await chatWithGroq(trimmed, apiHistory);
      const aiMsg: ChatMessageWithTime = {
        role: "assistant",
        content: res.response || "I couldn't generate a response. Please try again.",
        timestamp: new Date(res.timestamp || Date.now()),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      setMessages(prev => prev.slice(0, -1)); // remove optimistic user msg
      setError(err instanceof Error ? err.message : "Failed to send message. Is the backend online?");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  const handleCopy = (idx: number, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(idx);
      setTimeout(() => setCopied(null), 2000);
    });
  };

  const clearChat = () => { setMessages([]); setError(null); };

  const charsLeft = MAX_CHARS - input.length;

  return (
    <div className="chat-layout">

      {/* ── SIDEBAR ─────────────────────────────────────────────────────── */}
      <aside className="chat-sidebar">
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <div className="sidebar-brand-icon">
              {/* Molecular hexagon logo mark */}
              <svg width={22} height={22} viewBox="0 0 28 28" fill="none">
                <path d="M14 2L24 7.5V20.5L14 26L4 20.5V7.5Z" fill="url(#npGrad)" />
                <path d="M14 2L24 7.5V20.5L14 26L4 20.5V7.5Z" stroke="rgba(255,255,255,0.15)" strokeWidth="0.75" fill="none"/>
                {/* Center core */}
                <circle cx="14" cy="14" r="3" fill="white"/>
                {/* Orbital nodes */}
                <circle cx="9.5" cy="11" r="1.6" fill="white" fillOpacity="0.8"/>
                <circle cx="18.5" cy="11" r="1.6" fill="white" fillOpacity="0.8"/>
                <circle cx="9.5" cy="17" r="1.6" fill="white" fillOpacity="0.8"/>
                <circle cx="18.5" cy="17" r="1.6" fill="white" fillOpacity="0.8"/>
                {/* Bond lines */}
                <line x1="11.3" y1="12.3" x2="12.1" y2="12.9" stroke="rgba(255,255,255,0.65)" strokeWidth="1.2" strokeLinecap="round"/>
                <line x1="16.7" y1="12.3" x2="15.9" y2="12.9" stroke="rgba(255,255,255,0.65)" strokeWidth="1.2" strokeLinecap="round"/>
                <line x1="11.3" y1="15.7" x2="12.1" y2="15.1" stroke="rgba(255,255,255,0.65)" strokeWidth="1.2" strokeLinecap="round"/>
                <line x1="16.7" y1="15.7" x2="15.9" y2="15.1" stroke="rgba(255,255,255,0.65)" strokeWidth="1.2" strokeLinecap="round"/>
                <defs>
                  <linearGradient id="npGrad" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#1e40af"/>
                    <stop offset="1" stopColor="#3b82f6"/>
                  </linearGradient>
                </defs>
              </svg>
              {/* Live pulse indicator */}
              <span className="brand-live-dot"/>
            </div>
            <div>
              <div className="sidebar-brand-name"><span style={{ color: "#60a5fa" }}>Ni</span>Pharm <span style={{ color: "#94a3b8", fontWeight: 500 }}>AI</span></div>
              <div className="sidebar-brand-sub">Drug Intelligence · UK</div>
            </div>
          </div>
          <button className="sidebar-new-btn" onClick={clearChat}>
            <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round"><line x1={12} y1={5} x2={12} y2={19}/><line x1={5} y1={12} x2={19} y2={12}/></svg>
            New Chat
          </button>
        </div>

        <div className="sidebar-divider" />

        <div className="sidebar-section-label">Suggested Questions</div>
        <div className="sidebar-questions">
          {QUICK_QUESTIONS.map(q => (
            <button key={q} className="sidebar-q-btn" onClick={() => sendMessage(q)} disabled={loading}>
              <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" style={{ flexShrink: 0, opacity: 0.5 }}>
                <line x1={5} y1={12} x2={19} y2={12}/><polyline points="12 5 19 12 12 19"/>
              </svg>
              {q}
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-model-info">
            <div className="sidebar-model-row">
              <span className="sidebar-model-label">Model</span>
              <span className="sidebar-model-val">llama-3.3-70b</span>
            </div>
            <div className="sidebar-model-row">
              <span className="sidebar-model-label">Provider</span>
              <span className="sidebar-model-val">Groq</span>
            </div>
            <div className="sidebar-model-row">
              <span className="sidebar-model-label">Search</span>
              <span className="sidebar-model-val" style={{ color: tavilyOn ? "#10b981" : "#64748b" }}>
                {tavilyOn ? "Tavily ON" : "Tavily OFF"}
              </span>
            </div>
            <div className="sidebar-model-row">
              <span className="sidebar-model-label">Backend</span>
              <span className="sidebar-model-val" style={{ color: backendOk === true ? "#10b981" : backendOk === false ? "#ef4444" : "#64748b" }}>
                {backendOk === null ? "Checking…" : backendOk ? "Online" : "Offline"}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── MAIN CHAT AREA ──────────────────────────────────────────────── */}
      <div className="chat-main">

        {/* Top bar */}
        <div className="chat-topbar">
          <div className="chat-topbar-left">
            <div className="chat-topbar-title">NiPharm AI Assistant</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="model-badge">
                <svg width={11} height={11} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" style={{ opacity: 0.7 }}>
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>
                llama-3.3-70b · Groq
              </span>
              {tavilyOn && (
                <span className="search-badge">
                  <svg width={11} height={11} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
                    <circle cx={11} cy={11} r={8}/><line x1={21} y1={21} x2={16.65} y2={16.65}/>
                  </svg>
                  Web Search
                </span>
              )}
            </div>
          </div>
          <button className="chat-clear-btn" onClick={clearChat} title="Clear conversation">
            <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
            </svg>
            Clear
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <div className="chat-error-bar">
            <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
              <circle cx={12} cy={12} r={10}/><line x1={12} y1={8} x2={12} y2={12}/><line x1={12} y1={16} x2="12.01" y2={16}/>
            </svg>
            {error}
            <button onClick={() => setError(null)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "inherit", padding: "0 4px", fontSize: 16, lineHeight: 1 }}>×</button>
          </div>
        )}

        {/* Messages */}
        <div className="chat-messages">
          {messages.length === 0 && !loading && (
            <WelcomeScreen onAsk={sendMessage} />
          )}
          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} idx={i} onCopy={handleCopy} copied={copied} />
          ))}
          {loading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="chat-input-area">
          {/* Quick pill suggestions (show only when no messages) */}
          {messages.length === 0 && (
            <div className="chat-pills-row">
              {QUICK_QUESTIONS.slice(0, 3).map(q => (
                <button key={q} className="chat-pill-btn" onClick={() => sendMessage(q)} disabled={loading}>
                  {q}
                </button>
              ))}
            </div>
          )}

          <div className="chat-input-box">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about drug shortages, prices, concessions..."
              maxLength={MAX_CHARS}
              rows={1}
              disabled={loading}
            />
            <div className="chat-input-actions">
              {input.length > 0 && (
                <span className="char-count" style={{ color: charsLeft < 50 ? "#ef4444" : "#94a3b8" }}>
                  {charsLeft}
                </span>
              )}
              <button
                className="send-btn"
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim()}
                aria-label="Send message"
              >
                {loading ? (
                  <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" style={{ animation: "chat-spin 1s linear infinite" }}>
                    <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
                  </svg>
                ) : (
                  <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
                    <line x1={22} y1={2} x2={11} y2={13}/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                  </svg>
                )}
              </button>
            </div>
          </div>
          <div className="chat-input-hint">
            Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line · {MAX_CHARS} char limit
          </div>
        </div>
      </div>

      <style>{CSS}</style>
    </div>
  );
}

// ── CSS ───────────────────────────────────────────────────────────────────────
const CSS = `
.chat-layout {
  display: flex;
  height: calc(100vh - 60px);
  overflow: hidden;
  font-family: var(--app-font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif);
}

@keyframes chat-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ── SIDEBAR ── */
.chat-sidebar {
  width: 260px;
  min-width: 260px;
  background: #0f172a;
  border-right: 1px solid rgba(255,255,255,0.07);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-top {
  padding: 18px 16px 12px;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.sidebar-brand-icon {
  width: 40px;
  height: 40px;
  position: relative;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 0 0 1px rgba(59,130,246,0.25), 0 4px 12px rgba(30,64,175,0.35);
}
.brand-live-dot {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  border: 1.5px solid #0f172a;
  animation: livePulse 2s ease-in-out infinite;
}
@keyframes livePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.6); }
  50%       { box-shadow: 0 0 0 4px rgba(16,185,129,0); }
}

.sidebar-brand-name {
  font-size: 0.95rem;
  font-weight: 800;
  color: white;
  letter-spacing: -0.2px;
}

.sidebar-brand-sub {
  font-size: 0.65rem;
  color: #475569;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 1px;
}

.sidebar-new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  width: 100%;
  padding: 9px;
  background: rgba(59,130,246,0.12);
  border: 1px solid rgba(59,130,246,0.2);
  border-radius: 10px;
  color: #93c5fd;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.sidebar-new-btn:hover {
  background: rgba(59,130,246,0.22);
  color: #bfdbfe;
}

.sidebar-divider {
  height: 1px;
  background: rgba(255,255,255,0.06);
  margin: 0;
  flex-shrink: 0;
}

.sidebar-section-label {
  padding: 14px 16px 8px;
  font-size: 0.67rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #334155;
  flex-shrink: 0;
}

.sidebar-questions {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
}

.sidebar-q-btn {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 10px;
  background: none;
  border: none;
  border-radius: 8px;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.45;
  text-align: left;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  width: 100%;
}

.sidebar-q-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.05);
  color: #94a3b8;
}

.sidebar-q-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.sidebar-footer {
  flex-shrink: 0;
  padding: 12px 14px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.sidebar-model-info { display: flex; flex-direction: column; gap: 5px; }

.sidebar-model-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-model-label { font-size: 0.7rem; color: #334155; font-weight: 600; }
.sidebar-model-val   { font-size: 0.7rem; color: #64748b; font-family: monospace; }

/* ── MAIN ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  overflow: hidden;
  min-width: 0;
}

/* Top bar */
.chat-topbar {
  height: 56px;
  background: white;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.chat-topbar-left { display: flex; flex-direction: column; gap: 3px; }

.chat-topbar-title {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1;
}

.model-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.7rem;
  font-weight: 700;
  color: #8b5cf6;
  background: rgba(139,92,246,0.08);
  border: 1px solid rgba(139,92,246,0.2);
  padding: 2px 8px;
  border-radius: 999px;
}

.search-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.7rem;
  font-weight: 700;
  color: #10b981;
  background: rgba(16,185,129,0.08);
  border: 1px solid rgba(16,185,129,0.2);
  padding: 2px 8px;
  border-radius: 999px;
}

.chat-clear-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.chat-clear-btn:hover {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #dc2626;
}

/* Error bar */
.chat-error-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  background: #fef2f2;
  border-bottom: 1px solid #fecaca;
  color: #dc2626;
  font-size: 0.82rem;
  font-weight: 600;
  flex-shrink: 0;
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 24px 12px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  scroll-behavior: smooth;
}

/* Welcome */
.welcome-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 40px 20px 20px;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.welcome-icon {
  width: 60px;
  height: 60px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}

.welcome-title {
  font-size: 1.3rem;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 10px;
}

.welcome-sub {
  font-size: 0.88rem;
  color: #64748b;
  line-height: 1.6;
  max-width: 420px;
  margin-bottom: 28px;
}

.welcome-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
}

.welcome-chip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  color: #334155;
  font-size: 0.8rem;
  line-height: 1.45;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.welcome-chip:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(59,130,246,0.12);
}

/* Message rows */
.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  animation: msg-in 0.18s ease both;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.msg-row-user { flex-direction: row-reverse; }

.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.msg-avatar-ai   { background: #eff6ff; color: #3b82f6; border: 1px solid #bfdbfe; }
.msg-avatar-user { background: #3b82f6; color: white; }

.msg-bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 72%;
}

.msg-bubble-wrap-user { align-items: flex-end; }

.msg-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 0.875rem;
  line-height: 1.6;
  word-break: break-word;
}

.msg-bubble-user {
  background: #3b82f6;
  color: white;
  border-bottom-right-radius: 4px;
}

.msg-bubble-ai {
  background: white;
  color: #0f172a;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 4px;
}

.msg-meta-right { flex-direction: row-reverse; }

.msg-time {
  font-size: 0.68rem;
  color: #94a3b8;
  font-family: monospace;
}

.msg-copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.68rem;
  color: #94a3b8;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: color 0.12s;
}

.msg-copy:hover { color: #3b82f6; }

/* Typing dots */
.typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
}

.typing-dots span {
  width: 7px;
  height: 7px;
  background: #94a3b8;
  border-radius: 50%;
  animation: typing-bounce 1.2s infinite;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
  0%,60%,100% { transform: translateY(0); opacity: 0.5; }
  30%          { transform: translateY(-6px); opacity: 1; }
}

/* Input area */
.chat-input-area {
  flex-shrink: 0;
  background: white;
  border-top: 1px solid #e2e8f0;
  padding: 14px 20px 16px;
}

.chat-pills-row {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.chat-pill-btn {
  padding: 6px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.12s;
  white-space: nowrap;
}

.chat-pill-btn:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #3b82f6;
}

.chat-pill-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.chat-input-box {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  padding: 10px 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.chat-input-box:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background: white;
}

.chat-textarea {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 0.9rem;
  color: #0f172a;
  resize: none;
  line-height: 1.5;
  max-height: 120px;
  overflow-y: auto;
  scrollbar-width: thin;
}

.chat-textarea::placeholder { color: #94a3b8; }
.chat-textarea:disabled { opacity: 0.5; cursor: not-allowed; }

.chat-input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.char-count {
  font-size: 0.7rem;
  font-family: monospace;
  font-weight: 600;
}

.send-btn {
  width: 36px;
  height: 36px;
  background: #3b82f6;
  border: none;
  border-radius: 10px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: scale(1.05);
}

.send-btn:active:not(:disabled) { transform: scale(0.95); }

.send-btn:disabled {
  background: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
  transform: none;
}

.chat-input-hint {
  margin-top: 8px;
  font-size: 0.7rem;
  color: #94a3b8;
  text-align: center;
}

.chat-input-hint kbd {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.68rem;
  font-family: monospace;
  color: #64748b;
}

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
  .chat-sidebar { display: none; }
  .chat-messages { padding: 16px 14px 8px; }
  .chat-input-area { padding: 10px 14px 12px; }
  .welcome-grid { grid-template-columns: 1fr; }
  .msg-bubble-wrap { max-width: 85%; }
}

@media (prefers-reduced-motion: reduce) {
  .msg-row, .typing-dots span, .welcome-chip { animation: none !important; transition: none !important; }
}
`;
