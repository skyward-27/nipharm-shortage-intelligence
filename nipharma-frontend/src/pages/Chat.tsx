import { useState, useRef, useEffect } from "react";
import { chatWithGroq, healthCheck, ChatMessage } from "../api";

const MAX_CHARS = 500;

const QUICK_QUESTIONS = [
  "Which drugs are on NHS concessions this month?",
  "Top 5 drugs at shortage risk in UK right now?",
  "How is India's API shortage affecting UK pharmacies?",
  "What bulk buying opportunities exist for Amoxicillin?",
  "How does GBP/INR exchange rate affect drug costs?",
  "What are MHRA's latest shortage alerts?",
];

// Simple markdown renderer - no external library needed
function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h4 style="margin:12px 0 4px;color:#1a1a1a">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="margin:14px 0 6px;color:#1a1a1a">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 style="margin:16px 0 8px;color:#1a1a1a">$1</h2>')
    .replace(/^\d+\.\s(.+)$/gm, '<div style="display:flex;gap:8px;margin:4px 0"><span style="color:#1976d2;font-weight:600;min-width:20px">•</span><span>$1</span></div>')
    .replace(/^[-•]\s(.+)$/gm, '<div style="display:flex;gap:8px;margin:4px 0"><span style="color:#1976d2;font-weight:600">•</span><span>$1</span></div>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

interface ChatMessageWithTime extends ChatMessage {
  timestamp: Date;
}

export default function Chat() {
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<ChatMessageWithTime[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [tavilyEnabled, setTavilyEnabled] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [history]);

  // Check health endpoint on mount to determine if Tavily is configured
  useEffect(() => {
    healthCheck()
      .then((data: any) => {
        if (data?.tavily_configured) setTavilyEnabled(true);
      })
      .catch(() => {});
  }, []);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    try {
      setError(null);
      const userMsg: ChatMessageWithTime = {
        role: "user",
        content: trimmed,
        timestamp: new Date(),
      };
      setHistory((prev) => [...prev, userMsg]);
      setMessage("");
      setLoading(true);

      // Build history without timestamps for the API call
      const apiHistory: ChatMessage[] = history.map(({ role, content }) => ({
        role,
        content,
      }));

      const response = await chatWithGroq(trimmed, apiHistory);
      const assistantMsg: ChatMessageWithTime = {
        role: "assistant",
        content: response.response,
        timestamp: new Date(),
      };
      setHistory((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      // Remove the optimistically-added user message on error
      setHistory((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => sendMessage(message);

  const handleQuickQuestion = (q: string) => {
    sendMessage(q);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    });
  };

  const charCount = message.length;
  const charCountColor = charCount >= 450 ? "#c62828" : charCount >= 400 ? "#e65100" : "#999";

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-top">
          <h1>Pharma Intelligence Chat</h1>
          <div className="header-badges">
            <span className="badge badge-groq">🟢 AI Powered by Groq</span>
            {tavilyEnabled && (
              <span className="badge badge-tavily">🔍 Web Search Enabled</span>
            )}
          </div>
        </div>
        <p>Ask about drug shortages, pricing, supply chains, and forecasts</p>
      </div>

      <div className="chat-history">
        {history.length === 0 && (
          <div className="welcome-message">
            <h2>Welcome to Pharma Intelligence Chat</h2>
            <p>Try one of these questions to get started:</p>
            <div className="quick-questions">
              {QUICK_QUESTIONS.map((q) => (
                <button
                  key={q}
                  className="quick-chip"
                  onClick={() => handleQuickQuestion(q)}
                  disabled={loading}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((msg, index) => (
          <div key={index} className={`message message-${msg.role}`}>
            <div className="message-avatar">
              {msg.role === "user" ? "👤" : "🤖"}
            </div>
            <div className="message-bubble-wrapper">
              <div className="message-content">
                {msg.role === "assistant"
                  ? <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                  : <p>{msg.content}</p>
                }
              </div>
              <div className="message-meta">
                <span className="message-time">{formatTime(msg.timestamp)}</span>
                {msg.role === "assistant" && (
                  <button
                    className="copy-button"
                    onClick={() => handleCopy(msg.content, index)}
                    title="Copy to clipboard"
                  >
                    {copiedIndex === index ? "✅ Copied" : "📋 Copy"}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="message message-assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-bubble-wrapper">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value.slice(0, MAX_CHARS))}
            onKeyPress={handleKeyPress}
            placeholder="Ask about drug shortages, pricing, supply chains..."
            disabled={loading}
            className="chat-input"
          />
          <div className="char-counter" style={{ color: charCountColor }}>
            {charCount}/{MAX_CHARS}
          </div>
        </div>
        <button
          onClick={handleSend}
          disabled={loading || !message.trim()}
          className="send-button"
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>

      <style>{`
        .chat-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          max-width: 1000px;
          margin: 0 auto;
          background: #f5f5f5;
        }

        .chat-header {
          background: white;
          padding: 20px 24px;
          border-bottom: 1px solid #e0e0e0;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .chat-header-top {
          display: flex;
          align-items: center;
          gap: 16px;
          flex-wrap: wrap;
          margin-bottom: 4px;
        }

        .chat-header h1 {
          margin: 0;
          font-size: 2rem;
          color: #1a1a1a;
        }

        .chat-header p {
          margin: 0;
          color: #666;
          font-size: 1rem;
        }

        .header-badges {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 0.78rem;
          font-weight: 600;
          white-space: nowrap;
        }

        .badge-groq {
          background: #e8f5e9;
          color: #2e7d32;
          border: 1px solid #a5d6a7;
        }

        .badge-tavily {
          background: #e3f2fd;
          color: #1565c0;
          border: 1px solid #90caf9;
        }

        .chat-history {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .welcome-message {
          background: white;
          border-radius: 12px;
          padding: 32px;
          text-align: center;
          margin: auto;
          max-width: 700px;
          width: 100%;
        }

        .welcome-message h2 {
          color: #1a1a1a;
          margin-top: 0;
        }

        .welcome-message > p {
          color: #555;
          margin-bottom: 16px;
        }

        .quick-questions {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          justify-content: center;
        }

        .quick-chip {
          background: #f0f4ff;
          color: #1976d2;
          border: 1.5px solid #90caf9;
          border-radius: 20px;
          padding: 8px 16px;
          font-size: 0.88rem;
          cursor: pointer;
          transition: background 0.2s ease, transform 0.1s ease;
          text-align: left;
          line-height: 1.4;
        }

        .quick-chip:hover:not(:disabled) {
          background: #dceeff;
          transform: translateY(-1px);
        }

        .quick-chip:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .message {
          display: flex;
          gap: 12px;
          animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .message-user {
          justify-content: flex-end;
        }

        .message-assistant {
          justify-content: flex-start;
        }

        .message-avatar {
          font-size: 1.5rem;
          min-width: 32px;
          text-align: center;
          line-height: 32px;
          align-self: flex-start;
          padding-top: 4px;
        }

        .message-user .message-avatar {
          order: 2;
        }

        .message-bubble-wrapper {
          display: flex;
          flex-direction: column;
          max-width: 70%;
        }

        .message-user .message-bubble-wrapper {
          align-items: flex-end;
        }

        .message-assistant .message-bubble-wrapper {
          align-items: flex-start;
        }

        .message-content {
          padding: 12px 16px;
          border-radius: 8px;
          word-wrap: break-word;
          width: 100%;
        }

        .message-user .message-content {
          background: #1976d2;
          color: white;
        }

        .message-assistant .message-content {
          background: white;
          color: #333;
          border: 1px solid #e0e0e0;
        }

        .message-content p {
          margin: 0;
          line-height: 1.5;
        }

        .message-meta {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 4px;
          padding: 0 4px;
        }

        .message-time {
          font-size: 0.73rem;
          color: #aaa;
        }

        .copy-button {
          background: none;
          border: none;
          color: #999;
          font-size: 0.75rem;
          cursor: pointer;
          padding: 2px 6px;
          border-radius: 4px;
          transition: background 0.2s, color 0.2s;
        }

        .copy-button:hover {
          background: #f0f4ff;
          color: #1976d2;
        }

        /* Typing indicator - three bouncing dots */
        .typing-indicator {
          display: flex;
          align-items: center;
          gap: 5px;
          padding: 4px 0;
          min-height: 20px;
        }

        .typing-indicator span {
          display: inline-block;
          width: 8px;
          height: 8px;
          background: #bbb;
          border-radius: 50%;
          animation: bounce 1.2s infinite ease-in-out;
        }

        .typing-indicator span:nth-child(1) { animation-delay: 0s; }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }

        .error-message {
          background: #ffebee;
          color: #c62828;
          padding: 12px 16px;
          border-radius: 8px;
          border-left: 4px solid #c62828;
        }

        .error-message p {
          margin: 0;
        }

        .chat-input-area {
          display: flex;
          gap: 12px;
          padding: 16px 24px;
          background: white;
          border-top: 1px solid #e0e0e0;
          align-items: flex-start;
        }

        .chat-input-wrapper {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .chat-input {
          width: 100%;
          padding: 12px 16px;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          font-size: 1rem;
          font-family: inherit;
          transition: border-color 0.3s ease;
          box-sizing: border-box;
        }

        .chat-input:focus {
          outline: none;
          border-color: #1976d2;
          box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
        }

        .chat-input:disabled {
          background: #f5f5f5;
          color: #999;
        }

        .char-counter {
          font-size: 0.75rem;
          text-align: right;
          transition: color 0.2s ease;
        }

        .send-button {
          padding: 12px 24px;
          background: #1976d2;
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.3s ease;
          white-space: nowrap;
          align-self: flex-start;
        }

        .send-button:hover:not(:disabled) {
          background: #1565c0;
        }

        .send-button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }

        @media (max-width: 768px) {
          .message-bubble-wrapper {
            max-width: 85%;
          }

          .chat-header {
            padding: 16px;
          }

          .chat-header h1 {
            font-size: 1.5rem;
          }

          .chat-input-area {
            padding: 12px 16px;
          }

          .welcome-message {
            padding: 20px 16px;
          }

          .quick-chip {
            font-size: 0.82rem;
            padding: 7px 13px;
          }
        }
      `}</style>
    </div>
  );
}
