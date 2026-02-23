"use client";
import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { keys as keysApi, settings as settingsApi } from "@/lib/api";

// ── Bodhi's dialogue for each onboarding step ─────────────────────────────
const BODHI_SCRIPT = [
  {
    step:    "welcome",
    emoji:   "🏄",
    lines: [
      "YO! I'm BODHI — your legislative surf guide.",
      "I'll shred through the data so you don't wipe out.",
      "First things first — let's get you logged in.",
    ],
  },
  {
    step:    "auth",
    emoji:   "🔑",
    lines: [
      "Drop your email and I'll send you a magic link.",
      "No passwords. Just vibes and cryptography.",
    ],
  },
  {
    step:    "username",
    emoji:   "👤",
    lines: [
      "Sick! What should I call you?",
      "This shows up on your dashboard and reports.",
    ],
  },
  {
    step:    "legiscan",
    emoji:   "📋",
    lines: [
      "Now let's paddle out to the data.",
      "Paste your LegiScan API key — it's free at legiscan.com.",
      "This unlocks all 50 states worth of bills.",
    ],
  },
  {
    step:    "congress",
    emoji:   "🏛️",
    lines: [
      "Next up: Congress.gov API key.",
      "Free at api.congress.gov — takes 2 minutes.",
      "Federal bills, nominations, treaties — all of it.",
    ],
  },
  {
    step:    "ai",
    emoji:   "🤖",
    lines: [
      "Last wave: connect your AI model.",
      "Claude, GPT-4, Gemini, Groq — your call.",
      "I'll use it to generate reports and answer questions.",
    ],
  },
  {
    step:    "done",
    emoji:   "🤙",
    lines: [
      "GNARLY! You're all set.",
      "Time to shred some legislation.",
      "Let's drop in!",
    ],
  },
];

const AI_OPTIONS = [
  { provider: "anthropic", model: "claude-sonnet-4-6",          label: "Claude Sonnet 4.6  (Anthropic)" },
  { provider: "anthropic", model: "claude-opus-4-6",            label: "Claude Opus 4.6   (Anthropic)" },
  { provider: "openai",    model: "gpt-4o",                     label: "GPT-4o            (OpenAI)" },
  { provider: "openai",    model: "gpt-4o-mini",                label: "GPT-4o Mini       (OpenAI)" },
  { provider: "google",    model: "gemini/gemini-1.5-pro",      label: "Gemini 1.5 Pro    (Google)" },
  { provider: "groq",      model: "groq/llama-3.1-70b-versatile", label: "Llama 3.1 70B  (Groq)" },
];

type Step = "welcome" | "auth" | "check_email" | "username" | "legiscan" | "congress" | "ai" | "done";

export default function LoginPage() {
  const router    = useRouter();
  const supabase  = createClient();

  const [step,         setStep]         = useState<Step>("welcome");
  const [scriptIdx,    setScriptIdx]    = useState(0);
  const [lineIdx,      setLineIdx]      = useState(0);
  const [displayText,  setDisplayText]  = useState("");
  const [typing,       setTyping]       = useState(true);

  const [email,         setEmail]         = useState("");
  const [username,      setUsername]      = useState("");
  const [legiscanKey,   setLegiscanKey]   = useState("");
  const [congressKey,   setCongressKey]   = useState("");
  const [aiKey,         setAiKey]         = useState("");
  const [selectedAi,   setSelectedAi]    = useState(AI_OPTIONS[0]);
  const [loading,      setLoading]       = useState(false);
  const [error,        setError]         = useState("");

  // Typewriter effect
  const currentScript = BODHI_SCRIPT.find((s) => s.step === step) ?? BODHI_SCRIPT[0];
  const currentLine   = currentScript.lines[lineIdx] ?? "";

  useEffect(() => {
    if (!typing) return;
    setDisplayText("");
    let i = 0;
    const iv = setInterval(() => {
      setDisplayText(currentLine.slice(0, i + 1));
      i++;
      if (i >= currentLine.length) { clearInterval(iv); setTyping(false); }
    }, 35);
    return () => clearInterval(iv);
  }, [currentLine, typing]);

  function nextLine() {
    if (lineIdx < currentScript.lines.length - 1) {
      setLineIdx(lineIdx + 1);
      setTyping(true);
    }
    // last line — ready for action
  }

  const allLinesShown = !typing && lineIdx === currentScript.lines.length - 1;

  // ── Handlers ─────────────────────────────────────────────────────────────
  async function handleEmailSubmit() {
    setError(""); setLoading(true);
    const { error: err } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/login` },
    });
    setLoading(false);
    if (err) { setError(err.message); return; }
    setStep("check_email");
    setLineIdx(0); setTyping(true);
  }

  async function handleUsername() {
    setError(""); setLoading(true);
    try {
      if (username.trim()) {
        await settingsApi.update({ display_name: username.trim() });
      }
      setStep("legiscan"); setLineIdx(0); setTyping(true);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function handleLegiScan() {
    setError(""); setLoading(true);
    try {
      await keysApi.save("legiscan", legiscanKey.trim());
      setStep("congress"); setLineIdx(0); setTyping(true);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function handleCongress() {
    setError(""); setLoading(true);
    try {
      await keysApi.save("congress", congressKey.trim());
      setStep("ai"); setLineIdx(0); setTyping(true);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function handleAi() {
    setError(""); setLoading(true);
    try {
      await keysApi.save(selectedAi.provider, aiKey.trim());
      await settingsApi.update({ ai_provider: selectedAi.provider, ai_model: selectedAi.model });
      setStep("done"); setLineIdx(0); setTyping(true);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  // Check for redirect back from magic link — detect returning vs new user
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event) => {
      if (event === "SIGNED_IN") {
        // Check if this is a returning user who already has API keys configured
        try {
          const keyStatuses = await keysApi.list();
          const hasAiKey = keyStatuses.some((k) => k.stored &&
            ["anthropic", "openai", "google", "groq", "mistral"].includes(k.provider));
          if (hasAiKey) {
            // Returning user — skip straight to dashboard
            router.push("/dashboard");
            return;
          }
        } catch {}
        // New user — start onboarding from username step
        setStep("username");
        setLineIdx(0); setTyping(true);
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6"
          style={{ background: "var(--bg)" }}>

      {/* Bodhi dialogue box */}
      <div className="card p-6 max-w-md w-full mb-6">
        <div className="flex items-start gap-4">
          {/* Pixel avatar */}
          <div className="text-4xl animate-wave flex-shrink-0">{currentScript.emoji}</div>
          <div>
            <p className="font-pixel text-xs mb-2" style={{ color: "var(--accent)" }}>
              BODHI_GUIDE.EXE
            </p>
            <p className="font-mono text-sm leading-relaxed cursor" style={{ color: "var(--text)" }}>
              {displayText}
            </p>
            {/* Progress dots */}
            <div className="flex gap-1 mt-3">
              {currentScript.lines.map((_, i) => (
                <span key={i}
                      className="inline-block w-2 h-2"
                      style={{ background: i <= lineIdx ? "var(--accent)" : "var(--text-muted)" }} />
              ))}
            </div>
          </div>
        </div>

        {!allLinesShown && (
          <button onClick={nextLine}
                  className="btn-arcade-outline mt-4 w-full font-pixel text-xs">
            ▶ CONTINUE
          </button>
        )}
      </div>

      {/* Step panel */}
      {allLinesShown && (
        <div className="card p-6 max-w-md w-full">

          {/* ── Welcome ── */}
          {step === "welcome" && (
            <button onClick={() => { setStep("auth"); setLineIdx(0); setTyping(true); }}
                    className="btn-arcade w-full font-pixel text-xs">
              ▶ LET'S GO
            </button>
          )}

          {/* ── Auth ── */}
          {step === "auth" && (
            <div className="flex flex-col gap-3">
              <label className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>EMAIL_ADDRESS</label>
              <input className="input-arcade"
                     type="email" placeholder="you@university.edu"
                     value={email} onChange={(e) => setEmail(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && handleEmailSubmit()} />
              <button className="btn-arcade w-full font-pixel text-xs"
                      onClick={handleEmailSubmit} disabled={loading || !email}>
                {loading ? "SENDING..." : "▶ SEND MAGIC LINK"}
              </button>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>{error}</p>}
            </div>
          )}

          {/* ── Check email ── */}
          {step === "check_email" && (
            <div className="text-center">
              <p className="text-3xl mb-4">📬</p>
              <p className="font-pixel text-xs mb-2" style={{ color: "var(--accent)" }}>CHECK YOUR EMAIL</p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Magic link sent to <strong>{email}</strong>.<br />
                Click it and Bodhi will pick up right where we left off.
              </p>
            </div>
          )}

          {/* ── Username ── */}
          {step === "username" && (
            <div className="flex flex-col gap-3">
              <label className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>DISPLAY_NAME</label>
              <input className="input-arcade"
                     placeholder="Dr. Jane Smith"
                     value={username}
                     onChange={(e) => setUsername(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && handleUsername()} />
              <div className="flex gap-2">
                <button className="btn-arcade-outline flex-1 font-pixel text-xs"
                        onClick={() => { setStep("legiscan"); setLineIdx(0); setTyping(true); }}>
                  SKIP
                </button>
                <button className="btn-arcade flex-1 font-pixel text-xs"
                        onClick={handleUsername} disabled={loading}>
                  {loading ? "SAVING..." : "▶ SAVE NAME"}
                </button>
              </div>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>{error}</p>}
            </div>
          )}

          {/* ── LegiScan key ── */}
          {step === "legiscan" && (
            <div className="flex flex-col gap-3">
              <label className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>LEGISCAN_API_KEY</label>
              <input className="input-arcade" type="password" placeholder="Paste key here..."
                     value={legiscanKey} onChange={(e) => setLegiscanKey(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && legiscanKey && handleLegiScan()} />
              <a href="https://legiscan.com/legiscan" target="_blank" rel="noreferrer"
                 className="font-pixel text-xs" style={{ color: "var(--accent)" }}>
                ↗ GET FREE KEY AT LEGISCAN.COM
              </a>
              <div className="flex gap-2">
                <button className="btn-arcade-outline flex-1 font-pixel text-xs"
                        onClick={() => { setStep("congress"); setLineIdx(0); setTyping(true); }}>
                  SKIP
                </button>
                <button className="btn-arcade flex-1 font-pixel text-xs"
                        onClick={handleLegiScan} disabled={loading || !legiscanKey}>
                  {loading ? "SAVING..." : "▶ SAVE KEY"}
                </button>
              </div>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>{error}</p>}
            </div>
          )}

          {/* ── Congress key ── */}
          {step === "congress" && (
            <div className="flex flex-col gap-3">
              <label className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>CONGRESS_API_KEY</label>
              <input className="input-arcade" type="password" placeholder="Paste key here..."
                     value={congressKey} onChange={(e) => setCongressKey(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && congressKey && handleCongress()} />
              <a href="https://api.congress.gov/sign-up/" target="_blank" rel="noreferrer"
                 className="font-pixel text-xs" style={{ color: "var(--accent)" }}>
                ↗ GET FREE KEY AT API.CONGRESS.GOV
              </a>
              <div className="flex gap-2">
                <button className="btn-arcade-outline flex-1 font-pixel text-xs"
                        onClick={() => { setStep("ai"); setLineIdx(0); setTyping(true); }}>
                  SKIP
                </button>
                <button className="btn-arcade flex-1 font-pixel text-xs"
                        onClick={handleCongress} disabled={loading || !congressKey}>
                  {loading ? "SAVING..." : "▶ SAVE KEY"}
                </button>
              </div>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>{error}</p>}
            </div>
          )}

          {/* ── AI model ── */}
          {step === "ai" && (
            <div className="flex flex-col gap-3">
              <label className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>SELECT_AI_MODEL</label>
              <div className="grid gap-2">
                {AI_OPTIONS.map((opt) => (
                  <button key={opt.model}
                          onClick={() => setSelectedAi(opt)}
                          className="text-left p-3 font-mono text-xs transition-all"
                          style={{
                            border: "3px solid",
                            borderColor: selectedAi.model === opt.model ? "var(--accent)" : "var(--border)",
                            background:  selectedAi.model === opt.model ? "var(--accent)" : "transparent",
                            color:       selectedAi.model === opt.model ? "var(--bg)"     : "var(--text)",
                            boxShadow:   selectedAi.model === opt.model ? "3px 3px 0 var(--border)" : "none",
                          }}>
                    {selectedAi.model === opt.model ? "▶ " : "  "}{opt.label}
                  </button>
                ))}
              </div>
              <label className="font-pixel text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                {selectedAi.provider.toUpperCase()}_API_KEY
              </label>
              <input className="input-arcade" type="password" placeholder="Paste key here..."
                     value={aiKey} onChange={(e) => setAiKey(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && aiKey && handleAi()} />
              <button className="btn-arcade w-full font-pixel text-xs"
                      onClick={handleAi} disabled={loading || !aiKey}>
                {loading ? "CONNECTING..." : "▶ CONNECT AI"}
              </button>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>{error}</p>}
            </div>
          )}

          {/* ── Done ── */}
          {step === "done" && (
            <div className="text-center flex flex-col gap-4">
              <p className="text-4xl animate-wave">🤙</p>
              <p className="font-pixel text-sm neon-text" style={{ color: "var(--accent)" }}>
                SETUP COMPLETE!
              </p>
              <button className="btn-arcade w-full font-pixel text-xs"
                      onClick={() => router.push("/dashboard")}>
                ▶ DROP IN
              </button>
            </div>
          )}

        </div>
      )}

      {/* Step indicator */}
      <div className="flex gap-2 mt-6">
        {(["auth","username","legiscan","congress","ai","done"] as Step[]).map((s, i) => (
          <span key={s}
                className="w-3 h-3 inline-block"
                style={{ background: ["auth","username","legiscan","congress","ai","done"].indexOf(step) >= i
                  ? "var(--accent)" : "var(--text-muted)" }} />
        ))}
      </div>
    </main>
  );
}
