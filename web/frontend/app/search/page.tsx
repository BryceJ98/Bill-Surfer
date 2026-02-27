"use client";
import { useState } from "react";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import { search as searchApi, docket as docketApi, exportCsv, explain as explainApi, federalRegister, type ExplainResult, type FrDocument } from "@/lib/api";

type SearchType = "federal-bills" | "nominations" | "treaties" | "state-bills" | "agent" | "federal-register";

const PAGE_SIZE = 20;
const CURRENT_CONGRESS = 119;

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"];

// Valid congress ranges based on Congress.gov data availability
const CONGRESS_RANGE: Record<SearchType, { min: number } | null> = {
  "federal-bills":     { min: 93  },   // Congress.gov bills: 93rd (1973) onward
  "nominations":       { min: 100 },   // nominations: 100th (1987) onward
  "treaties":          { min: 90  },   // treaties: 90th (1967) onward
  "state-bills":       null,           // uses year filter, not congress
  "agent":             null,           // AI agent — no congress filter
  "federal-register":  null,           // keyword only, no congress
};

function ordinal(n: number): string {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${n}th`;
  const mod10 = n % 10;
  if (mod10 === 1) return `${n}st`;
  if (mod10 === 2) return `${n}nd`;
  if (mod10 === 3) return `${n}rd`;
  return `${n}th`;
}

function congressLabel(n: number): string {
  const start = 1789 + (n - 1) * 2;
  return `${ordinal(n)} (${start}–${String(start + 1).slice(-2)})`;
}

const PLACEHOLDERS: Record<SearchType, string> = {
  "federal-bills":    "e.g. infrastructure, healthcare...",
  "nominations":      "e.g. secretary, ambassador, judge...",
  "treaties":         "e.g. Japan, trade, extradition, defense... (optional)",
  "state-bills":      "e.g. minimum wage, climate, education...",
  "agent":            "",  // agent has its own input
  "federal-register": "e.g. EPA emissions, FDA food safety, immigration...",
};

export default function SearchPage() {
  const [searchType,    setSearchType]    = useState<SearchType>("federal-bills");
  const [query,         setQuery]         = useState("");
  const [state,         setState]         = useState("CA");
  const [congress,      setCongress]      = useState<number | "">("");
  const [results,       setResults]       = useState<any[]>([]);
  const [total,         setTotal]         = useState(0);
  const [page,          setPage]          = useState(0);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState("");
  const [exportError,   setExportError]   = useState("");
  const [added,         setAdded]         = useState<Set<string>>(new Set());
  // Agent search state
  const [agentQuery,    setAgentQuery]    = useState("");
  const [agentLoading,  setAgentLoading]  = useState(false);
  const [agentResult,   setAgentResult]   = useState<{ bills: any[]; explanation: string; searches: string[] } | null>(null);
  const [agentError,    setAgentError]    = useState("");
  // Plain-English explain state
  const [explaining,    setExplaining]    = useState<Set<string>>(new Set());
  const [explanations,  setExplanations]  = useState<Map<string, ExplainResult>>(new Map());
  // Federal Register search state
  const [frResults,     setFrResults]     = useState<FrDocument[]>([]);
  const [frTotal,       setFrTotal]       = useState(0);
  const [frLoading,     setFrLoading]     = useState(false);
  const [frError,       setFrError]       = useState("");

  function switchTab(t: SearchType) {
    setSearchType(t);
    setResults([]);
    setTotal(0);
    setPage(0);
    setError("");
    setExportError("");
    setAgentError("");
    setFrResults([]);
    setFrTotal(0);
    setFrError("");
  }

  async function doAgentSearch() {
    if (!agentQuery.trim() || agentLoading) return;
    setAgentError(""); setAgentLoading(true); setAgentResult(null);
    try {
      const data = await searchApi.agent(agentQuery.trim());
      setAgentResult({ bills: data.bills, explanation: data.explanation, searches: data.searches });
    } catch (e: any) { setAgentError(e.message); }
    setAgentLoading(false);
  }

  async function doSearch(pageNum = 0) {
    if (searchType === "federal-register") { doFrSearch(); return; }
    setError(""); setLoading(true); setResults([]);
    try {
      let data: any;
      const cong   = congress !== "" ? Number(congress) : undefined;
      const offset = pageNum * PAGE_SIZE;
      if      (searchType === "federal-bills") data = await searchApi.federalBills(query, cong, offset || undefined);
      else if (searchType === "nominations")   data = await searchApi.nominations(query || undefined, cong, offset || undefined);
      else if (searchType === "treaties")      data = await searchApi.treaties(cong, query || undefined, offset || undefined);
      else if (searchType === "state-bills")   data = await searchApi.stateBills(query, state, undefined, offset || undefined);

      const list = data?.bills ?? data?.nominations ?? data?.treaties ?? data?.results ?? [];
      setResults(Array.isArray(list) ? list : []);
      setTotal(data?.total ?? data?.count ?? (Array.isArray(list) ? list.length : 0));
      setPage(pageNum);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function doFrSearch() {
    if (!query.trim() || frLoading) return;
    setFrError(""); setFrLoading(true); setFrResults([]);
    try {
      const data = await federalRegister.search(query.trim(), 20);
      setFrResults(data.documents);
      setFrTotal(data.count);
    } catch (e: any) { setFrError(e.message); }
    setFrLoading(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") doSearch(0);
  }

  async function addToDocket(r: any) {
    const billId = String(r.bill_id ?? r.number ?? r.citation ?? Math.random());
    try {
      await docketApi.add({
        bill_id:     billId,
        bill_number: String(r.bill_number ?? r.bill_label ?? r.citation ?? r.number ?? billId),
        state:       String(r.state ?? (searchType === "state-bills" ? state : "US")),
        title:       String(r.title ?? r.description ?? r.topic ?? ""),
      });
      setAdded((s) => new Set([...s, billId]));
    } catch (e: any) {
      if (e.message.includes("already")) setAdded((s) => new Set([...s, billId]));
      else alert(e.message);
    }
  }

  async function explainBill(r: any, key: string) {
    if (explanations.has(key) || explaining.has(key)) return;
    setExplaining((s) => new Set([...s, key]));
    try {
      const isFederal = searchType === "federal-bills";
      const result = await explainApi.bill({
        title:           String(r.title ?? r.description ?? ""),
        state:           String(r.state ?? (isFederal ? "US" : state)),
        bill_number:     String(r.bill_label ?? r.bill_number ?? r.citation ?? ""),
        bill_id:         String(r.bill_id ?? ""),
        status:          String(r.status ?? ""),
        // Federal enrichment: let backend fetch CRS summary
        congress:        isFederal ? (r.congress ?? undefined)     : undefined,
        bill_type:       isFederal ? (r.bill_type ?? undefined)    : undefined,
        bill_number_int: isFederal ? (r.bill_number ?? undefined)  : undefined,
      });
      setExplanations((m) => new Map([...m, [key, result]]));
    } catch (e: any) { alert(`Explain failed: ${e.message}`); }
    setExplaining((s) => { const n = new Set(s); n.delete(key); return n; });
  }

  async function doExport() {
    setExportError("");
    try {
      await exportCsv({
        export_type: searchType,
        query:       query || undefined,
        state:       searchType === "state-bills" ? state : undefined,
        congress:    congress !== "" ? Number(congress) : undefined,
      });
    } catch (e: any) {
      setExportError(e.message ?? "Export failed");
    }
  }

  function getBillUrl(r: any): string | null {
    return r.url ?? r.congress_url ?? r.legiscan_url ?? null;
  }

  function getBillLabel(r: any): string {
    return r.bill_label ?? r.bill_number ?? r.citation ?? r.number ?? "—";
  }

  function getDetailHref(r: any): string | null {
    if (searchType === "federal-bills" && r.congress && r.bill_type && r.bill_number) {
      return `/bill/US/${r.congress}-${r.bill_type}-${r.bill_number}`;
    }
    if (searchType === "state-bills" && r.bill_id) {
      return `/bill/${state}/${r.bill_id}`;
    }
    return null;
  }

  const totalPages  = total > 0 ? Math.ceil(total / PAGE_SIZE) : 0;
  const hasPrev     = page > 0;
  const hasNext     = results.length === PAGE_SIZE && (page + 1) * PAGE_SIZE < total;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />
      <main className="max-w-5xl mx-auto p-6 flex flex-col gap-6">

        <h1 className="font-pixel text-sm" style={{ color: "var(--accent)" }}>🔍 SEARCH</h1>

        {/* Search type tabs */}
        <div className="flex flex-wrap gap-2">
          {(["federal-bills","nominations","treaties","state-bills"] as SearchType[]).map((t) => (
            <button key={t} onClick={() => switchTab(t)}
                    className="font-pixel text-xs px-3 py-2"
                    style={{
                      border:     "3px solid",
                      borderColor: searchType === t ? "var(--accent)" : "var(--border)",
                      background:  searchType === t ? "var(--accent)" : "transparent",
                      color:       searchType === t ? "var(--bg)"     : "var(--text)",
                      boxShadow:   searchType === t ? "3px 3px 0 var(--border)" : "none",
                      fontSize: "0.65rem",
                    }}>
              {searchType === t ? "▶ " : ""}{t.toUpperCase().replace(/-/g," ")}
            </button>
          ))}
          {/* Federal Register tab */}
          <button onClick={() => switchTab("federal-register")}
                  className="font-pixel text-xs px-3 py-2"
                  style={{
                    border:     "3px solid",
                    borderColor: searchType === "federal-register" ? "var(--accent)" : "var(--border)",
                    background:  searchType === "federal-register" ? "var(--accent)" : "transparent",
                    color:       searchType === "federal-register" ? "var(--bg)"     : "var(--text)",
                    boxShadow:   searchType === "federal-register" ? "3px 3px 0 var(--border)" : "none",
                    fontSize: "0.65rem",
                  }}>
            {searchType === "federal-register" ? "▶ " : ""}📰 FED REGISTER
          </button>
          {/* AI Search tab — distinct style */}
          <button onClick={() => switchTab("agent")}
                  className="font-pixel text-xs px-3 py-2"
                  style={{
                    border:     "3px solid",
                    borderColor: searchType === "agent" ? "var(--border)" : "var(--border)",
                    background:  searchType === "agent" ? "var(--border)" : "transparent",
                    color:       searchType === "agent" ? "var(--bg)"     : "var(--border)",
                    boxShadow:   searchType === "agent" ? "3px 3px 0 var(--accent)" : "none",
                    fontSize: "0.65rem",
                  }}>
            {searchType === "agent" ? "▶ " : ""}🤖 AI SEARCH
          </button>
        </div>

        {/* ── Agent search UI ─────────────────────────────────────── */}
        {searchType === "agent" && (
          <div className="flex flex-col gap-4">
            <div className="card p-5 flex flex-col gap-3">
              <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                DESCRIBE WHAT YOU'RE LOOKING FOR IN PLAIN ENGLISH
              </p>
              <textarea
                className="input-arcade"
                rows={3}
                style={{ resize: "vertical", fontFamily: "inherit" }}
                placeholder={`e.g. "Find the CHIPS Act"\n"Senate bills restricting social media for minors"\n"California legislation on wildfire insurance from 2024"`}
                value={agentQuery}
                onChange={(e) => setAgentQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) doAgentSearch(); }}
              />
              <button className="btn-arcade font-pixel text-xs" onClick={doAgentSearch}
                      disabled={agentLoading || !agentQuery.trim()}>
                {agentLoading ? "🤖 AGENT SEARCHING..." : "🤖 RUN AGENT SEARCH"}
              </button>
              <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                The agent runs multiple searches across congress numbers and keyword variations — may take 15-30 seconds.
                Uses your configured AI model + Congress API key.
              </p>
            </div>

            {agentError && (
              <p className="font-pixel text-xs p-3" style={{ background: "#fff0f0", color: "#c53030", border: "2px solid #c53030" }}>
                ⚠ {agentError}
              </p>
            )}

            {agentLoading && (
              <div className="card p-5 flex flex-col gap-2">
                <p className="font-pixel text-xs animate-pulse" style={{ color: "var(--accent)" }}>
                  🤖 AGENT IS SEARCHING...
                </p>
                <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                  Running targeted searches across multiple congresses and keyword variations.
                </p>
              </div>
            )}

            {agentResult && (
              <div className="flex flex-col gap-3">
                {/* Searches run */}
                {agentResult.searches.length > 0 && (
                  <div className="p-3" style={{ background: "var(--bg-card)", border: "2px dashed var(--border)" }}>
                    <p className="font-pixel mb-1" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>SEARCHES RUN:</p>
                    <div className="flex flex-wrap gap-1">
                      {agentResult.searches.map((s, i) => (
                        <span key={i} className="font-pixel px-2 py-1"
                              style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)", fontSize: "0.5rem" }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI explanation */}
                {agentResult.explanation && (
                  <div className="p-4" style={{ background: "var(--bg-card)", border: "3px solid var(--border)", borderLeft: "6px solid var(--border)" }}>
                    <p className="font-pixel mb-1" style={{ color: "var(--border)", fontSize: "0.55rem" }}>🤖 AGENT SUMMARY</p>
                    <p className="font-mono text-sm leading-relaxed" style={{ color: "var(--text)" }}>
                      {agentResult.explanation}
                    </p>
                  </div>
                )}

                {/* Result count */}
                <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
                  {agentResult.bills.length} BILLS FOUND
                </p>

                {/* Bill cards — same format as regular search */}
                {agentResult.bills.length === 0 ? (
                  <div className="card p-6 flex flex-col items-center gap-2">
                    <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>NO BILLS FOUND</p>
                    <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>
                      Try rephrasing your query or adding more context.
                    </p>
                  </div>
                ) : (
                  agentResult.bills.map((r, i) => {
                    const key     = r.bill_id ?? r.citation ?? i;
                    const isAdded = added.has(String(key));
                    const extUrl  = r.url ?? r.congress_url ?? null;
                    const label   = r.bill_label ?? r.bill_number ?? r.citation ?? "—";
                    const detailHref = (r.congress && r.bill_type && r.bill_number)
                      ? `/bill/US/${r.congress}-${r.bill_type}-${r.bill_number}`
                      : (r.bill_id && r.state && r.state !== "US")
                        ? `/bill/${r.state}/${r.bill_id}`
                        : null;
                    return (
                      <div key={i} className="card p-4 flex items-start gap-3"
                           style={{ cursor: detailHref ? "pointer" : "default" }}
                           onClick={() => detailHref && window.location.assign(detailHref)}>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <span className="font-pixel text-xs px-2 py-0"
                                  style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)", fontSize: "0.6rem" }}>
                              {r.state ?? r.congress ?? "US"}
                            </span>
                            <span className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>{label}</span>
                            {detailHref && (
                              <span className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>▶ DETAILS</span>
                            )}
                            {extUrl && (
                              <a href={extUrl} target="_blank" rel="noreferrer"
                                 className="font-pixel text-xs" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}
                                 onClick={(e) => e.stopPropagation()}>↗ VIEW</a>
                            )}
                          </div>
                          <p className="font-mono text-sm leading-snug">{r.title ?? r.description ?? "—"}</p>
                          {(r.status || r.status_date) && (
                            <p className="font-mono text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                              {r.status}{r.status_date ? ` — ${r.status_date}` : ""}
                            </p>
                          )}
                        </div>
                        <button onClick={(e) => { e.stopPropagation(); addToDocket(r); }}
                                disabled={isAdded}
                                className="font-pixel text-xs px-3 py-2 flex-shrink-0"
                                style={{
                                  border:     "3px solid",
                                  borderColor: isAdded ? "#2D7A4F" : "var(--accent)",
                                  background:  isAdded ? "#2D7A4F" : "transparent",
                                  color:       isAdded ? "#fff"    : "var(--accent)",
                                  boxShadow:   isAdded ? "none"    : "3px 3px 0 var(--accent)",
                                  fontSize: "0.6rem",
                                }}>
                          {isAdded ? "✓ ADDED" : "+ DOCKET"}
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Federal Register search UI ──────────────────────────── */}
        {searchType === "federal-register" && (
          <div className="flex flex-col gap-4">
            <div className="card p-4 flex flex-col gap-3">
              <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                SEARCH RULES, PROPOSED RULES &amp; EXECUTIVE ORDERS
              </p>
              <div className="flex gap-2">
                <input className="input-arcade flex-1"
                       placeholder="e.g. EPA emissions, FDA food safety, tariffs..."
                       value={query}
                       onChange={(e) => setQuery(e.target.value)}
                       onKeyDown={(e) => { if (e.key === "Enter") doFrSearch(); }} />
                <button className="btn-arcade font-pixel text-xs px-4"
                        onClick={doFrSearch} disabled={frLoading || !query.trim()}>
                  {frLoading ? "SEARCHING..." : "▶ SEARCH"}
                </button>
              </div>
              {frError && <p className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ {frError}</p>}
            </div>

            {frResults.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
                  {frResults.length} OF {frTotal} RESULTS — SORTED BY REGULATORY BURDEN SCORE
                </p>
                {frResults.map((doc) => {
                  const typeLabel = doc.type === "PRORULE" ? "PROP RULE" : doc.type === "PRESDOCU" ? "EXEC ORDER" : doc.type;
                  return (
                    <a key={doc.document_number} href={doc.html_url} target="_blank" rel="noreferrer"
                       style={{ textDecoration: "none" }}>
                      <div className="card p-4" style={{ cursor: "pointer" }}>
                        <div className="flex items-start gap-3">
                          {/* RBS score */}
                          <div style={{ flexShrink: 0, textAlign: "center", minWidth: "44px" }}>
                            <div className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.85rem", lineHeight: 1 }}>{doc.rbs}</div>
                            <div className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.45rem" }}>RBS</div>
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <p className="font-mono text-sm leading-snug" style={{ marginBottom: "4px" }}>
                              {doc.title}
                            </p>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-pixel" style={{ background: "var(--primary)", color: "var(--bg)", padding: "1px 5px", fontSize: "0.5rem" }}>
                                {typeLabel}
                              </span>
                              {doc.agency_names?.[0] && (
                                <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                                  {doc.agency_names[0]}
                                </span>
                              )}
                              <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.5rem" }}>
                                {doc.publication_date}
                              </span>
                              {doc.comments_close_on && (
                                <span className="font-pixel" style={{ color: "#856404", fontSize: "0.5rem" }}>
                                  ● COMMENT BY {doc.comments_close_on}
                                </span>
                              )}
                            </div>
                            {doc.abstract && (
                              <p className="font-mono text-xs mt-2" style={{ color: "var(--text-muted)", lineHeight: 1.4 }}>
                                {doc.abstract.slice(0, 200)}{doc.abstract.length > 200 ? "…" : ""}
                              </p>
                            )}
                          </div>

                          <span className="font-pixel flex-shrink-0" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>↗</span>
                        </div>
                      </div>
                    </a>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Regular search form — hidden on agent + FR tabs */}
        {searchType !== "agent" && searchType !== "federal-register" && <div className="card p-4 flex flex-col gap-3">
          <div className="flex gap-2 flex-wrap">
            {/* Keyword input — always shown; optional for treaties */}
            <input className="input-arcade flex-1"
                   placeholder={PLACEHOLDERS[searchType]}
                   value={query}
                   onChange={(e) => setQuery(e.target.value)}
                   onKeyDown={handleKeyDown} />

            {searchType === "state-bills" && (
              <select className="input-arcade w-24"
                      value={state} onChange={(e) => setState(e.target.value)}>
                {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            )}
            {CONGRESS_RANGE[searchType] !== null && (
              <select
                className="input-arcade"
                style={{ width: "auto", minWidth: "10rem" }}
                value={congress}
                onChange={(e) => setCongress(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">All Sessions</option>
                {Array.from(
                  { length: CURRENT_CONGRESS - CONGRESS_RANGE[searchType]!.min + 1 },
                  (_, i) => CURRENT_CONGRESS - i
                ).map((n) => (
                  <option key={n} value={n}>{congressLabel(n)}</option>
                ))}
              </select>
            )}
          </div>

          <div className="flex gap-2">
            <button className="btn-arcade font-pixel text-xs flex-1"
                    onClick={() => doSearch(0)} disabled={loading}>
              {loading ? "SEARCHING..." : "▶ SEARCH"}
            </button>
            {results.length > 0 && (
              <button className="btn-arcade-outline font-pixel text-xs px-4"
                      onClick={doExport}>
                ↓ CSV
              </button>
            )}
          </div>

          {error       && <p className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ {error}</p>}
          {exportError && <p className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ Export failed: {exportError}</p>}
        </div>}

        {/* Results — hidden on agent + FR tabs */}
        {searchType !== "agent" && searchType !== "federal-register" && results.length > 0 && (
          <div className="flex flex-col gap-2">
            {/* Count + pagination */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
                {results.length} OF {total > 0 ? total : "?"} RESULTS
                {totalPages > 1 && ` — PAGE ${page + 1} / ${totalPages}`}
              </p>
              <div className="flex gap-2">
                <button onClick={() => doSearch(page - 1)} disabled={!hasPrev || loading}
                        className="font-pixel text-xs px-3 py-1"
                        style={{
                          border: "2px solid var(--border)",
                          color:  hasPrev ? "var(--text)" : "var(--text-muted)",
                          opacity: hasPrev ? 1 : 0.4,
                        }}>
                  ◀ PREV
                </button>
                <button onClick={() => doSearch(page + 1)} disabled={!hasNext || loading}
                        className="font-pixel text-xs px-3 py-1"
                        style={{
                          border: "2px solid var(--border)",
                          color:  hasNext ? "var(--text)" : "var(--text-muted)",
                          opacity: hasNext ? 1 : 0.4,
                        }}>
                  NEXT ▶
                </button>
              </div>
            </div>

            {/* Result cards */}
            {results.map((r, i) => {
              const key        = String(r.bill_id ?? r.citation ?? r.number ?? i);
              const isAdded    = added.has(key);
              const isExplaining = explaining.has(key);
              const explResult = explanations.get(key);
              const extUrl     = getBillUrl(r);
              const label      = getBillLabel(r);
              const detailHref = getDetailHref(r);
              return (
                <div key={i} className="card p-4"
                     style={{ cursor: detailHref ? "pointer" : "default" }}
                     onClick={() => detailHref && window.location.assign(detailHref)}>
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-pixel text-xs px-2 py-0"
                              style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)", fontSize: "0.6rem" }}>
                          {r.state ?? r.congress ?? "US"}
                        </span>
                        <span className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>
                          {label}
                        </span>
                        {detailHref && (
                          <span className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.55rem" }}>
                            ▶ DETAILS
                          </span>
                        )}
                        {extUrl && (
                          <a href={extUrl} target="_blank" rel="noreferrer"
                             className="font-pixel text-xs"
                             style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}
                             onClick={(e) => e.stopPropagation()}>
                            ↗ VIEW
                          </a>
                        )}
                      </div>
                      <p className="font-mono text-sm leading-snug">{r.title ?? r.description ?? r.topic ?? "—"}</p>
                      {(r.status || r.status_date) && (
                        <p className="font-mono text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                          {r.status}{r.status_date ? ` — ${r.status_date}` : ""}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-col gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => addToDocket(r)}
                              disabled={isAdded}
                              className="font-pixel text-xs px-3 py-2"
                              style={{
                                border:     "3px solid",
                                borderColor: isAdded ? "#2D7A4F" : "var(--accent)",
                                background:  isAdded ? "#2D7A4F" : "transparent",
                                color:       isAdded ? "#fff"    : "var(--accent)",
                                boxShadow:   isAdded ? "none"    : "3px 3px 0 var(--accent)",
                                fontSize: "0.6rem",
                              }}>
                        {isAdded ? "✓ ADDED" : "+ DOCKET"}
                      </button>
                      <button onClick={() => explainBill(r, key)}
                              disabled={isExplaining || !!explResult}
                              className="font-pixel text-xs px-3 py-2"
                              style={{
                                border:     "3px solid",
                                borderColor: explResult ? "var(--border)" : "var(--border)",
                                background:  explResult ? "var(--border)" : "transparent",
                                color:       explResult ? "var(--bg)"    : "var(--text)",
                                fontSize: "0.6rem",
                              }}>
                        {isExplaining ? "⟳ ..." : explResult ? "📖 SHOWN" : "📖 EXPLAIN"}
                      </button>
                    </div>
                  </div>

                  {/* Inline plain-English explanation panel */}
                  {explResult && (
                    <div className="mt-3 p-4 flex flex-col gap-3"
                         style={{ borderTop: "2px dashed var(--border)" }}
                         onClick={(e) => e.stopPropagation()}>
                      <p className="font-pixel text-xs" style={{ color: "var(--border)", fontSize: "0.6rem" }}>
                        📖 PLAIN ENGLISH EXPLANATION
                      </p>
                      <p className="font-mono text-sm leading-relaxed" style={{ color: "var(--text)" }}>
                        {explResult.summary}
                      </p>
                      {explResult.key_points?.length > 0 && (
                        <div>
                          <p className="font-pixel mb-1" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>KEY CHANGES:</p>
                          <ul className="flex flex-col gap-1">
                            {explResult.key_points.map((pt, j) => (
                              <li key={j} className="font-mono text-xs flex gap-2" style={{ color: "var(--text)" }}>
                                <span style={{ color: "var(--accent)" }}>▸</span>{pt}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {explResult.who_is_affected && (
                        <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>
                          <span className="font-pixel" style={{ fontSize: "0.55rem" }}>WHO'S AFFECTED: </span>
                          {explResult.who_is_affected}
                        </p>
                      )}
                      {explResult.notes && (
                        <p className="font-mono text-xs" style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                          {explResult.notes}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Bottom pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 pt-2">
                <button onClick={() => doSearch(page - 1)} disabled={!hasPrev || loading}
                        className="btn-arcade font-pixel text-xs"
                        style={{ opacity: hasPrev ? 1 : 0.4 }}>
                  ◀ PREV PAGE
                </button>
                <span className="font-pixel text-xs" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                  {page + 1} / {totalPages}
                </span>
                <button onClick={() => doSearch(page + 1)} disabled={!hasNext || loading}
                        className="btn-arcade font-pixel text-xs"
                        style={{ opacity: hasNext ? 1 : 0.4 }}>
                  NEXT PAGE ▶
                </button>
              </div>
            )}
          </div>
        )}

      </main>
      <BodhiChat />
    </div>
  );
}
