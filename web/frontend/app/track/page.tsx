"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import {
  track as trackApi, docket as docketApi, reports as reportsApi,
  type TrackResult,
} from "@/lib/api";

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"];
const AUTO_REFRESH_MS = 30 * 60 * 1000; // 30 minutes
const STORAGE_KEY = "bill_surfer_trackers";

interface SavedTracker {
  id:            string;
  topic:         string;
  state?:        string;
  created_at:    string;
  last_checked:  string;
  last_bill_ids: string[];
  new_count:     number;
  last_result?:  TrackResult;
}

function uuid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function billKey(b: any): string {
  return String(b.bill_id ?? b.number ?? b.bill_number ?? "");
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins   = Math.floor(diffMs / 60000);
  if (mins < 1)  return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function TrackPage() {
  const [topic,      setTopic]      = useState("");
  const [state,      setState]      = useState<string>("");
  const [loading,    setLoading]    = useState(false);
  const [result,     setResult]     = useState<TrackResult | null>(null);
  const [error,      setError]      = useState("");
  const [added,      setAdded]      = useState<Set<string>>(new Set());
  const [reporting,  setReporting]  = useState<Set<string>>(new Set());
  const [reported,   setReported]   = useState<Set<string>>(new Set());

  // Saved live trackers
  const [trackers,       setTrackers]       = useState<SavedTracker[]>([]);
  const [refreshingId,   setRefreshingId]   = useState<string | null>(null);
  const [expandedId,     setExpandedId]     = useState<string | null>(null);
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load trackers from localStorage ────────────────────────────────────
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setTrackers(JSON.parse(raw));
    } catch { /* ignore */ }
  }, []);

  function saveTrackers(updated: SavedTracker[]) {
    setTrackers(updated);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(updated)); } catch { /* ignore */ }
  }

  // ── Auto-refresh stale trackers on mount and every 30 min ──────────────
  const refreshTracker = useCallback(async (tracker: SavedTracker, silent = false) => {
    if (!silent) setRefreshingId(tracker.id);
    try {
      const data = await trackApi.topic({
        topic: tracker.topic,
        state: tracker.state || undefined,
        include_crs: true,
      });
      const newIds   = [...data.federal_bills, ...data.state_bills].map(billKey).filter(Boolean);
      const prevIds  = new Set(tracker.last_bill_ids);
      const newCount = newIds.filter(id => id && !prevIds.has(id)).length;

      const updated: SavedTracker = {
        ...tracker,
        last_checked:  new Date().toISOString(),
        last_bill_ids: newIds,
        new_count:     newCount,
        last_result:   data,
      };
      setTrackers(prev => {
        const next = prev.map(t => t.id === tracker.id ? updated : t);
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* ignore */ }
        return next;
      });
    } catch { /* silent fail */ }
    if (!silent) setRefreshingId(null);
  }, []);

  useEffect(() => {
    // Auto-refresh any tracker last checked > 30 min ago
    trackers.forEach(t => {
      const stale = Date.now() - new Date(t.last_checked).getTime() > AUTO_REFRESH_MS;
      if (stale) refreshTracker(t, true);
    });

    autoRefreshRef.current = setInterval(() => {
      setTrackers(prev => {
        prev.forEach(t => refreshTracker(t, true));
        return prev;
      });
    }, AUTO_REFRESH_MS);

    return () => {
      if (autoRefreshRef.current) clearInterval(autoRefreshRef.current);
    };
  }, []); // run once on mount

  // ── One-shot search ──────────────────────────────────────────────────────
  async function doTrack() {
    if (!topic.trim() || loading) return;
    setError(""); setLoading(true); setResult(null);
    try {
      const data = await trackApi.topic({
        topic:       topic.trim(),
        state:       state || undefined,
        include_crs: true,
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  function saveTracker() {
    if (!result) return;
    const allIds = [...result.federal_bills, ...result.state_bills].map(billKey).filter(Boolean);
    const tracker: SavedTracker = {
      id:            uuid(),
      topic:         result.topic,
      state:         state || undefined,
      created_at:    new Date().toISOString(),
      last_checked:  new Date().toISOString(),
      last_bill_ids: allIds,
      new_count:     0,
      last_result:   result,
    };
    saveTrackers([tracker, ...trackers]);
  }

  function deleteTracker(id: string) {
    saveTrackers(trackers.filter(t => t.id !== id));
    if (expandedId === id) setExpandedId(null);
  }

  // ── Docket / report helpers ──────────────────────────────────────────────
  async function addToDocket(r: any, billState = "US") {
    const billId = String(r.bill_id ?? r.number ?? Math.random());
    try {
      await docketApi.add({
        bill_id:     billId,
        bill_number: String(r.bill_label ?? r.bill_number ?? r.citation ?? billId),
        state:       billState,
        title:       String(r.title ?? r.description ?? ""),
      });
      setAdded(s => new Set([...s, billId]));
    } catch (e: any) {
      if ((e.message ?? "").includes("already")) setAdded(s => new Set([...s, billId]));
      else alert(e.message);
    }
  }

  async function generateReport(r: any, billState = "US") {
    const billId  = String(r.bill_id ?? r.number ?? "");
    const billNum = String(r.bill_label ?? r.bill_number ?? billId);
    const title   = String(r.title ?? r.description ?? "");
    setReporting(s => new Set([...s, billId]));
    try {
      await reportsApi.create({ bill_id: billId, bill_number: billNum, state: billState, title });
      setReported(s => new Set([...s, billId]));
    } catch (e: any) { alert(e.message); }
    setReporting(s => { const n = new Set(s); n.delete(billId); return n; });
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />
      <main className="max-w-5xl mx-auto p-6 flex flex-col gap-6">

        <h1 className="font-pixel text-sm" style={{ color: "var(--accent)" }}>📡 TRACK TOPIC</h1>

        {/* ── Live Trackers ─────────────────────────────────────────────── */}
        {trackers.length > 0 && (
          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <p className="font-pixel text-xs" style={{ color: "var(--accent)" }}>
                ⚡ LIVE TRACKERS ({trackers.length})
              </p>
              <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                Auto-refreshes every 30 min
              </p>
            </div>

            {trackers.map(t => {
              const isExpanded    = expandedId === t.id;
              const isRefreshing  = refreshingId === t.id;
              const trackerResult = t.last_result;
              const prevIds       = new Set(t.last_bill_ids);

              return (
                <div key={t.id} className="card p-4 flex flex-col gap-3">
                  {/* Header row */}
                  <div className="flex items-center gap-3 flex-wrap">
                    {/* Live pulse */}
                    <span className="font-pixel text-xs flex items-center gap-1"
                          style={{ color: "#2D7A4F", fontSize: "0.55rem" }}>
                      <span style={{ display: "inline-block", width: 8, height: 8,
                        borderRadius: "50%", background: "#2D7A4F",
                        animation: "pulse 2s ease-in-out infinite" }} />
                      LIVE
                    </span>

                    {/* Topic */}
                    <span className="font-pixel text-xs flex-1"
                          style={{ color: "var(--text)" }}>
                      {t.topic.toUpperCase()}
                    </span>

                    {/* State badge */}
                    {t.state && (
                      <span className="font-pixel text-xs px-2 py-0"
                            style={{ background: "var(--primary)", color: "var(--bg)",
                              border: "2px solid var(--border)", fontSize: "0.55rem" }}>
                        {t.state}
                      </span>
                    )}

                    {/* NEW count badge */}
                    {t.new_count > 0 && (
                      <span className="font-pixel text-xs px-2 py-1"
                            style={{ background: "#c53030", color: "#fff", fontSize: "0.55rem" }}>
                        🆕 {t.new_count} NEW
                      </span>
                    )}

                    {/* Last checked */}
                    <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                      {isRefreshing ? "⟳ CHECKING..." : `checked ${timeAgo(t.last_checked)}`}
                    </span>

                    {/* Actions */}
                    <div className="flex gap-1">
                      <button onClick={() => refreshTracker(t)}
                              disabled={isRefreshing}
                              className="font-pixel text-xs px-2 py-1"
                              style={{ border: "2px solid var(--border)", color: "var(--text)",
                                fontSize: "0.55rem" }}>
                        ⟳ REFRESH
                      </button>
                      <button onClick={() => setExpandedId(isExpanded ? null : t.id)}
                              className="font-pixel text-xs px-2 py-1"
                              style={{ border: "2px solid var(--accent)", color: "var(--accent)",
                                fontSize: "0.55rem" }}>
                        {isExpanded ? "▲ HIDE" : "▼ VIEW"}
                      </button>
                      <button onClick={() => deleteTracker(t.id)}
                              className="font-pixel text-xs px-2 py-1"
                              style={{ border: "2px solid #c53030", color: "#c53030",
                                fontSize: "0.55rem" }}>
                        ✕
                      </button>
                    </div>
                  </div>

                  {/* Stats row */}
                  {trackerResult && (
                    <div className="flex gap-4 flex-wrap">
                      {trackerResult.total_federal > 0 && (
                        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                          🏛️ {trackerResult.total_federal} federal
                        </span>
                      )}
                      {trackerResult.total_state > 0 && (
                        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                          🗺️ {trackerResult.total_state} state
                        </span>
                      )}
                      {trackerResult.total_crs > 0 && (
                        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                          📚 {trackerResult.total_crs} CRS reports
                        </span>
                      )}
                    </div>
                  )}

                  {/* Expanded bill list */}
                  {isExpanded && trackerResult && (
                    <div className="flex flex-col gap-2 pt-2"
                         style={{ borderTop: "2px dashed var(--border)" }}>

                      {/* AI Summary */}
                      {trackerResult.ai_summary && (
                        <div className="p-3" style={{ background: "var(--bg)", border: "2px solid var(--border)" }}>
                          <p className="font-pixel mb-1" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>
                            🤖 LANDSCAPE
                          </p>
                          <p className="font-mono text-xs leading-relaxed"
                             style={{ color: "var(--text)" }}>
                            {trackerResult.ai_summary.slice(0, 400)}
                            {trackerResult.ai_summary.length > 400 ? "..." : ""}
                          </p>
                        </div>
                      )}

                      {/* Bills — NEW ones first */}
                      {[...trackerResult.federal_bills, ...trackerResult.state_bills].map((r, i) => {
                        const key      = billKey(r);
                        const isNew    = key && !prevIds.has(key);
                        const isAdded  = added.has(key);
                        const billSt   = r.state && r.state !== "US" ? r.state : (t.state || "US");
                        return (
                          <div key={i} className="p-3 flex items-start gap-2"
                               style={{ border: isNew ? "2px solid #c53030" : "2px solid var(--border)",
                                 background: isNew ? "rgba(197,48,48,0.05)" : "transparent" }}>
                            {isNew && (
                              <span className="font-pixel flex-shrink-0"
                                    style={{ background: "#c53030", color: "#fff",
                                      fontSize: "0.45rem", padding: "2px 4px" }}>
                                NEW
                              </span>
                            )}
                            <div className="flex-1 min-w-0">
                              <p className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>
                                {r.bill_label ?? r.bill_number ?? "—"}
                              </p>
                              <p className="font-mono text-xs leading-snug"
                                 style={{ color: "var(--text)" }}>
                                {(r.title ?? r.description ?? "").slice(0, 120)}
                              </p>
                            </div>
                            <button onClick={() => addToDocket(r, billSt)}
                                    disabled={isAdded}
                                    className="font-pixel flex-shrink-0 px-2 py-1"
                                    style={{ border: "2px solid",
                                      borderColor: isAdded ? "#2D7A4F" : "var(--accent)",
                                      background:  isAdded ? "#2D7A4F" : "transparent",
                                      color:       isAdded ? "#fff"    : "var(--accent)",
                                      fontSize: "0.5rem" }}>
                              {isAdded ? "✓" : "+ DOCKET"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        )}

        {/* ── New search ────────────────────────────────────────────────── */}
        <section className="card p-5 flex flex-col gap-3">
          <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
            SEARCH A POLICY TOPIC
          </p>
          <div className="flex gap-2 flex-wrap">
            <input
              className="input-arcade flex-1"
              placeholder="e.g. climate change, AI regulation, healthcare, housing..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") doTrack(); }}
            />
            <select
              className="input-arcade"
              style={{ width: "auto", minWidth: "8rem" }}
              value={state}
              onChange={(e) => setState(e.target.value)}
            >
              <option value="">Federal only</option>
              {STATES.map(s => <option key={s} value={s}>{s} + Federal</option>)}
            </select>
          </div>
          <button className="btn-arcade font-pixel text-xs" onClick={doTrack}
                  disabled={loading || !topic.trim()}>
            {loading ? "⟳ SEARCHING..." : "▶ TRACK THIS TOPIC"}
          </button>
          {error && (
            <p className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ {error}</p>
          )}
        </section>

        {/* ── Loading ───────────────────────────────────────────────────── */}
        {loading && (
          <div className="card p-6 flex flex-col gap-3 items-center">
            <p className="font-pixel text-xs animate-pulse" style={{ color: "var(--accent)" }}>
              ⟳ FETCHING BILLS + CRS REPORTS + AI ANALYSIS...
            </p>
            <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
              Searching Congress.gov and LegiScan, then running AI landscape analysis.
            </p>
          </div>
        )}

        {/* ── Results ───────────────────────────────────────────────────── */}
        {result && (
          <div className="flex flex-col gap-6">

            {/* Save as live tracker CTA */}
            <div className="flex items-center justify-between flex-wrap gap-3 p-4 card"
                 style={{ borderColor: "#2D7A4F" }}>
              <div>
                <p className="font-pixel text-xs" style={{ color: "#2D7A4F" }}>
                  ⚡ SAVE AS LIVE TRACKER
                </p>
                <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                  Auto-checks every 30 min for new legislation. NEW bills are highlighted.
                </p>
              </div>
              <button className="btn-arcade font-pixel text-xs"
                      style={{ borderColor: "#2D7A4F", boxShadow: "3px 3px 0 #2D7A4F" }}
                      onClick={saveTracker}>
                📌 SAVE TRACKER
              </button>
            </div>

            {/* AI Summary */}
            {result.ai_summary && (
              <section className="card p-5">
                <p className="font-pixel text-xs mb-3" style={{ color: "var(--accent)" }}>
                  🤖 AI LEGISLATIVE LANDSCAPE — "{result.topic}"
                </p>
                <div className="font-mono text-sm leading-relaxed whitespace-pre-line"
                     style={{ color: "var(--text)" }}>
                  {result.ai_summary}
                </div>
              </section>
            )}

            {/* CRS Reports */}
            {result.crs_reports.length > 0 && (
              <section>
                <p className="font-pixel text-xs mb-2" style={{ color: "var(--accent)" }}>
                  📚 CRS RESEARCH REPORTS ({result.total_crs})
                </p>
                <p className="font-pixel mb-3" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                  Nonpartisan Congressional Research Service background analysis
                </p>
                <div className="flex flex-col gap-2">
                  {result.crs_reports.map((r, i) => (
                    <div key={i} className="card p-4">
                      <div className="flex items-start gap-3">
                        <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
                              style={{ background: "var(--primary)", color: "var(--bg)",
                                border: "2px solid var(--border)", fontSize: "0.55rem" }}>
                          CRS
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-sm leading-snug">{r.title ?? "—"}</p>
                          <div className="flex gap-3 mt-1 flex-wrap">
                            {r.reportNumber && (
                              <span className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>
                                {r.reportNumber}
                              </span>
                            )}
                            {r.date && (
                              <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                                {r.date}
                              </span>
                            )}
                          </div>
                          {r.detail?.summary && (
                            <p className="font-mono text-xs mt-2 leading-snug"
                               style={{ color: "var(--text-muted)" }}>
                              {r.detail.summary.slice(0, 300)}{r.detail.summary.length > 300 ? "..." : ""}
                            </p>
                          )}
                          {r.url && (
                            <a href={r.url} target="_blank" rel="noreferrer"
                               className="font-pixel mt-1 inline-block"
                               style={{ color: "var(--accent)", fontSize: "0.55rem" }}>
                              ↗ FULL REPORT
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Federal Bills */}
            {result.federal_bills.length > 0 && (
              <section>
                <p className="font-pixel text-xs mb-2" style={{ color: "var(--accent)" }}>
                  🏛️ FEDERAL BILLS ({result.total_federal})
                </p>
                <div className="flex flex-col gap-2">
                  {result.federal_bills.map((r, i) => {
                    const key       = billKey(r) || String(i);
                    const isAdded   = added.has(key);
                    const isRep     = reporting.has(key);
                    const isDoneRep = reported.has(key);
                    const detailHref = r.congress && r.bill_type && r.bill_number
                      ? `/bill/US/${r.congress}-${r.bill_type}-${r.bill_number}` : null;
                    return (
                      <BillCard key={i}
                        bill={r} label={r.bill_label ?? r.number ?? "—"}
                        badge={String(r.congress ?? "US")} detailHref={detailHref}
                        extUrl={r.url ?? r.congress_url ?? null}
                        isAdded={isAdded} isReporting={isRep} isReported={isDoneRep}
                        onAdd={() => addToDocket(r, "US")}
                        onReport={() => generateReport(r, "US")} />
                    );
                  })}
                </div>
              </section>
            )}

            {/* State Bills */}
            {result.state_bills.length > 0 && (
              <section>
                <p className="font-pixel text-xs mb-2" style={{ color: "var(--accent)" }}>
                  🗺️ STATE BILLS — {state} ({result.total_state})
                </p>
                <div className="flex flex-col gap-2">
                  {result.state_bills.map((r, i) => {
                    const key       = billKey(r) || String(i);
                    const isAdded   = added.has(key);
                    const isRep     = reporting.has(key);
                    const isDoneRep = reported.has(key);
                    const detailHref = r.bill_id ? `/bill/${state}/${r.bill_id}` : null;
                    return (
                      <BillCard key={i}
                        bill={r} label={r.bill_number ?? "—"}
                        badge={state} detailHref={detailHref}
                        extUrl={r.url ?? r.legiscan_url ?? null}
                        isAdded={isAdded} isReporting={isRep} isReported={isDoneRep}
                        onAdd={() => addToDocket(r, state)}
                        onReport={() => generateReport(r, state)} />
                    );
                  })}
                </div>
              </section>
            )}

            {result.federal_bills.length === 0 && result.state_bills.length === 0 && (
              <div className="card p-8 flex flex-col items-center gap-3">
                <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
                  NO BILLS FOUND
                </p>
                <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>
                  Try different keywords or a broader topic.
                </p>
              </div>
            )}
          </div>
        )}

      </main>
      <BodhiChat />
    </div>
  );
}

// ── Bill card ───────────────────────────────────────────────────────────────
function BillCard({ bill, label, badge, detailHref, extUrl,
  isAdded, isReporting, isReported, onAdd, onReport }: {
  bill: any; label: string; badge: string;
  detailHref: string | null; extUrl: string | null;
  isAdded: boolean; isReporting: boolean; isReported: boolean;
  onAdd: () => void; onReport: () => void;
}) {
  return (
    <div className="card p-4"
         style={{ cursor: detailHref ? "pointer" : "default" }}
         onClick={() => detailHref && window.location.assign(detailHref)}>
      <div className="flex items-start gap-3">
        <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
              style={{ background: "var(--primary)", color: "var(--bg)",
                border: "2px solid var(--border)", fontSize: "0.6rem" }}>
          {badge}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>
              {label}
            </span>
            {detailHref && (
              <span className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>
                ▶ DETAILS
              </span>
            )}
            {extUrl && (
              <a href={extUrl} target="_blank" rel="noreferrer"
                 className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}
                 onClick={e => e.stopPropagation()}>↗ VIEW</a>
            )}
          </div>
          <p className="font-mono text-sm leading-snug">{bill.title ?? bill.description ?? "—"}</p>
          {(bill.status || bill.status_date) && (
            <p className="font-mono text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              {bill.status}{bill.status_date ? ` — ${bill.status_date}` : ""}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-1 flex-shrink-0" onClick={e => e.stopPropagation()}>
          <button onClick={onAdd} disabled={isAdded}
                  className="font-pixel text-xs px-2 py-1"
                  style={{ border: "2px solid",
                    borderColor: isAdded ? "#2D7A4F" : "var(--accent)",
                    background:  isAdded ? "#2D7A4F" : "transparent",
                    color:       isAdded ? "#fff"    : "var(--accent)",
                    fontSize: "0.55rem" }}>
            {isAdded ? "✓ TRACKED" : "+ DOCKET"}
          </button>
          <button onClick={onReport} disabled={isReporting || isReported}
                  className="font-pixel text-xs px-2 py-1"
                  style={{ border: "2px solid",
                    borderColor: isReported ? "#2D7A4F" : "var(--border)",
                    background:  isReported ? "#2D7A4F" : "transparent",
                    color:       isReported ? "#fff"    : "var(--text)",
                    fontSize: "0.55rem" }}>
            {isReported ? "✓ QUEUED" : isReporting ? "..." : "📊 REPORT"}
          </button>
        </div>
      </div>
    </div>
  );
}
