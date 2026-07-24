import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export: the whole app is HTML/JS/JSON on a CDN, no server to run or pay for.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
