"use client";
import { useState } from "react";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import { search as searchApi, docket as docketApi, exportCsv } from "@/lib/api";

type SearchType = "federal-bills" | "nominations" | "treaties" | "state-bills";

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"];

export default function SearchPage() {
  const [searchType, setSearchType] = useState<SearchType>("federal-bills");
  const [query,      setQuery]      = useState("");
  const [state,      setState]      = useState("CA");
  const [congress,   setCongress]   = useState<number | "">("");
  const [results,    setResults]    = useState<any[]>([]);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState("");
  const [exportError, setExportError] = useState("");
  const [added,      setAdded]      = useState<Set<string>>(new Set());

  function switchTab(t: SearchType) {
    setSearchType(t);
    setResults([]);   // BUG-002: clear results on tab switch
    setError("");
    setExportError("");
  }

  async function doSearch() {
    setError(""); setLoading(true); setResults([]);
    try {
      let data: any;
      const cong = congress !== "" ? Number(congress) : undefined;
      if      (searchType === "federal-bills")  data = await searchApi.federalBills(query, cong);
      else if (searchType === "nominations")    data = await searchApi.nominations(query || undefined, cong);
      else if (searchType === "treaties")       data = await searchApi.treaties(cong);
      else if (searchType === "state-bills")    data = await searchApi.stateBills(query, state);

      const list = data?.bills ?? data?.nominations ?? data?.treaties ?? data?.results ?? [];
      setResults(Array.isArray(list) ? list : []);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  // BUG-003: Enter key triggers search from any input
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") doSearch();
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

  // BUG-006: show export errors
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

  // BUG-005: get external URL for a result
  function getBillUrl(r: any): string | null {
    return r.url ?? r.congress_url ?? r.legiscan_url ?? null;
  }

  // BUG-004: get bill number/label robustly
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

  const placeholder = searchType === "state-bills"
    ? "e.g. minimum wage, climate, education..."
    : searchType === "treaties" ? "(no query needed for treaties)" : "e.g. infrastructure, healthcare...";

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />
      <main className="max-w-5xl mx-auto p-6 flex flex-col gap-6">

        <h1 className="font-pixel text-sm" style={{ color: "var(--accent)" }}>🔍 SEARCH</h1>

        {/* Search type selector */}
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
              {searchType === t ? "▶ " : ""}{t.toUpperCase().replace("-"," ")}
            </button>
          ))}
        </div>

        {/* Search form */}
        <div className="card p-4 flex flex-col gap-3">
          <div className="flex gap-2 flex-wrap">
            {searchType !== "treaties" && (
              <input className="input-arcade flex-1"
                     placeholder={placeholder}
                     value={query}
                     onChange={(e) => setQuery(e.target.value)}
                     onKeyDown={handleKeyDown} />
            )}
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
                    onClick={doSearch} disabled={loading}>
              {loading ? "SEARCHING..." : "▶ SEARCH"}
            </button>
            {results.length > 0 && (
              <button className="btn-arcade-outline font-pixel text-xs px-4"
                      onClick={doExport}>
                ↓ CSV
              </button>
            )}
          </div>

          {error      && <p className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ {error}</p>}
          {exportError && <p className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ Export failed: {exportError}</p>}
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
              {results.length} RESULTS
            </p>
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
                      {/* BUG-004: show bill label with correct field fallback */}
                      <span className="font-pixel text-xs" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>
                        {label}
                      </span>
                      {/* Detail page link */}
                      {detailHref && (
                        <span className="font-pixel text-xs"
                              style={{ color: "var(--accent)", fontSize: "0.55rem" }}>
                          ▶ DETAILS
                        </span>
                      )}
                      {/* BUG-005: link to external source */}
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
          </div>
        )}

      </main>
      <BodhiChat />
    </div>
  );
}
