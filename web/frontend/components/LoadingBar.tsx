"use client";
import { useTheme } from "@/lib/ThemeContext";

interface Props {
  label?: string;
}

export default function LoadingBar({ label }: Props) {
  const { ski } = useTheme();

  const emoji    = ski ? "🎿" : "🏄";
  const track    = ski ? "▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒" : "≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
      {/* Track */}
      <div style={{
        position:   "relative",
        width:      "240px",
        height:     "32px",
        overflow:   "hidden",
        border:     "2px solid var(--border)",
        background: "var(--surface, var(--bg-card))",
      }}>
        {/* Track fill */}
        <div style={{
          position:   "absolute",
          inset:      0,
          display:    "flex",
          alignItems: "center",
          paddingLeft: "4px",
          color:      "var(--border)",
          opacity:    0.35,
          fontSize:   "13px",
          letterSpacing: "1px",
          fontFamily: "monospace",
          overflow:   "hidden",
          whiteSpace: "nowrap",
        }}>
          {track}
        </div>

        {/* Rider */}
        <div style={{
          position:  "absolute",
          top:       "50%",
          transform: "translateY(-50%)",
          fontSize:  "18px",
          animation: "loader-ride 1.8s linear infinite",
          lineHeight: 1,
        }}>
          {emoji}
        </div>
      </div>

      {label && (
        <p className="font-pixel" style={{ color: "var(--border)", fontSize: "10px", letterSpacing: "1px" }}>
          {label}
        </p>
      )}
    </div>
  );
}
