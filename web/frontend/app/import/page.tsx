"use client";
import { useState, useRef, useCallback } from "react";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import CsvChat from "@/components/CsvChat";
import LoadingBar from "@/components/LoadingBar";
import {
  csvImport,
  explain as explainApi,
  reports as reportsApi,
  type CsvUploadResult,
  type BulkImportResult,
  type CsvStatsResult,
  type ExplainResult,
} from "@/lib/api";

// ── Column mapping types ───────────────────────────────────────────────────
type ColumnMap = {
  bill_id:     string;
  state:       string;
  title:       string;
  bill_number: string;
  notes:       string;
  stance:      string;
  tags:        string;
};

const BILL_FIELDS: { key: keyof ColumnMap; label: string; required: boolean; guessFrom: string[] }[] = [
  { key: "bill_id",     label: "Bill ID",     required: true,  guessFrom: ["bill_id", "billid", "id"] },
  { key: "state",       label: "State",       required: true,  guessFrom: ["state", "jurisdiction"] },
  { key: "title",       label: "Title",       required: false, guessFrom: ["title", "description", "name"] },
  { key: "bill_number", label: "Bill Number", required: false, guessFrom: ["bill_number", "bill_no", "number"] },
  { key: "notes",       label: "Notes",       required: false, guessFrom: ["notes", "note", "comments"] },
  { key: "stance",      label: "Stance",      required: false, guessFrom: ["stance", "position"] },
  { key: "tags",        label: "Tags",        required: false, guessFrom: ["tags", "tag", "labels"] },
];

function autoGuess(columns: string[], guessFrom: string[]): string {
  const lower = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
  for (const hint of guessFrom) {
    const match = columns.find(c => lower(c).includes(lower(hint)) || lower(hint).includes(lower(c)));
    if (match) return match;
  }
  return "";
}

function applyMap(row: Record<string, string>, map: ColumnMap, field: keyof ColumnMap): string {
  const col = map[field];
  return col ? (row[col] ?? "").trim() : "";
}

// ── Phase type ─────────────────────────────────────────────────────────────
type Phase = "idle" | "uploading" | "mapping" | "results";

// ── Per-row bill state ─────────────────────────────────────────────────────
interface BillRowState {
  explain:   ExplainResult | null;
  expanding: boolean;
  reporting: boolean;
  reported:  boolean;
}

export default function ImportPage() {
  const [phase,        setPhase]        = useState<Phase>("idle");
  const [dragOver,     setDragOver]     = useState(false);
  const [uploadResult, setUploadResult] = useState<CsvUploadResult | null>(null);
  const [uploadError,  setUploadError]  = useState<string | null>(null);
  const [columnMap,    setColumnMap]    = useState<ColumnMap>({ bill_id: "", state: "", title: "", bill_number: "", notes: "", stance: "", tags: "" });

  // Bill mode result states
  const [bulkResult,   setBulkResult]   = useState<BulkImportResult | null>(null);
  const [bulkLoading,  setBulkLoading]  = useState(false);
  const [landscapeText,setLandscapeText]= useState<string | null>(null);
  const [landscapeLoading, setLandscapeLoading] = useState(false);
  const [billRows,     setBillRows]     = useState<BillRowState[]>([]);

  // Generic mode result states
  const [statsResult,  setStatsResult]  = useState<CsvStatsResult | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Upload handler ────────────────────────────────────────────────────────
  async function handleFile(file: File) {
    if (!file.name.match(/\.csv$/i)) {
      setUploadError("Please upload a .csv file.");
      return;
    }
    setUploadError(null);
    setPhase("uploading");
    try {
      const result = await csvImport.upload(file);
      setUploadResult(result);
      if (result.mode === "bill") {
        // Auto-guess column mapping
        const guessed: ColumnMap = { bill_id: "", state: "", title: "", bill_number: "", notes: "", stance: "", tags: "" };
        for (const f of BILL_FIELDS) {
          guessed[f.key] = autoGuess(result.columns, f.guessFrom);
        }
        setColumnMap(guessed);
        setBillRows(result.rows.slice(0, 50).map(() => ({ explain: null, expanding: false, reporting: false, reported: false })));
        setPhase("mapping");
      } else {
        setPhase("results");
      }
    } catch (err: any) {
      setUploadError(err.message ?? "Upload failed");
      setPhase("idle");
    }
  }

  // ── Drop zone ─────────────────────────────────────────────────────────────
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => setDragOver(false), []);

  function reset() {
    setPhase("idle");
    setUploadResult(null);
    setUploadError(null);
    setBulkResult(null);
    setLandscapeText(null);
    setStatsResult(null);
    setBillRows([]);
    setColumnMap({ bill_id: "", state: "", title: "", bill_number: "", notes: "", stance: "", tags: "" });
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  // ── Bill mode actions ─────────────────────────────────────────────────────
  async function doBulkImport() {
    if (!uploadResult) return;
    setBulkLoading(true);
    try {
      const rows = uploadResult.rows.map(row => ({
        bill_id:     applyMap(row, columnMap, "bill_id"),
        state:       applyMap(row, columnMap, "state"),
        title:       applyMap(row, columnMap, "title") || undefined,
        bill_number: applyMap(row, columnMap, "bill_number") || undefined,
        notes:       applyMap(row, columnMap, "notes") || undefined,
        tags:        applyMap(row, columnMap, "tags") ? [applyMap(row, columnMap, "tags")] : [],
      })).filter(r => r.bill_id && r.state);
      const result = await csvImport.docketBulk(rows);
      setBulkResult(result);
    } catch (err: any) {
      setBulkResult({ imported: 0, skipped: 0, errors: [err.message] });
    } finally {
      setBulkLoading(false);
    }
  }

  async function doLandscape() {
    if (!uploadResult) return;
    setLandscapeLoading(true);
    try {
      const result = await csvImport.landscape({
        raw_csv:   uploadResult.raw_csv,
        row_count: uploadResult.row_count,
        columns:   uploadResult.columns,
      });
      setLandscapeText(result.ai_summary);
    } catch (err: any) {
      setLandscapeText(`Error: ${err.message}`);
    } finally {
      setLandscapeLoading(false);
    }
  }

  async function doExplain(idx: number) {
    if (!uploadResult) return;
    const row = uploadResult.rows[idx];
    setBillRows(prev => prev.map((r, i) => i === idx ? { ...r, expanding: true } : r));
    try {
      const result = await explainApi.bill({
        title:       applyMap(row, columnMap, "title") || applyMap(row, columnMap, "bill_id"),
        state:       applyMap(row, columnMap, "state") || "US",
        bill_number: applyMap(row, columnMap, "bill_number") || undefined,
        bill_id:     applyMap(row, columnMap, "bill_id") || undefined,
        status:      row["status"] || undefined,
      });
      setBillRows(prev => prev.map((r, i) => i === idx ? { ...r, explain: result, expanding: false } : r));
    } catch {
      setBillRows(prev => prev.map((r, i) => i === idx ? { ...r, expanding: false } : r));
    }
  }

  async function doReport(idx: number) {
    if (!uploadResult) return;
    const row = uploadResult.rows[idx];
    setBillRows(prev => prev.map((r, i) => i === idx ? { ...r, reporting: true } : r));
    try {
      await reportsApi.create({
        bill_id:     applyMap(row, columnMap, "bill_id") || `csv-${idx}`,
        bill_number: applyMap(row, columnMap, "bill_number") || applyMap(row, columnMap, "bill_id"),
        state:       applyMap(row, columnMap, "state") || "US",
        title:       applyMap(row, columnMap, "title") || applyMap(row, columnMap, "bill_id"),
      });
      setBillRows(prev => prev.map((r, i) => i === idx ? { ...r, reporting: false, reported: true } : r));
    } catch {
      setBillRows(prev => prev.map((r, i) => i === idx ? { ...r, reporting: false } : r));
    }
  }

  // ── Generic mode actions ──────────────────────────────────────────────────
  async function doStats() {
    if (!uploadResult) return;
    setStatsLoading(true);
    try {
      const result = await csvImport.stats({
        raw_csv:   uploadResult.raw_csv,
        row_count: uploadResult.row_count,
        columns:   uploadResult.columns,
      });
      setStatsResult(result);
    } catch (err: any) {
      setStatsResult({ abstract: `Error: ${err.message}`, stats_table: [], insights: [] });
    } finally {
      setStatsLoading(false);
    }
  }

  // ── Shared styles ─────────────────────────────────────────────────────────
  const card: React.CSSProperties = {
    border:     "2px solid var(--border)",
    background: "var(--card)",
    padding:    "16px",
    marginBottom: "16px",
  };

  const tileBtn: React.CSSProperties = {
    background: "var(--primary)",
    color:      "#F4F9FC",
    border:     "2px solid var(--border)",
    padding:    "8px 16px",
    cursor:     "pointer",
    fontFamily: "monospace",
    fontSize:   "12px",
  };

  const mutedText: React.CSSProperties = {
    color:    "var(--muted)",
    fontSize: "12px",
    fontFamily: "monospace",
  };

  // ──────────────────────────────────────────────────────────────────────────
  // RENDER
  // ──────────────────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <NavBar />
      <div style={{ maxWidth: "900px", margin: "0 auto", padding: "24px 16px" }}>
        <h1 className="font-pixel text-xs" style={{ color: "var(--border)", marginBottom: "4px", fontSize: "18px" }}>
          ↑ BYOD — BRING YOUR OWN DATA
        </h1>
        <p style={{ ...mutedText, marginBottom: "24px" }}>
          Upload a CSV. Bill Surfer detects the format and unlocks the right tools.
        </p>

        {/* ── IDLE: Drop Zone ──────────────────────────────────────────── */}
        {phase === "idle" && (
          <div style={card}>
            <div
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border:         `3px dashed ${dragOver ? "var(--border)" : "var(--muted)"}`,
                background:     dragOver ? "rgba(var(--border-rgb, 0,0,0),0.05)" : "transparent",
                padding:        "48px 24px",
                textAlign:      "center",
                cursor:         "pointer",
                transition:     "all 0.15s",
              }}
            >
              <div style={{ fontSize: "48px", marginBottom: "12px" }}>↑</div>
              <p className="font-pixel text-xs" style={{ color: "var(--text)", marginBottom: "8px" }}>
                DRAG & DROP CSV HERE
              </p>
              <p style={{ ...mutedText }}>or click to browse — max 2 MB, 1,000 rows</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                style={{ display: "none" }}
                onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
              />
            </div>

            {uploadError && (
              <div style={{ marginTop: "12px", padding: "10px", background: "#2d0000", border: "2px solid #ff4444", color: "#ff4444", fontFamily: "monospace", fontSize: "13px" }}>
                ⚠ {uploadError}
              </div>
            )}

            <div style={{ marginTop: "16px", display: "flex", gap: "12px", alignItems: "center" }}>
              <span style={mutedText}>Not sure what format to use?</span>
              <a
                href={csvImport.templateUrl()}
                download
                className="font-pixel text-xs"
                style={{ color: "var(--border)", textDecoration: "underline" }}
              >
                ↓ DOWNLOAD TEMPLATE
              </a>
            </div>
          </div>
        )}

        {/* ── UPLOADING: Themed loader ─────────────────────────────────── */}
        {phase === "uploading" && (
          <div style={{ ...card, display: "flex", justifyContent: "center", alignItems: "center", padding: "64px" }}>
            <LoadingBar label="PARSING CSV..." />
          </div>
        )}

        {/* ── MAPPING: Column mapping screen ───────────────────────────── */}
        {phase === "mapping" && uploadResult && (
          <div style={card}>
            <h2 className="font-pixel text-xs" style={{ color: "var(--border)", fontSize: "14px", marginBottom: "4px" }}>
              🗂 MAP YOUR COLUMNS
            </h2>
            <p style={{ ...mutedText, marginBottom: "20px" }}>
              Match your CSV columns to Bill Surfer fields. Required fields are marked with *.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
              {BILL_FIELDS.map(f => (
                <div key={f.key} style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                  <label
                    style={{ ...mutedText, width: "120px", flexShrink: 0, color: f.required ? "var(--text)" : "var(--muted)" }}
                  >
                    {f.label}{f.required ? " *" : ""}
                  </label>
                  <select
                    value={columnMap[f.key]}
                    onChange={e => setColumnMap(prev => ({ ...prev, [f.key]: e.target.value }))}
                    style={{
                      background:  "var(--surface)",
                      color:       "var(--text)",
                      border:      `1px solid ${columnMap[f.key] ? "var(--border)" : "var(--muted)"}`,
                      padding:     "4px 8px",
                      fontFamily:  "monospace",
                      fontSize:    "12px",
                      minWidth:    "220px",
                    }}
                  >
                    <option value="">— none —</option>
                    {uploadResult.columns.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  {columnMap[f.key] && (
                    <span style={{ ...mutedText, fontSize: "11px" }}>
                      sample: {String(uploadResult.rows[0]?.[columnMap[f.key]] ?? "").slice(0, 30)}
                    </span>
                  )}
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              <button onClick={reset} style={{ ...tileBtn, background: "var(--surface)", color: "var(--text)" }}>
                ◀ BACK
              </button>
              <button
                onClick={() => setPhase("results")}
                disabled={!columnMap.bill_id || !columnMap.state}
                style={{
                  ...tileBtn,
                  opacity: (!columnMap.bill_id || !columnMap.state) ? 0.4 : 1,
                  cursor:  (!columnMap.bill_id || !columnMap.state) ? "not-allowed" : "pointer",
                }}
              >
                ▶ CONFIRM MAPPING
              </button>
            </div>

            <div style={{ marginTop: "20px", paddingTop: "12px", borderTop: "1px solid var(--muted)" }}>
              <button
                onClick={() => { if (uploadResult) { setUploadResult({ ...uploadResult, mode: "generic" }); setPhase("results"); } }}
                style={{ background: "transparent", border: "none", cursor: "pointer", ...mutedText, textDecoration: "underline" }}
              >
                This isn&apos;t bill data → analyze as generic CSV
              </button>
            </div>
          </div>
        )}

        {/* ── RESULTS ─────────────────────────────────────────────────────── */}
        {phase === "results" && uploadResult && (
          <>
            {/* Stats bar */}
            <div style={{ ...card, display: "flex", flexWrap: "wrap", gap: "16px", alignItems: "center" }}>
              <span className="font-pixel text-xs" style={{ color: "var(--border)" }}>
                {uploadResult.mode === "bill" ? "🏛 BILL DATA" : "📊 GENERIC DATA"}
              </span>
              <span style={mutedText}>● {uploadResult.row_count} rows</span>
              <span style={{ ...mutedText, maxWidth: "400px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {uploadResult.columns.join(", ")}
              </span>
              <div style={{ marginLeft: "auto" }}>
                <button onClick={reset} style={{ ...tileBtn, background: "var(--surface)", color: "var(--text)" }}>
                  ↑ UPLOAD NEW FILE
                </button>
              </div>
            </div>

            {/* Preview table */}
            <div style={{ ...card, overflowX: "auto" }}>
              <h3 className="font-pixel text-xs" style={{ color: "var(--muted)", marginBottom: "10px", fontSize: "11px" }}>
                PREVIEW (first 5 rows)
              </h3>
              <table style={{ borderCollapse: "collapse", fontSize: "11px", fontFamily: "monospace", width: "100%" }}>
                <thead>
                  <tr>
                    {uploadResult.columns.map(c => (
                      <th key={c} style={{ padding: "4px 8px", border: "1px solid var(--muted)", background: "var(--surface)", color: "var(--text)", textAlign: "left", whiteSpace: "nowrap" }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {uploadResult.rows.slice(0, 5).map((row, i) => (
                    <tr key={i}>
                      {uploadResult.columns.map(c => (
                        <td key={c} style={{ padding: "4px 8px", border: "1px solid var(--muted)", color: "var(--muted)", maxWidth: "180px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {row[c] ?? ""}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* ── BILL MODE tools ──────────────────────────────────────── */}
            {uploadResult.mode === "bill" && (
              <>
                {/* Bulk Import tile */}
                <div style={card}>
                  <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
                    <div style={{ flex: 1 }}>
                      <h3 className="font-pixel text-xs" style={{ color: "var(--text)", marginBottom: "6px" }}>
                        📋 BULK IMPORT TO DOCKET
                      </h3>
                      <p style={mutedText}>
                        Upsert all rows from your CSV into your personal docket. Re-importing is idempotent — duplicates are skipped.
                      </p>
                    </div>
                    <button onClick={doBulkImport} disabled={bulkLoading} style={{ ...tileBtn, flexShrink: 0 }}>
                      {bulkLoading ? "IMPORTING..." : "▶ IMPORT"}
                    </button>
                  </div>
                  {bulkResult && (
                    <div style={{ marginTop: "12px", padding: "10px", background: "var(--surface)", border: "1px solid var(--border)", fontFamily: "monospace", fontSize: "12px" }}>
                      ✓ {bulkResult.imported} imported · {bulkResult.skipped} skipped
                      {bulkResult.errors.length > 0 && (
                        <div style={{ color: "#ff4444", marginTop: "6px" }}>
                          {bulkResult.errors.slice(0, 5).map((e, i) => <div key={i}>{e}</div>)}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* AI Landscape tile */}
                <div style={card}>
                  <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
                    <div style={{ flex: 1 }}>
                      <h3 className="font-pixel text-xs" style={{ color: "var(--text)", marginBottom: "6px" }}>
                        🤖 AI LANDSCAPE
                      </h3>
                      <p style={mutedText}>
                        AI-powered nonpartisan summary of the legislative landscape in your dataset.
                      </p>
                    </div>
                    <button onClick={doLandscape} disabled={landscapeLoading} style={{ ...tileBtn, flexShrink: 0 }}>
                      {landscapeLoading ? "ANALYZING..." : "▶ ANALYZE"}
                    </button>
                  </div>
                  {landscapeText && (
                    <div style={{ marginTop: "12px", padding: "12px", background: "var(--surface)", border: "1px solid var(--border)", fontSize: "13px", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                      {landscapeText}
                    </div>
                  )}
                </div>

                {/* Per-bill rows */}
                <div style={card}>
                  <h3 className="font-pixel text-xs" style={{ color: "var(--muted)", marginBottom: "12px", fontSize: "11px" }}>
                    PER-BILL TOOLS (first {Math.min(50, uploadResult.rows.length)} rows)
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {uploadResult.rows.slice(0, 50).map((row, i) => {
                      const rowState = billRows[i] ?? { explain: null, expanding: false, reporting: false, reported: false };
                      const billId    = applyMap(row, columnMap, "bill_id");
                      const title     = applyMap(row, columnMap, "title") || billId;
                      const state     = applyMap(row, columnMap, "state");
                      return (
                        <div key={i} style={{ border: "1px solid var(--muted)", background: "var(--surface)", padding: "10px 12px" }}>
                          <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                            <span style={{ ...mutedText, flex: 1, minWidth: "180px" }}>
                              <strong>{billId}</strong>{state ? ` · ${state}` : ""} — {title.slice(0, 60)}{title.length > 60 ? "…" : ""}
                            </span>
                            <button
                              onClick={() => doExplain(i)}
                              disabled={rowState.expanding}
                              style={{ ...tileBtn, padding: "4px 10px", background: "var(--surface)", color: "var(--text)", border: "1px solid var(--border)" }}
                            >
                              {rowState.expanding ? "..." : "💡 EXPLAIN"}
                            </button>
                            <button
                              onClick={() => doReport(i)}
                              disabled={rowState.reporting || rowState.reported}
                              style={{ ...tileBtn, padding: "4px 10px", background: "var(--surface)", color: rowState.reported ? "var(--muted)" : "var(--text)", border: "1px solid var(--border)" }}
                            >
                              {rowState.reporting ? "..." : rowState.reported ? "✓ QUEUED" : "📊 REPORT"}
                            </button>
                          </div>
                          {rowState.explain && (
                            <div style={{ marginTop: "10px", padding: "10px", background: "var(--card)", border: "1px solid var(--border)", fontSize: "12px", lineHeight: 1.5 }}>
                              <p style={{ marginBottom: "6px" }}><strong>Summary:</strong> {rowState.explain.summary}</p>
                              {rowState.explain.key_points?.length > 0 && (
                                <ul style={{ margin: "0 0 6px 16px", padding: 0 }}>
                                  {rowState.explain.key_points.map((kp, j) => <li key={j}>{kp}</li>)}
                                </ul>
                              )}
                              {rowState.explain.who_is_affected && (
                                <p><strong>Who&apos;s affected:</strong> {rowState.explain.who_is_affected}</p>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* CsvChat */}
                <div style={{ marginBottom: "16px" }}>
                  <CsvChat rawCsv={uploadResult.raw_csv} rowCount={uploadResult.row_count} columns={uploadResult.columns} />
                </div>
              </>
            )}

            {/* ── GENERIC MODE tools ───────────────────────────────────── */}
            {uploadResult.mode === "generic" && (
              <>
                {/* Summary Stats tile */}
                <div style={card}>
                  <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
                    <div style={{ flex: 1 }}>
                      <h3 className="font-pixel text-xs" style={{ color: "var(--text)", marginBottom: "6px" }}>
                        📊 SUMMARY STATS
                      </h3>
                      <p style={mutedText}>AI-generated statistics table, abstract, and insights from your data.</p>
                    </div>
                    <button onClick={doStats} disabled={statsLoading} style={{ ...tileBtn, flexShrink: 0 }}>
                      {statsLoading ? "ANALYZING..." : "▶ ANALYZE"}
                    </button>
                  </div>

                  {statsResult && (
                    <div style={{ marginTop: "16px" }}>
                      {/* Abstract */}
                      <div style={{ padding: "12px", background: "var(--surface)", border: "1px solid var(--border)", fontSize: "13px", lineHeight: 1.6, marginBottom: "12px" }}>
                        {statsResult.abstract}
                      </div>

                      {/* Stats table */}
                      {statsResult.stats_table?.length > 0 && (
                        <table style={{ borderCollapse: "collapse", fontSize: "12px", fontFamily: "monospace", width: "100%", marginBottom: "12px" }}>
                          <thead>
                            <tr>
                              <th style={{ padding: "6px 10px", border: "1px solid var(--muted)", background: "var(--surface)", textAlign: "left" }}>METRIC</th>
                              <th style={{ padding: "6px 10px", border: "1px solid var(--muted)", background: "var(--surface)", textAlign: "left" }}>VALUE</th>
                            </tr>
                          </thead>
                          <tbody>
                            {statsResult.stats_table.map((row, i) => (
                              <tr key={i}>
                                <td style={{ padding: "5px 10px", border: "1px solid var(--muted)", color: "var(--muted)" }}>{row.metric}</td>
                                <td style={{ padding: "5px 10px", border: "1px solid var(--muted)", color: "var(--text)" }}>{row.value}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}

                      {/* Insights */}
                      {statsResult.insights?.length > 0 && (
                        <div style={{ padding: "12px", background: "var(--surface)", border: "1px solid var(--border)" }}>
                          <p className="font-pixel text-xs" style={{ color: "var(--muted)", marginBottom: "8px", fontSize: "10px" }}>
                            💡 AI INSIGHTS
                          </p>
                          <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "13px", lineHeight: 1.7 }}>
                            {statsResult.insights.map((ins, i) => <li key={i}>{ins}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* CsvChat */}
                <div style={{ marginBottom: "16px" }}>
                  <CsvChat rawCsv={uploadResult.raw_csv} rowCount={uploadResult.row_count} columns={uploadResult.columns} />
                </div>
              </>
            )}
          </>
        )}
      </div>
      <BodhiChat />
    </div>
  );
}
