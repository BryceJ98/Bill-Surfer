"use client";
import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8"
          style={{ background: "var(--bg)" }}>

      {/* Logo / title */}
      <div className="text-center mb-10">
        <p className="font-pixel text-xs mb-3" style={{ color: "var(--accent)" }}>
          ▶ INSERT COIN ◀
        </p>
        <h1 className="font-pixel text-2xl md:text-4xl leading-loose neon-text"
            style={{ color: "var(--accent)" }}>
          BILL-SURFER
        </h1>
        <p className="font-pixel text-xs mt-3" style={{ color: "var(--text-muted)" }}>
          LEGISLATIVE RESEARCH ARCADE
        </p>
        <div className="mt-4 text-4xl animate-wave inline-block">🏄</div>
      </div>

      {/* Feature grid — BUG-015: cards are now clickable */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl w-full mb-10">
        {[
          { icon: "📜", label: "SEARCH BILLS",   desc: "Federal + all 50 states",        href: "/login" },
          { icon: "🗳️", label: "TRACK DOCKET",   desc: "Your personal bill watchlist",   href: "/login" },
          { icon: "📊", label: "GEN REPORTS",    desc: "AI policy impact reports",        href: "/login" },
          { icon: "🤝", label: "NOMINATIONS",    desc: "Presidential confirmations",      href: "/login" },
          { icon: "📤", label: "CSV EXPORT",     desc: "Download any dataset",            href: "/login" },
          { icon: "🤖", label: "BODHI CHAT",     desc: "Your AI surf/ski guide",          href: "/login" },
        ].map((f) => (
          <Link key={f.label} href={f.href}>
            <div className="card p-4 text-center cursor-pointer transition-transform hover:scale-105"
                 style={{ transition: "transform 0.1s" }}>
              <div className="text-2xl mb-2">{f.icon}</div>
              <p className="font-pixel text-xs mb-1" style={{ color: "var(--accent)" }}>{f.label}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{f.desc}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* CTA */}
      <Link href="/login">
        <button className="btn-arcade font-pixel text-sm px-8 py-3 animate-pulse">
          ▶ START GAME
        </button>
      </Link>

      <p className="font-pixel text-xs mt-6" style={{ color: "var(--text-muted)" }}>
        BRING YOUR OWN API KEYS · USE YOUR OWN AI
      </p>

      {/* Ticker */}
      <div className="fixed bottom-0 left-0 right-0 py-1 px-2"
           style={{ background: "var(--primary)", color: "var(--bg)", borderTop: "3px solid var(--border)" }}>
        <div className="ticker-wrap">
          <span className="ticker font-pixel text-xs">
            ★ CONGRESS.GOV DATA ★ LEGISCAN STATE BILLS ★ AI-POWERED REPORTS ★
            PRESIDENTIAL NOMINATIONS ★ TREATY TRACKING ★ CSV EXPORT ★
            BRING YOUR OWN API KEYS ★ CLAUDE · GPT · GEMINI · GROQ SUPPORT ★
          </span>
        </div>
      </div>
    </main>
  );
}
