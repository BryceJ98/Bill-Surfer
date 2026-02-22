/**
 * api.ts — Typed client for the Bill-Surfer FastAPI backend.
 * Automatically attaches the Supabase session JWT to every request.
 */

import { createClient } from "./supabase";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getToken(): Promise<string> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? "";
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
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
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
export const search = {
  federalBills:    (q: string, congress?: number) =>
    request<any>(`/search/federal/bills?q=${encodeURIComponent(q)}${congress ? `&congress=${congress}` : ""}`),
  nominations:     (q?: string, congress?: number) =>
    request<any>(`/search/federal/nominations${q ? `?q=${encodeURIComponent(q)}` : ""}${congress ? `${q ? "&" : "?"}congress=${congress}` : ""}`),
  treaties:        (congress?: number) =>
    request<any>(`/search/federal/treaties${congress ? `?congress=${congress}` : ""}`),
  stateBills:      (q: string, state: string, year?: number) =>
    request<any>(`/search/state/bills?q=${encodeURIComponent(q)}&state=${state}${year ? `&year=${year}` : ""}`),
};

// ── Reports ───────────────────────────────────────────────────────────────
export const reports = {
  list:           ()               => request<Report[]>("/reports"),
  create:         (data: ReportRequest) =>
    request<{ report_id: string; status: string }>("/reports", { method: "POST", body: JSON.stringify(data) }),
  get:            (id: string)     => request<Report>(`/reports/${id}`),
  pdfUrl:         (id: string)     => `${BASE}/reports/${id}/pdf`,
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

// ── Types ─────────────────────────────────────────────────────────────────
export interface KeyStatus      { provider: string; stored: boolean; masked?: string }
export interface UserSettings   { user_id?: string; display_name?: string; institution?: string; research_areas?: string[]; ai_provider: string; ai_model: string }
export interface Scoreboard     { docket_count: number; reports_total: number; reports_today: number; ai_model: string; ai_provider: string; date: string }
export interface DocketItem     { id: string; bill_id: string; bill_number?: string; state: string; title?: string; stance?: string; priority?: string; notes?: string; tags: string[]; added_date: string }
export interface DocketItemIn   { bill_id: string; bill_number?: string; state: string; title?: string; stance?: string; priority?: string; notes?: string; tags?: string[] }
export interface Report         { id: string; bill_id: string; bill_number: string; state: string; title: string; report_type: string; ai_model?: string; status: string; is_public: boolean; created_at: string; content_json?: any }
export interface ReportRequest  { bill_id: string; bill_number: string; state: string; title: string; report_type?: string }
export interface ExportRequest  { export_type: string; query?: string; state?: string; congress?: number; year?: number; limit?: number }
export interface ChatMessage    { role: "user" | "assistant" | "system"; content: string }
