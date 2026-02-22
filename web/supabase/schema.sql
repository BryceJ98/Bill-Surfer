-- =============================================================================
-- Bill-Surfer Web — Supabase Schema
-- Run this in the Supabase SQL Editor for your project.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- user_keys — encrypted API keys per user
-- Stores AES-256-GCM ciphertext; plaintext never persisted.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_keys (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider    text        NOT NULL CHECK (provider IN (
                                'legiscan', 'congress',
                                'anthropic', 'openai', 'google', 'groq', 'mistral'
                            )),
    key_enc     text        NOT NULL,   -- AES-256-GCM ciphertext (base64)
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);

-- ---------------------------------------------------------------------------
-- user_settings — profile and AI provider preference per user
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_settings (
    user_id         uuid    PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name    text,
    institution     text,
    research_areas  text[]  DEFAULT '{}',
    ai_provider     text    NOT NULL DEFAULT 'anthropic'
                            CHECK (ai_provider IN ('anthropic','openai','google','groq','mistral')),
    ai_model        text    NOT NULL DEFAULT 'claude-sonnet-4-6',
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- docket — personal bill tracking list per user
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS docket (
    id              uuid    PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- Identifies the bill. For federal: "us-hr-1234". For state: LegiScan bill_id as text.
    bill_id         text    NOT NULL,
    bill_number     text,
    state           text    NOT NULL,   -- 'US', 'CA', 'TX', etc.
    title           text,
    stance          text    CHECK (stance IN ('support','oppose','neutral','watching')),
    priority        text    CHECK (priority IN ('high','medium','low')),
    notes           text,
    tags            text[]  DEFAULT '{}',
    added_date      date    NOT NULL DEFAULT current_date,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, bill_id)
);

-- ---------------------------------------------------------------------------
-- reports — policy report library per user
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id               uuid    PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          uuid    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    bill_id          text    NOT NULL,
    bill_number      text    NOT NULL,
    state            text    NOT NULL,
    title            text    NOT NULL,
    report_type      text    NOT NULL DEFAULT 'policy_impact'
                             CHECK (report_type IN (
                                 'policy_impact','summary','vote_analysis','comparison'
                             )),
    ai_provider      text,
    ai_model         text,
    -- Structured AI output stored as JSON for frontend rendering
    content_json     jsonb,
    -- Path in Supabase Storage bucket "reports" — null until PDF is generated
    pdf_storage_path text,
    is_public        boolean NOT NULL DEFAULT false,
    status           text    NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','generating','complete','error')),
    error_message    text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- saved_searches — store named search queries for reuse
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_searches (
    id          uuid    PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    label       text    NOT NULL,
    search_type text    NOT NULL CHECK (search_type IN ('bills','nominations','treaties','federal')),
    params      jsonb   NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
ALTER TABLE user_keys      ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings  ENABLE ROW LEVEL SECURITY;
ALTER TABLE docket         ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports        ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;

-- user_keys: users can only read/write their own keys
CREATE POLICY "own user_keys"
    ON user_keys FOR ALL
    USING  (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- user_settings: users can only read/write their own settings
CREATE POLICY "own user_settings"
    ON user_settings FOR ALL
    USING  (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- docket: users can only read/write their own docket
CREATE POLICY "own docket"
    ON docket FOR ALL
    USING  (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- reports: users see their own + any public reports; write only own
CREATE POLICY "read own or public reports"
    ON reports FOR SELECT
    USING (user_id = auth.uid() OR is_public = true);

CREATE POLICY "write own reports"
    ON reports FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "update own reports"
    ON reports FOR UPDATE
    USING  (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "delete own reports"
    ON reports FOR DELETE
    USING (user_id = auth.uid());

-- saved_searches: users manage only their own
CREATE POLICY "own saved_searches"
    ON saved_searches FOR ALL
    USING  (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_user_keys_updated_at
    BEFORE UPDATE ON user_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_docket_updated_at
    BEFORE UPDATE ON docket
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- Auto-create user_settings row on first sign-up
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.user_settings (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ---------------------------------------------------------------------------
-- Storage bucket for report PDFs
-- Create via Supabase Dashboard > Storage > New Bucket, or uncomment below
-- if your project supports storage schema manipulation via SQL.
-- ---------------------------------------------------------------------------
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('reports', 'reports', false)
-- ON CONFLICT (id) DO NOTHING;

-- Storage RLS: users can only access their own folder (reports/{user_id}/*)
-- CREATE POLICY "users access own report pdfs"
--     ON storage.objects FOR ALL
--     USING (
--         bucket_id = 'reports'
--         AND auth.uid()::text = (storage.foldername(name))[1]
--     )
--     WITH CHECK (
--         bucket_id = 'reports'
--         AND auth.uid()::text = (storage.foldername(name))[1]
--     );
