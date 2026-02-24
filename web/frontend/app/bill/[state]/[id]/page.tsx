"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import { search as searchApi, docket as docketApi } from "@/lib/api";

export default function BillDetailPage() {
  const params  = useParams();
  const router  = useRouter();
  const stateParam = (params.state as string).toUpperCase();
  const idParam    = params.id as string;

  const [bill,    setBill]    = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");
  const [added,   setAdded]   = useState(false);

  const isFederal = stateParam === "US";

  useEffect(() => {
    async function load() {
      setLoading(true); setError("");
      try {
        if (isFederal) {
          // id format: "119-hr-1234"
          const parts = idParam.split("-");
          const congress    = Number(parts[0]);
          const bill_type   = parts[1];
          const bill_number = Number(parts.slice(2).join("-"));
          if (!congress || !bill_type || !bill_number) throw new Error("Invalid bill ID format");
          const data = await searchApi.federalBillFull(congress, bill_type, bill_number);
          setBill(data);
        } else {
          const data = await searchApi.stateBillDetail(Number(idParam));
          setBill(data);
        }
      } catch (e: any) { setError(e.message); }
      setLoading(false);
    }
    load();
  }, [idParam, stateParam]);

  async function addToDocket() {
    try {
      await docketApi.add({
        bill_id:     idParam,
        bill_number: isFederal ? (bill?.bill_label ?? idParam) : (bill?.bill_number ?? idParam),
        state:       stateParam,
        title:       bill?.title ?? "",
      });
      setAdded(true);
    } catch (e: any) {
      if ((e.message ?? "").includes("already")) setAdded(true);
      else alert(e.message);
    }
  }

  function goToReport() {
    const p = new URLSearchParams({
      bill_id:     idParam,
      bill_number: isFederal ? (bill?.bill_label ?? idParam) : (bill?.bill_number ?? idParam),
      state:       stateParam,
      title:       bill?.title ?? "",
    });
    router.push(`/reports?${p.toString()}`);
  }

  // ── Derived display values ─────────────────────────────────────────────
  const title      = bill?.title ?? "Loading...";
  const billLabel  = isFederal ? (bill?.bill_label ?? idParam) : (bill?.bill_number ?? idParam);
  const status     = isFederal ? bill?.status : bill?.last_action;
  const statusDate = isFederal ? bill?.status_date : bill?.last_action_date;
  const introduced = isFederal ? bill?.introduced_date : bill?.status_date;
  const policyArea = isFederal ? bill?.policy_area : (bill?.subjects ?? []).slice(0,3).map((s: any) => s.subject_name ?? s).join(", ");
  const sponsor    = isFederal
    ? (bill?.primary_sponsor?.name ? `${bill.primary_sponsor.name} (${bill.primary_sponsor.party}-${bill.primary_sponsor.state})` : "")
    : (bill?.sponsors ?? []).slice(0,1).map((s: any) => `${s.name} (${s.party || ""})`).join("");
  const summaryText   = isFederal ? bill?.summary_text : bill?.description;
  const recentActions = isFederal
    ? (bill?.recent_actions ?? [])
    : (bill?.history ?? []).slice(-8).reverse();
  const extUrl = isFederal ? (bill?.congress_url ?? bill?.govtrack_url) : bill?.state_link;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />
      <main className="max-w-4xl mx-auto p-6 flex flex-col gap-6">

        {/* Back */}
        <button onClick={() => router.back()}
                className="font-pixel text-xs self-start"
                style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}>
          ◀ BACK
        </button>

        {loading && (
          <div className="card p-10 flex flex-col items-center gap-4">
            <p className="font-pixel text-xs animate-pulse" style={{ color: "var(--accent)" }}>LOADING BILL DATA...</p>
          </div>
        )}

        {error && (
          <p className="font-pixel text-xs p-3" style={{ background: "#c53030", color: "#fff", border: "3px solid #8b0000" }}>
            ⚠ {error}
          </p>
        )}

        {bill && !loading && (
          <>
            {/* Header */}
            <div className="card p-5 flex flex-col gap-3">
              <div className="flex items-start gap-3 flex-wrap">
                <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
                      style={{ background: "var(--primary)", color: "var(--bg)", border: "2px solid var(--border)" }}>
                  {stateParam}
                </span>
                <span className="font-pixel text-xs px-2 py-1 flex-shrink-0"
                      style={{ background: "var(--accent)", color: "var(--bg)", border: "2px solid var(--border)" }}>
                  {billLabel}
                </span>
              </div>
              <h1 className="font-mono text-base leading-snug" style={{ color: "var(--text)" }}>{title}</h1>

              {/* Meta grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-2">
                {status && (
                  <div>
                    <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>LATEST ACTION</p>
                    <p className="font-mono text-xs">{status}</p>
                    {statusDate && <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>{statusDate}</p>}
                  </div>
                )}
                {introduced && (
                  <div>
                    <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>INTRODUCED</p>
                    <p className="font-mono text-xs">{introduced}</p>
                  </div>
                )}
                {sponsor && (
                  <div>
                    <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>SPONSOR</p>
                    <p className="font-mono text-xs">{sponsor}</p>
                  </div>
                )}
                {policyArea && (
                  <div>
                    <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>POLICY AREA</p>
                    <p className="font-mono text-xs">{policyArea}</p>
                  </div>
                )}
                {isFederal && bill?.cosponsor_count > 0 && (
                  <div>
                    <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>COSPONSORS</p>
                    <p className="font-mono text-xs">{bill.cosponsor_count}</p>
                  </div>
                )}
                {isFederal && bill?.chamber && (
                  <div>
                    <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>CHAMBER</p>
                    <p className="font-mono text-xs">{bill.chamber}</p>
                  </div>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 flex-wrap mt-2">
                <button className="btn-arcade font-pixel text-xs px-4" onClick={goToReport}
                        style={{ fontSize: "0.65rem" }}>
                  📊 GENERATE REPORT
                </button>
                <button onClick={addToDocket} disabled={added}
                        className="font-pixel text-xs px-4 py-2"
                        style={{
                          border: "3px solid",
                          borderColor: added ? "#2D7A4F" : "var(--accent)",
                          background:  added ? "#2D7A4F" : "transparent",
                          color:       added ? "#fff"    : "var(--accent)",
                          boxShadow:   added ? "none"    : "3px 3px 0 var(--accent)",
                          fontSize: "0.65rem",
                        }}>
                  {added ? "✓ IN DOCKET" : "+ ADD TO DOCKET"}
                </button>
                {extUrl && (
                  <a href={extUrl} target="_blank" rel="noreferrer"
                     className="btn-arcade-outline font-pixel text-xs px-4"
                     style={{ fontSize: "0.65rem" }}>
                    ↗ {isFederal ? "CONGRESS.GOV" : "STATE SOURCE"}
                  </a>
                )}
              </div>
            </div>

            {/* CRS Summary / Description */}
            {summaryText && (
              <div className="card p-5">
                <p className="font-pixel text-xs mb-3" style={{ color: "var(--accent)" }}>
                  📄 {isFederal ? "CRS SUMMARY" : "DESCRIPTION"}
                  {bill?.summary_date && (
                    <span className="font-pixel ml-2" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>
                      {bill.summary_date}
                    </span>
                  )}
                </p>
                <p className="font-mono text-xs leading-relaxed" style={{ color: "var(--text)" }}>
                  {summaryText}
                </p>
              </div>
            )}

            {/* Action history */}
            {recentActions.length > 0 && (
              <div className="card p-5">
                <p className="font-pixel text-xs mb-3" style={{ color: "var(--accent)" }}>
                  📋 {isFederal ? "RECENT ACTIONS" : "LEGISLATIVE HISTORY"}
                </p>
                <div className="flex flex-col gap-2">
                  {recentActions.map((a: any, i: number) => (
                    <div key={i} className="flex gap-3 items-start"
                         style={{ borderBottom: "1px dashed var(--border)", paddingBottom: "0.5rem" }}>
                      <span className="font-pixel text-xs flex-shrink-0"
                            style={{ color: "var(--text-muted)", fontSize: "0.55rem", minWidth: "80px" }}>
                        {a.date ?? a.date ?? ""}
                      </span>
                      <p className="font-mono text-xs" style={{ color: "var(--text)" }}>
                        {a.text ?? a.action ?? ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* State bill votes */}
            {!isFederal && (bill?.votes ?? []).length > 0 && (
              <div className="card p-5">
                <p className="font-pixel text-xs mb-3" style={{ color: "var(--accent)" }}>🗳️ VOTES</p>
                <div className="flex flex-col gap-2">
                  {(bill.votes as any[]).map((v: any, i: number) => (
                    <div key={i} className="flex gap-3 items-center"
                         style={{ borderBottom: "1px dashed var(--border)", paddingBottom: "0.5rem" }}>
                      <span className="font-pixel text-xs flex-shrink-0"
                            style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>{v.date}</span>
                      <span className="font-mono text-xs flex-1">{v.desc}</span>
                      <span className="font-pixel text-xs"
                            style={{ color: v.passed ? "#2D7A4F" : "#c53030", fontSize: "0.55rem" }}>
                        {v.yea}Y / {v.nay}N {v.passed ? "PASSED" : "FAILED"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </>
        )}

      </main>
      <BodhiChat />
    </div>
  );
}
