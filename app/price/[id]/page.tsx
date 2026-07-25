import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import ProductPage from "@/components/ProductPage";
import { ProductJsonLd } from "@/components/StructuredData";
import productsData from "@/data/products.json";
import zonesData from "@/data/zones.json";
import { absolute, SITE_NAME } from "@/lib/site";
import { priceBands, type Zone } from "@/lib/pricing";
import type { Product } from "@/lib/types";

const products = productsData as Product[];
const zones = zonesData as Zone[];

/**
 * One static page per product.
 *
 * Search intent here is specific -- people type "how much is a coke in egypt", not
 * "egypt prices" -- and a single page cannot rank for sixteen different products at
 * once. Each of these carries its own title, description and structured data.
 */
export function generateStaticParams() {
  return products.map((product) => ({ id: product.id }));
}

// Next 15+ passes params as a Promise. Destructuring it synchronously yields undefined,
// so every lookup here silently missed and the page fell back to the layout's metadata.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const product = products.find((p) => p.id === id);
  if (!product) return {};

  const cairo = zones[0];
  const bands = priceBands(product.baseline_egp, cairo);
  const title = `${product.name} price in Egypt — what should it cost?`;
  const description =
    `A ${product.name} costs about ${product.baseline_egp} EGP in an Egyptian supermarket. ` +
    `A fair kiosk price is ${Math.round(bands.fairLow)}–${Math.round(bands.fairHigh)} EGP; ` +
    `above ${Math.round(bands.highMax)} EGP you are being overcharged. ` +
    `Prices adjusted for tourist areas and shown in your own currency.`;

  return {
    title,
    description,
    alternates: { canonical: absolute(`/price/${product.id}`) },
    openGraph: {
      title,
      description,
      url: absolute(`/price/${product.id}`),
      siteName: SITE_NAME,
      type: "article",
      images: product.image ? [{ url: absolute(product.image) }] : undefined,
    },
    twitter: {
      card: "summary",
      title,
      description,
      images: product.image ? [absolute(product.image)] : undefined,
    },
  };
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = products.find((p) => p.id === id);
  if (!product) notFound();

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto max-w-2xl px-4 pb-16 pt-6">
        <nav className="mb-4 text-sm">
          <Link
            href="/"
            className="text-sky-700 underline underline-offset-2 dark:text-sky-400"
          >
            ← All prices
          </Link>
        </nav>
        <ProductJsonLd product={product} zone={zones[0]} />
        <ProductPage product={product} zones={zones} />
      </div>
    </main>
  );
}
