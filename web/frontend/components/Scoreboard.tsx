"use client";
import { useEffect, useState } from "react";
import { settings as settingsApi, type Scoreboard } from "@/lib/api";

export default function Scoreboard() {
  const [data, setData] = useState<Scoreboard | null>(null);

  useEffect(() => {
    settingsApi.scoreboard().then(setData).catch(() => {});
  }, []);

  const score    = data?.productivity_score ?? null;
  const aiCalls  = data?.usage?.reduce((s, u) => s + (u.call_count || 0), 0) ?? 0;
  const modelName = data?.ai_model?.split("/").pop()?.toUpperCase() ?? "—";

  return (
    <div className="flex flex-col gap-3">

      {/* Row 1: Points + AI Model */}
      <div className="grid grid-cols-2 gap-3">

        {/* ⬡ Points */}
        <div className="card p-4 flex items-center gap-3">
          <div className="flex-shrink-0 flex items-center justify-center"
               style={{ width: 46, height: 46, background: "var(--accent)",
                 border: "3px solid var(--border)", boxShadow: "3px 3px 0 var(--border)" }}>
            <span style={{ fontSize: "1.3rem" }}>⬡</span>
          </div>
          <div className="flex flex-col gap-0">
            <span className="font-pixel" style={{ color: "var(--accent)", fontSize: "1.5rem", lineHeight: 1 }}>
              {score !== null ? score.toLocaleString() : "—"}
            </span>
            <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
              POINTS
            </span>
          </div>
        </div>

        {/* 🤖 AI Model */}
        <div className="card p-4 flex items-center gap-3">
          <div className="flex-shrink-0 flex items-center justify-center"
               style={{ width: 46, height: 46, background: "var(--primary)",
                 border: "3px solid var(--border)", boxShadow: "3px 3px 0 var(--border)" }}>
            <span style={{ fontSize: "1.3rem" }}>🤖</span>
          </div>
          <div className="flex flex-col gap-0 min-w-0">
            <span className="font-pixel" style={{ color: "var(--text)", fontSize: "0.65rem", lineHeight: 1.3,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {modelName}
            </span>
            <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
              {data?.ai_provider?.toUpperCase() ?? "AI MODEL"}
            </span>
          </div>
        </div>
      </div>

      {/* Row 2: Bills / Reports / AI Calls */}
      <div className="grid grid-cols-3 gap-3">

        {/* 📋 Bills */}
        <div className="card p-4 flex flex-col items-center gap-1 text-center">
          <span style={{ fontSize: "1.25rem" }}>📋</span>
          <span className="font-pixel" style={{ color: "var(--text)", fontSize: "1.1rem", lineHeight: 1 }}>
            {data?.docket_count ?? "—"}
          </span>
          <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.48rem" }}>BILLS</span>
        </div>

        {/* 📄 Reports */}
        <div className="card p-4 flex flex-col items-center gap-1 text-center">
          <span style={{ fontSize: "1.25rem" }}>📄</span>
          <span className="font-pixel" style={{ color: "var(--text)", fontSize: "1.1rem", lineHeight: 1 }}>
            {data?.reports_total ?? "—"}
          </span>
          <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.48rem" }}>REPORTS</span>
        </div>

        {/* ⚡ AI Calls */}
        <div className="card p-4 flex flex-col items-center gap-1 text-center">
          <span style={{ fontSize: "1.25rem" }}>⚡</span>
          <span className="font-pixel" style={{ color: "var(--text)", fontSize: "1.1rem", lineHeight: 1 }}>
            {aiCalls}
          </span>
          <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.48rem" }}>AI CALLS</span>
        </div>

      </div>
    </div>
  );
}
