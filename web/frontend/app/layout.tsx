import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/lib/ThemeContext";
import SkiBackground from "@/components/SkiBackground";

export const metadata: Metadata = {
  title: "Bill-Surfer",
  description: "Retro legislative research for political science researchers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Share+Tech+Mono&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="scanlines min-h-screen">
        <ThemeProvider>
          <SkiBackground />
          <div className="ski-content-layer min-h-screen">
            {children}
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
