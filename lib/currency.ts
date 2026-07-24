/**
 * EGP -> home currency conversion.
 *
 * Cell service at the pyramids and in the Sahel strip is unreliable, so rates are cached
 * in localStorage and the app falls back to a rate baked in at build time. A tourist
 * holding a bottle of water needs a number now, not a spinner.
 */

export const CURRENCIES = [
  { code: "EUR", symbol: "€", label: "Euro" },
  { code: "USD", symbol: "$", label: "US Dollar" },
  { code: "GBP", symbol: "£", label: "British Pound" },
  { code: "EGP", symbol: "E£", label: "Egyptian Pound" },
] as const;

export type CurrencyCode = (typeof CURRENCIES)[number]["code"];

/**
 * Rates per 1 EGP, refreshed at build time from open.er-api.com. Used when the device is
 * offline and nothing is cached. Approximate by design -- a few percent drift never
 * changes a fair/overcharged verdict.
 */
const FALLBACK_RATES: Record<CurrencyCode, number> = {
  EGP: 1,
  USD: 0.0207,
  EUR: 0.0191,
  GBP: 0.0163,
};

const CACHE_KEY = "egp-rates-v1";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const API = "https://open.er-api.com/v6/latest/EGP";

interface CachedRates {
  rates: Record<string, number>;
  fetchedAt: number;
}

function readCache(): CachedRates | null {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as CachedRates) : null;
  } catch {
    return null;
  }
}

/**
 * Best available rates: fresh cache, else network, else stale cache, else the build-time
 * fallback. Never throws and never leaves the caller without numbers.
 */
export async function getRates(): Promise<Record<string, number>> {
  const cached = readCache();
  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
    return cached.rates;
  }

  try {
    const response = await fetch(API, { signal: AbortSignal.timeout(4000) });
    if (!response.ok) throw new Error(`rates HTTP ${response.status}`);
    const data = (await response.json()) as { rates?: Record<string, number> };
    if (!data.rates) throw new Error("rates missing from response");

    try {
      localStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ rates: data.rates, fetchedAt: Date.now() } satisfies CachedRates),
      );
    } catch {
      // Private browsing or a full quota -- the rates still work for this session.
    }
    return data.rates;
  } catch {
    // Offline or slow: stale rates beat no rates.
    return cached?.rates ?? FALLBACK_RATES;
  }
}

/** Convert EGP to the chosen currency using the supplied rate table. */
export function convert(
  egp: number,
  currency: CurrencyCode,
  rates: Record<string, number>,
): number {
  const rate = rates[currency] ?? FALLBACK_RATES[currency];
  return egp * rate;
}

/** Format a converted amount, keeping small foreign values readable (€0.28, not €0). */
export function formatMoney(amount: number, currency: CurrencyCode): string {
  const symbol = CURRENCIES.find((c) => c.code === currency)?.symbol ?? currency;
  if (currency === "EGP") return `${Math.round(amount)} EGP`;
  const decimals = amount < 10 ? 2 : 0;
  return `${symbol}${amount.toFixed(decimals)}`;
}

export { FALLBACK_RATES };
