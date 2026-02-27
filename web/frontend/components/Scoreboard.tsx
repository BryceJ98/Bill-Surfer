"use client";
import { useEffect, useState } from "react";
import { settings as settingsApi, type Scoreboard } from "@/lib/api";

export default function Scoreboard() {
  const [data, setData] = useState<Scoreboard | null>(null);

  useEffect(() => {
    settingsApi.scoreboard().then(setData).catch(() => {});
  }, []);

  const score = data?.productivity_score ?? null;

  return (
    <div className="card p-4 flex items-center gap-4">
      {/* Coin icon */}
      <div className="flex-shrink-0 flex items-center justify-center"
           style={{ width: 52, height: 52, background: "var(--accent)",
             border: "3px solid var(--border)", boxShadow: "3px 3px 0 var(--border)" }}>
        <span style={{ fontSize: "1.5rem" }}>⬡</span>
      </div>

      {/* Score */}
      <div className="flex flex-col gap-0">
        <span className="font-pixel" style={{ color: "var(--accent)", fontSize: "1.6rem", lineHeight: 1 }}>
          {score !== null ? score.toLocaleString() : "—"}
        </span>
        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
          ACTIVITY COINS
        </span>
      </div>

      {/* Sub-stats */}
      {data && (
        <div className="flex gap-4 ml-auto flex-wrap">
          <div className="text-center">
            <div className="font-pixel" style={{ color: "var(--text)", fontSize: "0.85rem" }}>{data.docket_count}</div>
            <div className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.45rem" }}>BILLS</div>
          </div>
          <div className="text-center">
            <div className="font-pixel" style={{ color: "var(--text)", fontSize: "0.85rem" }}>{data.reports_total}</div>
            <div className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.45rem" }}>REPORTS</div>
          </div>
          <div className="text-center">
            <div className="font-pixel" style={{ color: "var(--text)", fontSize: "0.85rem" }}>
              {data.usage?.reduce((s, u) => s + (u.call_count || 0), 0) ?? 0}
            </div>
            <div className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.45rem" }}>AI CALLS</div>
          </div>
        </div>
      )}
    </div>
  );
}
