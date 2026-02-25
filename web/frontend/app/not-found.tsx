"use client";
import Link from "next/link";
import { useState, useEffect } from "react";

const LINES = [
  "WOAH DUDE — you wiped out.",
  "This page got eaten by the shore break.",
  "Hang loose — she's still under construction.",
  "We're waxing the board, bro. Come back soon.",
  "Gnarly 404, my friend.",
];

export default function NotFound() {
  const [line, setLine] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setLine(l => (l + 1) % LINES.length), 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center gap-8 p-8"
      style={{ background: "var(--bg)" }}
    >
      {/* Bodhi avatar */}
      <div className="flex flex-col items-center gap-2">
        <span style={{ fontSize: "5rem", lineHeight: 1 }}>🏄</span>
        <p className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>
          BODHI — LEGISLATIVE SURFER
        </p>
      </div>

      {/* 404 */}
      <h1
        className="font-pixel neon-text"
        style={{ fontSize: "3rem", color: "var(--border)", letterSpacing: "0.2em" }}
      >
        404
      </h1>

      {/* Rotating surf-speak message */}
      <div
        className="text-center p-5 max-w-sm"
        style={{ border: "3px solid var(--border)", background: "var(--bg-card)" }}
      >
        <p
          className="font-pixel text-xs mb-3"
          style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}
        >
          BODHI SAYS:
        </p>
        <p
          key={line}
          className="font-pixel"
          style={{ color: "var(--text)", fontSize: "0.75rem", lineHeight: 1.6 }}
        >
          "{LINES[line]}"
        </p>
      </div>

      {/* Under construction sign */}
      <div
        className="text-center p-4"
        style={{ border: "3px dashed var(--accent)", maxWidth: "24rem" }}
      >
        <p className="font-pixel text-xs mb-1" style={{ color: "var(--accent)" }}>
          🚧 UNDER CONSTRUCTION 🚧
        </p>
        <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>
          The crew is shaping something rad. Paddle back soon and catch the next set.
        </p>
      </div>

      {/* Back home */}
      <Link
        href="/"
        className="btn-arcade font-pixel text-xs"
      >
        🏠 PADDLE BACK HOME
      </Link>

      <p
        className="font-pixel"
        style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}
      >
        HANG TEN — BILL-SURFER.COM
      </p>
    </div>
  );
}
