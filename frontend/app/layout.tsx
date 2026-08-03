import type { Metadata, Viewport } from "next";
import { Inter, Instrument_Serif } from "next/font/google";

import "./globals.css";
import { Providers } from "./providers";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const display = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Nomad — your itinerary, when travel changes",
    template: "%s · Nomad",
  },
  description:
    "Planning is easy. Travel changes. Nomad is a real-time travel companion that rewrites your itinerary when the weather turns, the train is late, or your feet give out.",
  openGraph: {
    title: "Nomad — your itinerary, when travel changes",
    description:
      "A travel companion that adapts your plan to what's actually happening.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf8f5" },
    { media: "(prefers-color-scheme: dark)", color: "#0d1117" },
  ],
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${sans.variable} ${display.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
