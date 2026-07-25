import type { MetadataRoute } from "next";
import { absolute } from "@/lib/site";

/**
 * Emitted as a static robots.txt at build time.
 *
 * Everything is public and worth indexing -- there is no user content, no accounts and
 * no private routes -- so the only job here is pointing crawlers at the sitemap.
 */
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/" }],
    sitemap: absolute("/sitemap.xml"),
  };
}
