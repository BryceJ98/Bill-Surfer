"use client";
import { createContext, useContext, useEffect, useState } from "react";

export type PersonalityId = "bodhi" | "bernhard";

interface ThemeCtx {
  ski:           boolean;
  toggle:        () => void;
  personality:   PersonalityId;
  setPersonality: (id: PersonalityId) => void;
}

const ThemeContext = createContext<ThemeCtx>({
  ski: false, toggle: () => {},
  personality: "bodhi", setPersonality: () => {},
});
export const useTheme = () => useContext(ThemeContext);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [ski,         setSki]         = useState(false);
  const [personality, setPersonalityState] = useState<PersonalityId>("bodhi");

  useEffect(() => {
    if (localStorage.getItem("theme") === "dark") {
      setSki(true);
      document.documentElement.classList.add("dark");
    }
    const saved = localStorage.getItem("active_personality") as PersonalityId | null;
    if (saved === "bodhi" || saved === "bernhard") setPersonalityState(saved);
  }, []);

  function toggle() {
    const next = !ski;
    setSki(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  function setPersonality(id: PersonalityId) {
    setPersonalityState(id);
    localStorage.setItem("active_personality", id);
  }

  return (
    <ThemeContext.Provider value={{ ski, toggle, personality, setPersonality }}>
      {children}
    </ThemeContext.Provider>
  );
}
