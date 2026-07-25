/**
 * EGP -> home currency conversion.
 *
 * Cell service at the pyramids and along the North Coast is unreliable, so rates are
 * cached in localStorage and the app falls back to rates baked in at build time. A tourist
 * holding a bottle of water needs a number now, not a spinner.
 */

export interface Currency {
  code: string;
  label: string;
  /** Region heading, used to group the picker. */
  group: string;
}

/**
 * Egypt's visitors are not only European. The list covers the Gulf and African
 * neighbours alongside the usual European and North American source markets, grouped so
 * the picker stays navigable on a phone.
 */
export const CURRENCIES: Currency[] = [
  { code: "EUR", label: "Euro", group: "Popular" },
  { code: "USD", label: "US Dollar", group: "Popular" },
  { code: "GBP", label: "British Pound", group: "Popular" },
  { code: "EGP", label: "Egyptian Pound", group: "Popular" },
  { code: "CHF", label: "Swiss Franc", group: "Europe" },
  { code: "PLN", label: "Polish Zloty", group: "Europe" },
  { code: "CZK", label: "Czech Koruna", group: "Europe" },
  { code: "SEK", label: "Swedish Krona", group: "Europe" },
  { code: "NOK", label: "Norwegian Krone", group: "Europe" },
  { code: "DKK", label: "Danish Krone", group: "Europe" },
  { code: "RUB", label: "Russian Ruble", group: "Europe" },
  { code: "TRY", label: "Turkish Lira", group: "Europe" },
  { code: "UAH", label: "Ukrainian Hryvnia", group: "Europe" },
  { code: "CAD", label: "Canadian Dollar", group: "Americas" },
  { code: "BRL", label: "Brazilian Real", group: "Americas" },
  { code: "MXN", label: "Mexican Peso", group: "Americas" },
  { code: "SAR", label: "Saudi Riyal", group: "Middle East" },
  { code: "AED", label: "UAE Dirham", group: "Middle East" },
  { code: "KWD", label: "Kuwaiti Dinar", group: "Middle East" },
  { code: "QAR", label: "Qatari Riyal", group: "Middle East" },
  { code: "BHD", label: "Bahraini Dinar", group: "Middle East" },
  { code: "OMR", label: "Omani Rial", group: "Middle East" },
  { code: "JOD", label: "Jordanian Dinar", group: "Middle East" },
  { code: "ILS", label: "Israeli Shekel", group: "Middle East" },
  { code: "LBP", label: "Lebanese Pound", group: "Middle East" },
  { code: "ZAR", label: "South African Rand", group: "Africa" },
  { code: "NGN", label: "Nigerian Naira", group: "Africa" },
  { code: "KES", label: "Kenyan Shilling", group: "Africa" },
  { code: "MAD", label: "Moroccan Dirham", group: "Africa" },
  { code: "TND", label: "Tunisian Dinar", group: "Africa" },
  { code: "DZD", label: "Algerian Dinar", group: "Africa" },
  { code: "LYD", label: "Libyan Dinar", group: "Africa" },
  { code: "SDG", label: "Sudanese Pound", group: "Africa" },
  { code: "GHS", label: "Ghanaian Cedi", group: "Africa" },
  { code: "ETB", label: "Ethiopian Birr", group: "Africa" },
  { code: "TZS", label: "Tanzanian Shilling", group: "Africa" },
  { code: "UGX", label: "Ugandan Shilling", group: "Africa" },
  { code: "JPY", label: "Japanese Yen", group: "Asia-Pacific" },
  { code: "CNY", label: "Chinese Yuan", group: "Asia-Pacific" },
  { code: "INR", label: "Indian Rupee", group: "Asia-Pacific" },
  { code: "AUD", label: "Australian Dollar", group: "Asia-Pacific" },
  { code: "NZD", label: "NZ Dollar", group: "Asia-Pacific" },
  { code: "KRW", label: "South Korean Won", group: "Asia-Pacific" },
  { code: "SGD", label: "Singapore Dollar", group: "Asia-Pacific" },
  { code: "THB", label: "Thai Baht", group: "Asia-Pacific" },
  { code: "MYR", label: "Malaysian Ringgit", group: "Asia-Pacific" },
];

export type CurrencyCode = string;

export const CURRENCY_GROUPS: string[] = [
  ...new Set(CURRENCIES.map((c) => c.group)),
];

/**
 * Rates per 1 EGP, snapshotted from open.er-api.com at build time. Used when the device
 * is offline with nothing cached. Approximate by design -- a few percent of drift never
 * changes a fair/overcharged verdict.
 */
const FALLBACK_RATES: Record<string, number> = {
  EUR: 0.017105,
  USD: 0.019483,
  GBP: 0.014624,
  EGP: 1,
  CHF: 0.015907,
  PLN: 0.073896,
  CZK: 0.413118,
  SEK: 0.189287,
  NOK: 0.18664,
  DKK: 0.12761,
  RUB: 1.526284,
  TRY: 0.922006,
  UAH: 0.873059,
  CAD: 0.027426,
  BRL: 0.098862,
  MXN: 0.341089,
  SAR: 0.073063,
  AED: 0.071553,
  KWD: 0.006027,
  QAR: 0.07092,
  BHD: 0.007326,
  OMR: 0.007491,
  JOD: 0.013814,
  ILS: 0.059766,
  LBP: 1743.765437,
  ZAR: 0.327757,
  NGN: 26.672518,
  KES: 2.522898,
  MAD: 0.182745,
  TND: 0.057463,
  DZD: 2.596468,
  LYD: 0.124959,
  SDG: 9.946068,
  GHS: 0.227055,
  ETB: 3.129375,
  TZS: 51.47443,
  UGX: 73.240159,
  JPY: 3.187527,
  CNY: 0.132135,
  INR: 1.880626,
  AUD: 0.027893,
  NZD: 0.033686,
  KRW: 28.50818,
  SGD: 0.025143,
  THB: 0.656434,
  MYR: 0.079728,
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
 * snapshot. Never throws and never leaves the caller without numbers.
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
  const rate = rates[currency] ?? FALLBACK_RATES[currency] ?? 1;
  return egp * rate;
}

/**
 * Format a converted amount for display.
 *
 * Intl handles symbol placement and each currency's conventions -- yen and won have no
 * minor unit, Gulf dinars have three. The decimal count is chosen by magnitude so small
 * European amounts stay readable (EUR 0.28, not EUR 0) while large ones in weaker
 * currencies do not become a wall of digits (NGN 160, not NGN 160.34).
 */
export function formatMoney(amount: number, currency: CurrencyCode): string {
  const decimals = amount < 10 ? 2 : 0;
  try {
    return new Intl.NumberFormat("en", {
      style: "currency",
      currency,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(amount);
  } catch {
    // Unknown code on an old engine: show the number with the code appended.
    return `${amount.toFixed(decimals)} ${currency}`;
  }
}

export { FALLBACK_RATES };
