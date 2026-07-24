"use client";

import { useState } from "react";
import {
  counterOffer,
  judgePrice,
  overchargeFactor,
  priceBands,
  type Verdict,
  type Zone,
} from "@/lib/pricing";
import { convert, formatMoney, type CurrencyCode } from "@/lib/currency";
import type { Product } from "@/lib/types";

interface Props {
  product: Product;
  zone: Zone;
  currency: CurrencyCode;
  rates: Record<string, number>;
}

const VERDICT_STYLES: Record<Verdict, { box: string; label: string; icon: string }> = {
  fair: {
    box: "bg-emerald-50 border-emerald-300 text-emerald-900 dark:bg-emerald-950 dark:border-emerald-700 dark:text-emerald-100",
    label: "Fair price",
    icon: "✓",
  },
  high: {
    box: "bg-amber-50 border-amber-300 text-amber-900 dark:bg-amber-950 dark:border-amber-700 dark:text-amber-100",
    label: "High, but not a scam",
    icon: "!",
  },
  overcharged: {
    box: "bg-rose-50 border-rose-300 text-rose-900 dark:bg-rose-950 dark:border-rose-700 dark:text-rose-100",
    label: "Overcharged",
    icon: "✕",
  },
};

export default function ProductCard({ product, zone, currency, rates }: Props) {
  const [asked, setAsked] = useState("");

  const bands = priceBands(product.baseline_egp, zone);
  const askedNumber = Number.parseFloat(asked);
  const hasAsked = Number.isFinite(askedNumber) && askedNumber > 0;
  const verdict = hasAsked ? judgePrice(askedNumber, product.baseline_egp, zone) : null;

  const money = (egp: number) => formatMoney(convert(egp, currency, rates), currency);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="mb-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50">{product.name}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400" dir="rtl" lang="ar">
          {product.name_ar}
        </p>
      </header>

      {/* Price bands: the headline answer, readable without any input. */}
      <dl className="space-y-2">
        <Band
          tone="fair"
          term="Fair"
          value={`${money(bands.fairLow)} – ${money(bands.fairHigh)}`}
          egp={`${Math.round(bands.fairLow)}–${Math.round(bands.fairHigh)} EGP`}
        />
        <Band
          tone="high"
          term="Pricey"
          value={`up to ${money(bands.highMax)}`}
          egp={`up to ${Math.round(bands.highMax)} EGP`}
        />
        <Band
          tone="over"
          term="Walk away"
          value={`over ${money(bands.highMax)}`}
          egp={`over ${Math.round(bands.highMax)} EGP`}
        />
      </dl>

      {/* Optional price check. Purely local arithmetic -- nothing is sent anywhere. */}
      <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-700">
        <label
          htmlFor={`asked-${product.id}`}
          className="block text-sm font-medium text-slate-700 dark:text-slate-300"
        >
          They&rsquo;re asking me…
        </label>
        <div className="mt-2 flex items-center gap-2">
          <input
            id={`asked-${product.id}`}
            type="number"
            inputMode="decimal"
            min="0"
            value={asked}
            onChange={(event) => setAsked(event.target.value)}
            placeholder="0"
            className="w-28 rounded-xl border border-slate-300 px-3 py-3 text-lg tabular-nums
                       focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200
                       dark:border-slate-600 dark:bg-slate-800 dark:text-slate-50"
          />
          <span className="text-lg font-medium text-slate-600 dark:text-slate-400">EGP</span>
        </div>

        {verdict && (
          <div
            role="status"
            className={`mt-3 rounded-xl border-2 p-3 ${VERDICT_STYLES[verdict].box}`}
          >
            <p className="flex items-center gap-2 font-bold">
              <span aria-hidden="true">{VERDICT_STYLES[verdict].icon}</span>
              {VERDICT_STYLES[verdict].label}
            </p>
            {verdict !== "fair" && (
              <p className="mt-1 text-sm">
                That&rsquo;s {overchargeFactor(askedNumber, product.baseline_egp, zone)}× the
                normal {zone.label} price. Offer{" "}
                <strong>{counterOffer(product.baseline_egp, zone)} EGP</strong>
                {verdict === "overcharged" ? " and walk away if refused." : "."}
              </p>
            )}
          </div>
        )}

        <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
          Stays on your phone — nothing is sent anywhere.
        </p>
      </div>

      <footer className="mt-4 text-xs text-slate-400 dark:text-slate-500">
        Baseline {product.baseline_egp} EGP · {product.source.store} · verified{" "}
        {product.updated}
        {zone.source === "estimate" && " · zone markup is an estimate"}
      </footer>
    </article>
  );
}

function Band({
  tone,
  term,
  value,
  egp,
}: {
  tone: "fair" | "high" | "over";
  term: string;
  value: string;
  egp: string;
}) {
  const dot =
    tone === "fair" ? "bg-emerald-500" : tone === "high" ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-400">
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden="true" />
        {term}
      </dt>
      <dd className="text-right">
        <span className="text-lg font-bold tabular-nums text-slate-900 dark:text-slate-50">
          {value}
        </span>
        <span className="ml-2 text-sm tabular-nums text-slate-500 dark:text-slate-400">
          {egp}
        </span>
      </dd>
    </div>
  );
}
