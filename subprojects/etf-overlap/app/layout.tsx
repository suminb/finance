import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ETF Overlap Analysis",
  description: "Compare multiple ETFs and visualize their weighted overlap",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
