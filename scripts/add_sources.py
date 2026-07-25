"""Attach verification links from other stores to data/products.json.

The app asks a tourist to trust a number. Linking the actual shop listing the price came
from turns that into something checkable -- by the user, and by whoever maintains the
catalogue later. Carrefour is already recorded by the seeder; this adds Spinneys and
Mahmoud El Far.

Prices are never overwritten: Carrefour remains the single baseline, because averaging
across chains that genuinely price differently produces a number matching none of them.
The extra stores are evidence, not input.

    .venv/bin/python scripts/add_sources.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crosscheck import best_match  # noqa: E402
from elfar import search as elfar_search  # noqa: E402
from seed_products import CATALOGUE, OUT  # noqa: E402
from spinneys import browser  # noqa: E402
from spinneys import search as spinneys_search  # noqa: E402


def main() -> int:
    products = json.loads(OUT.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in products}
    catalogue = {item.id: item for item in CATALOGUE}
    added = {"spinneys": 0, "elfar": 0}

    with browser() as instance:
        for product in products:
            item = catalogue.get(product["id"])
            if not item:
                continue

            # Keep Carrefour first: it is the source of the committed baseline.
            sources = [{
                "store": "Carrefour Egypt",
                "product": product["source"]["product"],
                "url": product["source"]["url"],
                "price_egp": product["baseline_egp"],
            }]

            for label, finder, key in (
                ("Spinneys", spinneys_search, "spinneys"),
                ("Mahmoud El Far", elfar_search, "elfar"),
            ):
                try:
                    found = best_match(finder(item.keyword, instance), item)
                except Exception as exc:  # noqa: BLE001 - a missing store is not fatal
                    print(f"  !! {product['id']} @ {label}: {str(exc)[:70]}", file=sys.stderr)
                    continue
                if not found or not found.url:
                    continue
                sources.append({
                    "store": label,
                    "product": found.name,
                    "url": found.url,
                    "price_egp": found.unit_price_egp,
                })
                added[key] += 1

            product["sources"] = sources
            print(f"  {product['id']:20} {len(sources)} source(s)")

    OUT.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nadded links -- Spinneys: {added['spinneys']}, El Far: {added['elfar']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
