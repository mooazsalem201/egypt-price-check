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
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crosscheck import ranked_matches  # noqa: E402
from elfar import search as elfar_search  # noqa: E402
from seed_products import CATALOGUE, OUT, size_value  # noqa: E402
from spinneys import browser  # noqa: E402
from spinneys import search as spinneys_search  # noqa: E402
from talabat import search as talabat_search  # noqa: E402


# How far down the ranking to look for a working link before giving up on a store.
MAX_CANDIDATES = 4

# Spinneys is slow and intermittently times out under a long run. Without a retry a
# transient failure silently costs that product its link, which looks identical to the
# store genuinely not stocking the item -- eight of them vanished that way in one run.
SEARCH_ATTEMPTS = 3
RETRY_PAUSE_S = 5


def search_with_retry(finder, keyword, instance, needs_browser, label, product_id):
    """Run a store search, retrying transient failures before giving up."""
    for attempt in range(1, SEARCH_ATTEMPTS + 1):
        try:
            return finder(keyword, instance) if needs_browser else finder(keyword)
        except Exception as exc:  # noqa: BLE001
            if attempt == SEARCH_ATTEMPTS:
                print(f"  !! {product_id} @ {label}: {str(exc)[:60]} (after {attempt} tries)",
                      file=sys.stderr)
                return []
            time.sleep(RETRY_PAUSE_S)
    return []

# These SPAs return HTTP 200 with a shell for any URL and render "not found" client-side,
# so status codes tell us nothing -- the page has to be rendered to know if it is real.
NOT_FOUND_MARKERS = ("not found", "oops", "\u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f")


# How far a store's price may sit from the Carrefour baseline before the listing is
# assumed to be a different product rather than a different price. Generous on purpose:
# chains genuinely differ, and the goal is to reject "Nestle 600ml Carton at 97.95 EGP
# beside a 6.50 bottle", not to hide honest disagreement.
MAX_PRICE_RATIO = 3.0


def price_is_plausible(candidate, baseline_egp: float) -> bool:
    """Whether a candidate could be the same product, judged by price alone.

    Name-based rules keep missing new phrasings -- "Pack of 12" was handled, then "24
    Pieces", then "Carton". A ratio test catches the whole class regardless of wording.
    """
    if baseline_egp <= 0 or candidate.unit_price_egp <= 0:
        return False
    ratio = candidate.unit_price_egp / baseline_egp
    return 1 / MAX_PRICE_RATIO <= ratio <= MAX_PRICE_RATIO


# How far a link's size may sit from the baseline product's size. The item's own
# size_range is deliberately wide (30-120g covers every chocolate bar), so it admits an
# 80g bar as evidence for a 30g one. This tightens against what was actually priced.
MAX_SIZE_RATIO = 1.4


def size_matches_baseline(candidate, baseline_size: str) -> bool:
    """Whether a candidate is the same size as the product the baseline came from."""
    want, got = size_value(baseline_size), size_value(candidate.size)
    if want is None or got is None:
        return True  # nothing to compare; other guards still apply
    ratio = max(want, got) / min(want, got)
    return ratio <= MAX_SIZE_RATIO


def is_same_variant(candidate, item) -> bool:
    """Whether a candidate is genuinely the same thing, not merely the nearest one.

    ranked_matches orders by *closest* size, which is right for price comparison -- a
    2-finger KitKat still tells you something about a 4-finger one. It is wrong for a
    verification link: sending someone to a 12-pack of a different brand when the card
    prices a single bottle reads as the app citing the wrong product. Better no link.
    """
    if item.size_range:
        value = size_value(candidate.size)
        if value is None or not (item.size_range[0] <= value <= item.size_range[1]):
            return False

    # A tourist buys one bottle. Linking a case of twelve is not evidence for the price
    # of one, even though the per-unit maths works out.
    if getattr(candidate, "pack_count", 1) > item.max_pack:
        return False

    if item.exclude and re.search(item.exclude, candidate.name, re.I):
        return False

    return True


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
    added = {"spinneys": 0, "elfar": 0, "talabat": 0}

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

            for label, finder, key, needs_browser in (
                ("Spinneys", spinneys_search, "spinneys", True),
                ("Talabat Mart", talabat_search, "talabat", False),
                ("Mahmoud El Far", elfar_search, "elfar", True),
            ):
                # Talabat is server-rendered, so it takes an HTTP session rather than a
                # browser -- no point launching a page for it.
                found_items = search_with_retry(
                    finder, item.keyword, instance, needs_browser, label, product["id"]
                )
                if not found_items:
                    continue
                ranked = ranked_matches(found_items, item)

                # Publishing a link that 404s is worse than publishing none: the whole
                # point is that a reader can check the price. Listings can reference
                # products that have since been delisted, so each candidate link is
                # loaded and confirmed before being committed.
                found = None
                for candidate in ranked[:MAX_CANDIDATES]:
                    if not candidate.url or not is_same_variant(candidate, item):
                        continue
                    if not size_matches_baseline(candidate, product["source"]["size"]):
                        continue
                    if not price_is_plausible(candidate, product["baseline_egp"]):
                        print(f"     (implausible price, skipping: {label} / {product['id']} "
                              f"@ {candidate.unit_price_egp} vs {product['baseline_egp']})",
                              file=sys.stderr)
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
    print(f"\nadded links -- Spinneys: {added['spinneys']}, "
          f"Talabat: {added['talabat']}, El Far: {added['elfar']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
