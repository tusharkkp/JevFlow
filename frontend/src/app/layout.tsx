import type { Metadata } from "next";
import React from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "JevFlow — Adaptive AI Gateway Observability & Benchmark Dashboard",
  description:
    "Real-time observability, flamegraph latency waterfall, token economics, and empirical A/B evaluation for JevFlow Adaptive AI Gateway.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body>{children}</body>
    </html>
  );
}
