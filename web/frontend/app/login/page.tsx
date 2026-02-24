"use client";
import { useState, useEffect, useRef } from "react";
import { createClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { keys as keysApi, settings as settingsApi } from "@/lib/api";

// ── Bodhi dialogue ─────────────────────────────────────────────────────────
const BODHI_SCRIPT = [
  {
    step:  "welcome",
    emoji: "🏄",
    lines: [
      "YO! I'm BODHI — your legislative surf guide.",
      "I'll shred through the data so you don't wipe out.",
      "First things first — let's get you in the water.",
    ],
  },
  {
    step:  "new_or_return",
    emoji: "🌊",
    lines: [
      "Alright dude — first time hitting these waves?",
      "Or have you surfed the Bill-Surfer break before?",
    ],
  },
  {
    step:  "register",
    emoji: "🤙",
    lines: [
      "STOKED! Let's get you set up.",
      "Pick a name, drop your email, and set a password.",
      "API keys come next — you can always skip and add them in Settings.",
    ],
  },
  {
    step:  "signin",
    emoji: "🏄",
    lines: [
      "Welcome back, shredder!",
      "Drop your credentials and let's paddle out.",
    ],
  },
  {
    step:  "check_email",
    emoji: "📬",
    lines: [
      "Magic link incoming!",
      "Check your email and click the link.",
      "I'll be right here when you get back.",
    ],
  },
  {
    step:  "legiscan",
    emoji: "📋",
    lines: [
      "Now let's paddle out to the data.",
      "Paste your LegiScan API key — it's free at legiscan.com.",
      "This unlocks all 50 states worth of bills.",
    ],
  },
  {
    step:  "congress",
    emoji: "🏛️",
    lines: [
      "Next wave: Congress.gov API key.",
      "Free at api.congress.gov — takes 2 minutes.",
      "Federal bills, nominations, treaties — all of it.",
    ],
  },
  {
    step:  "ai",
    emoji: "🤖",
    lines: [
      "Last wave: connect your AI model.",
      "Claude, GPT-4o, Gemini, Groq — your call.",
      "I'll use it to generate reports and chat with you.",
    ],
  },
  {
    step:  "done",
    emoji: "🤙",
    lines: [
      "GNARLY! You're all set.",
      "Time to shred some legislation.",
      "Let's drop in!",
    ],
  },
] as const;

const AI_OPTIONS = [
  { provider: "anthropic", model: "claude-sonnet-4-6",            label: "Claude Sonnet 4.6   (Anthropic)" },
  { provider: "anthropic", model: "claude-opus-4-6",              label: "Claude Opus 4.6     (Anthropic)" },
  { provider: "openai",    model: "gpt-4o",                       label: "GPT-4o              (OpenAI)"    },
  { provider: "openai",    model: "gpt-4o-mini",                  label: "GPT-4o Mini         (OpenAI)"    },
  { provider: "google",    model: "gemini/gemini-2.0-flash",      label: "Gemini 2.0 Flash    (Google)"    },
  { provider: "groq",      model: "groq/llama-3.1-70b-versatile", label: "Llama 3.1 70B       (Groq)"      },
];

type Step = "welcome" | "new_or_return" | "register" | "signin" | "check_email"
          | "legiscan" | "congress" | "ai" | "done";

export default function LoginPage() {
  const router   = useRouter();
  const supabase = createClient();

  const [step,        setStep]        = useState<Step>("welcome");
  const [lineIdx,     setLineIdx]     = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [typing,      setTyping]      = useState(true);

  // Form fields
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [username,    setUsername]    = useState("");
  const [legiscanKey, setLegiscanKey] = useState("");
  const [congressKey, setCongressKey] = useState("");
  const [aiKey,       setAiKey]       = useState("");
  const [selectedAi,  setSelectedAi]  = useState(AI_OPTIONS[0]);

  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");
  const [showMagic, setShowMagic] = useState(false);

  // Track step in a ref to avoid stale closure in onAuthStateChange
  const stepRef = useRef(step);
  useEffect(() => { stepRef.current = step; }, [step]);

  // ── Typewriter ─────────────────────────────────────────────────────────
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
    }, 32);
    return () => clearInterval(iv);
  }, [currentLine, typing]);

  function nextLine() {
    if (lineIdx < currentScript.lines.length - 1) {
      setLineIdx(lineIdx + 1);
      setTyping(true);
    }
  }

  function goToStep(s: Step) {
    setStep(s); setLineIdx(0); setTyping(true); setError("");
  }

  const allLinesShown = !typing && lineIdx === currentScript.lines.length - 1;

  // ── Magic link callback (user returns from email) ───────────────────────
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event) => {
      if (event === "SIGNED_IN" && stepRef.current === "check_email") {
        // Returned from magic link
        try {
          const ks = await keysApi.list();
          const hasAi = ks.some((k) => k.stored &&
            ["anthropic","openai","google","groq","mistral"].includes(k.provider));
          if (hasAi) { router.push("/dashboard"); return; }
        } catch {}
        goToStep("legiscan");
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  // ── Handlers ──────────────────────────────────────────────────────────
  async function handleRegister() {
    setError(""); setLoading(true);
    const { error: err } = await supabase.auth.signUp({ email, password });
    if (err) { setError(err.message); setLoading(false); return; }
    // Save display name immediately (best-effort)
    if (username.trim()) {
      try { await settingsApi.update({ display_name: username.trim() }); } catch {}
    }
    setLoading(false);
    goToStep("legiscan");
  }

  async function handleSignIn() {
    setError(""); setLoading(true);
    const { error: err } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (err) {
      setError(
        err.message.toLowerCase().includes("invalid") || err.message.toLowerCase().includes("credentials")
          ? "Wrong email or password. Try magic link below, or register a new account."
          : err.message
      );
      return;
    }
    router.push("/dashboard");
  }

  async function handleMagicLink() {
    setError(""); setLoading(true);
    const { error: err } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/login` },
    });
    setLoading(false);
    if (err) { setError(err.message); return; }
    goToStep("check_email");
  }

  async function handleLegiScan() {
    setError(""); setLoading(true);
    try {
      await keysApi.save("legiscan", legiscanKey.trim());
      goToStep("congress");
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function handleCongress() {
    setError(""); setLoading(true);
    try {
      await keysApi.save("congress", congressKey.trim());
      goToStep("ai");
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function handleAi() {
    setError(""); setLoading(true);
    try {
      await keysApi.save(selectedAi.provider, aiKey.trim());
      await settingsApi.update({ ai_provider: selectedAi.provider, ai_model: selectedAi.model });
      goToStep("done");
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  // ── Step indicator config ──────────────────────────────────────────────
  const NEW_STEPS:  Step[] = ["register", "legiscan", "congress", "ai", "done"];
  const BACK_STEPS: Step[] = ["signin", "done"];
  const isNewFlow = NEW_STEPS.includes(step);
  const dotSteps  = isNewFlow ? NEW_STEPS : BACK_STEPS;

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6"
          style={{ background: "var(--bg)" }}>

      {/* Bodhi dialogue */}
      <div className="card p-6 max-w-md w-full mb-6">
        <div className="flex items-start gap-4">
          <div className="text-4xl animate-wave flex-shrink-0">{currentScript.emoji}</div>
          <div className="flex-1">
            <p className="font-pixel text-xs mb-2" style={{ color: "var(--accent)" }}>BODHI_GUIDE.EXE</p>
            <p className="font-mono text-sm leading-relaxed" style={{ color: "var(--text)" }}>
              {displayText}<span className="animate-blink">▌</span>
            </p>
            <div className="flex gap-1 mt-3">
              {currentScript.lines.map((_, i) => (
                <span key={i} className="inline-block w-2 h-2"
                      style={{ background: i <= lineIdx ? "var(--accent)" : "var(--text-muted)" }} />
              ))}
            </div>
          </div>
        </div>
        {!allLinesShown && (
          <button onClick={nextLine} className="btn-arcade-outline mt-4 w-full font-pixel text-xs">
            ▶ CONTINUE
          </button>
        )}
      </div>

      {/* Step panel */}
      {allLinesShown && (
        <div className="card p-6 max-w-md w-full">

          {/* ── Welcome ── */}
          {step === "welcome" && (
            <button onClick={() => goToStep("new_or_return")}
                    className="btn-arcade w-full font-pixel text-xs">
              ▶ LET'S GO
            </button>
          )}

          {/* ── New or returning ── */}
          {step === "new_or_return" && (
            <div className="flex flex-col gap-3">
              <button onClick={() => goToStep("register")}
                      className="btn-arcade w-full font-pixel text-sm py-4">
                🤙 NEW TO THE BREAK
                <span className="block font-pixel mt-1" style={{ fontSize: "0.55rem", opacity: 0.8 }}>
                  CREATE AN ACCOUNT
                </span>
              </button>
              <button onClick={() => goToStep("signin")}
                      className="btn-arcade-outline w-full font-pixel text-sm py-4">
                🏄 I'VE SURFED HERE BEFORE
                <span className="block font-pixel mt-1" style={{ fontSize: "0.55rem", opacity: 0.7 }}>
                  SIGN IN
                </span>
              </button>
            </div>
          )}

          {/* ── Register ── */}
          {step === "register" && (
            <div className="flex flex-col gap-3">
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                  YOUR_NAME (display name)
                </label>
                <input className="input-arcade" placeholder="Dr. Jane Smith"
                       value={username} onChange={(e) => setUsername(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && email && password && handleRegister()} />
              </div>
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>EMAIL_ADDRESS</label>
                <input className="input-arcade" type="email" placeholder="you@university.edu"
                       value={email} onChange={(e) => setEmail(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && email && password && handleRegister()} />
              </div>
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>PASSWORD</label>
                <input className="input-arcade" type="password" placeholder="Min 6 characters"
                       value={password} onChange={(e) => setPassword(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && email && password && handleRegister()} />
              </div>
              <button className="btn-arcade w-full font-pixel text-xs"
                      onClick={handleRegister} disabled={loading || !email || !password}>
                {loading ? "CREATING ACCOUNT..." : "▶ CREATE ACCOUNT"}
              </button>
              <button onClick={() => goToStep("new_or_return")}
                      className="font-pixel text-xs text-center"
                      style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}>
                ◀ BACK
              </button>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>⚠ {error}</p>}
            </div>
          )}

          {/* ── Sign In ── */}
          {step === "signin" && (
            <div className="flex flex-col gap-3">
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>EMAIL_ADDRESS</label>
                <input className="input-arcade" type="email" placeholder="you@university.edu"
                       value={email} onChange={(e) => setEmail(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && email && password && handleSignIn()} />
              </div>
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>PASSWORD</label>
                <input className="input-arcade" type="password" placeholder="Your password"
                       value={password} onChange={(e) => setPassword(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && email && password && handleSignIn()} />
              </div>
              <button className="btn-arcade w-full font-pixel text-xs"
                      onClick={handleSignIn} disabled={loading || !email || !password}>
                {loading ? "SIGNING IN..." : "▶ SIGN IN"}
              </button>

              {/* Magic link secondary */}
              <div style={{ borderTop: "2px dashed var(--border)", paddingTop: "0.75rem" }}>
                <button onClick={() => setShowMagic((s) => !s)}
                        className="font-pixel text-xs w-full text-center"
                        style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}>
                  {showMagic ? "▼" : "▶"} USE MAGIC LINK INSTEAD
                </button>
                {showMagic && (
                  <div className="flex flex-col gap-2 mt-2">
                    <input className="input-arcade" type="email" placeholder="your@email.com"
                           value={email} onChange={(e) => setEmail(e.target.value)}
                           onKeyDown={(e) => e.key === "Enter" && email && handleMagicLink()} />
                    <button className="btn-arcade-outline w-full font-pixel text-xs"
                            onClick={handleMagicLink} disabled={loading || !email}>
                      {loading ? "SENDING..." : "SEND MAGIC LINK"}
                    </button>
                  </div>
                )}
              </div>

              <button onClick={() => goToStep("new_or_return")}
                      className="font-pixel text-xs text-center"
                      style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}>
                ◀ BACK
              </button>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>⚠ {error}</p>}
            </div>
          )}

          {/* ── Check email ── */}
          {step === "check_email" && (
            <div className="text-center flex flex-col gap-3">
              <p className="text-4xl">📬</p>
              <p className="font-pixel text-xs" style={{ color: "var(--accent)" }}>CHECK YOUR EMAIL</p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Magic link sent to <strong>{email}</strong>.<br />
                Click it and I'll pick up right where we left off.
              </p>
              <button onClick={() => goToStep("signin")}
                      className="font-pixel text-xs"
                      style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}>
                ◀ BACK TO SIGN IN
              </button>
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
                        onClick={() => goToStep("congress")}>
                  SKIP ▶
                </button>
                <button className="btn-arcade flex-1 font-pixel text-xs"
                        onClick={handleLegiScan} disabled={loading || !legiscanKey}>
                  {loading ? "SAVING..." : "▶ SAVE KEY"}
                </button>
              </div>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>⚠ {error}</p>}
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
                        onClick={() => goToStep("ai")}>
                  SKIP ▶
                </button>
                <button className="btn-arcade flex-1 font-pixel text-xs"
                        onClick={handleCongress} disabled={loading || !congressKey}>
                  {loading ? "SAVING..." : "▶ SAVE KEY"}
                </button>
              </div>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>⚠ {error}</p>}
            </div>
          )}

          {/* ── AI model ── */}
          {step === "ai" && (
            <div className="flex flex-col gap-3">
              <label className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>SELECT_AI_MODEL</label>
              <div className="grid gap-2">
                {AI_OPTIONS.map((opt) => (
                  <button key={opt.model} onClick={() => setSelectedAi(opt)}
                          className="text-left p-3 font-mono text-xs"
                          style={{
                            border:      "3px solid",
                            borderColor: selectedAi.model === opt.model ? "var(--accent)" : "var(--border)",
                            background:  selectedAi.model === opt.model ? "var(--accent)" : "transparent",
                            color:       selectedAi.model === opt.model ? "var(--bg)"     : "var(--text)",
                            boxShadow:   selectedAi.model === opt.model ? "3px 3px 0 var(--border)" : "none",
                          }}>
                    {selectedAi.model === opt.model ? "▶ " : "  "}{opt.label}
                  </button>
                ))}
              </div>
              <label className="font-pixel text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                {selectedAi.provider.toUpperCase()}_API_KEY
              </label>
              <input className="input-arcade" type="password" placeholder="Paste key here..."
                     value={aiKey} onChange={(e) => setAiKey(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && aiKey && handleAi()} />
              <div className="flex gap-2">
                <button className="btn-arcade-outline flex-1 font-pixel text-xs"
                        onClick={() => goToStep("done")}>
                  SKIP ▶
                </button>
                <button className="btn-arcade flex-1 font-pixel text-xs"
                        onClick={handleAi} disabled={loading || !aiKey}>
                  {loading ? "CONNECTING..." : "▶ CONNECT AI"}
                </button>
              </div>
              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>⚠ {error}</p>}
            </div>
          )}

          {/* ── Done ── */}
          {step === "done" && (
            <div className="text-center flex flex-col gap-4">
              <p className="text-4xl animate-wave">🤙</p>
              <p className="font-pixel text-sm neon-text" style={{ color: "var(--accent)" }}>
                SETUP COMPLETE!
              </p>
              <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                You can add API keys anytime in Settings.
              </p>
              <button className="btn-arcade w-full font-pixel text-xs"
                      onClick={() => router.push("/dashboard")}>
                ▶ DROP IN
              </button>
            </div>
          )}

        </div>
      )}

      {/* Step progress dots */}
      {(isNewFlow || BACK_STEPS.includes(step)) && (
        <div className="flex gap-2 mt-6">
          {dotSteps.map((s, i) => (
            <span key={s} className="w-3 h-3 inline-block"
                  style={{ background: dotSteps.indexOf(step) >= i ? "var(--accent)" : "var(--text-muted)" }} />
          ))}
        </div>
      )}
    </main>
  );
}
