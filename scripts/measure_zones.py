"""Measure regional price differences using Seoudi's per-store catalogue.

Every other source prices nationally, so none can answer the question the app's zone
multipliers depend on: does the same bottle cost more in the North Coast than in Cairo?
Seoudi runs a separate catalogue per store, so the same product can be read in both and
compared directly.

Reports only. The multipliers in data/zones.json stay a human decision -- one supermarket
chain is evidence about supermarkets, not proof about kiosks.

    .venv/bin/python scripts/measure_zones.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from seoudi import choose_location, scrape_category  # noqa: E402
from spinneys import browser  # noqa: E402

# Categories the tourist catalogue draws from.
CATEGORIES = ["water", "snacks-sweets"]

# Cairo is the baseline; the rest are the zones the app models.
LOCATIONS = [
    ("Cairo", None, None),
    ("North Coast", None, None),
    ("Giza", None, None),
]

# Products whose names differ only by whitespace/case should still match.
def key(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def main() -> int:
    by_location: dict[str, dict[str, float]] = {}
    labels: dict[str, str] = {}

    with browser() as instance:
        page = instance.new_page()
        for city, area, district in LOCATIONS:
            try:
                chosen_area, chosen_district = choose_location(page, city, area, district)
            except Exception as exc:  # noqa: BLE001
                print(f"  !! {city}: {str(exc)[:70]}", file=sys.stderr)
                continue
            label = f"{city} ({chosen_area}{'/' + chosen_district if chosen_district else ''})"
            labels[city] = label
            prices: dict[str, float] = {}
            for slug in CATEGORIES:
                for product in scrape_category(page, slug, label):
                    # Keep the cheapest listing per product name.
                    k = key(product.name)
                    if k not in prices or product.unit_price_egp < prices[k]:
                        prices[k] = product.unit_price_egp
            by_location[city] = prices
            print(f"  {label:34} {len(prices)} products")
        page.close()

    base = by_location.get("Cairo")
    if not base:
        print("\nno Cairo baseline; cannot compare", file=sys.stderr)
        return 1

    print()
    for city, prices in by_location.items():
        if city == "Cairo":
            continue
        common = sorted(set(base) & set(prices))
        if not common:
            print(f"{city}: no products in common with Cairo")
            continue
        ratios = [prices[k] / base[k] for k in common if base[k] > 0]
        ratios.sort()
        median = ratios[len(ratios) // 2]
        identical = sum(1 for r in ratios if abs(r - 1) < 0.005)
        print(f"=== {labels.get(city, city)} vs Cairo ===")
        print(f"  products compared : {len(common)}")
        print(f"  median ratio      : {median:.3f}")
        print(f"  identical price   : {identical}/{len(ratios)}")
        differing = [(k, base[k], prices[k]) for k in common if abs(prices[k] / base[k] - 1) > 0.02]
        for k, a, c in differing[:6]:
            print(f"    {a:>7.2f} -> {c:>7.2f}  ({c / a:.2f}x)  {k[:46]}")
        if not differing:
            print("    every compared product is priced identically")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
