import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      // ── Surf theme (day / light mode) ───────────────────────────────────
      // Orange + Navy
      // ── Ski theme (night / dark mode) ───────────────────────────────────
      // Light blue + White + Alpine green
      colors: {
        surf: {
          orange:     "#F4632A",
          "orange-lt":"#F7894E",
          navy:       "#0D2B52",
          "navy-lt":  "#1A4A8A",
          sand:       "#FFF5E6",
          foam:       "#FFF9F5",
          wave:       "#1A6BA0",
        },
        ski: {
          blue:       "#5BBFED",
          "blue-lt":  "#A8DCF5",
          white:      "#F4F9FC",
          alpine:     "#2D7A4F",
          "alpine-lt":"#4CAF75",
          slate:      "#1A2535",
          powder:     "#E8F4FD",
        },
      },
      fontFamily: {
        // Pixel / retro arcade fonts loaded via next/font or Google Fonts
        pixel: ['"Press Start 2P"', "monospace"],
        mono:  ['"Share Tech Mono"', "monospace"],
        sans:  ['"Share Tech Mono"', "monospace"],
      },
      backgroundImage: {
        "surf-grain": "url('/textures/surf-grain.png')",
        "ski-grain":  "url('/textures/ski-grain.png')",
      },
      boxShadow: {
        arcade:    "4px 4px 0px 0px rgba(0,0,0,0.8)",
        "arcade-lg":"6px 6px 0px 0px rgba(0,0,0,0.8)",
        neon:      "0 0 8px 2px rgba(244,99,42,0.7)",
        "neon-ski":"0 0 8px 2px rgba(91,191,237,0.7)",
      },
      borderWidth: {
        3: "3px",
      },
      animation: {
        blink:  "blink 1s step-end infinite",
        scroll: "marquee 20s linear infinite",
        wave:   "wave 3s ease-in-out infinite",
        snow:   "snow 8s linear infinite",
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0" },
        },
        marquee: {
          "0%":   { transform: "translateX(100%)" },
          "100%": { transform: "translateX(-100%)" },
        },
        wave: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-6px)" },
        },
        snow: {
          "0%":   { transform: "translateY(-10px)", opacity: "1" },
          "100%": { transform: "translateY(100vh)",  opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
