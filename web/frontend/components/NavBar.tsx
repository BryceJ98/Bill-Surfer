"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase";

const NAV = [
  { href: "/dashboard", label: "HOME",    icon: "🏠" },
  { href: "/search",    label: "SEARCH",  icon: "🔍" },
  { href: "/docket",    label: "DOCKET",  icon: "📋" },
  { href: "/reports",   label: "REPORTS", icon: "📊" },
  { href: "/settings",  label: "SETTINGS",icon: "⚙️" },
];

export default function NavBar() {
  const pathname  = usePathname();
  const router    = useRouter();
  const supabase  = createClient();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "dark") { setDark(true); document.documentElement.classList.add("dark"); }
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  async function signOut() {
    await supabase.auth.signOut();
    router.push("/");
  }

  return (
    <nav className="w-full flex items-center gap-1 px-3 py-2"
         style={{ background: "var(--primary)", borderBottom: "3px solid var(--border)" }}>
      {/* Logo */}
      <Link href="/dashboard"
            className="font-pixel text-xs mr-4 neon-text"
            style={{ color: dark ? "var(--accent)" : "#F4F9FC" }}>
        🏄 BILL-SURFER
      </Link>

      {/* Nav links */}
      {NAV.map((n) => (
        <Link key={n.href} href={n.href}
              className="font-pixel text-xs px-2 py-1 transition-all"
              style={{
                color:      pathname === n.href ? "var(--accent)" : "#F4F9FC",
                background: pathname === n.href ? "rgba(255,255,255,0.1)" : "transparent",
                border:     pathname === n.href ? "2px solid var(--accent)" : "2px solid transparent",
              }}>
          <span className="hidden md:inline">{n.icon} </span>{n.label}
        </Link>
      ))}

      {/* Spacer */}
      <div className="ml-auto flex items-center gap-2">
        {/* Theme toggle */}
        <button onClick={toggleTheme}
                className="font-pixel text-xs px-2 py-1"
                style={{ color: "#F4F9FC", border: "2px solid rgba(255,255,255,0.3)" }}
                title={dark ? "Switch to Surf (day)" : "Switch to Ski (night)"}>
          {dark ? "🏔️ SKI" : "🏄 SURF"}
        </button>

        {/* Sign out */}
        <button onClick={signOut}
                className="font-pixel text-xs px-2 py-1"
                style={{ color: "#F4F9FC", border: "2px solid rgba(255,255,255,0.3)" }}>
          EXIT
        </button>
      </div>
    </nav>
  );
}
