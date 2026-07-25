export interface ProductSource {
  store: string;
  product: string;
  url: string;
  size: string;
}

/** A shop listing the price can be checked against. */
export interface VerificationSource {
  store: string;
  product: string;
  url: string;
  price_egp: number;
}

export interface Product {
  id: string;
  name: string;
  name_ar: string;
  category: string;
  baseline_egp: number;
  /** Site-relative path to the packaging photo, or "" if none was found. */
  image: string;
  aliases: string[];
  source: ProductSource;
  /** Shop listings backing this price, so a user can check it rather than trust it. */
  sources?: VerificationSource[];
  /** Month the baseline was last verified, e.g. "2026-07". */
  updated: string;
}
