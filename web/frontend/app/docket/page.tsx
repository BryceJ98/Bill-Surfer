"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import { docket as docketApi, exportCsv, type DocketItem } from "@/lib/api";

const STANCES  = ["support","oppose","neutral","watching"] as const;
const PRIORITIES = ["high","medium","low"] as const;

const STANCE_COLOR: Record<string, string> = {
  support: "#2D7A4F", oppose: "#c53030", neutral: "#888", watching: "#1A6BA0",
};
const PRIORITY_COLOR: Record<string, string> = {
  high: "#c53030", medium: "#856404", low: "#2D7A4F",
};

export default function DocketPage() {
  const router = useRouter();
  const [items,       setItems]       = useState<DocketItem[]>([]);
  const [editing,     setEditing]     = useState<string | null>(null);
  const [editData,    setEditData]    = useState<Partial<DocketItem>>({});
  const [filter,      setFilter]      = useState<string>("all");
  const [loadError,   setLoadError]   = useState("");
  const [csvExporting, setCsvExporting] = useState(false);

  function load() {
    docketApi.list()
      .then(setItems)
      .catch((e: any) => setLoadError(e.message));
  }
  useEffect(load, []);

  const filtered = filter === "all" ? items : items.filter((i) => i.stance === filter || i.priority === filter);

  function startEdit(item: DocketItem) {
    setEditing(item.id);
    setEditData({ stance: item.stance, priority: item.priority, notes: item.notes ?? "", tags: item.tags });
  }

  async function saveEdit(id: string) {
    try {
      await docketApi.update(id, editData);
      setEditing(null);
      load();
    } catch (e: any) {
      alert(`Failed to save: ${e.message}`);
    }
  }

  async function exportDocketCsv() {
    setCsvExporting(true);
    try { await exportCsv({ export_type: "docket" }); }
    catch (e: any) { alert(`Export failed: ${e.message}`); }
    setCsvExporting(false);
  }

  function goToReport(item: DocketItem) {
    const p = new URLSearchParams({
      bill_id:     item.bill_id,
      bill_number: item.bill_number ?? "",
      state:       item.state,
      title:       item.title ?? item.bill_number ?? item.bill_id,
    });
    router.push(`/reports?${p.toString()}`);
  }

  async function remove(id: string) {
    if (!confirm("Remove from docket?")) return;
    try {
      await docketApi.remove(id);
      load();
    } catch (e: any) {
      alert(`Failed to remove: ${e.message}`);
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

        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="font-pixel text-sm" style={{ color: "var(--accent)" }}>
            📋 MY DOCKET <span className="text-xs">({items.length} BILLS)</span>
          </h1>

          <button className="btn-arcade-outline font-pixel text-xs px-3 py-1"
                  onClick={exportDocketCsv} disabled={csvExporting || items.length === 0}
                  style={{ fontSize: "0.6rem" }}>
            {csvExporting ? "EXPORTING..." : "↓ CSV EXPORT"}
          </button>

          {/* Filter */}
          <div className="flex gap-1 flex-wrap">
            {(["all", ...STANCES, ...PRIORITIES] as string[]).map((f) => (
              <button key={f} onClick={() => setFilter(f)}
                      className="font-pixel text-xs px-2 py-1"
                      style={{
                        border:     "2px solid",
                        borderColor: filter === f ? "var(--accent)" : "var(--border)",
                        background:  filter === f ? "var(--accent)" : "transparent",
                        color:       filter === f ? "var(--bg)"     : "var(--text)",
                        fontSize: "0.55rem",
                      }}>
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0
          ? (
            <div className="card p-12 flex flex-col items-center gap-4">
              <span className="text-4xl">📋</span>
              <p className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>
                {filter === "all" ? "DOCKET IS EMPTY — ADD BILLS FROM SEARCH" : `NO ${filter.toUpperCase()} BILLS`}
              </p>
            </div>
          )
          : (
            <div className="flex flex-col gap-3">
              {filtered.map((item) => (
                <div key={item.id} className="card p-4">
                  {editing === item.id
                    ? (
                      /* ── Edit mode ── */
                      <div className="flex flex-col gap-3">
                        <div className="flex gap-2 flex-wrap">
                          <div>
                            <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>STANCE</label>
                            <div className="flex gap-1">
                              {STANCES.map((s) => (
                                <button key={s} onClick={() => setEditData((d) => ({ ...d, stance: s }))}
                                        className="font-pixel text-xs px-2 py-1"
                                        style={{
                                          border:     "2px solid",
                                          borderColor: editData.stance === s ? STANCE_COLOR[s] : "var(--border)",
                                          background:  editData.stance === s ? STANCE_COLOR[s] : "transparent",
                                          color:       editData.stance === s ? "#fff"           : "var(--text)",
                                          fontSize: "0.55rem",
                                        }}>
                                  {s.toUpperCase()}
                                </button>
                              ))}
                            </div>
                          </div>
                          <div>
                            <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>PRIORITY</label>
                            <div className="flex gap-1">
                              {PRIORITIES.map((p) => (
                                <button key={p} onClick={() => setEditData((d) => ({ ...d, priority: p }))}
                                        className="font-pixel text-xs px-2 py-1"
                                        style={{
                                          border:     "2px solid",
                                          borderColor: editData.priority === p ? PRIORITY_COLOR[p] : "var(--border)",
                                          background:  editData.priority === p ? PRIORITY_COLOR[p] : "transparent",
                                          color:       editData.priority === p ? "#fff"             : "var(--text)",
                                          fontSize: "0.55rem",
                                        }}>
                                  {p.toUpperCase()}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                        <textarea className="input-arcade resize-none" rows={2}
                                  placeholder="Notes..."
                                  value={editData.notes ?? ""}
                                  onChange={(e) => setEditData((d) => ({ ...d, notes: e.target.value }))} />
                        <div className="flex gap-2">
                          <button className="btn-arcade font-pixel text-xs" onClick={() => saveEdit(item.id)}>▶ SAVE</button>
                          <button className="btn-arcade-outline font-pixel text-xs" onClick={() => setEditing(null)}>CANCEL</button>
                        </div>
                      </div>
                    )
                    : (
                      /* ── Display mode ── */
                      <div className="flex items-start gap-3 flex-wrap">
                        <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
                              style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)" }}>
                          {item.state}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-sm">{item.title ?? item.bill_number}</p>
                          <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>{item.bill_number} · Added {item.added_date}</p>
                          <div className="flex gap-2 mt-1 flex-wrap">
                            {item.stance && (
                              <span className="font-pixel text-xs px-2 py-0"
                                    style={{ background: STANCE_COLOR[item.stance], color: "#fff", fontSize: "0.55rem" }}>
                                {item.stance.toUpperCase()}
                              </span>
                            )}
                            {item.priority && (
                              <span className="font-pixel text-xs px-2 py-0"
                                    style={{ border: `2px solid ${PRIORITY_COLOR[item.priority]}`, color: PRIORITY_COLOR[item.priority], fontSize: "0.55rem" }}>
                                {item.priority.toUpperCase()}
                              </span>
                            )}
                            {(item.tags ?? []).map((t) => (
                              <span key={t} className="font-pixel text-xs px-2"
                                    style={{ border: "2px solid var(--border)", fontSize: "0.55rem" }}>
                                #{t}
                              </span>
                            ))}
                          </div>
                          {item.notes && <p className="font-mono text-xs mt-1" style={{ color: "var(--text-muted)" }}>{item.notes}</p>}
                        </div>

                        <div className="flex gap-2 flex-shrink-0 flex-wrap">
                          <button className="btn-arcade font-pixel text-xs px-3 py-1"
                                  onClick={() => goToReport(item)}
                                  style={{ fontSize: "0.6rem" }}>
                            📊 GEN REPORT
                          </button>
                          <button className="btn-arcade-outline font-pixel text-xs px-3 py-1" onClick={() => startEdit(item)}
                                  style={{ fontSize: "0.6rem" }}>
                            EDIT
                          </button>
                          <button onClick={() => remove(item.id)}
                                  className="font-pixel text-xs px-3 py-1"
                                  style={{ border: "2px solid #c53030", color: "#c53030", fontSize: "0.6rem" }}>
                            ✕
                          </button>
                        </div>
                      </div>
                    )
                  }
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
