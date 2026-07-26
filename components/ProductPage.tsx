"use client";

import { useCallback, useEffect, useState } from "react";
import ProductCard from "./ProductCard";
import { usePersisted } from "@/lib/usePersisted";
import {
  CURRENCIES,
  CURRENCY_GROUPS,
  FALLBACK_RATES,
  getRates,
  type CurrencyCode,
} from "@/lib/currency";
import { priceBands, type Zone } from "@/lib/pricing";
import type { Product } from "@/lib/types";

interface Props {
  product: Product;
  zones: Zone[];
}

const ZONE_KEY = "zone-v1";
const CURRENCY_KEY = "currency-v1";

export default function ProductPage({ product, zones }: Props) {
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

  return (
    <>
      <h1 className="mb-1 text-2xl font-black tracking-tight text-slate-900 dark:text-slate-50">
        {product.name} price in Egypt
      </h1>
      <p className="mb-5 text-sm text-slate-600 dark:text-slate-400">
        A {product.name} costs about <strong>{product.baseline_egp} EGP</strong> in an
        Egyptian supermarket. Kiosks and tourist areas charge more — here is what counts
        as fair where you are.
      </p>

      {/* Same compact pair as the home page. Wrapped pills cost four rows on a phone, and
          both selects stay at 16px so iOS does not zoom the viewport on focus. */}
      <div className="mb-5 flex flex-wrap gap-2">
        <div className="min-w-[9rem] flex-1">
          <label htmlFor="zone" className="sr-only">
            Where are you?
          </label>
          <select
            id="zone"
            value={zoneId}
            onChange={(event) => setZoneId(event.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-base
                       focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200
                       dark:border-slate-600 dark:bg-slate-800 dark:text-slate-50"
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                📍 {z.label}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[9rem] flex-1">
          <label htmlFor="currency" className="sr-only">
            Show prices in
          </label>
          <select
            id="currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-base
                       focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200
                       dark:border-slate-600 dark:bg-slate-800 dark:text-slate-50"
          >
            {CURRENCY_GROUPS.map((group) => (
              <optgroup key={group} label={group}>
                {CURRENCIES.filter((c) => c.group === group).map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code} — {c.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </div>

      <ProductCard
        product={product}
        zone={zone}
        currency={currency}
        rates={rates}
        linkToDetail={false}
      />

      {/* Every region in one table. Useful in itself, and it is the concrete text a
          search engine can actually match against a query like "water price hurghada". */}
      <section className="mt-8">
        <h2 className="mb-3 text-lg font-bold text-slate-900 dark:text-slate-50">
          {product.name} price by area
        </h2>
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-slate-100 dark:bg-slate-800">
              <tr>
                <th scope="col" className="p-3 text-left font-semibold">Area</th>
                <th scope="col" className="p-3 text-right font-semibold">Fair price</th>
                <th scope="col" className="p-3 text-right font-semibold">Too much</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((z) => {
                const bands = priceBands(product.baseline_egp, z);
                return (
                  <tr key={z.id} className="border-t border-slate-200 dark:border-slate-700">
                    <th scope="row" className="p-3 text-left font-medium">
                      {z.label}
                    </th>
                    <td className="p-3 text-right tabular-nums">
                      {Math.round(bands.fairLow)}–{Math.round(bands.fairHigh)} EGP
                    </td>
                    <td className="p-3 text-right tabular-nums text-rose-700 dark:text-rose-400">
                      over {Math.round(bands.highMax)} EGP
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          Supermarket baseline from Carrefour Egypt, verified {product.updated}. Regional
          markups are estimates.
        </p>
      </section>
    </>
  );
}
