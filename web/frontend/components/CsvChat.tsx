"use client";
import { useState, useRef, useEffect } from "react";
import { chat } from "@/lib/api";

interface Props {
  rawCsv:   string;
  rowCount: number;
  columns:  string[];
}

interface Message {
  role:    "user" | "assistant";
  content: string;
}

export default function CsvChat({ rawCsv, rowCount, columns }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const bottomRef               = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const systemContent = `You are a data analysis assistant helping a researcher explore a CSV dataset.
Dataset: ${rowCount} rows, columns: ${columns.join(", ")}
CSV DATA:
${rawCsv.slice(0, 12000)}

Answer questions about this data concisely and accurately. Reference specific values from the data when relevant.`;

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const reply = await chat.send([
        { role: "system", content: systemContent },
        ...messages,
        userMsg,
      ]);
      setMessages(prev => [...prev, { role: "assistant", content: reply.content }]);
    } catch (err: any) {
      setError(err.message ?? "Chat error");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div style={{
      border:       "2px solid var(--border)",
      background:   "var(--card)",
      fontFamily:   "monospace",
    }}>
      {/* Header */}
      <div style={{
        background:  "var(--primary)",
        padding:     "8px 12px",
        display:     "flex",
        alignItems:  "center",
        justifyContent: "space-between",
        borderBottom: "2px solid var(--border)",
      }}>
        <span className="font-pixel text-xs" style={{ color: "var(--border)" }}>
          ⛷️ BERNHARD / 🏄 BODHI — CSV CHAT
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span className="font-pixel text-xs" style={{ color: "#F4F9FC", opacity: 0.7 }}>
            ● {rowCount} ROWS LOADED
          </span>
          {messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              className="font-pixel text-xs"
              style={{ color: "#F4F9FC", background: "transparent", border: "1px solid rgba(255,255,255,0.3)", padding: "2px 6px", cursor: "pointer" }}
            >
              CLEAR
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div style={{
        minHeight:  "180px",
        maxHeight:  "320px",
        overflowY:  "auto",
        padding:    "12px",
        display:    "flex",
        flexDirection: "column",
        gap:        "10px",
      }}>
        {messages.length === 0 && (
          <p className="font-pixel text-xs" style={{ color: "var(--muted)", textAlign: "center", marginTop: "60px" }}>
            Ask anything about your CSV data...
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf:   m.role === "user" ? "flex-end" : "flex-start",
            maxWidth:    "80%",
            background:  m.role === "user" ? "var(--primary)" : "var(--surface)",
            border:      `1px solid ${m.role === "user" ? "var(--border)" : "var(--muted)"}`,
            padding:     "8px 12px",
            fontSize:    "12px",
            color:       m.role === "user" ? "#F4F9FC" : "var(--text)",
            whiteSpace:  "pre-wrap",
            lineHeight:  1.5,
          }}>
            <span style={{ opacity: 0.6, fontSize: "10px", display: "block", marginBottom: "4px" }}>
              {m.role === "user" ? "YOU" : "🏄 BODHI"}
            </span>
            {m.content}
          </div>
        ))}
        {loading && (
          <div style={{
            alignSelf:  "flex-start",
            fontSize:   "12px",
            color:      "var(--muted)",
            padding:    "8px 12px",
            border:     "1px solid var(--muted)",
            background: "var(--surface)",
          }}>
            <span className="font-pixel text-xs">● ● ●</span>
          </div>
        )}
        {error && (
          <div style={{ color: "#ff4444", fontSize: "12px", padding: "4px 0" }}>
            Error: {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        borderTop:   "2px solid var(--border)",
        padding:     "8px 12px",
        display:     "flex",
        gap:         "8px",
        background:  "var(--surface)",
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about your data... (Enter to send)"
          rows={2}
          style={{
            flex:       1,
            background: "transparent",
            border:     "1px solid var(--border)",
            color:      "var(--text)",
            padding:    "6px 8px",
            fontSize:   "12px",
            fontFamily: "monospace",
            resize:     "none",
            outline:    "none",
          }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="font-pixel text-xs"
          style={{
            background: loading ? "var(--muted)" : "var(--primary)",
            color:      "#F4F9FC",
            border:     "2px solid var(--border)",
            padding:    "6px 14px",
            cursor:     loading ? "not-allowed" : "pointer",
            alignSelf:  "flex-end",
          }}
        >
          {loading ? "..." : "SEND ▶"}
        </button>
      </div>
    </div>
  );
}
