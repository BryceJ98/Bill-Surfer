"use client";
import { useEffect, useState } from "react";
import NavBar from "@/components/NavBar";
import Scoreboard from "@/components/Scoreboard";
import BodhiChat from "@/components/BodhiChat";
import { docket as docketApi, federalRegister, type DocketItem, type FrDocument } from "@/lib/api";
import Link from "next/link";

const STORAGE_KEY = "bill_surfer_trackers";

interface SavedTracker {
  id:            string;
  topic:         string;
  state?:        string;
  created_at:    string;
  last_checked:  string;
  last_bill_ids: string[];
  new_count:     number;
  last_result?:  any;
}

function billKey(b: any): string {
  return String(b.bill_id ?? b.number ?? b.bill_number ?? "");
}

export default function Dashboard() {
  const [docketItems,   setDocketItems]   = useState<DocketItem[]>([]);
  const [loadError,     setLoadError]     = useState("");
  const [frDigest,      setFrDigest]      = useState<FrDocument[] | null>(null);
  const [frLoading,     setFrLoading]     = useState(true);
  const [frDate,        setFrDate]        = useState("");
  const [trackers,      setTrackers]      = useState<SavedTracker[]>([]);
  const [expandedId,    setExpandedId]    = useState<string | null>(null);
  const [frByTracker,   setFrByTracker]   = useState<Record<string, FrDocument[]>>({});

  useEffect(() => {
    docketApi.list()
      .then((d) => setDocketItems(d.slice(0, 5)))
      .catch((e: any) => setLoadError(e.message));

    federalRegister.digest(undefined, 5)
      .then((r) => { setFrDigest(r.documents); setFrDate(r.date); })
      .catch(() => setFrDigest([]))
      .finally(() => setFrLoading(false));

    // Load saved trackers from localStorage
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const loaded: SavedTracker[] = JSON.parse(raw);
        const top = loaded.slice(0, 5);
        setTrackers(top);
        // Fetch FR data for each tracker topic
        top.forEach(async (t) => {
          try {
            const res = await federalRegister.search(t.topic, 3);
            setFrByTracker(prev => ({ ...prev, [t.id]: res.documents }));
          } catch { /* ignore */ }
        });
      }
    } catch { /* ignore */ }
  }, []);

  const STANCE_COLOR: Record<string, string> = {
    support: "#2D7A4F", oppose: "#c53030", neutral: "#555", watching: "#1A6BA0",
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

        {/* Federal Register Daily Digest — full width under scoreboard */}
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
                const typeLabel = doc.type === "PRORULE" ? "PROP RULE" : doc.type === "PRESDOCU" ? "EXEC ORDER" : doc.type;
                return (
                  <a key={doc.document_number} href={doc.html_url} target="_blank" rel="noreferrer"
                     style={{ textDecoration: "none" }}>
                    <div className="card p-3" style={{ cursor: "pointer" }}>
                      <div className="flex items-start gap-3">
                        {/* RBS score */}
                        <div style={{ flexShrink: 0, textAlign: "center", minWidth: "44px" }}>
                          <div className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.7rem", lineHeight: 1 }}>{doc.rbs}</div>
                          <div className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.45rem" }}>RBS</div>
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
                            {doc.comments_close_on && (
                              <span className="font-pixel" style={{ color: "#856404", fontSize: "0.5rem" }}>
                                ● COMMENT BY {doc.comments_close_on}
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

          {/* Tracked Topics */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-pixel text-xs" style={{ color: "var(--accent)" }}>📡 TRACKED TOPICS</h2>
              <Link href="/track" className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>MANAGE ▶</Link>
            </div>

            {trackers.length === 0
              ? <EmptyState icon="📡" msg="No topics tracked yet." action="/track" actionLabel="TRACK A TOPIC" />
              : (
                <div className="flex flex-col gap-2">
                  {trackers.map((t) => {
                    const isExpanded = expandedId === t.id;
                    const allBills   = t.last_result
                      ? [...(t.last_result.federal_bills ?? []), ...(t.last_result.state_bills ?? [])]
                      : [];
                    const frDocs     = frByTracker[t.id] ?? null;

                    return (
                      <div key={t.id} className="card p-3 flex flex-col gap-2">
                        {/* Header */}
                        <div className="flex items-center gap-2 flex-wrap">
                          {/* Live pulse */}
                          <span style={{ display: "inline-block", width: 7, height: 7,
                            borderRadius: "50%", background: "#2D7A4F", flexShrink: 0,
                            animation: "pulse 2s ease-in-out infinite" }} />

                          {/* Topic */}
                          <span className="font-pixel text-xs flex-1 truncate"
                                style={{ color: "var(--text)", fontSize: "0.6rem" }}>
                            {t.topic.toUpperCase()}
                          </span>

                          {/* State badge */}
                          {t.state && (
                            <span className="font-pixel text-xs px-1"
                                  style={{ background: "var(--primary)", color: "var(--bg)",
                                    border: "2px solid var(--border)", fontSize: "0.5rem" }}>
                              {t.state}
                            </span>
                          )}

                          {/* NEW count — clickable */}
                          {t.new_count > 0 && (
                            <button
                              onClick={() => setExpandedId(isExpanded ? null : t.id)}
                              className="font-pixel text-xs px-2 py-0"
                              style={{ background: "#c53030", color: "#fff",
                                border: "none", cursor: "pointer", fontSize: "0.5rem" }}>
                              🆕 {t.new_count} NEW ▼
                            </button>
                          )}

                          {/* Expand toggle (when no new count) */}
                          {t.new_count === 0 && allBills.length > 0 && (
                            <button
                              onClick={() => setExpandedId(isExpanded ? null : t.id)}
                              className="font-pixel text-xs px-2 py-0"
                              style={{ border: "2px solid var(--border)", color: "var(--text-muted)",
                                background: "transparent", cursor: "pointer", fontSize: "0.5rem" }}>
                              {isExpanded ? "▲" : "▼"}
                            </button>
                          )}
                        </div>

                        {/* Stats row */}
                        {t.last_result && (
                          <div className="flex gap-3 flex-wrap">
                            {(t.last_result.total_federal ?? 0) > 0 && (
                              <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                                🏛️ {t.last_result.total_federal} federal
                              </span>
                            )}
                            {(t.last_result.total_state ?? 0) > 0 && (
                              <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                                🗺️ {t.last_result.total_state} state
                              </span>
                            )}
                            {frDocs === null && (
                              <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                                ● loading FR...
                              </span>
                            )}
                            {frDocs && frDocs.length > 0 && (
                              <span className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.5rem" }}>
                                📰 {frDocs.length} FR docs
                              </span>
                            )}
                          </div>
                        )}

                        {/* Expanded: bills + FR docs */}
                        {isExpanded && (
                          <div className="flex flex-col gap-2 pt-2"
                               style={{ borderTop: "2px dashed var(--border)" }}>

                            {/* Bills */}
                            {allBills.slice(0, 5).map((b: any, i: number) => {
                              const extUrl = b.url ?? b.congress_url ?? b.legiscan_url ?? null;
                              const label  = b.bill_label ?? b.bill_number ?? b.number ?? "—";
                              const title  = (b.title ?? b.description ?? "").slice(0, 80);
                              return (
                                <div key={i} className="flex items-start gap-2 px-2 py-2"
                                     style={{ border: "2px solid var(--border)" }}>
                                  <span className="font-pixel flex-shrink-0"
                                        style={{ color: "var(--accent)", fontSize: "0.5rem", minWidth: "2.5rem" }}>
                                    {label}
                                  </span>
                                  <p className="font-mono flex-1 min-w-0"
                                     style={{ fontSize: "0.6rem", lineHeight: 1.3, color: "var(--text)" }}>
                                    {title}{title.length >= 80 ? "…" : ""}
                                  </p>
                                  {extUrl && (
                                    <a href={extUrl} target="_blank" rel="noreferrer"
                                       className="font-pixel flex-shrink-0"
                                       style={{ color: "var(--accent)", fontSize: "0.5rem" }}
                                       onClick={e => e.stopPropagation()}>
                                      ↗
                                    </a>
                                  )}
                                </div>
                              );
                            })}

                            {/* FR docs for this topic */}
                            {frDocs && frDocs.length > 0 && (
                              <div className="flex flex-col gap-1 pt-1"
                                   style={{ borderTop: "1px dashed var(--border)" }}>
                                <p className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.5rem" }}>
                                  📰 FEDERAL REGISTER
                                </p>
                                {frDocs.map((doc) => (
                                  <a key={doc.document_number} href={doc.html_url}
                                     target="_blank" rel="noreferrer"
                                     style={{ textDecoration: "none" }}>
                                    <div className="flex items-start gap-2 px-2 py-1"
                                         style={{ border: "2px solid var(--border)" }}>
                                      <span className="font-pixel flex-shrink-0"
                                            style={{ color: "var(--accent)", fontSize: "0.5rem", minWidth: "1.8rem" }}>
                                        {doc.rbs}
                                      </span>
                                      <p className="font-mono flex-1 min-w-0"
                                         style={{ fontSize: "0.55rem", lineHeight: 1.3, color: "var(--text)" }}>
                                        {doc.title.slice(0, 70)}{doc.title.length > 70 ? "…" : ""}
                                      </p>
                                      <span className="font-pixel flex-shrink-0"
                                            style={{ color: "var(--accent)", fontSize: "0.5rem" }}>↗</span>
                                    </div>
                                  </a>
                                ))}
                              </div>
                            )}

                            <Link href="/track"
                                  className="font-pixel text-xs text-center pt-1"
                                  style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                              VIEW FULL TRACKER ▶
                            </Link>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )
            }
          </section>
        </div>

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
