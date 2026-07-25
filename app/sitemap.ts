import type { MetadataRoute } from "next";
import productsData from "@/data/products.json";
import { absolute } from "@/lib/site";
import type { Product } from "@/lib/types";

const products = productsData as Product[];

/**
 * Static sitemap covering the home page and every per-product page.
 *
 * lastModified comes from each product's own "verified" month rather than the build
 * date, so a rebuild that changed nothing does not tell crawlers the content is new.
 */
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const productPages = products.map((product) => ({
    url: absolute(`/price/${product.id}`),
    lastModified: new Date(`${product.updated}-01`),
    changeFrequency: "monthly" as const,
    priority: 0.8,
  }));

  return [
    {
      url: absolute("/"),
      lastModified: new Date(),
      changeFrequency: "weekly" as const,
      priority: 1,
    },
    ...productPages,
  ];
}
