import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import ServiceWorker from "@/components/ServiceWorker";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Egypt Price Check — what should this cost?",
  description:
    "Fair prices for water, snacks and everyday items in Egypt, adjusted for where you are and shown in your own currency. Works offline.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, title: "Egypt Prices", statusBarStyle: "default" },
};

export const viewport: Viewport = {
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
