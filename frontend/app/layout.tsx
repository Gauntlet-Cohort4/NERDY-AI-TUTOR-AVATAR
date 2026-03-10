import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nerdy AI Tutor",
  description: "Real-time AI video avatar tutor for interactive learning",
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
