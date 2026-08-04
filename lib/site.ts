/**
 * Canonical site configuration.
 *
 * Absolute URLs are required for canonical tags, sitemaps, Open Graph images and
 * structured data -- relative paths are ignored or misresolved by crawlers and social
 * scrapers. Set NEXT_PUBLIC_SITE_URL in the host's environment when the domain changes;
 * everything else derives from it, so a domain move needs one edit.
 */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://egyptprice.com"
).replace(/\/$/, "");

export const SITE_NAME = "Egypt Price Check";

export const SITE_DESCRIPTION =
  "What should it cost in Egypt? Fair prices for water, soft drinks, snacks and " +
  "sunscreen, adjusted for the region you are in and shown in your own currency. " +
  "Check what you are being quoted before you pay.";

/** Absolute URL for a site-relative path. */
export function absolute(path: string): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
