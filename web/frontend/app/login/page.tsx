"use client";
import { useState, useEffect, useRef } from "react";
import { createClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { keys as keysApi, settings as settingsApi } from "@/lib/api";

// ── Bodhi dialogue ─────────────────────────────────────────────────────────
const BODHI_SCRIPT = [
  {
    step:  "reset_password",
    emoji: "🔑",
    lines: [
      "Password reset! Enter your new password below.",
    ],
  },
  {
    step:  "auth",
    emoji: "🏄",
    lines: [
      "YO! I'm BODHI — your legislative surf guide.",
      "Shred through bills, track legislation, generate reports.",
      "Paddle in below.",
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

type Step     = "auth" | "check_email" | "reset_password" | "legiscan" | "congress" | "ai" | "done";
type AuthMode = "signin" | "register";

export default function LoginPage() {
  const router   = useRouter();
  const supabase = createClient();

  const [step,        setStep]        = useState<Step>("auth");
  const [lineIdx,     setLineIdx]     = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [typing,      setTyping]      = useState(true);
  const [authMode,    setAuthMode]    = useState<AuthMode>("signin");
  const [showMagic,   setShowMagic]   = useState(false);

  // Form fields
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [username,    setUsername]    = useState("");
  const [legiscanKey, setLegiscanKey] = useState("");
  const [congressKey, setCongressKey] = useState("");
  const [aiKey,       setAiKey]       = useState("");
  const [selectedAi,  setSelectedAi]  = useState(AI_OPTIONS[0]);

  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState("");
  const [showForgot,  setShowForgot]  = useState(false);
  const [forgotSent,  setForgotSent]  = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPw,   setConfirmPw]   = useState("");

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
    }, 28);
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
      if (event === "PASSWORD_RECOVERY") {
        goToStep("reset_password");
        return;
      }
      if (event === "SIGNED_IN" && stepRef.current === "check_email") {
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

    // Poll until session is available (email confirm disabled returns session immediately
    // but client may not have stored it yet)
    let attempts = 0;
    while (attempts < 10) {
      const { data: sd } = await supabase.auth.getSession();
      if (sd.session?.access_token) break;
      await new Promise((r) => setTimeout(r, 300));
      attempts++;
    }

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
          ? "Wrong email or password. Try magic link below, or create a new account."
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

  async function handleForgotPassword() {
    if (!email) { setError("Enter your email address above first."); return; }
    setError(""); setLoading(true);
    const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${location.origin}/login`,
    });
    setLoading(false);
    if (err) { setError(err.message); return; }
    setForgotSent(true);
  }

  async function handleResetPassword() {
    if (newPassword.length < 6) { setError("Password must be at least 6 characters."); return; }
    if (newPassword !== confirmPw) { setError("Passwords don't match."); return; }
    setError(""); setLoading(true);
    const { error: err } = await supabase.auth.updateUser({ password: newPassword });
    setLoading(false);
    if (err) { setError(err.message); return; }
    router.push("/dashboard");
  }

  async function handleLegiScan() {
    setError(""); setLoading(true);
    try { await keysApi.save("legiscan", legiscanKey.trim()); goToStep("congress"); }
    catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function handleCongress() {
    setError(""); setLoading(true);
    try { await keysApi.save("congress", congressKey.trim()); goToStep("ai"); }
    catch (e: any) { setError(e.message); }
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

  // ── Step progress dots (key-setup phase only) ──────────────────────────
  const SETUP_STEPS: Step[] = ["legiscan", "congress", "ai", "done"];
  const inSetup = SETUP_STEPS.includes(step);

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
        {/* Only show Continue on non-auth steps (auth form is always visible) */}
        {step !== "auth" && !allLinesShown && (
          <button onClick={nextLine} className="btn-arcade-outline mt-4 w-full font-pixel text-xs">
            ▶ CONTINUE
          </button>
        )}
      </div>

      {/* Step panel — auth step always visible; others wait for allLinesShown */}
      {(step === "auth" || allLinesShown) && (
        <div className="card p-6 max-w-md w-full">

          {/* ── Auth (signin / register combined) ── */}
          {step === "auth" && (
            <div className="flex flex-col gap-3">
              {/* Mode toggle tabs */}
              <div style={{ display: "flex", borderBottom: "2px solid var(--border)", marginBottom: "4px" }}>
                {(["signin", "register"] as AuthMode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => { setAuthMode(m); setError(""); setShowMagic(false); }}
                    className="font-pixel text-xs flex-1 py-2"
                    style={{
                      background:   authMode === m ? "var(--accent)"   : "transparent",
                      color:        authMode === m ? "var(--bg)"        : "var(--text-muted)",
                      border:       "none",
                      borderBottom: authMode === m ? "3px solid var(--border)" : "none",
                      cursor:       "pointer",
                      fontSize:     "0.55rem",
                    }}
                  >
                    {m === "signin" ? "🏄 SIGN IN" : "🤙 CREATE ACCOUNT"}
                  </button>
                ))}
              </div>

              {/* Register-only field */}
              {authMode === "register" && (
                <div>
                  <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                    YOUR_NAME (display name)
                  </label>
                  <input className="input-arcade" placeholder="Dr. Jane Smith"
                         value={username} onChange={(e) => setUsername(e.target.value)}
                         onKeyDown={(e) => e.key === "Enter" && email && password && handleRegister()} />
                </div>
              )}

              {/* Shared fields */}
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>EMAIL_ADDRESS</label>
                <input className="input-arcade" type="email" placeholder="you@university.edu"
                       value={email} onChange={(e) => setEmail(e.target.value)}
                       onKeyDown={(e) => {
                         if (e.key !== "Enter" || !email || !password) return;
                         authMode === "register" ? handleRegister() : handleSignIn();
                       }} />
              </div>
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>PASSWORD</label>
                <input className="input-arcade" type="password"
                       placeholder={authMode === "register" ? "Min 6 characters" : "Your password"}
                       value={password} onChange={(e) => setPassword(e.target.value)}
                       onKeyDown={(e) => {
                         if (e.key !== "Enter" || !email || !password) return;
                         authMode === "register" ? handleRegister() : handleSignIn();
                       }} />
              </div>

              <button
                className="btn-arcade w-full font-pixel text-xs"
                onClick={authMode === "register" ? handleRegister : handleSignIn}
                disabled={loading || !email || !password}
              >
                {loading
                  ? (authMode === "register" ? "CREATING ACCOUNT..." : "SIGNING IN...")
                  : (authMode === "register" ? "▶ CREATE ACCOUNT" : "▶ SIGN IN")}
              </button>

              {/* Magic link + forgot password (signin only) */}
              {authMode === "signin" && (
                <div style={{ borderTop: "2px dashed var(--border)", paddingTop: "0.75rem", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <button onClick={() => setShowMagic((s) => !s)}
                          className="font-pixel text-xs w-full text-center"
                          style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}>
                    {showMagic ? "▼" : "▶"} USE MAGIC LINK INSTEAD
                  </button>
                  {showMagic && (
                    <div className="flex flex-col gap-2 mt-1">
                      <button className="btn-arcade-outline w-full font-pixel text-xs"
                              onClick={handleMagicLink} disabled={loading || !email}>
                        {loading ? "SENDING..." : "SEND MAGIC LINK"}
                      </button>
                    </div>
                  )}

                  {/* Forgot password */}
                  <button
                    onClick={() => { setShowForgot((s) => !s); setForgotSent(false); setError(""); }}
                    className="font-pixel text-xs w-full text-center"
                    style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}
                  >
                    {showForgot ? "▼" : "▶"} FORGOT PASSWORD?
                  </button>
                  {showForgot && (
                    <div className="flex flex-col gap-2 mt-1">
                      {forgotSent ? (
                        <p className="font-pixel text-xs" style={{ color: "#2D7A4F" }}>
                          ✓ Reset link sent to {email}. Check your inbox.
                        </p>
                      ) : (
                        <button className="btn-arcade-outline w-full font-pixel text-xs"
                                onClick={handleForgotPassword} disabled={loading || !email}>
                          {loading ? "SENDING..." : "SEND RESET LINK"}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}

              {error && <p className="font-pixel text-xs" style={{ color: "#e53e3e" }}>⚠ {error}</p>}
            </div>
          )}

          {/* ── Reset password ── */}
          {step === "reset_password" && (
            <div className="flex flex-col gap-3">
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>NEW_PASSWORD</label>
                <input className="input-arcade" type="password" placeholder="Min 6 characters"
                       value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && newPassword && confirmPw && handleResetPassword()} />
              </div>
              <div>
                <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>CONFIRM_PASSWORD</label>
                <input className="input-arcade" type="password" placeholder="Repeat new password"
                       value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && newPassword && confirmPw && handleResetPassword()} />
              </div>
              <button className="btn-arcade w-full font-pixel text-xs"
                      onClick={handleResetPassword} disabled={loading || !newPassword || !confirmPw}>
                {loading ? "SAVING..." : "▶ SET NEW PASSWORD"}
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
                Click it and I&apos;ll pick up right where we left off.
              </p>
              <button onClick={() => goToStep("auth")}
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
                <button className="btn-arcade-outline flex-1 font-pixel text-xs" onClick={() => goToStep("congress")}>SKIP ▶</button>
                <button className="btn-arcade flex-1 font-pixel text-xs" onClick={handleLegiScan} disabled={loading || !legiscanKey}>
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
                <button className="btn-arcade-outline flex-1 font-pixel text-xs" onClick={() => goToStep("ai")}>SKIP ▶</button>
                <button className="btn-arcade flex-1 font-pixel text-xs" onClick={handleCongress} disabled={loading || !congressKey}>
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
                <button className="btn-arcade-outline flex-1 font-pixel text-xs" onClick={() => goToStep("done")}>SKIP ▶</button>
                <button className="btn-arcade flex-1 font-pixel text-xs" onClick={handleAi} disabled={loading || !aiKey}>
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
              <p className="font-pixel text-sm neon-text" style={{ color: "var(--accent)" }}>SETUP COMPLETE!</p>
              <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                You can add API keys anytime in Settings.
              </p>
              <button className="btn-arcade w-full font-pixel text-xs" onClick={() => router.push("/dashboard")}>
                ▶ DROP IN
              </button>
            </div>
          )}

        </div>
      )}

      {/* Progress dots — key setup phase only */}
      {inSetup && (
        <div className="flex gap-2 mt-6">
          {SETUP_STEPS.map((s, i) => (
            <span key={s} className="w-3 h-3 inline-block"
                  style={{ background: SETUP_STEPS.indexOf(step) >= i ? "var(--accent)" : "var(--text-muted)" }} />
          ))}
        </div>
      )}
    </main>
  );
}
