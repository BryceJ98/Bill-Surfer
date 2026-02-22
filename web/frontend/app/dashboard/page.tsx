"use client";
import { useEffect, useState } from "react";
import NavBar from "@/components/NavBar";
import Scoreboard from "@/components/Scoreboard";
import BodhiChat from "@/components/BodhiChat";
import { docket as docketApi, reports as reportsApi, type DocketItem, type Report } from "@/lib/api";
import Link from "next/link";

export default function Dashboard() {
  const [docketItems,  setDocketItems]  = useState<DocketItem[]>([]);
  const [recentReports, setRecentReports] = useState<Report[]>([]);

  useEffect(() => {
    docketApi.list().then((d) => setDocketItems(d.slice(0, 5))).catch(() => {});
    reportsApi.list().then((r) => setRecentReports(r.slice(0, 5))).catch(() => {});
  }, []);

  const STANCE_COLOR: Record<string, string> = {
    support: "#2D7A4F", oppose: "#c53030", neutral: "#555", watching: "#1A6BA0",
  };

  const STATUS_COLOR: Record<string, string> = {
    complete: "#2D7A4F", generating: "#856404", error: "#c53030", pending: "#555",
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />

      <main className="max-w-5xl mx-auto p-6 flex flex-col gap-6">

        {/* Scoreboard */}
        <Scoreboard />

        {/* Ticker */}
        <div className="py-1 px-2"
             style={{ background: "var(--primary)", border: "3px solid var(--border)", boxShadow: "4px 4px 0 var(--border)" }}>
          <div className="ticker-wrap">
            <span className="ticker font-pixel text-xs" style={{ color: "var(--bg)" }}>
              ★ WELCOME TO BILL-SURFER ★ YOUR DOCKET HAS {docketItems.length} BILLS ★
              {recentReports.length} REPORTS IN LIBRARY ★ RIDE THE LEGISLATIVE WAVE ★
            </span>
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Recent docket */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-pixel text-xs" style={{ color: "var(--accent)" }}>📋 RECENT DOCKET</h2>
              <Link href="/docket" className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>VIEW ALL ▶</Link>
            </div>
            {docketItems.length === 0
              ? <EmptyState icon="📋" msg="No bills in docket yet." action="/search" actionLabel="SEARCH BILLS" />
              : (
                <div className="flex flex-col gap-2">
                  {docketItems.map((item) => (
                    <div key={item.id} className="card p-3 flex items-start gap-3">
                      <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
                            style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)" }}>
                        {item.state}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-mono text-xs truncate">{item.title ?? item.bill_number}</p>
                        {item.stance && (
                          <span className="font-pixel text-xs" style={{ color: STANCE_COLOR[item.stance] ?? "#555", fontSize: "0.55rem" }}>
                            ● {item.stance.toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
            }
          </section>

          {/* Recent reports */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-pixel text-xs" style={{ color: "var(--accent)" }}>📊 RECENT REPORTS</h2>
              <Link href="/reports" className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>VIEW ALL ▶</Link>
            </div>
            {recentReports.length === 0
              ? <EmptyState icon="📊" msg="No reports generated yet." action="/reports" actionLabel="NEW REPORT" />
              : (
                <div className="flex flex-col gap-2">
                  {recentReports.map((r) => (
                    <div key={r.id} className="card p-3">
                      <div className="flex items-start gap-2">
                        <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
                              style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)" }}>
                          {r.state}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-xs truncate">{r.title}</p>
                          <span className="font-pixel text-xs" style={{ color: STATUS_COLOR[r.status] ?? "#555", fontSize: "0.55rem" }}>
                            ● {r.status.toUpperCase()}
                          </span>
                        </div>
                        {r.status === "complete" && (
                          <a href={reportsApi.pdfUrl(r.id)}
                             className="font-pixel text-xs flex-shrink-0"
                             style={{ color: "var(--accent)" }}
                             target="_blank" rel="noreferrer">
                            PDF ↗
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
            }
          </section>
        </div>

        {/* Quick actions */}
        <section>
          <h2 className="font-pixel text-xs mb-3" style={{ color: "var(--accent)" }}>⚡ QUICK ACTIONS</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { href: "/search",  icon: "🔍", label: "SEARCH BILLS" },
              { href: "/docket",  icon: "📋", label: "MY DOCKET"    },
              { href: "/reports", icon: "📊", label: "GEN REPORT"   },
              { href: "/settings",icon: "⚙️", label: "SETTINGS"     },
            ].map((a) => (
              <Link key={a.href} href={a.href}>
                <button className="btn-arcade-outline w-full flex flex-col items-center gap-2 py-4">
                  <span className="text-2xl">{a.icon}</span>
                  <span className="font-pixel" style={{ fontSize: "0.55rem" }}>{a.label}</span>
                </button>
              </Link>
            ))}
          </div>
        </section>

      </main>

      <BodhiChat />
    </div>
  );
}

function EmptyState({ icon, msg, action, actionLabel }: { icon: string; msg: string; action: string; actionLabel: string }) {
  return (
    <div className="card p-6 flex flex-col items-center gap-3">
      <span className="text-3xl">{icon}</span>
      <p className="font-pixel text-xs text-center" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>{msg}</p>
      <Link href={action}><button className="btn-arcade font-pixel" style={{ fontSize: "0.6rem" }}>▶ {actionLabel}</button></Link>
    </div>
  );
}
