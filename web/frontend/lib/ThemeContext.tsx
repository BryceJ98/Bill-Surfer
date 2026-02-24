"use client";
import { createContext, useContext, useEffect, useState } from "react";

interface ThemeCtx { ski: boolean; toggle: () => void; }
const ThemeContext = createContext<ThemeCtx>({ ski: false, toggle: () => {} });
export const useTheme = () => useContext(ThemeContext);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [ski, setSki] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("theme") === "dark") {
      setSki(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  function toggle() {
    const next = !ski;
    setSki(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  return (
    <ThemeContext.Provider value={{ ski, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}
