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

from crosscheck import ranked_matches  # noqa: E402
from elfar import search as elfar_search  # noqa: E402
from seed_products import CATALOGUE, OUT, size_value  # noqa: E402
from spinneys import browser  # noqa: E402
from spinneys import search as spinneys_search  # noqa: E402


# How far down the ranking to look for a working link before giving up on a store.
MAX_CANDIDATES = 4

# These SPAs return HTTP 200 with a shell for any URL and render "not found" client-side,
# so status codes tell us nothing -- the page has to be rendered to know if it is real.
NOT_FOUND_MARKERS = ("not found", "oops", "\u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f")


def in_size_range(candidate, item) -> bool:
    """Whether a candidate is genuinely the same variant, not merely the nearest one.

    ranked_matches orders by *closest* size, which is right for price comparison -- a
    2-finger KitKat is still informative about a 4-finger one. It is wrong for a
    verification link: sending someone to a 330ml 24-box when the card prices a single
    600ml bottle looks like an error, not evidence. Better to show no link.
    """
    if not item.size_range:
        return True
    value = size_value(candidate.size)
    return value is not None and item.size_range[0] <= value <= item.size_range[1]


def link_is_live(url: str, browser_instance, timeout_ms: int = 40000) -> bool:
    """Whether a product URL actually renders a product."""
    page = browser_instance.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2800)
        text = page.inner_text("body").lower()
        return len(text) > 200 and not any(m in text for m in NOT_FOUND_MARKERS)
    except Exception:  # noqa: BLE001 - unreachable counts as dead
        return False
    finally:
        page.close()


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
                    ranked = ranked_matches(finder(item.keyword, instance), item)
                except Exception as exc:  # noqa: BLE001 - a missing store is not fatal
                    print(f"  !! {product['id']} @ {label}: {str(exc)[:70]}", file=sys.stderr)
                    continue

                # Publishing a link that 404s is worse than publishing none: the whole
                # point is that a reader can check the price. Listings can reference
                # products that have since been delisted, so each candidate link is
                # loaded and confirmed before being committed.
                found = None
                for candidate in ranked[:MAX_CANDIDATES]:
                    if not candidate.url or not in_size_range(candidate, item):
                        continue
                    if link_is_live(candidate.url, instance):
                        found = candidate
                        break
                    print(f"     (dead link, trying next: {label} / {product['id']})",
                          file=sys.stderr)

                if not found:
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
