import { useState, useRef, useEffect } from "react";
import { chatWithGroq, ChatMessage } from "../api";

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

export default function Chat() {
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [history]);

  const handleSend = async () => {
    if (!message.trim()) return;

    try {
      setError(null);
      const userMsg: ChatMessage = { role: "user", content: message };
      setHistory((prev) => [...prev, userMsg]);
      setMessage("");
      setLoading(true);

      const response = await chatWithGroq(message, history);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response.response,
      };
      setHistory((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      // Remove the user message if there's an error
      setHistory((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>Pharma Intelligence Chat</h1>
        <p>Ask about drug shortages, pricing, supply chains, and forecasts</p>
      </div>

      <div className="chat-history">
        {history.length === 0 && (
          <div className="welcome-message">
            <h2>Welcome to Pharma Intelligence Chat</h2>
            <p>I can help you with:</p>
            <ul>
              <li>Drug shortage alerts and supply chain risks</li>
              <li>Price analysis and bulk purchasing discounts</li>
              <li>API manufacturer intelligence</li>
              <li>Market forecasts and recommendations</li>
            </ul>
            <p>Ask me anything about pharmaceutical supply and pricing intelligence.</p>
          </div>
        )}

        {history.map((msg, index) => (
          <div key={index} className={`message message-${msg.role}`}>
            <div className="message-avatar">
              {msg.role === "user" ? "👤" : "🤖"}
            </div>
            <div className="message-content">
              {msg.role === "assistant"
                ? <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                : <p>{msg.content}</p>
              }
            </div>
          </div>
        ))}

        {loading && (
          <div className="message message-assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <p className="thinking">Thinking...</p>
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
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask about drug shortages, pricing, supply chains..."
          disabled={loading}
          className="chat-input"
        />
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
          padding: 24px;
          border-bottom: 1px solid #e0e0e0;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .chat-header h1 {
          margin: 0 0 8px 0;
          font-size: 2rem;
          color: #1a1a1a;
        }

        .chat-header p {
          margin: 0;
          color: #666;
          font-size: 1rem;
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
          border-radius: 8px;
          padding: 32px;
          text-align: center;
          margin: auto;
        }

        .welcome-message h2 {
          color: #1a1a1a;
          margin-top: 0;
        }

        .welcome-message ul {
          text-align: left;
          display: inline-block;
          color: #666;
        }

        .welcome-message li {
          margin: 8px 0;
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
        }

        .message-user .message-avatar {
          order: 2;
        }

        .message-content {
          max-width: 70%;
          padding: 12px 16px;
          border-radius: 8px;
          word-wrap: break-word;
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

        .thinking {
          font-style: italic;
          color: #999;
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
        }

        .chat-input {
          flex: 1;
          padding: 12px 16px;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          font-size: 1rem;
          font-family: inherit;
          transition: border-color 0.3s ease;
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
        }

        .send-button:hover:not(:disabled) {
          background: #1565c0;
        }

        .send-button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }

        @media (max-width: 768px) {
          .message-content {
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
        }
      `}</style>
    </div>
  );
}
