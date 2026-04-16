import { useState, useRef, useEffect } from "react";
import { chatWithGroq, ChatMessage } from "../api";

const MAX_CHARS = 500;

const QUICK_QUESTIONS = [
  "Which drugs are on NHS concessions this month?",
  "Top 5 drugs at shortage risk in UK right now?",
  "What bulk buying opportunities exist for Amoxicillin?",
];

function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^### (.+)$/gm, '<h4 style="margin:10px 0 3px;color:#1a1a1a;font-size:0.9rem">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="margin:12px 0 4px;color:#1a1a1a;font-size:0.95rem">$1</h3>')
    .replace(/^\d+\.\s(.+)$/gm, '<div style="display:flex;gap:6px;margin:3px 0"><span style="color:#1976d2;font-weight:600;min-width:16px">•</span><span>$1</span></div>')
    .replace(/^[-•]\s(.+)$/gm, '<div style="display:flex;gap:6px;margin:3px 0"><span style="color:#1976d2;font-weight:600">•</span><span>$1</span></div>')
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

interface ChatMessageWithTime extends ChatMessage {
  timestamp: Date;
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<ChatMessageWithTime[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        inputRef.current?.focus();
      }, 100);
    }
  }, [open, history]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMessageWithTime = {
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };
    setHistory((prev) => [...prev, userMsg]);
    setMessage("");
    setLoading(true);
    setError(null);

    try {
      const apiHistory: ChatMessage[] = history.map(({ role, content }) => ({ role, content }));
      const response = await chatWithGroq(trimmed, apiHistory);
      const assistantMsg: ChatMessageWithTime = {
        role: "assistant",
        content: response.response,
        timestamp: new Date(),
      };
      setHistory((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      setHistory((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(message);
    }
  };

  const charCountColor =
    message.length >= 450 ? "#c62828" : message.length >= 380 ? "#e65100" : "#90a4ae";

  return (
    <>
      {/* ── BACKDROP ── */}
      {open && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.28)",
            zIndex: 998,
            backdropFilter: "blur(1px)",
          }}
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── PANEL ── */}
      <div
        style={{
          position: "fixed",
          bottom: 88,
          right: 24,
          width: 400,
          maxWidth: "calc(100vw - 32px)",
          height: 560,
          background: "white",
          borderRadius: 16,
          boxShadow: "0 12px 48px rgba(0,0,0,0.22), 0 2px 8px rgba(0,0,0,0.1)",
          zIndex: 999,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          transform: open ? "translateY(0) scale(1)" : "translateY(20px) scale(0.95)",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
          transition: "transform 0.25s cubic-bezier(0.34,1.56,0.64,1), opacity 0.2s ease",
          transformOrigin: "bottom right",
        }}
      >
        {/* Header */}
        <div
          style={{
            background: "linear-gradient(135deg, #0d47a1 0%, #1565c0 60%, #1976d2 100%)",
            padding: "14px 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Molecular hexagon logo mark */}
            <div style={{ position: "relative", width: 36, height: 36, flexShrink: 0 }}>
              <svg width={36} height={36} viewBox="0 0 36 36" fill="none">
                <path d="M18 3L31 10.5V25.5L18 33L5 25.5V10.5Z" fill="rgba(255,255,255,0.12)"/>
                <path d="M18 3L31 10.5V25.5L18 33L5 25.5V10.5Z" stroke="rgba(255,255,255,0.3)" strokeWidth="1" fill="none"/>
                <circle cx="18" cy="18" r="3.5" fill="white"/>
                <circle cx="12.5" cy="14.5" r="2" fill="white" fillOpacity="0.8"/>
                <circle cx="23.5" cy="14.5" r="2" fill="white" fillOpacity="0.8"/>
                <circle cx="12.5" cy="21.5" r="2" fill="white" fillOpacity="0.8"/>
                <circle cx="23.5" cy="21.5" r="2" fill="white" fillOpacity="0.8"/>
                <line x1="14.5" y1="15.9" x2="15.5" y2="16.7" stroke="rgba(255,255,255,0.7)" strokeWidth="1.4" strokeLinecap="round"/>
                <line x1="21.5" y1="15.9" x2="20.5" y2="16.7" stroke="rgba(255,255,255,0.7)" strokeWidth="1.4" strokeLinecap="round"/>
                <line x1="14.5" y1="20.1" x2="15.5" y2="19.3" stroke="rgba(255,255,255,0.7)" strokeWidth="1.4" strokeLinecap="round"/>
                <line x1="21.5" y1="20.1" x2="20.5" y2="19.3" stroke="rgba(255,255,255,0.7)" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
              <span style={{ position: "absolute", top: 1, right: 1, width: 9, height: 9, borderRadius: "50%", background: "#10b981", border: "2px solid #1565c0", display: "block" }}/>
            </div>
            <div>
              <div style={{ color: "white", fontWeight: 800, fontSize: "0.95rem", lineHeight: 1.2, letterSpacing: "-0.2px" }}>
                <span style={{ color: "#93c5fd" }}>Ni</span>Pharm AI
              </div>
              <div style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.7rem", letterSpacing: "0.04em" }}>
                Drug Intelligence · UK
              </div>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            style={{
              background: "rgba(255,255,255,0.15)",
              border: "none",
              color: "white",
              width: 30,
              height: 30,
              borderRadius: "50%",
              cursor: "pointer",
              fontSize: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.2s",
              flexShrink: 0,
            }}
            aria-label="Close chat"
          >
            ×
          </button>
        </div>

        {/* Quick questions (only when no history) */}
        {history.length === 0 && !loading && (
          <div
            style={{
              padding: "10px 12px 6px",
              background: "#f8fafc",
              borderBottom: "1px solid #e8ecf0",
              flexShrink: 0,
            }}
          >
            <div style={{ fontSize: "0.72rem", color: "#90a4ae", marginBottom: 6, fontWeight: 600 }}>
              QUICK QUESTIONS
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {QUICK_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  disabled={loading}
                  style={{
                    background: "white",
                    border: "1px solid #d6eaf8",
                    borderRadius: 8,
                    padding: "6px 10px",
                    fontSize: "0.78rem",
                    color: "#1565c0",
                    cursor: "pointer",
                    textAlign: "left",
                    lineHeight: 1.4,
                    transition: "background 0.2s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#e3f2fd")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "white")}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "14px 12px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
            background: "#f8fafc",
          }}
        >
          {history.length === 0 && !loading && (
            <div
              style={{
                textAlign: "center",
                color: "#b0bec5",
                fontSize: "0.82rem",
                marginTop: "auto",
                paddingBottom: 8,
              }}
            >
              Ask me anything about drug shortages, NHS tariff pricing, or supply chain intelligence.
            </div>
          )}

          {history.map((msg, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                gap: 8,
                alignItems: "flex-end",
              }}
            >
              {msg.role === "assistant" && (
                <span style={{ fontSize: "1.2rem", flexShrink: 0, lineHeight: 1 }}>🤖</span>
              )}
              <div
                style={{
                  maxWidth: "80%",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: msg.role === "user" ? "flex-end" : "flex-start",
                  gap: 2,
                }}
              >
                <div
                  style={{
                    padding: "9px 13px",
                    borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                    background: msg.role === "user" ? "#1976d2" : "white",
                    color: msg.role === "user" ? "white" : "#333",
                    fontSize: "0.84rem",
                    lineHeight: 1.5,
                    wordBreak: "break-word",
                    boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
                    border: msg.role === "assistant" ? "1px solid #e8ecf0" : "none",
                  }}
                >
                  {msg.role === "assistant" ? (
                    <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                  ) : (
                    msg.content
                  )}
                </div>
                <span style={{ fontSize: "0.68rem", color: "#b0bec5" }}>
                  {formatTime(msg.timestamp)}
                </span>
              </div>
              {msg.role === "user" && (
                <span style={{ fontSize: "1.2rem", flexShrink: 0, lineHeight: 1 }}>👤</span>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
              <span style={{ fontSize: "1.2rem" }}>🤖</span>
              <div
                style={{
                  padding: "10px 14px",
                  background: "white",
                  border: "1px solid #e8ecf0",
                  borderRadius: "14px 14px 14px 4px",
                  boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
                }}
              >
                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                  {[0, 0.2, 0.4].map((delay, i) => (
                    <span
                      key={i}
                      style={{
                        width: 7,
                        height: 7,
                        background: "#b0bec5",
                        borderRadius: "50%",
                        display: "inline-block",
                        animation: `widgetBounce 1.2s ${delay}s infinite ease-in-out`,
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {error && (
            <div
              style={{
                background: "#ffebee",
                color: "#c62828",
                padding: "8px 12px",
                borderRadius: 8,
                fontSize: "0.78rem",
                borderLeft: "3px solid #c62828",
              }}
            >
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div
          style={{
            padding: "10px 12px",
            borderTop: "1px solid #e8ecf0",
            background: "white",
            display: "flex",
            gap: 8,
            alignItems: "flex-end",
            flexShrink: 0,
          }}
        >
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
            <input
              ref={inputRef}
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value.slice(0, MAX_CHARS))}
              onKeyDown={handleKeyDown}
              placeholder="Ask about drug shortages..."
              disabled={loading}
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1px solid #e0e0e0",
                borderRadius: 8,
                fontSize: "0.85rem",
                fontFamily: "inherit",
                outline: "none",
                boxSizing: "border-box",
                transition: "border-color 0.2s",
                background: loading ? "#f5f5f5" : "white",
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "#1976d2")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "#e0e0e0")}
            />
            <span style={{ fontSize: "0.65rem", textAlign: "right", color: charCountColor }}>
              {message.length}/{MAX_CHARS}
            </span>
          </div>
          <button
            onClick={() => sendMessage(message)}
            disabled={loading || !message.trim()}
            style={{
              padding: "9px 18px",
              background: loading || !message.trim() ? "#e0e0e0" : "#1976d2",
              color: loading || !message.trim() ? "#aaa" : "white",
              border: "none",
              borderRadius: 8,
              fontWeight: 700,
              fontSize: "0.85rem",
              cursor: loading || !message.trim() ? "not-allowed" : "pointer",
              transition: "background 0.2s",
              whiteSpace: "nowrap",
              alignSelf: "flex-start",
            }}
          >
            Send
          </button>
        </div>
      </div>

      {/* ── FAB BUTTON ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          position: "fixed",
          bottom: 24,
          right: 24,
          width: 56,
          height: 56,
          borderRadius: "50%",
          background: open
            ? "#0d47a1"
            : "linear-gradient(135deg, #1565c0 0%, #1976d2 100%)",
          color: "white",
          border: "none",
          cursor: "pointer",
          fontSize: "1.5rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 18px rgba(25,118,210,0.45)",
          zIndex: 1000,
          transition: "background 0.2s, transform 0.2s",
          transform: open ? "rotate(90deg)" : "rotate(0deg)",
        }}
        aria-label={open ? "Close AI chat" : "Open AI chat"}
      >
        {open ? "×" : "💬"}
      </button>

      <style>{`
        @keyframes widgetBounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-5px); }
        }
      `}</style>
    </>
  );
}
