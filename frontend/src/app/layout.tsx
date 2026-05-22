import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AstroPipeline",
  description:
    "Astronomical data reduction, photometry, and light curve analysis tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}