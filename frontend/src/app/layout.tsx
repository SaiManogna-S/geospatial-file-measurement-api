import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope, Syne } from "next/font/google";
import { AppShell } from "@/components/shell/AppShell";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
});

const ibm = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-ibm",
});

export const metadata: Metadata = {
  title: "TerraMetric — Precision in every coordinate",
  description:
    "Geospatial workspace for measuring polygon area and line length from KML and Shapefile datasets.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${syne.variable} ${manrope.variable} ${ibm.variable} antialiased`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
