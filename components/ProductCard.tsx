"use client";

import { useState } from "react";
import Link from "next/link";
import ProductImage from "./ProductImage";
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
  /** False on the product's own page, where linking to itself is pointless. */
  linkToDetail?: boolean;
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

export default function ProductCard({
  product,
  zone,
  currency,
  rates,
  linkToDetail = true,
}: Props) {
  const [asked, setAsked] = useState("");

  const bands = priceBands(product.baseline_egp, zone);
  const askedNumber = Number.parseFloat(asked);
  const hasAsked = Number.isFinite(askedNumber) && askedNumber > 0;
  const verdict = hasAsked ? judgePrice(askedNumber, product.baseline_egp, zone) : null;

  const money = (egp: number) => formatMoney(convert(egp, currency, rates), currency);
  const showEgp = currency !== "EGP";

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      {/* The photo is the fastest way to confirm this is the item in your hand -- brands
          and packaging differ, and so do their fair prices. */}
      <header className="mb-3 flex items-start gap-3">
        {product.image && (
          <ProductImage src={product.image} alt={product.source.product} />
        )}
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50">
            {linkToDetail ? (
              // Links the card to its own page. Without them the per-product pages are
              // orphans that only the sitemap knows about, which crawlers weight poorly.
              <Link href={`/price/${product.id}`} className="hover:underline">
                {product.name}
              </Link>
            ) : (
              product.name
            )}
          </h2>
          {/* The exact brand the price was taken from. "Local water 600ml" alone leaves a
              tourist unable to tell whether the bottle in their hand is the one priced. */}
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {product.source.product}
          </p>
          {/* bdi rather than dir="rtl" on the block: the latter right-aligns the line, so
              the Arabic drifts to the far edge away from the English name it belongs to.
              bdi keeps the line left-aligned while still rendering the Arabic correctly. */}
          <p className="text-sm text-slate-500 dark:text-slate-400">
            <bdi lang="ar">{product.name_ar}</bdi>
          </p>
        </div>
      </header>

      {/* Price bands: the headline answer, readable without any input. */}
      {/* The EGP figure sits beside the converted one so a tourist knows what to actually
          hand over. When EGP *is* the chosen currency it would just repeat itself. */}
      <dl className="space-y-1.5">
        <Band
          tone="fair"
          term="Fair"
          value={`${money(bands.fairLow)} – ${money(bands.fairHigh)}`}
          egp={showEgp ? `${Math.round(bands.fairLow)}–${Math.round(bands.fairHigh)} EGP` : ""}
        />
        <Band
          tone="high"
          term="Pricey"
          value={`up to ${money(bands.highMax)}`}
          egp={showEgp ? `up to ${Math.round(bands.highMax)} EGP` : ""}
        />
        <Band
          tone="over"
          term="Walk away"
          value={`over ${money(bands.highMax)}`}
          egp={showEgp ? `over ${Math.round(bands.highMax)} EGP` : ""}
        />
      </dl>

      {/* Optional price check. Purely local arithmetic -- nothing is sent anywhere. */}
      <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-700">
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
            className="w-24 rounded-xl border border-slate-300 px-3 py-2.5 text-base tabular-nums
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
            {/* Only on the worst verdict, and worded for pressure rather than for a price
                disagreement -- telling someone to ring a hotline over a few pounds would be
                absurd and would waste a line meant for people who actually need it. */}
            {verdict === "overcharged" && (
              <p className="mt-2 text-xs">
                Being pressured, followed, or refused your change? Tourism hotline{" "}
                <a href="tel:19654" className="font-bold underline underline-offset-2">
                  19654
                </a>{" "}
                · Tourist Police{" "}
                <a href="tel:126" className="font-bold underline underline-offset-2">
                  126
                </a>
              </p>
            )}
          </div>
        )}

        {/* Shown only once a verdict exists. As static text it repeated on all 41 cards,
            which is where reassurance turns into noise -- and it matters at the moment
            someone has actually typed a price, not before. */}
        {verdict && (
          <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
            Worked out on your phone — nothing is sent anywhere.
          </p>
        )}
      </div>

      <footer className="mt-3 space-y-1 text-xs text-slate-400 dark:text-slate-500">
        <p>
          Baseline {product.baseline_egp} EGP · verified {product.updated}
          {zone.source === "estimate" && " · area markup is an estimate"}
        </p>
        {/* The app asks for trust in a number; linking the shop listings makes that
            number checkable instead. */}
        {product.sources && product.sources.length > 0 && (
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>Check the price:</span>
            {product.sources.map((source) => (
              <a
                key={source.store}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                title={`${source.product} — ${source.price_egp} EGP`}
                className="underline decoration-dotted underline-offset-2 hover:text-sky-600 dark:hover:text-sky-400"
              >
                {source.store} {source.price_egp} EGP
                {/* Some stores have no per-product page, so the link lands on the aisle
                    the price was read from. Saying so beats letting it look broken. */}
                {source.link_kind === "category" && " (aisle)"}
              </a>
            ))}
          </p>
        )}
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
  // "Fair" is the answer someone came for; the other two are context for judging a quote,
  // so they sit a step quieter rather than competing with it.
  const emphasis =
    tone === "fair"
      ? "text-lg font-bold text-slate-900 dark:text-slate-50"
      : "text-base font-semibold text-slate-600 dark:text-slate-300";
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
      <dt className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-400">
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden="true" />
        {term}
      </dt>
      <dd className="ml-auto text-right">
        <span className={`tabular-nums ${emphasis}`}>{value}</span>
        {egp && (
          <span className="ml-2 text-sm tabular-nums text-slate-500 dark:text-slate-400">
            {egp}
          </span>
        )}
      </dd>
    </div>
  );
}
