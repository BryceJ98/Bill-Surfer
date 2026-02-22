"use client";
import { useState, useRef, useEffect } from "react";
import { chat as chatApi, type ChatMessage } from "@/lib/api";

const BODHI_INTROS = [
  "BODHI_GUIDE.EXE — Ready to shred some legislation.",
  "What bills are you tracking today, dude?",
  "Ask me anything — I've got the federal and state data locked in.",
];

export default function BodhiChat() {
  const [messages,  setMessages]  = useState<ChatMessage[]>([]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [introIdx,  setIntroIdx]  = useState(0);
  const [open,      setOpen]      = useState(false);
  const bottomRef   = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && messages.length === 0) {
      // Show intro message
      setMessages([{ role: "assistant", content: BODHI_INTROS[0] }]);
    }
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = { role: "user", content: input.trim() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const reply = await chatApi.send([...messages, userMsg]);
      setMessages((m) => [...m, reply]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠ ${e.message}` }]);
    }
    setLoading(false);
  }

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-12 right-4 z-50 w-14 h-14 flex items-center justify-center text-2xl animate-wave"
        style={{
          background:   "var(--accent)",
          border:       "3px solid var(--border)",
          boxShadow:    "4px 4px 0 var(--border)",
        }}
        title="Chat with Bodhi"
      >
        {open ? "✕" : "🏄"}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          className="fixed bottom-28 right-4 z-50 flex flex-col"
          style={{
            width:     "min(400px, calc(100vw - 2rem))",
            height:    "480px",
            background: "var(--bg-card)",
            border:    "3px solid var(--border)",
            boxShadow: "6px 6px 0 var(--border)",
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-2 px-3 py-2"
               style={{ background: "var(--primary)", borderBottom: "3px solid var(--border)" }}>
            <span className="text-lg animate-wave">🏄</span>
            <span className="font-pixel text-xs" style={{ color: "var(--bg)" }}>BODHI_GUIDE.EXE</span>
            <span className="font-pixel text-xs ml-auto animate-blink" style={{ color: "var(--accent-lt, #F7894E)" }}>●LIVE</span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
            {messages.map((m, i) => (
              <div key={i}
                   className={`flex gap-2 ${m.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                <span className="text-xl flex-shrink-0">{m.role === "user" ? "👤" : "🏄"}</span>
                <div className="p-2 max-w-[80%]"
                     style={{
                       border:     "2px solid var(--border)",
                       background: m.role === "user" ? "var(--accent)" : "var(--bg)",
                       color:      m.role === "user" ? "var(--bg)"     : "var(--text)",
                       boxShadow:  "2px 2px 0 var(--border)",
                     }}>
                  <p className="font-mono text-xs leading-relaxed whitespace-pre-wrap">{m.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-2">
                <span className="text-xl">🏄</span>
                <div className="p-2" style={{ border: "2px solid var(--border)", background: "var(--bg)" }}>
                  <p className="font-pixel text-xs animate-pulse" style={{ color: "var(--accent)" }}>
                    SHREDDING DATA...
                  </p>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex gap-0" style={{ borderTop: "3px solid var(--border)" }}>
            <input
              className="flex-1 input-arcade"
              style={{ border: "none" }}
              placeholder="Ask Bodhi anything..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              className="btn-arcade px-4"
              style={{ border: "none", borderLeft: "3px solid var(--border)" }}
            >
              ▶
            </button>
          </div>
        </div>
      )}
    </>
  );
}
