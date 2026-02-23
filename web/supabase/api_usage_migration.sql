-- Migration: API usage tracking for the scoreboard
-- Run this in the Supabase SQL editor.

CREATE TABLE api_usage (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider    TEXT NOT NULL,          -- 'legiscan', 'congress', 'anthropic', 'openai', etc.
  month       TEXT NOT NULL,          -- 'YYYY-MM'
  call_count  INTEGER NOT NULL DEFAULT 0,
  token_count INTEGER NOT NULL DEFAULT 0,
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, provider, month)
);

ALTER TABLE api_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own api_usage"
  ON api_usage FOR ALL USING (auth.uid() = user_id);

-- Atomic upsert-increment (avoids race conditions)
CREATE OR REPLACE FUNCTION increment_api_usage(
  p_user_id  UUID, p_provider TEXT, p_month TEXT,
  p_calls    INTEGER DEFAULT 1, p_tokens INTEGER DEFAULT 0
) RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO api_usage (user_id, provider, month, call_count, token_count)
  VALUES (p_user_id, p_provider, p_month, p_calls, p_tokens)
  ON CONFLICT (user_id, provider, month) DO UPDATE SET
    call_count  = api_usage.call_count  + EXCLUDED.call_count,
    token_count = api_usage.token_count + EXCLUDED.token_count,
    updated_at  = NOW();
END; $$;
