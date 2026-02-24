"use client";
import { useState, useRef, useEffect } from "react";
import { chat as chatApi, type ChatMessage } from "@/lib/api";
import { useTheme } from "@/lib/ThemeContext";

const BODHI_INTRO  = "BODHI_GUIDE.EXE — Ready to shred some legislation.";
const BERNHARD_INTRO = "BERNHARD_GUIDE.EXE — Guten Tag. I am here to help you navigate the law. Precisely.";

export default function BodhiChat() {
  const { ski } = useTheme();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input,    setInput]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [open,     setOpen]     = useState(false);
  const bottomRef  = useRef<HTMLDivElement>(null);

  // Reset intro when mode switches
  useEffect(() => {
    setMessages([]);
  }, [ski]);

  useEffect(() => {
    if (open && messages.length === 0) {
      setMessages([{ role: "assistant", content: ski ? BERNHARD_INTRO : BODHI_INTRO }]);
    }
  }, [open, ski]);

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

  const guideEmoji  = ski ? "⛷️" : "🏄";
  const guideName   = ski ? "BERNHARD_GUIDE.EXE" : "BODHI_GUIDE.EXE";
  const placeholder = ski ? "Ask Bernhard..." : "Ask Bodhi anything...";
  const loadingText = ski ? "ANALYSING DATA..." : "SHREDDING DATA...";

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-12 right-4 z-50 w-14 h-14 flex items-center justify-center text-2xl"
        style={{
          background: "var(--accent)",
          border:     "3px solid var(--border)",
          boxShadow:  "4px 4px 0 var(--border)",
          animation:  ski ? "none" : undefined,
        }}
        title={ski ? "Chat with Bernhard" : "Chat with Bodhi"}
      >
        {open ? "✕" : guideEmoji}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          className="fixed bottom-28 right-4 z-50 flex flex-col"
          style={{
            width:      "min(400px, calc(100vw - 2rem))",
            height:     "480px",
            background: "var(--bg-card)",
            border:     "3px solid var(--border)",
            boxShadow:  "6px 6px 0 var(--border)",
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-2 px-3 py-2"
               style={{ background: "var(--primary)", borderBottom: "3px solid var(--border)" }}>
            <span className="text-lg">{guideEmoji}</span>
            <span className="font-pixel text-xs" style={{ color: ski ? "var(--border)" : "var(--bg)" }}>
              {guideName}
            </span>
            <span className="font-pixel text-xs ml-auto animate-blink"
                  style={{ color: "var(--accent-lt, #F7894E)" }}>●LIVE</span>
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="font-pixel text-xs px-2"
                style={{ color: ski ? "var(--border)" : "var(--bg)", opacity: 0.7, fontSize: "0.55rem" }}
                title="Clear chat">
                CLR
              </button>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
            {messages.map((m, i) => (
              <div key={i}
                   className={`flex gap-2 ${m.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                <span className="text-xl flex-shrink-0">
                  {m.role === "user" ? "👤" : guideEmoji}
                </span>
                <div className="p-2 max-w-[80%]"
                     style={{
                       border:     "2px solid var(--border)",
                       background: m.role === "user" ? "var(--accent)" : "var(--bg)",
                       color:      m.role === "user" ? (ski ? "#EDE4D0" : "var(--bg)") : "var(--text)",
                       boxShadow:  "2px 2px 0 var(--border)",
                     }}>
                  <p className="font-mono text-xs leading-relaxed whitespace-pre-wrap">{m.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-2">
                <span className="text-xl">{guideEmoji}</span>
                <div className="p-2" style={{ border: "2px solid var(--border)", background: "var(--bg)" }}>
                  <p className="font-pixel text-xs animate-pulse" style={{ color: "var(--accent)" }}>
                    {loadingText}
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
              placeholder={placeholder}
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
