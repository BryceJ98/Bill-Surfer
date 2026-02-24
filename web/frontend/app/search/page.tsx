"use client";
import { useState } from "react";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import { search as searchApi, docket as docketApi, exportCsv } from "@/lib/api";

type SearchType = "federal-bills" | "nominations" | "treaties" | "state-bills";

const PAGE_SIZE = 20;

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"];

const PLACEHOLDERS: Record<SearchType, string> = {
  "federal-bills": "e.g. infrastructure, healthcare...",
  "nominations":   "e.g. secretary, ambassador, judge...",
  "treaties":      "e.g. trade, extradition, defense... (optional)",
  "state-bills":   "e.g. minimum wage, climate, education...",
};

export default function SearchPage() {
  const [searchType,  setSearchType]  = useState<SearchType>("federal-bills");
  const [query,       setQuery]       = useState("");
  const [state,       setState]       = useState("CA");
  const [congress,    setCongress]    = useState<number | "">("");
  const [results,     setResults]     = useState<any[]>([]);
  const [total,       setTotal]       = useState(0);
  const [page,        setPage]        = useState(0);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState("");
  const [exportError, setExportError] = useState("");
  const [added,       setAdded]       = useState<Set<string>>(new Set());

  function switchTab(t: SearchType) {
    setSearchType(t);
    setResults([]);
    setTotal(0);
    setPage(0);
    setError("");
    setExportError("");
  }

  async function doSearch(pageNum = 0) {
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
        </div>

        {/* Search form */}
        <div className="card p-4 flex flex-col gap-3">
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
            {(searchType === "federal-bills" || searchType === "nominations" || searchType === "treaties") && (
              <input className="input-arcade w-28"
                     type="number" placeholder="Congress #"
                     value={congress}
                     onChange={(e) => setCongress(e.target.value ? Number(e.target.value) : "")}
                     onKeyDown={handleKeyDown} />
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
        </div>

        {/* Results */}
        {results.length > 0 && (
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
              const key        = r.bill_id ?? r.citation ?? r.number ?? i;
              const isAdded    = added.has(String(key));
              const extUrl     = getBillUrl(r);
              const label      = getBillLabel(r);
              const detailHref = getDetailHref(r);
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
