import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShelfReady",
  description:
    "Make your store buyable by AI shopping agents, with rule-guarded PayPal checkout. Sandbox only.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Archivo for the whole UI; the font stack falls back to system-ui if it is blocked. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font -- app router: root layout covers every page */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;800&display=swap"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
