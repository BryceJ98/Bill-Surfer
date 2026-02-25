"use client";
import { useState } from "react";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import {
  track as trackApi, docket as docketApi, reports as reportsApi,
  type TrackResult,
} from "@/lib/api";

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"];

export default function TrackPage() {
  const [topic,      setTopic]      = useState("");
  const [state,      setState]      = useState<string>("");
  const [loading,    setLoading]    = useState(false);
  const [result,     setResult]     = useState<TrackResult | null>(null);
  const [error,      setError]      = useState("");
  const [added,      setAdded]      = useState<Set<string>>(new Set());
  const [reporting,  setReporting]  = useState<Set<string>>(new Set());
  const [reported,   setReported]   = useState<Set<string>>(new Set());

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

  async function addToDocket(r: any, isState = false) {
    const billId = String(r.bill_id ?? r.number ?? Math.random());
    try {
      await docketApi.add({
        bill_id:     billId,
        bill_number: String(r.bill_label ?? r.bill_number ?? r.citation ?? billId),
        state:       isState && state ? state : "US",
        title:       String(r.title ?? r.description ?? ""),
      });
      setAdded((s) => new Set([...s, billId]));
    } catch (e: any) {
      if ((e.message ?? "").includes("already")) setAdded((s) => new Set([...s, billId]));
      else alert(e.message);
    }
  }

  async function generateReport(r: any, isState = false) {
    const billId    = String(r.bill_id ?? r.number ?? "");
    const billNum   = String(r.bill_label ?? r.bill_number ?? billId);
    const billState = isState && state ? state : "US";
    const title     = String(r.title ?? r.description ?? "");
    setReporting((s) => new Set([...s, billId]));
    try {
      await reportsApi.create({ bill_id: billId, bill_number: billNum, state: billState, title });
      setReported((s) => new Set([...s, billId]));
    } catch (e: any) { alert(e.message); }
    setReporting((s) => { const n = new Set(s); n.delete(billId); return n; });
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />
      <main className="max-w-5xl mx-auto p-6 flex flex-col gap-6">

        <h1 className="font-pixel text-sm" style={{ color: "var(--accent)" }}>📡 TRACK TOPIC</h1>
        <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
          Enter a policy topic to see all relevant federal bills, CRS research reports, and state
          legislation — with an AI-generated legislative landscape summary.
        </p>

        {/* Search form */}
        <div className="card p-5 flex flex-col gap-3">
          <div className="flex gap-2 flex-wrap">
            <input
              className="input-arcade flex-1"
              placeholder="e.g. climate change, healthcare, AI regulation, housing affordability..."
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
              {STATES.map((s) => <option key={s} value={s}>{s} + Federal</option>)}
            </select>
          </div>
          <button className="btn-arcade font-pixel text-xs" onClick={doTrack}
                  disabled={loading || !topic.trim()}>
            {loading ? "⟳ TRACKING..." : "▶ TRACK THIS TOPIC"}
          </button>
          {error && (
            <p className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ {error}</p>
          )}
        </div>

        {/* Loading state */}
        {loading && (
          <div className="card p-6 flex flex-col gap-3 items-center">
            <p className="font-pixel text-xs animate-pulse" style={{ color: "var(--accent)" }}>
              ⟳ FETCHING BILLS + CRS REPORTS + AI ANALYSIS...
            </p>
            <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
              Searching Congress.gov and LegiScan, then running AI landscape analysis.
              This may take 15–30 seconds.
            </p>
          </div>
        )}

        {result && (
          <div className="flex flex-col gap-6">

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

            {/* CRS Research Reports */}
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
                              style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)", fontSize: "0.55rem" }}>
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
                            {r.type && (
                              <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                                {r.type}
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
                    const key      = r.bill_id ?? r.number ?? i;
                    const isAdded  = added.has(String(key));
                    const isRep    = reporting.has(String(key));
                    const isDoneRep = reported.has(String(key));
                    const detailHref = r.congress && r.bill_type && r.bill_number
                      ? `/bill/US/${r.congress}-${r.bill_type}-${r.bill_number}` : null;
                    return (
                      <BillCard key={i}
                        bill={r} label={r.bill_label ?? r.number ?? "—"}
                        badge="US" detailHref={detailHref}
                        extUrl={r.url ?? r.congress_url ?? null}
                        isAdded={isAdded} isReporting={isRep} isReported={isDoneRep}
                        onAdd={() => addToDocket(r, false)}
                        onReport={() => generateReport(r, false)} />
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
                    const key       = r.bill_id ?? i;
                    const isAdded   = added.has(String(key));
                    const isRep     = reporting.has(String(key));
                    const isDoneRep = reported.has(String(key));
                    const detailHref = r.bill_id ? `/bill/${state}/${r.bill_id}` : null;
                    return (
                      <BillCard key={i}
                        bill={r} label={r.bill_number ?? "—"}
                        badge={state} detailHref={detailHref}
                        extUrl={r.url ?? r.legiscan_url ?? null}
                        isAdded={isAdded} isReporting={isRep} isReported={isDoneRep}
                        onAdd={() => addToDocket(r, true)}
                        onReport={() => generateReport(r, true)} />
                    );
                  })}
                </div>
              </section>
            )}

            {result.federal_bills.length === 0 && result.state_bills.length === 0 && (
              <div className="card p-8 flex flex-col items-center gap-3">
                <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
                  NO BILLS FOUND FOR THIS TOPIC
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

// ---------------------------------------------------------------------------
// Shared bill card component
// ---------------------------------------------------------------------------
function BillCard({
  bill, label, badge, detailHref, extUrl,
  isAdded, isReporting, isReported,
  onAdd, onReport,
}: {
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
              style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)", fontSize: "0.6rem" }}>
          {badge}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>{label}</span>
            {detailHref && (
              <span className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>▶ DETAILS</span>
            )}
            {extUrl && (
              <a href={extUrl} target="_blank" rel="noreferrer"
                 className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}
                 onClick={(e) => e.stopPropagation()}>↗ VIEW</a>
            )}
          </div>
          <p className="font-mono text-sm leading-snug">{bill.title ?? bill.description ?? "—"}</p>
          {(bill.status || bill.status_date) && (
            <p className="font-mono text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              {bill.status}{bill.status_date ? ` — ${bill.status_date}` : ""}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          <button onClick={onAdd} disabled={isAdded}
                  className="font-pixel text-xs px-2 py-1"
                  style={{
                    border: "2px solid",
                    borderColor: isAdded ? "#2D7A4F" : "var(--accent)",
                    background:  isAdded ? "#2D7A4F" : "transparent",
                    color:       isAdded ? "#fff"    : "var(--accent)",
                    fontSize: "0.55rem",
                  }}>
            {isAdded ? "✓ TRACKED" : "+ DOCKET"}
          </button>
          <button onClick={onReport} disabled={isReporting || isReported}
                  className="font-pixel text-xs px-2 py-1"
                  style={{
                    border: "2px solid",
                    borderColor: isReported ? "#2D7A4F" : "var(--border)",
                    background:  isReported ? "#2D7A4F" : "transparent",
                    color:       isReported ? "#fff"    : "var(--text)",
                    fontSize: "0.55rem",
                  }}>
            {isReported ? "✓ QUEUED" : isReporting ? "..." : "📊 REPORT"}
          </button>
        </div>
      </div>
    </div>
  );
}
