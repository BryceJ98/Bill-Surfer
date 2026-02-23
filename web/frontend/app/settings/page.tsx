"use client";
import { useEffect, useState } from "react";
import NavBar from "@/components/NavBar";
import BodhiChat from "@/components/BodhiChat";
import { keys as keysApi, settings as settingsApi, type KeyStatus, type UserSettings } from "@/lib/api";

const PROVIDERS = [
  { id: "legiscan",  label: "LEGISCAN",   url: "https://legiscan.com/legiscan",      icon: "📋", desc: "State bills — all 50 states" },
  { id: "congress",  label: "CONGRESS",   url: "https://api.congress.gov/sign-up/",  icon: "🏛️", desc: "Federal bills, nominations, treaties" },
  { id: "anthropic", label: "ANTHROPIC",  url: "https://console.anthropic.com/",     icon: "🤖", desc: "Claude models" },
  { id: "openai",    label: "OPENAI",     url: "https://platform.openai.com/",       icon: "🤖", desc: "GPT models" },
  { id: "google",    label: "GOOGLE",     url: "https://makersuite.google.com/",     icon: "🤖", desc: "Gemini models" },
  { id: "groq",      label: "GROQ",       url: "https://console.groq.com/",          icon: "🤖", desc: "Fast open models" },
  { id: "mistral",   label: "MISTRAL",    url: "https://console.mistral.ai/",        icon: "🤖", desc: "Mistral models" },
];

const AI_MODELS: Record<string, string[]> = {
  anthropic: ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
  openai:    ["gpt-4o", "gpt-4o-mini"],
  google:    ["gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash"],
  groq:      ["groq/llama-3.1-70b-versatile", "groq/llama-3.1-8b-instant"],
  mistral:   ["mistral/mistral-large-latest", "mistral/mistral-small-latest"],
};

export default function SettingsPage() {
  const [storedKeys, setStoredKeys]   = useState<KeyStatus[]>([]);
  const [userSettings, setUserSettings] = useState<UserSettings | null>(null);
  const [inputKeys, setInputKeys]     = useState<Record<string, string>>({});
  const [saving, setSaving]           = useState<Record<string, boolean>>({});
  const [saved, setSaved]             = useState<Record<string, boolean>>({});
  const [profile, setProfile]         = useState({ display_name: "", institution: "" });
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState("");

  useEffect(() => {
    keysApi.list().then(setStoredKeys).catch(() => {});
    settingsApi.get().then((s) => {
      setUserSettings(s);
      setProfile({ display_name: s.display_name ?? "", institution: s.institution ?? "" });
    }).catch(() => {});
  }, []);

  function isStored(provider: string) {
    return storedKeys.some((k) => k.provider === provider && k.stored);
  }
  function maskedKey(provider: string) {
    return storedKeys.find((k) => k.provider === provider)?.masked ?? "";
  }

  async function saveKey(provider: string) {
    const key = inputKeys[provider];
    if (!key?.trim()) return;
    setSaving((s) => ({ ...s, [provider]: true }));
    try {
      await keysApi.save(provider, key.trim());
      setSaved((s) => ({ ...s, [provider]: true }));
      setInputKeys((k) => ({ ...k, [provider]: "" }));
      keysApi.list().then(setStoredKeys);
      setTimeout(() => setSaved((s) => ({ ...s, [provider]: false })), 2000);
    } catch (e: any) { alert(e.message); }
    setSaving((s) => ({ ...s, [provider]: false }));
  }

  async function deleteKey(provider: string) {
    if (!confirm(`Remove ${provider} key?`)) return;
    try {
      await keysApi.remove(provider);
      keysApi.list().then(setStoredKeys);
    } catch (e: any) {
      alert(`Failed to remove key: ${e.message}`);
    }
  }

  async function saveAiModel(provider: string, model: string) {
    try {
      await settingsApi.update({ ai_provider: provider, ai_model: model });
      setUserSettings((s) => s ? { ...s, ai_provider: provider, ai_model: model } : s);
    } catch (e: any) {
      alert(`Failed to update AI model: ${e.message}`);
    }
  }

  async function saveProfile() {
    setProfileError("");
    setProfileSaved(false);
    try {
      await settingsApi.update(profile);
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (e: any) {
      setProfileError(e.message);
    }
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <NavBar />
      <main className="max-w-3xl mx-auto p-6 flex flex-col gap-8">

        <h1 className="font-pixel text-sm" style={{ color: "var(--accent)" }}>⚙️ SETTINGS</h1>

        {/* Profile */}
        <section className="card p-5 flex flex-col gap-4">
          <p className="font-pixel text-xs" style={{ color: "var(--accent)" }}>👤 PROFILE</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>DISPLAY_NAME</label>
              <input className="input-arcade" value={profile.display_name}
                     onChange={(e) => setProfile({ ...profile, display_name: e.target.value })} placeholder="Dr. Jane Smith" />
            </div>
            <div>
              <label className="font-pixel block mb-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>INSTITUTION</label>
              <input className="input-arcade" value={profile.institution}
                     onChange={(e) => setProfile({ ...profile, institution: e.target.value })} placeholder="University of ..." />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="btn-arcade font-pixel text-xs" onClick={saveProfile}>▶ SAVE PROFILE</button>
            {profileSaved && (
              <span className="font-pixel text-xs" style={{ color: "#2D7A4F" }}>✓ SAVED!</span>
            )}
            {profileError && (
              <span className="font-pixel text-xs" style={{ color: "#c53030" }}>⚠ {profileError}</span>
            )}
          </div>
        </section>

        {/* API Keys */}
        <section className="card p-5 flex flex-col gap-4">
          <p className="font-pixel text-xs" style={{ color: "var(--accent)" }}>🔑 API KEYS</p>
          <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
            Keys are encrypted before storage. Never exposed in plaintext.
          </p>

          {PROVIDERS.map((p) => (
            <div key={p.id} className="flex flex-col gap-2 pb-4"
                 style={{ borderBottom: "2px dashed var(--border)" }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span>{p.icon}</span>
                  <span className="font-pixel text-xs" style={{ color: "var(--text)" }}>{p.label}</span>
                  <span className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.55rem" }}>{p.desc}</span>
                </div>
                {isStored(p.id)
                  ? <span className="font-pixel text-xs" style={{ color: "#2D7A4F" }}>● STORED {maskedKey(p.id)}</span>
                  : <span className="font-pixel text-xs" style={{ color: "var(--text-muted)" }}>○ NOT SET</span>
                }
              </div>

              <div className="flex gap-2">
                <input className="input-arcade flex-1" type="password"
                       placeholder={isStored(p.id) ? "Enter new key to replace..." : "Paste API key..."}
                       value={inputKeys[p.id] ?? ""}
                       onChange={(e) => setInputKeys((k) => ({ ...k, [p.id]: e.target.value }))} />
                <button className="btn-arcade font-pixel text-xs flex-shrink-0"
                        onClick={() => saveKey(p.id)}
                        disabled={saving[p.id] || !inputKeys[p.id]?.trim()}>
                  {saved[p.id] ? "✓ SAVED" : saving[p.id] ? "..." : "SAVE"}
                </button>
                {isStored(p.id) && (
                  <button onClick={() => deleteKey(p.id)}
                          className="font-pixel text-xs px-3"
                          style={{ border: "3px solid #c53030", color: "#c53030", boxShadow: "3px 3px 0 #c53030" }}>
                    ✕
                  </button>
                )}
              </div>

              <a href={p.url} target="_blank" rel="noreferrer"
                 className="font-pixel" style={{ color: "var(--accent)", fontSize: "0.6rem" }}>
                ↗ GET KEY AT {p.label}.COM
              </a>
            </div>
          ))}
        </section>

        {/* AI Model */}
        <section className="card p-5 flex flex-col gap-4">
          <p className="font-pixel text-xs" style={{ color: "var(--accent)" }}>🤖 AI MODEL (ACTIVE)</p>
          {userSettings && (
            <p className="font-pixel" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
              CURRENT: {userSettings.ai_provider.toUpperCase()} / {userSettings.ai_model.split("/").pop()?.toUpperCase()}
            </p>
          )}

          {Object.entries(AI_MODELS).map(([provider, models]) => (
            <div key={provider}>
              <p className="font-pixel mb-2" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>{provider.toUpperCase()}</p>
              <div className="flex flex-wrap gap-2">
                {models.map((m) => {
                  const active = userSettings?.ai_model === m;
                  return (
                    <button key={m} onClick={() => saveAiModel(provider, m)}
                            className="font-pixel text-xs px-3 py-2"
                            style={{
                              border:     "3px solid",
                              borderColor: active ? "var(--accent)" : "var(--border)",
                              background:  active ? "var(--accent)" : "transparent",
                              color:       active ? "var(--bg)"     : "var(--text)",
                              boxShadow:   active ? "3px 3px 0 var(--border)" : "none",
                              fontSize: "0.6rem",
                            }}>
                      {active ? "▶ " : ""}{m.split("/").pop()?.toUpperCase()}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </section>

      </main>
      <BodhiChat />
    </div>
  );
}
