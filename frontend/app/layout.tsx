import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Review Console",
  description: "Evidence-backed review console for enterprise IT support recommendations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
