// @ts-nocheck
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = ["/", "/login"];

// ── Maintenance mode ─────────────────────────────────────────────────────────
// To take the site offline: set MAINTENANCE to true, commit, push.
// To bring it back: set MAINTENANCE to false, commit, push.
const MAINTENANCE = true;
// ─────────────────────────────────────────────────────────────────────────────

export async function middleware(request: NextRequest) {
  if (MAINTENANCE) {
    const path = request.nextUrl.pathname;
    if (path !== "/maintenance") {
      return NextResponse.redirect(new URL("/maintenance", request.url));
    }
    return NextResponse.next();
  }

  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll:  () => request.cookies.getAll(),
        setAll: (cookiesToSet: { name: string; value: string; options?: object }[]) => {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();
  const path = request.nextUrl.pathname;

  // Redirect unauthenticated users to login
  if (!user && !PUBLIC_PATHS.includes(path) && !path.startsWith("/login")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Redirect authenticated users away from login
  if (user && path === "/login") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|textures|fonts).*)"],
};
