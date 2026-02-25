/**
 * api.ts — Typed client for the Bill-Surfer FastAPI backend.
 * Automatically attaches the Supabase session JWT to every request.
 */

import { createClient } from "./supabase";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getToken(): Promise<string> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token ?? "";
  if (!token) throw new Error("Not authenticated. Please sign in again.");
  return token;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = Array.isArray(err.detail)
      ? err.detail.map((e: any) => e.msg ?? JSON.stringify(e)).join("; ")
      : err.detail;
    throw new Error(detail ?? `API error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Keys ──────────────────────────────────────────────────────────────────
export const keys = {
  list:   ()                     => request<KeyStatus[]>("/keys"),
  save:   (provider: string, key: string) =>
    request<void>(`/keys/${provider}`, { method: "POST", body: JSON.stringify({ key }) }),
  remove: (provider: string)    => request<void>(`/keys/${provider}`, { method: "DELETE" }),
};

// ── Settings ──────────────────────────────────────────────────────────────
export const settings = {
  get:        ()                   => request<UserSettings>("/settings"),
  update:     (data: Partial<UserSettings>) =>
    request<void>("/settings", { method: "PATCH", body: JSON.stringify(data) }),
  aiModels:   ()                   => request<Record<string, string[]>>("/settings/ai-models"),
  scoreboard: ()                   => request<Scoreboard>("/settings/scoreboard"),
};

// ── Docket ────────────────────────────────────────────────────────────────
export const docket = {
  list:   ()                        => request<DocketItem[]>("/docket"),
  add:    (item: DocketItemIn)      =>
    request<DocketItem>("/docket", { method: "POST", body: JSON.stringify(item) }),
  update: (id: string, data: Partial<DocketItem>) =>
    request<DocketItem>(`/docket/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  remove: (id: string)              => request<void>(`/docket/${id}`, { method: "DELETE" }),
};

// ── Search ────────────────────────────────────────────────────────────────
function _qs(parts: (string | undefined)[]): string {
  const s = parts.filter((p): p is string => p !== undefined && p !== "").join("&");
  return s ? `?${s}` : "";
}

export const search = {
  federalBills: (q: string, congress?: number, offset?: number) =>
    request<any>(`/search/federal/bills${_qs([
      `q=${encodeURIComponent(q)}`,
      congress  != null ? `congress=${congress}`  : undefined,
      offset    != null ? `offset=${offset}`      : undefined,
    ])}`),
  nominations: (q?: string, congress?: number, offset?: number) =>
    request<any>(`/search/federal/nominations${_qs([
      q        != null ? `q=${encodeURIComponent(q)}` : undefined,
      congress != null ? `congress=${congress}`        : undefined,
      offset   != null ? `offset=${offset}`            : undefined,
    ])}`),
  treaties: (congress?: number, q?: string, offset?: number) =>
    request<any>(`/search/federal/treaties${_qs([
      congress != null ? `congress=${congress}`        : undefined,
      q        != null ? `q=${encodeURIComponent(q)}` : undefined,
      offset   != null ? `offset=${offset}`            : undefined,
    ])}`),
  stateBills: (q: string, state: string, year?: number, offset?: number) =>
    request<any>(`/search/state/bills${_qs([
      `q=${encodeURIComponent(q)}`,
      `state=${state}`,
      year   != null ? `year=${year}`     : undefined,
      offset != null ? `offset=${offset}` : undefined,
    ])}`),
  federalBillFull: (congress: number, bill_type: string, bill_number: number) =>
    request<any>(`/search/federal/bill/full?congress=${congress}&bill_type=${encodeURIComponent(bill_type)}&bill_number=${bill_number}`),
  stateBillDetail: (bill_id: number) =>
    request<any>(`/search/state/bill?bill_id=${bill_id}`),
  agent: (query: string, state?: string) =>
    request<AgentSearchResult>("/search/agent", { method: "POST", body: JSON.stringify({ query, state }) }),
};

export interface AgentSearchResult {
  bills:       any[];
  explanation: string;
  searches:    string[];
  query:       string;
}

// ── Reports ───────────────────────────────────────────────────────────────
export const reports = {
  list:           ()               => request<Report[]>("/reports"),
  create:         (data: ReportRequest) =>
    request<{ report_id: string; status: string }>("/reports", { method: "POST", body: JSON.stringify(data) }),
  get:            (id: string)     => request<Report>(`/reports/${id}`),
  pdfUrl:         (id: string)     => `${BASE}/reports/${id}/pdf`,
  pdfDownload:    async (id: string): Promise<void> => {
    const token = await getToken();
    const res = await fetch(`${BASE}/reports/${id}/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("PDF download failed");
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `report-${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
  setVisibility:  (id: string, isPublic: boolean) =>
    request<void>(`/reports/${id}/visibility?is_public=${isPublic}`, { method: "PATCH" }),
  remove:         (id: string)     => request<void>(`/reports/${id}`, { method: "DELETE" }),
};

// ── Export ────────────────────────────────────────────────────────────────
export async function exportCsv(params: ExportRequest): Promise<void> {
  const token = await getToken();
  const res = await fetch(`${BASE}/export/csv`, {
    method:  "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body:    JSON.stringify(params),
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `${params.export_type}_export.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Chat ──────────────────────────────────────────────────────────────────
export const chat = {
  send: (messages: ChatMessage[]) =>
    request<ChatMessage>("/chat", { method: "POST", body: JSON.stringify({ messages }) }),
};

// ── Explain ───────────────────────────────────────────────────────────────
export const explain = {
  bill: (data: ExplainRequest) =>
    request<ExplainResult>("/explain", { method: "POST", body: JSON.stringify(data) }),
};

// ── Track ─────────────────────────────────────────────────────────────────
export const track = {
  topic: (data: TrackRequest) =>
    request<TrackResult>("/track", { method: "POST", body: JSON.stringify(data) }),
};

// ── Types ─────────────────────────────────────────────────────────────────
export interface KeyStatus      { provider: string; stored: boolean; masked?: string }
export interface UserSettings   { user_id?: string; display_name?: string; institution?: string; research_areas?: string[]; ai_provider: string; ai_model: string }
export interface Scoreboard     { docket_count: number; reports_total: number; reports_today: number; ai_model: string; ai_provider: string; date: string; usage: { provider: string; call_count: number; token_count: number }[] }
export interface DocketItem     { id: string; bill_id: string; bill_number?: string; state: string; title?: string; stance?: string; priority?: string; notes?: string; tags: string[]; added_date: string }
export interface DocketItemIn   { bill_id: string; bill_number?: string; state: string; title?: string; stance?: string; priority?: string; notes?: string; tags?: string[] }
export interface Report         { id: string; bill_id: string; bill_number: string; state: string; title: string; report_type: string; ai_model?: string; status: string; is_public: boolean; created_at: string; content_json?: any; error_message?: string }
export interface ReportRequest  { bill_id: string; bill_number: string; state: string; title: string; report_type?: string }
export interface ExportRequest  { export_type: string; query?: string; state?: string; congress?: number; year?: number; limit?: number }
export interface ChatMessage    { role: "user" | "assistant" | "system"; content: string }
export interface ExplainRequest {
  title: string; state: string; bill_number?: string; bill_id?: string;
  summary_text?: string; status?: string;
  congress?: number; bill_type?: string; bill_number_int?: number;
}
export interface ExplainResult  {
  summary: string; key_points: string[]; who_is_affected: string;
  current_status: string; notes: string;
}
export interface TrackRequest   {
  topic: string; state?: string; congress?: number;
  include_crs?: boolean; include_record?: boolean;
}
export interface TrackResult    {
  topic: string; federal_bills: any[]; state_bills: any[];
  crs_reports: any[]; record_items: any[];
  ai_summary: string; total_federal: number; total_state: number; total_crs: number;
}
