import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import ServiceWorker from "@/components/ServiceWorker";
import { SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "@/lib/site";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  // metadataBase makes every relative URL below resolve absolutely, which crawlers and
  // social scrapers require -- relative Open Graph images are simply dropped.
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — what should this cost in Egypt?`,
    // Per-product pages set their own title; this frames it consistently.
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: [
    "Egypt prices",
    "Egypt tourist prices",
    "how much does water cost in Egypt",
    "Egypt scam prices",
    "Cairo prices",
    "Hurghada prices",
    "Sharm El-Sheikh prices",
    "Sahel prices",
    "أسعار مصر",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: `${SITE_NAME} — what should this cost in Egypt?`,
    description: SITE_DESCRIPTION,
    url: SITE_URL,
    locale: "en",
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} — what should this cost in Egypt?`,
    description: SITE_DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  manifest: "/manifest.json",
  appleWebApp: { capable: true, title: "Egypt Prices", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  // Emitted before stylesheets load, so a browser never gets a chance to decide the page
  // is light-only and apply its own force-dark filter.
  colorScheme: "light dark",
  themeColor: "#0284c7",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        {children}
        <ServiceWorker />
      </body>
    </html>
  );
}
