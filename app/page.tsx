import PriceChecker from "@/components/PriceChecker";
import productsData from "@/data/products.json";
import zonesData from "@/data/zones.json";
import type { Zone } from "@/lib/pricing";
import type { Product } from "@/lib/types";

// Data is imported at build time and inlined into the bundle, so the page needs no
// network at runtime and keeps working offline once cached.
const products = productsData as Product[];
const zones = zonesData as Zone[];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <PriceChecker products={products} zones={zones} />
    </main>
  );
}
