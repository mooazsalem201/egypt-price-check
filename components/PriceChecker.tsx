"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Fuse from "fuse.js";
import ProductCard from "./ProductCard";
import { usePersisted } from "@/lib/usePersisted";
import {
  CURRENCIES,
  CURRENCY_GROUPS,
  FALLBACK_RATES,
  getRates,
  type CurrencyCode,
} from "@/lib/currency";
import type { Zone } from "@/lib/pricing";
import type { Product } from "@/lib/types";

interface Props {
  products: Product[];
  zones: Zone[];
}

const ZONE_KEY = "zone-v1";
const CURRENCY_KEY = "currency-v1";

export default function PriceChecker({ products, zones }: Props) {
  const [query, setQuery] = useState("");
  const [rates, setRates] = useState<Record<string, number>>(FALLBACK_RATES);

  const isKnownZone = useCallback((id: string) => zones.some((z) => z.id === id), [zones]);
  const isKnownCurrency = useCallback(
    (code: string) => CURRENCIES.some((c) => c.code === code),
    [],
  );

  const [zoneId, setZoneId] = usePersisted(ZONE_KEY, zones[0].id, isKnownZone);
  const [currency, setCurrency] = usePersisted<CurrencyCode>(
    CURRENCY_KEY,
    "EUR",
    isKnownCurrency,
  );

  useEffect(() => {
    getRates().then(setRates);
  }, []);

  const zone = zones.find((z) => z.id === zoneId) ?? zones[0];

  // Tourists type "water", not "Mineral Water 1.5L", so aliases are weighted as highly
  // as the display name.
  const fuse = useMemo(
    () =>
      new Fuse(products, {
        keys: [
          { name: "name", weight: 2 },
          { name: "aliases", weight: 2 },
          { name: "name_ar", weight: 1 },
          { name: "source.product", weight: 0.5 },
        ],
        threshold: 0.4,
        ignoreLocation: true,
      }),
    [products],
  );

  const results = query.trim() ? fuse.search(query.trim()).map((r) => r.item) : products;

  return (
    <div className="mx-auto max-w-2xl px-4 pb-16">
      <header className="pt-6 pb-4">
        <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-50">
          What should this cost?
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Fair prices for Egypt, adjusted for where you are.
        </p>
      </header>

      {/* Zone first: every price below depends on it. */}
      <section aria-labelledby="zone-heading" className="mb-4">
        <h2
          id="zone-heading"
          className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
        >
          Where are you?
        </h2>
        <div className="flex flex-wrap gap-2">
          {zones.map((z) => (
            <button
              key={z.id}
              type="button"
              onClick={() => setZoneId(z.id)}
              aria-pressed={z.id === zoneId}
              className={`rounded-full px-4 py-2.5 text-sm font-medium transition ${
                z.id === zoneId
                  ? "bg-sky-600 text-white shadow"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              }`}
            >
              {z.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{zone.note}</p>
      </section>

      {/* A dropdown rather than pills: 46 currencies as buttons would fill a phone
          screen, and a native select is the fastest control to operate one-handed. */}
      <section className="mb-5">
        <label
          htmlFor="currency"
          className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
        >
          Show prices in
        </label>
        <select
          id="currency"
          value={currency}
          onChange={(event) => setCurrency(event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base
                     focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200
                     dark:border-slate-600 dark:bg-slate-800 dark:text-slate-50"
        >
          {CURRENCY_GROUPS.map((group) => (
            <optgroup key={group} label={group}>
              {CURRENCIES.filter((c) => c.group === group).map((c) => (
                <option key={c.code} value={c.code}>
                  {c.label} ({c.code})
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </section>

      <div className="sticky top-0 z-10 -mx-4 bg-slate-50/90 px-4 py-3 backdrop-blur dark:bg-slate-950/90">
        <label htmlFor="search" className="sr-only">
          Search for a product
        </label>
        <input
          id="search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search: water, coke, chips…"
          className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-4 text-lg
                     focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200
                     dark:border-slate-600 dark:bg-slate-800 dark:text-slate-50"
        />
      </div>

      <div className="mt-4 space-y-4">
        {results.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500 dark:border-slate-700 dark:text-slate-400">
            Nothing matches &ldquo;{query}&rdquo;. Try &ldquo;water&rdquo; or
            &ldquo;chips&rdquo;.
          </p>
        ) : (
          results.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              zone={zone}
              currency={currency}
              rates={rates}
            />
          ))
        )}
      </div>
    </div>
  );
}
