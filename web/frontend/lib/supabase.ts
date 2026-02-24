import { createBrowserClient } from "@supabase/ssr";

// Singleton — one instance shared across all components.
// Multiple instances compete for the same navigator lock on the auth token,
// causing "LockManager lock timed out" errors.
let _client: ReturnType<typeof createBrowserClient> | null = null;

export function createClient() {
  if (!_client) {
    _client = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
  }
  return _client;
}
