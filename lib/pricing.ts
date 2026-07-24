/**
 * Fair-price maths for Egyptian tourist zones.
 *
 * The baseline is a normal Cairo supermarket price. Kiosks legitimately charge more
 * than a supermarket, and resort areas legitimately charge more than Cairo -- so a
 * verdict is only meaningful relative to *where the tourist is standing*. The same
 * 35 EGP quote is a rip-off in Cairo and completely fair in Sahel.
 */

export type Verdict = "fair" | "high" | "overcharged";

export interface Zone {
  id: string;
  label: string;
  /** Short plain-language hint shown under the zone picker. */
  note: string;
  multiplier: number;
  /** "measured" comes from scraped regional data; "estimate" is a judgement call. */
  source: "measured" | "estimate";
}

export interface PriceBands {
  /** Bottom of the fair range: baseline adjusted for the zone. */
  fairLow: number;
  /** Top of the fair range -- normal kiosk convenience markup. */
  fairHigh: number;
  /** Above this is overcharging rather than an expensive-but-real price. */
  highMax: number;
}

/** Kiosks charge more than supermarkets even at a fair price. */
const KIOSK_MARKUP = 1.25;
/** Beyond this multiple of the zone-adjusted baseline, it is a tourist price. */
const OVERCHARGE_THRESHOLD = 1.6;

/**
 * Compute the fair / high / overcharged boundaries for a product in a zone.
 *
 * @param baselineEgp Normal Cairo supermarket price, in EGP.
 * @param zone The zone the tourist is buying in.
 */
export function priceBands(baselineEgp: number, zone: Zone): PriceBands {
  if (!Number.isFinite(baselineEgp) || baselineEgp <= 0) {
    throw new Error(`baselineEgp must be a positive number, got ${baselineEgp}`);
  }
  if (!Number.isFinite(zone.multiplier) || zone.multiplier <= 0) {
    throw new Error(`zone.multiplier must be positive, got ${zone.multiplier}`);
  }

  const adjusted = baselineEgp * zone.multiplier;
  return {
    fairLow: round2(adjusted),
    fairHigh: round2(adjusted * KIOSK_MARKUP),
    highMax: round2(adjusted * OVERCHARGE_THRESHOLD),
  };
}

/** Classify a quoted price against the bands for a product and zone. */
export function judgePrice(
  askedEgp: number,
  baselineEgp: number,
  zone: Zone,
): Verdict {
  const bands = priceBands(baselineEgp, zone);
  if (askedEgp <= bands.fairHigh) return "fair";
  if (askedEgp <= bands.highMax) return "high";
  return "overcharged";
}

/**
 * What the tourist should counter-offer: the top of the fair range, which is a price
 * a kiosk will actually accept rather than an unrealistic supermarket price.
 */
export function counterOffer(baselineEgp: number, zone: Zone): number {
  return Math.round(priceBands(baselineEgp, zone).fairHigh);
}

/** How many times over the fair price a quote is, for phrasing the warning. */
export function overchargeFactor(
  askedEgp: number,
  baselineEgp: number,
  zone: Zone,
): number {
  return round2(askedEgp / priceBands(baselineEgp, zone).fairLow);
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
