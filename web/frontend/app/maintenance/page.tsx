"use client";
import { useState, useEffect } from "react";

const LINES = [
  "Catching a gnarly set — back soon, dude.",
  "Waxing the board. Won't be long.",
  "Paddling through the maintenance break.",
  "The crew's shaping something tubular.",
  "Hang loose — we'll be back at high tide.",
];

export default function MaintenancePage() {
  const [line, setLine] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setLine(l => (l + 1) % LINES.length), 3500);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center gap-8 p-8"
      style={{ background: "var(--bg)" }}
    >
      {/* Bodhi */}
      <div className="flex flex-col items-center gap-2">
        <span style={{ fontSize: "5rem", lineHeight: 1 }}>🏄</span>
        <p className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>
          BODHI — LEGISLATIVE SURFER
        </p>
      </div>

      {/* Title */}
      <h1
        className="font-pixel neon-text text-center"
        style={{ color: "var(--border)", fontSize: "1.5rem", letterSpacing: "0.15em" }}
      >
        TAKING A WAVE BREAK
      </h1>

      {/* Rotating message */}
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

      {/* Status */}
      <div
        className="text-center p-4"
        style={{ border: "3px dashed var(--accent)", maxWidth: "24rem" }}
      >
        <p className="font-pixel text-xs mb-2" style={{ color: "var(--accent)" }}>
          🚧 SITE TEMPORARILY OFFLINE 🚧
        </p>
        <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>
          We're making upgrades under the hood. Paddle back shortly and catch the next session.
        </p>
      </div>

      <p
        className="font-pixel"
        style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}
      >
        HANG TEN — BILL-SURFER.COM
      </p>
    </div>
  );
}
