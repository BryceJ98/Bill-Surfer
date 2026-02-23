"use client";
import { useEffect, useState } from "react";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import { reports as reportsApi, type Report, type ReportRequest } from "@/lib/api";

const REPORT_TYPES = [
  { value: "policy_impact", label: "POLICY IMPACT" },
  { value: "summary",       label: "SUMMARY"       },
  { value: "vote_analysis", label: "VOTE ANALYSIS" },
  { value: "comparison",    label: "COMPARISON"    },
];

const STATUS_COLOR: Record<string, string> = {
  complete:   "#2D7A4F",
  generating: "#856404",
  error:      "#c53030",
  pending:    "#888",
};

export default function ReportsPage() {
  const [library,    setLibrary]    = useState<Report[]>([]);
  const [showForm,   setShowForm]   = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [polling,    setPolling]    = useState(false);
  const [loadError,  setLoadError]  = useState("");
  const [form, setForm] = useState<ReportRequest & { report_type: string }>({
    bill_id: "", bill_number: "", state: "", title: "", report_type: "policy_impact",
  });

  function loadLibrary() {
    reportsApi.list()
      .then(setLibrary)
      .catch((e: any) => setLoadError(e.message));
  }

  useEffect(() => {
    loadLibrary();
  }, []);

  // Poll while any report is generating
  useEffect(() => {
    const generating = library.some((r) => r.status === "generating" || r.status === "pending");
    if (generating && !polling) {
      setPolling(true);
      const iv = setInterval(loadLibrary, 5000);
      return () => { clearInterval(iv); setPolling(false); };
    }
  }, [library]);

  async function submitReport() {
    setLoading(true);
    try {
      await reportsApi.create(form);
      setShowForm(false);
      loadLibrary();
      setForm({ bill_id: "", bill_number: "", state: "", title: "", report_type: "policy_impact" });
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  }

  async function deleteReport(id: string) {
    if (!confirm("Delete this report?")) return;
    try {
      await reportsApi.remove(id);
      loadLibrary();
    } catch (e: any) {
      alert(`Failed to delete: ${e.message}`);
    }
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />
      <main className="max-w-5xl mx-auto p-6 flex flex-col gap-6">

        {loadError && (
          <p className="font-pixel text-xs p-3" style={{ background: "#c53030", color: "#fff", border: "3px solid #8b0000" }}>
            ⚠ {loadError}
          </p>
        )}

        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="font-pixel text-sm" style={{ color: "var(--accent)" }}>📊 REPORT LIBRARY</h1>
          <button className="btn-arcade font-pixel text-xs" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "✕ CANCEL" : "▶ NEW REPORT"}
          </button>
        </div>

        {/* New report form */}
        {showForm && (
          <div className="card p-5 flex flex-col gap-4">
            <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>GENERATE_NEW_REPORT</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="font-pixel text-xs block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>STATE (US, CA, TX...)</label>
                <input className="input-arcade" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value.toUpperCase() })} placeholder="US" />
              </div>
              <div>
                <label className="font-pixel text-xs block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>BILL NUMBER</label>
                <input className="input-arcade" value={form.bill_number} onChange={(e) => setForm({ ...form, bill_number: e.target.value })} placeholder="HR 1234" />
              </div>
              <div>
                <label className="font-pixel text-xs block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>BILL ID (internal)</label>
                <input className="input-arcade" value={form.bill_id} onChange={(e) => setForm({ ...form, bill_id: e.target.value })} placeholder="us-hr-1234 or LegiScan ID" />
              </div>
              <div>
                <label className="font-pixel text-xs block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>REPORT TITLE</label>
                <input className="input-arcade" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Short description" />
              </div>
            </div>

            {/* Report type */}
            <div>
              <label className="font-pixel text-xs block mb-2" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>REPORT TYPE</label>
              <div className="flex flex-wrap gap-2">
                {REPORT_TYPES.map((t) => (
                  <button key={t.value} onClick={() => setForm({ ...form, report_type: t.value })}
                          className="font-pixel text-xs px-3 py-2"
                          style={{
                            border:     "3px solid",
                            borderColor: form.report_type === t.value ? "var(--accent)" : "var(--border)",
                            background:  form.report_type === t.value ? "var(--accent)" : "transparent",
                            color:       form.report_type === t.value ? "var(--bg)"     : "var(--text)",
                            boxShadow:   form.report_type === t.value ? "3px 3px 0 var(--border)" : "none",
                            fontSize: "0.6rem",
                          }}>
                    {form.report_type === t.value ? "▶ " : ""}{t.label}
                  </button>
                ))}
              </div>
            </div>

            <button className="btn-arcade font-pixel text-xs"
                    onClick={submitReport}
                    disabled={loading || !form.bill_id || !form.state || !form.title}>
              {loading ? "GENERATING..." : "▶ GENERATE REPORT"}
            </button>
            <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
              Report generation runs in the background and may take 30–60 seconds.
            </p>
          </div>
        )}

        {/* Library */}
        {library.length === 0
          ? (
            <div className="card p-10 flex flex-col items-center gap-4">
              <span className="text-4xl">📊</span>
              <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>NO REPORTS YET</p>
              <button className="btn-arcade font-pixel text-xs" onClick={() => setShowForm(true)}>▶ GENERATE FIRST REPORT</button>
            </div>
          )
          : (
            <div className="flex flex-col gap-3">
              {library.map((r) => (
                <div key={r.id} className="card p-4">
                  <div className="flex items-start gap-3 flex-wrap">
                    {/* State badge */}
                    <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
                          style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)" }}>
                      {r.state}
                    </span>

                    {/* Title + meta */}
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-sm">{r.title}</p>
                      <div className="flex flex-wrap gap-3 mt-1">
                        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>{r.bill_number}</span>
                        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>{r.report_type.replace("_"," ").toUpperCase()}</span>
                        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>{r.ai_model?.split("/").pop()?.toUpperCase()}</span>
                        <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>{new Date(r.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    {/* Status + actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="font-pixel text-xs animate-pulse" style={{ color: STATUS_COLOR[r.status], fontSize: "0.6rem" }}>
                        ● {r.status.toUpperCase()}
                      </span>

                      {r.status === "complete" && (
                        <a href={reportsApi.pdfUrl(r.id)}
                           className="btn-arcade-outline font-pixel"
                           style={{ fontSize: "0.6rem", padding: "4px 8px" }}
                           target="_blank" rel="noreferrer">
                          ↓ PDF
                        </a>
                      )}

                      <button onClick={() => deleteReport(r.id)}
                              className="font-pixel text-xs px-2 py-1"
                              style={{ border: "2px solid #c53030", color: "#c53030" }}>
                        ✕
                      </button>
                    </div>
                  </div>

                  {/* Error message */}
                  {r.status === "error" && r.content_json?.error && (
                    <p className="font-mono text-xs mt-2" style={{ color: "#c53030" }}>{r.content_json.error}</p>
                  )}
                </div>
              ))}
            </div>
          )
        }
      </main>
      <BodhiChat />
    </div>
  );
}
