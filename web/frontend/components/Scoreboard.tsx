"use client";
import { useEffect, useState } from "react";
import { settings as settingsApi, type Scoreboard } from "@/lib/api";

export default function Scoreboard() {
  const [data, setData] = useState<Scoreboard | null>(null);

  useEffect(() => {
    settingsApi.scoreboard().then(setData).catch(() => {});
  }, []);

  const tiles = data
    ? [
        { label: "BILLS IN DOCKET", value: data.docket_count,   icon: "📋" },
        { label: "REPORTS TODAY",   value: data.reports_today,  icon: "📊" },
        { label: "REPORTS TOTAL",   value: data.reports_total,  icon: "🗂️" },
        { label: "AI MODEL",        value: (data.ai_model ?? "—").split("/").pop()?.toUpperCase().slice(0,16) ?? "—", icon: "🤖" },
      ]
    : Array(4).fill({ label: "...", value: "—", icon: "⬛" });

  const legiscanCalls = data?.usage?.find(u => u.provider === "legiscan")?.call_count ?? 0;
  const congressCalls = data?.usage?.find(u => u.provider === "congress")?.call_count ?? 0;
  const aiTokens      = data?.usage?.reduce((sum, u) => sum + (u.token_count || 0), 0) ?? 0;

  const usageTiles = data
    ? [
        { label: "LEGISCAN CALLS",  value: legiscanCalls,                    icon: "🏛️" },
        { label: "CONGRESS CALLS",  value: congressCalls,                    icon: "🇺🇸" },
        { label: "AI TOKENS",       value: aiTokens.toLocaleString(),        icon: "✨" },
      ]
    : Array(3).fill({ label: "...", value: "—", icon: "⬛" });

  return (
    <div className="w-full">
      {/* Scoreboard header */}
      <div className="flex items-center gap-2 mb-2 px-1">
        <span className="font-pixel text-xs" style={{ color: "var(--accent)" }}>▶ SCOREBOARD</span>
        <span className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
          {data?.date ?? "..."}
        </span>
      </div>

      {/* Main tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {tiles.map((t, i) => (
          <div key={i} className="card p-3 flex flex-col items-center gap-1">
            <span className="text-xl">{t.icon}</span>
            <span className="font-pixel text-center" style={{ color: "var(--accent)", fontSize: i === 3 ? "0.65rem" : "1.125rem", lineHeight: 1.3 }}>
              {t.value}
            </span>
            <span className="font-pixel text-xs text-center" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
              {t.label}
            </span>
          </div>
        ))}
      </div>

      {/* This month usage header */}
      <div className="flex items-center gap-2 mt-4 mb-2 px-1">
        <span className="font-pixel text-xs" style={{ color: "var(--accent)" }}>▶ THIS MONTH</span>
      </div>

      {/* Usage tiles */}
      <div className="grid grid-cols-3 gap-3">
        {usageTiles.map((t, i) => (
          <div key={i} className="card p-3 flex flex-col items-center gap-1">
            <span className="text-xl">{t.icon}</span>
            <span className="font-pixel text-lg" style={{ color: "var(--accent)" }}>
              {t.value}
            </span>
            <span className="font-pixel text-xs text-center" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
              {t.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
