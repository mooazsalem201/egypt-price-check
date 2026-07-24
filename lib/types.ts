export interface ProductSource {
  store: string;
  product: string;
  url: string;
  size: string;
}

export interface Product {
  id: string;
  name: string;
  name_ar: string;
  category: string;
  baseline_egp: number;
  aliases: string[];
  source: ProductSource;
  /** Month the baseline was last verified, e.g. "2026-07". */
  updated: string;
}
