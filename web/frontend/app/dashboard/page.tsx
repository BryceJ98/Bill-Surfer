"use client";
import { useEffect, useState } from "react";
import NavBar from "@/components/NavBar";
import Scoreboard from "@/components/Scoreboard";
import BodhiChat from "@/components/BodhiChat";
import { docket as docketApi, reports as reportsApi, federalRegister, type DocketItem, type Report, type FrDocument } from "@/lib/api";
import Link from "next/link";

export default function Dashboard() {
  const [docketItems,   setDocketItems]   = useState<DocketItem[]>([]);
  const [recentReports, setRecentReports] = useState<Report[]>([]);
  const [loadError,     setLoadError]     = useState("");
  const [frDigest,      setFrDigest]      = useState<FrDocument[] | null>(null);
  const [frLoading,     setFrLoading]     = useState(true);
  const [frDate,        setFrDate]        = useState("");

  useEffect(() => {
    docketApi.list()
      .then((d) => setDocketItems(d.slice(0, 5)))
      .catch((e: any) => setLoadError(e.message));
    reportsApi.list()
      .then((r) => setRecentReports(r.slice(0, 5)))
      .catch((e: any) => setLoadError(e.message));
    federalRegister.digest(undefined, 5)
      .then((r) => { setFrDigest(r.documents); setFrDate(r.date); })
      .catch(() => setFrDigest([]))
      .finally(() => setFrLoading(false));
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

        {loadError && (
          <p className="font-pixel text-xs p-3" style={{ background: "#c53030", color: "#fff", border: "3px solid #8b0000" }}>
            ⚠ {loadError}
          </p>
        )}

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
                    <Link key={item.id} href="/docket">
                      <div className="card p-3 flex items-start gap-3 cursor-pointer"
                           style={{ transition: "opacity 0.1s" }}>
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
                    </Link>
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
                    <Link key={r.id} href="/reports">
                      <div className="card p-3 cursor-pointer">
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
                               target="_blank" rel="noreferrer"
                               onClick={(e) => e.stopPropagation()}>
                              PDF ↗
                            </a>
                          )}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )
            }
          </section>
        </div>

        {/* Federal Register Daily Digest */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-pixel text-xs" style={{ color: "var(--accent)" }}>
              📰 FEDERAL REGISTER DIGEST
            </h2>
            <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
              {frDate && frDate !== "today" ? frDate : new Date().toLocaleDateString()}
            </span>
          </div>

          {frLoading && (
            <div className="card p-6 flex justify-center">
              <span className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>● LOADING DIGEST...</span>
            </div>
          )}

          {!frLoading && frDigest && frDigest.length === 0 && (
            <div className="card p-4 text-center">
              <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                No rules or executive orders published today.
              </p>
            </div>
          )}

          {!frLoading && frDigest && frDigest.length > 0 && (
            <div className="flex flex-col gap-2">
              {frDigest.map((doc) => {
                const impactColor = doc.impact === "HIGH" ? "#c53030" : doc.impact === "MED" ? "#856404" : "#2D7A4F";
                const typeLabel   = doc.type === "PRORULE" ? "PROP RULE" : doc.type === "PRESDOCU" ? "EXEC ORDER" : doc.type;
                return (
                  <a key={doc.document_number} href={doc.html_url} target="_blank" rel="noreferrer"
                     style={{ textDecoration: "none" }}>
                    <div className="card p-3" style={{ cursor: "pointer" }}>
                      <div className="flex items-start gap-3">
                        {/* RBS badge */}
                        <div style={{ flexShrink: 0, textAlign: "center", minWidth: "52px" }}>
                          <div className="font-pixel" style={{ background: impactColor, color: "#fff", padding: "2px 4px", fontSize: "0.5rem", marginBottom: "2px" }}>
                            {doc.impact}
                          </div>
                          <div className="font-pixel" style={{ color: impactColor, fontSize: "0.55rem" }}>
                            {doc.rbs}/100
                          </div>
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-xs" style={{ marginBottom: "3px", lineHeight: 1.4 }}>
                            {doc.title.length > 90 ? doc.title.slice(0, 90) + "…" : doc.title}
                          </p>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-pixel" style={{ background: "var(--primary)", color: "var(--bg)", padding: "1px 5px", fontSize: "0.5rem" }}>
                              {typeLabel}
                            </span>
                            {doc.agency_names?.[0] && (
                              <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                                {doc.agency_names[0].length > 40 ? doc.agency_names[0].slice(0, 40) + "…" : doc.agency_names[0]}
                              </span>
                            )}
                            {doc.comment_date && (
                              <span className="font-pixel" style={{ color: "#856404", fontSize: "0.5rem" }}>
                                ● COMMENT BY {doc.comment_date}
                              </span>
                            )}
                          </div>
                        </div>

                        <span className="font-pixel flex-shrink-0" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>↗</span>
                      </div>
                    </div>
                  </a>
                );
              })}
            </div>
          )}
        </section>

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
