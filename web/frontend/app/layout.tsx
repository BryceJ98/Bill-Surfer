import type { Metadata } from "next";
import "./globals.css";

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
        {children}
      </body>
    </html>
  );
}
